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
from typing import Dict, Any, List, Optional, Tuple, DefaultDict, Set
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func, exists
from collections import defaultdict

from src.database.models import Inspection, Violation
from src.database.connection import get_db_session
from src.services.osha_client import OSHAClient, ACTIVITY_NR_BATCH_SIZE, MAX_RECORDS_PER_REQUEST
from src.services.sync_service import SOUTHEAST_STATES, LogCollector

logger = logging.getLogger(__name__)
MIN_INSPECTION_DATE = date(2023, 1, 1)


class ViolationSyncService:
    """Service to sync violations for existing inspections."""

    def __init__(self):
        self.osha_client = OSHAClient()

    async def sync_violations_smart(
        self,
        max_inspections_to_check: int = 3,  # Default 3 for Vercel timeout
        rate_limit_delay: float = 1.5,  # Reduced for serverless
        days_back: int = 180,
        min_days_between_checks: int = 7,
        max_requests: int = 10,
    ) -> Dict[str, Any]:
        """
        Smart violation sync: Check recent inspections for new violations.

        Strategy:
        1. Only check inspections within the last N days (default 180)
        2. Prioritize inspections with no violations or stale last check
        3. Batch API calls to reduce rate limiting
        4. Keep each run short for Vercel timeouts

        Args:
            max_inspections_to_check: Limit to avoid rate limiting (default 3 for Vercel)
            rate_limit_delay: Seconds between API calls
            days_back: How far back to check inspections (default 180 days)
            min_days_between_checks: Skip inspections checked within this window
            max_requests: Max API requests per run

        Returns:
            Sync statistics with logs
        """
        logs = LogCollector()
        logs.log(f"Starting violation sync (max_inspections={max_inspections_to_check}, delay={rate_limit_delay}s)")
        logs.log(f"Window: last {days_back} days, min_days_between_checks={min_days_between_checks}, max_requests={max_requests}")

        stats = {
            "inspections_checked": 0,
            "inspections_with_new_violations": 0,
            "new_violations_found": 0,
            "updated_violations": 0,
            "errors": 0,
            "skipped": 0,
            "logs": [],
        }

        try:
            with get_db_session() as db:
                # Get candidate inspections to check
                candidates = self._get_candidate_inspections_recent(
                    db,
                    limit=max_inspections_to_check,
                    days_back=days_back,
                    min_days_between_checks=min_days_between_checks,
                )
                logs.log(f"Found {len(candidates)} candidate inspections to check")

                activity_nrs = [c.activity_nr for c in candidates]
                violations_by_activity, processed_activity_nrs = await self._fetch_violations_for_activity_batches(
                    activity_nrs=activity_nrs,
                    max_requests=max_requests,
                    rate_limit_delay=rate_limit_delay,
                    log_collector=logs,
                )

                for inspection in candidates:
                    if inspection.activity_nr not in processed_activity_nrs:
                        stats["skipped"] += 1
                        continue

                    try:
                        api_violations = violations_by_activity.get(inspection.activity_nr, [])
                        stats["inspections_checked"] += 1

                        if not api_violations:
                            logs.log(f"  No violations found for {inspection.activity_nr}")
                            self._update_last_violation_check(db, inspection)
                            continue

                        logs.log(f"  Found {len(api_violations)} violations from API")

                        new_count, updated_count, had_new = await self._process_violations(
                            db, inspection, api_violations
                        )

                        stats["new_violations_found"] += new_count
                        stats["updated_violations"] += updated_count

                        if had_new:
                            stats["inspections_with_new_violations"] += 1
                            logs.log(
                                f"  NEW: {new_count} new violations for {inspection.estab_name}"
                            )

                            inspection.new_violations_detected = True
                            inspection.new_violations_count = new_count
                            inspection.new_violations_date = datetime.utcnow()
                        else:
                            logs.log(f"  No new violations (updated {updated_count})")

                        self._update_inspection_penalties(db, inspection)
                        self._update_last_violation_check(db, inspection)

                    except Exception as e:
                        logs.error(f"Error syncing violations for {inspection.activity_nr}", e)
                        stats["errors"] += 1

            logs.log(
                f"Sync complete: {stats['inspections_checked']} checked, "
                f"{stats['new_violations_found']} new violations"
            )

        except Exception as e:
            logs.error(f"Violation sync failed", e)

        stats["logs"] = logs.get_logs()
        return stats

    def _get_candidate_inspections_recent(
        self,
        db: Session,
        limit: int,
        days_back: int,
        min_days_between_checks: int,
    ) -> List[Inspection]:
        """
        Get recent inspections likely to have new violations.

        Args:
            db: Database session
            limit: Maximum number to return
            days_back: Only check inspections within this window
            min_days_between_checks: Skip inspections checked recently

        Returns:
            List of Inspection objects
        """
        today = date.today()
        cutoff_open = max(today - timedelta(days=days_back), MIN_INSPECTION_DATE)
        check_cutoff = datetime.utcnow() - timedelta(days=min_days_between_checks)

        no_violations = ~exists(
            select(Violation.id).where(Violation.activity_nr == Inspection.activity_nr)
        )

        base_query = (
            select(Inspection)
            .where(
                and_(
                    Inspection.open_date >= cutoff_open,
                    Inspection.site_state.in_(SOUTHEAST_STATES),
                    or_(
                        Inspection.last_violation_check.is_(None),
                        Inspection.last_violation_check < check_cutoff,
                        no_violations,
                    ),
                )
            )
            .order_by(Inspection.open_date.desc())
            .limit(limit)
        )

        candidates = db.execute(base_query).scalars().all()
        logger.info(
            f"Selected SE state candidates: {len(candidates)} within last {days_back} days"
        )
        return candidates

    async def _fetch_violations_for_activity_batches(
        self,
        activity_nrs: List[str],
        max_requests: int,
        rate_limit_delay: float,
        log_collector: Optional[LogCollector] = None,
    ) -> Tuple[DefaultDict[str, List[Dict[str, Any]]], Set[str]]:
        """Fetch violations for activity numbers in batches with pagination."""
        violations_by_activity: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
        processed_activity_nrs: Set[str] = set()

        if not activity_nrs:
            return violations_by_activity, processed_activity_nrs

        batches = [
            activity_nrs[i:i + ACTIVITY_NR_BATCH_SIZE]
            for i in range(0, len(activity_nrs), ACTIVITY_NR_BATCH_SIZE)
        ]

        requests_made = 0
        for batch_num, batch_nrs in enumerate(batches):
            if requests_made >= max_requests:
                break

            offset = 0
            while requests_made < max_requests:
                violations = await self.osha_client.fetch_violations_for_activity_nrs(
                    activity_nrs=batch_nrs,
                    limit=MAX_RECORDS_PER_REQUEST,
                    offset=offset,
                    log_collector=log_collector,
                )
                requests_made += 1

                if not violations:
                    processed_activity_nrs.update(batch_nrs)
                    break

                for raw in violations:
                    activity_nr = str(raw.get("activity_nr", ""))
                    if activity_nr:
                        violations_by_activity[activity_nr].append(raw)

                offset += len(violations)
                if len(violations) < MAX_RECORDS_PER_REQUEST:
                    processed_activity_nrs.update(batch_nrs)
                    break

                await asyncio.sleep(rate_limit_delay)

            if batch_num < len(batches) - 1 and requests_made < max_requests:
                await asyncio.sleep(rate_limit_delay)

        return violations_by_activity, processed_activity_nrs

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
            citation_id = str(api_viol.get("citation_id", "")).lstrip("0") or "0"
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
            "citation_id": str(raw.get("citation_id", "")).lstrip("0") or "0",
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
