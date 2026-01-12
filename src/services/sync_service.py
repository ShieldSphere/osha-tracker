import logging
from datetime import datetime
from typing import Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select

from src.database.models import Inspection
from src.database.connection import get_db_session
from src.services.osha_client import OSHAClient

logger = logging.getLogger(__name__)

# Southeast states to focus on for sync
# This limits API calls and keeps database focused on target region
SOUTHEAST_STATES = {
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
    "VA",  # Virginia
    "WV",  # West Virginia
}


class SyncService:
    """Service to sync OSHA inspection data to the database."""

    def __init__(self):
        self.osha_client = OSHAClient()

    async def sync_inspections(self, days_back: int = 30) -> Dict[str, int]:
        """
        Fetch inspections from OSHA and sync to database.

        Args:
            days_back: Number of days to look back for inspections

        Returns:
            Dictionary with sync statistics
        """
        logger.info(f"Starting OSHA inspection sync (days_back={days_back})")

        stats = {
            "fetched": 0,
            "created": 0,
            "updated": 0,
            "skipped_old": 0,
            "skipped_state": 0,
            "errors": 0,
        }

        try:
            # Fetch inspections from OSHA API
            raw_inspections = await self.osha_client.fetch_all_recent_inspections(
                days_back=days_back
            )
            stats["fetched"] = len(raw_inspections)

            if not raw_inspections:
                logger.info("No inspections found to sync")
                return stats

            # Process each inspection
            with get_db_session() as db:
                for raw in raw_inspections:
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
                    except Exception as e:
                        logger.error(f"Error processing inspection: {e}")
                        stats["errors"] += 1

            logger.info(
                f"Sync completed: {stats['created']} created, "
                f"{stats['updated']} updated, {stats['skipped_old']} skipped (pre-2020), "
                f"{stats['skipped_state']} skipped (non-SE states), {stats['errors']} errors"
            )

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise

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
            logger.debug(f"Skipping inspection {activity_nr} - too old ({open_date.year})")
            return False, False, "old"

        # Filter: Only accept inspections from southeast states
        site_state = parsed.get("site_state")
        if site_state and site_state.upper() not in SOUTHEAST_STATES:
            logger.debug(f"Skipping inspection {activity_nr} - not in southeast ({site_state})")
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
