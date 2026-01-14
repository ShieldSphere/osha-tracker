import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List

from sqlalchemy.orm import Session
from sqlalchemy import select

from src.database.models import Inspection
from src.database.connection import get_db_session
from src.services.osha_client import OSHAClient

logger = logging.getLogger(__name__)

# Target states for sync (Southeast + Texas)
# This limits API calls and keeps database focused on target region
TARGET_STATES = {
    "AL",  # Alabama
    "AR",  # Arkansas
    "FL",  # Florida
    "GA",  # Georgia
    "KY",  # Kentucky
    "LA",  # Louisiana
    "MS",  # Mississippi
    "NC",  # North Carolina
    "SC",  # South Carolina
    "TN",  # Tennessee
    "TX",  # Texas
    "VA",  # Virginia
    "WV",  # West Virginia
}

# Alias for backwards compatibility
SOUTHEAST_STATES = TARGET_STATES


class LogCollector:
    """Collects log messages for returning in API responses."""

    def __init__(self):
        self.messages: List[str] = []

    def log(self, message: str):
        """Add a log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append(f"[{timestamp}] {message}")
        logger.info(message)  # Also log to standard logger

    def error(self, message: str, exc: Exception = None):
        """Add an error message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        error_msg = f"[{timestamp}] ERROR: {message}"
        if exc:
            error_msg += f" - {type(exc).__name__}: {str(exc)}"
        self.messages.append(error_msg)
        logger.error(message)

    def get_logs(self) -> List[str]:
        return self.messages


class SyncService:
    """Service to sync OSHA inspection data to the database."""

    def __init__(self):
        self.osha_client = OSHAClient()

    async def sync_inspections(self, days_back: int = 30, max_requests: int = 2) -> Dict[str, Any]:
        """
        Fetch inspections from OSHA and sync to database.

        Args:
            days_back: Number of days to look back for inspections
            max_requests: Maximum API requests to make (default 3 for Vercel timeout)

        Returns:
            Dictionary with sync statistics and log messages
        """
        logs = LogCollector()
        logs.log(f"Starting OSHA inspection sync (days_back={days_back}, max_requests={max_requests})")

        stats = {
            "fetched": 0,
            "created": 0,
            "updated": 0,
            "skipped_old": 0,
            "skipped_state": 0,
            "errors": 0,
            "logs": [],
        }

        try:
            # Calculate since_date from days_back
            since_date = (datetime.now() - timedelta(days=days_back)).date()
            logs.log(f"Fetching inspections with open_date > {since_date}")

            # Check API key
            from src.config import settings
            if not settings.DOL_API_KEY:
                logs.error("DOL_API_KEY is not configured!")
                stats["logs"] = logs.get_logs()
                return stats

            logs.log(f"DOL API Key configured: {settings.DOL_API_KEY[:8]}...")

            # Fetch inspections from OSHA API
            logs.log(f"Calling OSHA API fetch_all_new_inspections (max {max_requests} requests)...")
            try:
                raw_inspections = await self.osha_client.fetch_all_new_inspections(
                    since_date=since_date,
                    max_requests=max_requests,
                    log_collector=logs  # Pass log collector to client
                )
                stats["fetched"] = len(raw_inspections)
                logs.log(f"API returned {len(raw_inspections)} total inspections")
            except Exception as api_err:
                logs.error(f"API call failed", api_err)
                logs.log(f"Traceback: {traceback.format_exc()}")
                stats["logs"] = logs.get_logs()
                return stats

            if not raw_inspections:
                logs.log("No inspections returned from API - nothing to sync")
                stats["logs"] = logs.get_logs()
                return stats

            # Process each inspection
            logs.log("Processing inspections and saving to database...")
            try:
                with get_db_session() as db:
                    for i, raw in enumerate(raw_inspections):
                        try:
                            created, updated, skip_reason = self._upsert_inspection(db, raw)
                            if created:
                                stats["created"] += 1
                            elif updated:
                                stats["updated"] += 1
                            elif skip_reason == "old":
                                stats["skipped_old"] += 1
                            elif skip_reason == "state":
                                stats["skipped_state"] += 1

                            # Log progress every 100 records
                            if (i + 1) % 100 == 0:
                                logs.log(f"Processed {i + 1}/{len(raw_inspections)} inspections...")

                        except Exception as e:
                            logs.error(f"Error processing inspection {raw.get('activity_nr', 'unknown')}", e)
                            stats["errors"] += 1
            except Exception as db_err:
                logs.error(f"Database error", db_err)
                logs.log(f"Traceback: {traceback.format_exc()}")

            logs.log(
                f"Sync completed: {stats['created']} created, "
                f"{stats['updated']} updated, {stats['skipped_old']} skipped (pre-2020), "
                f"{stats['skipped_state']} skipped (non-SE states), {stats['errors']} errors"
            )

        except Exception as e:
            logs.error(f"Sync failed with unexpected error", e)
            logs.log(f"Traceback: {traceback.format_exc()}")

        stats["logs"] = logs.get_logs()
        return stats

    def _upsert_inspection(
        self, db: Session, raw: Dict[str, Any]
    ) -> Tuple[bool, bool, str]:
        """
        Insert or update an inspection record.

        Only processes inspections from 2020 onwards and in southeast states.

        Returns:
            Tuple of (created, updated, skip_reason) - skip_reason is empty string if not skipped
        """
        parsed = self.osha_client.parse_inspection(raw)
        activity_nr = parsed.get("activity_nr")

        if not activity_nr:
            raise ValueError("Inspection missing activity_nr")

        # Filter: Only accept inspections from 2020 onwards
        open_date = parsed.get("open_date")
        if open_date and open_date.year < 2020:
            return False, False, "old"

        # Filter: Only accept inspections from southeast states
        site_state = parsed.get("site_state")
        if site_state and site_state.upper() not in SOUTHEAST_STATES:
            return False, False, "state"

        # Check if inspection already exists
        existing = db.execute(
            select(Inspection).where(Inspection.activity_nr == activity_nr)
        ).scalar_one_or_none()

        if existing:
            # Update existing record
            updated = False
            for key, value in parsed.items():
                if key != "activity_nr" and getattr(existing, key, None) != value:
                    setattr(existing, key, value)
                    updated = True

            if updated:
                existing.updated_at = datetime.utcnow()

            return False, updated, ""
        else:
            # Create new record
            inspection = Inspection(**parsed)
            db.add(inspection)
            return True, False, ""

    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status and statistics."""
        with get_db_session() as db:
            total = db.query(Inspection).count()

            # Get date range
            oldest = db.query(Inspection).order_by(Inspection.open_date.asc()).first()
            newest = db.query(Inspection).order_by(Inspection.open_date.desc()).first()

            # Get last sync time (most recent updated_at)
            last_updated = db.query(Inspection).order_by(
                Inspection.updated_at.desc()
            ).first()

            # Add 'Z' suffix to indicate UTC time so JavaScript converts to local
            last_sync_utc = None
            if last_updated and last_updated.updated_at:
                last_sync_utc = last_updated.updated_at.isoformat() + "Z"

            return {
                "total_inspections": total,
                "oldest_inspection": oldest.open_date.isoformat() if oldest and oldest.open_date else None,
                "newest_inspection": newest.open_date.isoformat() if newest and newest.open_date else None,
                "last_sync": last_sync_utc,
            }


# Singleton instance
sync_service = SyncService()
