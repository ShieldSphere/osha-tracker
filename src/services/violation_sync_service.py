"""
Violation Sync Service - Smart strategy for tracking new violations on existing inspections.

Key Strategy:
- OSHA issues citations ~6 months after inspection
- We need to watch existing inspections for NEW violations appearing
- API rate limits force us to be selective about which inspections to check
- Prioritize inspections most likely to get new violations
"""
import logging
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func

from src.database.models import Inspection, Violation
from src.database.connection import get_db_session
from src.services.osha_client import OSHAClient
from src.services.sync_service import SOUTHEAST_STATES

logger = logging.getLogger(__name__)


class ViolationSyncService:
    """Service to sync violations for existing inspections."""

    def __init__(self):
        self.osha_client = OSHAClient()

    async def sync_violations_smart(
        self,
        max_inspections_to_check: int = 100,
        rate_limit_delay: float = 3.0  # Increased from 1.2 to match conservative API delay
    ) -> Dict[str, Any]:
        """
        Smart violation sync: Check inspections most likely to have new violations.

        Strategy:
        1. Prioritize inspections opened 3-9 months ago (citation window)
        2. Check inspections with no violations yet
        3. Re-check inspections with violations if they're not "closed"
        4. Skip inspections older than 12 months with violations (unlikely to change)

        Args:
            max_inspections_to_check: Limit to avoid rate limiting
            rate_limit_delay: Seconds between API calls

        Returns:
            Sync statistics
        """
        stats = {
            "inspections_checked": 0,
            "inspections_with_new_violations": 0,
            "new_violations_found": 0,
            "updated_violations": 0,
            "errors": 0,
            "skipped": 0,
        }

        logger.info(f"Starting smart violation sync (max_inspections={max_inspections_to_check})")

        with get_db_session() as db:
            # Get candidate inspections to check
            candidates = self._get_candidate_inspections(db, max_inspections_to_check)
            logger.info(f"Found {len(candidates)} candidate inspections to check for violations")

            for inspection in candidates:
                try:
                    await asyncio.sleep(rate_limit_delay)  # Rate limiting

                    # Fetch violations from API
                    api_violations = await self.osha_client.fetch_violations_for_inspection(
                        inspection.activity_nr
                    )

                    stats["inspections_checked"] += 1

                    if not api_violations:
                        logger.debug(f"No violations found for {inspection.activity_nr}")
                        # Update last check timestamp
                        self._update_last_violation_check(db, inspection)
                        continue

                    # Process violations
                    new_count, updated_count, had_new = await self._process_violations(
                        db, inspection, api_violations
                    )

                    stats["new_violations_found"] += new_count
                    stats["updated_violations"] += updated_count

                    if had_new:
                        stats["inspections_with_new_violations"] += 1
                        logger.info(
                            f"✓ Found {new_count} NEW violations for {inspection.estab_name} "
                            f"(inspection {inspection.activity_nr})"
                        )

                        # Flag inspection with new violations
                        inspection.new_violations_detected = True
                        inspection.new_violations_count = new_count
                        inspection.new_violations_date = datetime.utcnow()

                    # Update inspection last check and penalties
                    self._update_inspection_penalties(db, inspection)
                    self._update_last_violation_check(db, inspection)

                except Exception as e:
                    logger.error(f"Error syncing violations for {inspection.activity_nr}: {e}")
                    stats["errors"] += 1

        logger.info(
            f"Violation sync complete: checked {stats['inspections_checked']}, "
            f"found {stats['new_violations_found']} new violations across "
            f"{stats['inspections_with_new_violations']} inspections"
        )

        return stats

    def _get_candidate_inspections(
        self,
        db: Session,
        limit: int
    ) -> List[Inspection]:
        """
        Get inspections that are most likely to have new violations.

        Priority order:
        1. Inspections opened 3-9 months ago with NO violations yet (highest priority)
        2. Inspections opened 1-12 months ago with violations but case not closed
        3. Inspections never checked for violations (or not checked recently)

        Args:
            db: Database session
            limit: Maximum number to return

        Returns:
            List of Inspection objects
        """
        today = date.today()

        # Date ranges for prioritization
        nine_months_ago = today - timedelta(days=270)
        six_months_ago = today - timedelta(days=180)
        three_months_ago = today - timedelta(days=90)
        one_month_ago = today - timedelta(days=30)
        twelve_months_ago = today - timedelta(days=365)

        # Priority 1: Inspections in citation window (3-9 months) with no violations
        # Filter to southeast states only
        query_priority_1 = (
            select(Inspection)
            .outerjoin(Violation, Inspection.activity_nr == Violation.activity_nr)
            .where(
                and_(
                    Inspection.open_date >= nine_months_ago,
                    Inspection.open_date <= three_months_ago,
                    Inspection.site_state.in_(SOUTHEAST_STATES),
                    Violation.id == None  # No violations yet
                )
            )
            .group_by(Inspection.id)
            .order_by(Inspection.open_date.desc())
            .limit(limit // 2)  # Reserve half the slots for priority 1
        )

        priority_1 = db.execute(query_priority_1).scalars().all()

        # Priority 2: Recent inspections WITH violations but case not closed
        # (might get more violations added) - Southeast states only
        query_priority_2 = (
            select(Inspection)
            .join(Violation, Inspection.activity_nr == Violation.activity_nr)
            .where(
                and_(
                    Inspection.open_date >= twelve_months_ago,
                    Inspection.open_date <= one_month_ago,
                    Inspection.site_state.in_(SOUTHEAST_STATES),
                    or_(
                        Inspection.close_case_date == None,
                        Inspection.close_case_date > six_months_ago
                    )
                )
            )
            .group_by(Inspection.id)
            .order_by(Inspection.open_date.desc())
            .limit(limit // 4)
        )

        priority_2 = db.execute(query_priority_2).scalars().all()

        # Priority 3: Inspections that haven't been checked recently
        # Southeast states only
        thirty_days_ago = today - timedelta(days=30)

        # For now, just fill remaining slots with recent inspections
        remaining_slots = limit - len(priority_1) - len(priority_2)
        if remaining_slots > 0:
            existing_ids = {i.id for i in priority_1 + priority_2}

            query_priority_3 = (
                select(Inspection)
                .where(
                    and_(
                        Inspection.open_date >= twelve_months_ago,
                        Inspection.site_state.in_(SOUTHEAST_STATES),
                        ~Inspection.id.in_(existing_ids) if existing_ids else True
                    )
                )
                .order_by(Inspection.open_date.desc())
                .limit(remaining_slots)
            )

            priority_3 = db.execute(query_priority_3).scalars().all()
        else:
            priority_3 = []

        # Combine and return
        candidates = priority_1 + priority_2 + priority_3
        logger.info(
            f"Selected SE state candidates: {len(priority_1)} priority-1 (citation window, no viols), "
            f"{len(priority_2)} priority-2 (open cases with viols), "
            f"{len(priority_3)} priority-3 (other recent)"
        )

        return candidates

    async def _process_violations(
        self,
        db: Session,
        inspection: Inspection,
        api_violations: List[Dict[str, Any]]
    ) -> Tuple[int, int, bool]:
        """
        Process violations for an inspection.

        Args:
            db: Database session
            inspection: Inspection object
            api_violations: Violations from API

        Returns:
            Tuple of (new_count, updated_count, had_new_violations)
        """
        new_count = 0
        updated_count = 0
        had_new = False

        for api_viol in api_violations:
            citation_id = str(api_viol.get("citation_id", ""))
            if not citation_id:
                continue

            # Check if violation already exists
            existing = db.execute(
                select(Violation).where(
                    and_(
                        Violation.activity_nr == inspection.activity_nr,
                        Violation.citation_id == citation_id
                    )
                )
            ).scalar_one_or_none()

            if existing:
                # Update existing violation if changed
                parsed = self._parse_violation(api_viol, inspection.activity_nr)
                updated = False
                for key, value in parsed.items():
                    if key not in ["activity_nr", "citation_id"] and getattr(existing, key, None) != value:
                        setattr(existing, key, value)
                        updated = True

                if updated:
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
            else:
                # NEW violation found!
                parsed = self._parse_violation(api_viol, inspection.activity_nr)
                new_violation = Violation(**parsed)
                db.add(new_violation)
                new_count += 1
                had_new = True

                logger.info(
                    f"  NEW: Citation {citation_id} - {parsed.get('viol_type')} - "
                    f"${parsed.get('current_penalty', 0):,.2f}"
                )

        if new_count > 0 or updated_count > 0:
            db.commit()

        return new_count, updated_count, had_new

    def _parse_violation(self, raw: Dict[str, Any], activity_nr: str) -> Dict[str, Any]:
        """Parse raw violation data from API."""

        def safe_date(value: Any) -> Optional[date]:
            if not value:
                return None
            if isinstance(value, date):
                return value
            try:
                return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                return None

        def safe_float(value: Any) -> float:
            if value is None:
                return 0.0
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0

        def safe_int(value: Any) -> Optional[int]:
            if value is None:
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        def safe_str(value: Any) -> Optional[str]:
            if value is None:
                return None
            s = str(value).strip()
            return s if s else None

        return {
            "activity_nr": activity_nr,
            "citation_id": str(raw.get("citation_id", "")),
            "standard": safe_str(raw.get("standard")),
            "viol_type": safe_str(raw.get("viol_type")),
            "issuance_date": safe_date(raw.get("issuance_date")),
            "abate_date": safe_date(raw.get("abate_date")),
            "abate_complete": safe_str(raw.get("abate_complete")),
            "current_penalty": safe_float(raw.get("current_penalty")),
            "initial_penalty": safe_float(raw.get("initial_penalty")),
            "contest_date": safe_date(raw.get("contest_date")),
            "final_order_date": safe_date(raw.get("final_order_date")),
            "nr_instances": safe_int(raw.get("nr_instances")),
            "nr_exposed": safe_int(raw.get("nr_exposed")),
            "rec": safe_str(raw.get("rec")),
            "gravity": safe_str(raw.get("gravity")),
            "emphasis": safe_str(raw.get("emphasis")),
            "hazcat": safe_str(raw.get("hazcat")),
        }

    def _update_inspection_penalties(self, db: Session, inspection: Inspection):
        """Recalculate and update inspection penalty totals from violations."""
        result = db.execute(
            select(
                func.sum(Violation.current_penalty),
                func.sum(Violation.initial_penalty)
            ).where(Violation.activity_nr == inspection.activity_nr)
        ).one()

        inspection.total_current_penalty = float(result[0]) if result[0] else 0.0
        inspection.total_initial_penalty = float(result[1]) if result[1] else 0.0
        db.commit()

    def _update_last_violation_check(self, db: Session, inspection: Inspection):
        """Update timestamp for when we last checked this inspection for violations."""
        inspection.last_violation_check = datetime.utcnow()
        inspection.violation_check_count = (inspection.violation_check_count or 0) + 1
        inspection.updated_at = datetime.utcnow()
        db.commit()

    async def sync_violations_for_inspection(
        self,
        activity_nr: str
    ) -> Dict[str, Any]:
        """
        Sync violations for a single specific inspection (on-demand).

        Args:
            activity_nr: Inspection activity number

        Returns:
            Statistics dictionary
        """
        stats = {
            "new_violations": 0,
            "updated_violations": 0,
            "total_violations": 0,
        }

        with get_db_session() as db:
            inspection = db.execute(
                select(Inspection).where(Inspection.activity_nr == activity_nr)
            ).scalar_one_or_none()

            if not inspection:
                raise ValueError(f"Inspection {activity_nr} not found")

            # Fetch from API
            api_violations = await self.osha_client.fetch_violations_for_inspection(activity_nr)
            stats["total_violations"] = len(api_violations)

            if api_violations:
                new_count, updated_count, _ = await self._process_violations(
                    db, inspection, api_violations
                )
                stats["new_violations"] = new_count
                stats["updated_violations"] = updated_count

                # Update penalties
                self._update_inspection_penalties(db, inspection)

        return stats


# Singleton instance
violation_sync_service = ViolationSyncService()