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

        Important: This function manages DB connections carefully for serverless
        environments - it releases the connection during API calls.

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
            # Step 1: Get candidate inspections (quick DB query, then release connection)
            candidate_data = []
            with get_db_session() as db:
                candidates = self._get_candidate_inspections_recent(
                    db,
                    limit=max_inspections_to_check,
                    days_back=days_back,
                    min_days_between_checks=min_days_between_checks,
                )
                # Extract data before closing session
                for c in candidates:
                    candidate_data.append({
                        "activity_nr": c.activity_nr,
                        "estab_name": c.estab_name,
                    })

            logs.log(f"Found {len(candidate_data)} candidate inspections to check")

            if not candidate_data:
                stats["logs"] = logs.get_logs()
                return stats

            # Step 2: Fetch violations from API (DB connection is released)
            activity_nrs = [c["activity_nr"] for c in candidate_data]
            violations_by_activity, processed_activity_nrs = await self._fetch_violations_for_activity_batches(
                activity_nrs=activity_nrs,
                max_requests=max_requests,
                rate_limit_delay=rate_limit_delay,
                log_collector=logs,
            )

            # Step 3: Process each inspection (new DB connection for saves)
            with get_db_session() as db:
                for candidate in candidate_data:
                    activity_nr = candidate["activity_nr"]
                    estab_name = candidate["estab_name"]

                    if activity_nr not in processed_activity_nrs:
                        stats["skipped"] += 1
                        continue

                    try:
                        # Get the inspection object for updates
                        inspection = db.execute(
                            select(Inspection).where(Inspection.activity_nr == activity_nr)
                        ).scalar_one_or_none()

                        if not inspection:
                            continue

                        api_violations = violations_by_activity.get(activity_nr, [])
                        stats["inspections_checked"] += 1

                        if not api_violations:
                            logs.log(f"  No violations found for {activity_nr}")
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
                            logs.log(f"  NEW: {new_count} new violations for {estab_name}")

                            inspection.new_violations_detected = True
                            inspection.new_violations_count = new_count
                            inspection.new_violations_date = datetime.utcnow()
                        else:
                            logs.log(f"  No new violations (updated {updated_count})")

                        self._update_inspection_penalties(db, inspection)
                        self._update_last_violation_check(db, inspection)

                    except Exception as e:
                        logs.error(f"Error syncing violations for {activity_nr}", e)
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

    async def sync_recent_violations(
        self,
        inspection_days_back: int = 365,
        max_inspections: int = 200,
        max_requests: int = 50,
        rate_limit_delay: float = 1.5,
    ) -> Dict[str, Any]:
        """
        Fetch violations for inspections likely to have new violations.

        Strategy (due to DOL API limitations - no date filtering on violations):
        1. Get inspections from our DB opened in the last N days (default 365)
           that haven't been checked recently or have no violations yet
        2. Batch their activity_nrs and fetch violations from OSHA API
        3. Insert new violations, update existing ones

        OSHA typically issues citations ~6 months after inspection, so we check
        inspections from the past year to catch new violations.

        Note: The DOL API does NOT support filtering violations by date fields
        (issuance_date, load_dt). We must query by activity_nr.

        Important: This function manages DB connections carefully for serverless
        environments - it releases the connection during API calls.

        Args:
            inspection_days_back: Check inspections opened within this window (default 365)
            max_inspections: Maximum inspections to check per run (default 200)
            max_requests: Maximum API requests per run
            rate_limit_delay: Seconds between API calls

        Returns:
            Statistics dictionary with logs
        """
        logs = LogCollector()
        logs.log(f"Starting violations sync (inspection_days_back={inspection_days_back}, max_inspections={max_inspections})")

        stats = {
            "inspections_checked": 0,
            "violations_fetched": 0,
            "violations_inserted": 0,
            "violations_updated": 0,
            "inspections_with_new_violations": 0,
            "errors": 0,
            "logs": [],
        }

        try:
            # Step 1: Get candidate inspections (quick DB query, then release connection)
            cutoff_date = date.today() - timedelta(days=inspection_days_back)
            check_cutoff = datetime.utcnow() - timedelta(days=7)

            candidate_data = []  # Store just the data we need, not ORM objects
            with get_db_session() as db:
                candidates = db.execute(
                    select(Inspection.activity_nr, Inspection.estab_name)
                    .where(
                        and_(
                            Inspection.open_date >= cutoff_date,
                            Inspection.site_state.in_(SOUTHEAST_STATES),
                            or_(
                                Inspection.last_violation_check.is_(None),
                                Inspection.last_violation_check < check_cutoff,
                            ),
                        )
                    )
                    .order_by(Inspection.last_violation_check.asc().nullsfirst())
                    .limit(max_inspections)
                ).all()

                # Extract data before closing session
                for row in candidates:
                    candidate_data.append({
                        "activity_nr": row.activity_nr,
                        "estab_name": row.estab_name,
                    })

            logs.log(f"Found {len(candidate_data)} inspections to check for violations")

            if not candidate_data:
                logs.log("No inspections need checking")
                stats["logs"] = logs.get_logs()
                return stats

            # Step 2: Fetch violations from API (DB connection is released)
            activity_nrs = [c["activity_nr"] for c in candidate_data]
            logs.log(f"Fetching violations for {len(activity_nrs)} inspections...")

            api_violations = await self.osha_client.fetch_all_violations_for_inspections(
                activity_nrs=activity_nrs,
                max_requests=max_requests,
                log_collector=logs,
            )
            stats["violations_fetched"] = len(api_violations)
            logs.log(f"Fetched {len(api_violations)} total violations from API")

            # Group violations by activity_nr
            violations_by_activity: Dict[str, List[Dict[str, Any]]] = {}
            for viol in api_violations:
                activity_nr = str(viol.get("activity_nr", ""))
                if activity_nr:
                    if activity_nr not in violations_by_activity:
                        violations_by_activity[activity_nr] = []
                    violations_by_activity[activity_nr].append(viol)

            # Step 3: Process each inspection (new DB connection for saves)
            with get_db_session() as db:
                for candidate in candidate_data:
                    activity_nr = candidate["activity_nr"]
                    estab_name = candidate["estab_name"]

                    try:
                        stats["inspections_checked"] += 1
                        violations = violations_by_activity.get(activity_nr, [])

                        # Get the inspection object for updates
                        inspection = db.execute(
                            select(Inspection).where(Inspection.activity_nr == activity_nr)
                        ).scalar_one_or_none()

                        if not inspection:
                            continue

                        if violations:
                            new_count, updated_count = self._upsert_violations(
                                db, activity_nr, violations
                            )

                            stats["violations_inserted"] += new_count
                            stats["violations_updated"] += updated_count

                            if new_count > 0:
                                stats["inspections_with_new_violations"] += 1
                                logs.log(f"  {estab_name}: {new_count} new, {updated_count} updated")
                                # Mark inspection as having new violations
                                inspection.new_violations_detected = True
                                inspection.new_violations_count = (inspection.new_violations_count or 0) + new_count
                                inspection.new_violations_date = datetime.utcnow()

                            # Update penalty totals
                            self._update_inspection_penalties(db, inspection)

                        # Update last check timestamp
                        self._update_last_violation_check(db, inspection)

                    except Exception as e:
                        logs.error(f"Error processing {activity_nr}", e)
                        stats["errors"] += 1

            logs.log(
                f"Sync complete: checked {stats['inspections_checked']} inspections, "
                f"found {stats['violations_inserted']} new violations"
            )

        except Exception as e:
            logs.error("Violations sync failed", e)
            stats["errors"] += 1

        stats["logs"] = logs.get_logs()
        return stats

    async def sync_violations_bulk(
        self,
        days_back: int = 180,
        max_requests: int = 100,
    ) -> Dict[str, Any]:
        """
        Bulk fetch violations by issuance_date, then upsert to database.

        This is the efficient approach:
        1. Fetch ALL violations issued in the last N days (paginated, 200 per request)
        2. Bulk upsert to Supabase violations table
        3. Matching to inspections happens via foreign key in DB, not in Python

        Args:
            days_back: How far back to query (default 180 days to account for ~90 day lag)
            max_requests: Maximum API requests per run

        Returns:
            Statistics dictionary with logs
        """
        logs = LogCollector()
        logs.log(f"Starting BULK violation sync (days_back={days_back}, max_requests={max_requests})")

        stats = {
            "violations_fetched": 0,
            "violations_inserted": 0,
            "violations_updated": 0,
            "violations_skipped": 0,
            "inspections_with_new_violations": 0,
            "errors": 0,
            "logs": [],
        }

        try:
            # Step 1: Calculate the date cutoff
            since_date = date.today() - timedelta(days=days_back)
            logs.log(f"Fetching violations with issuance_date > {since_date}")

            # Step 2: Bulk fetch all violations from API
            all_violations = await self.osha_client.fetch_all_violations_by_date(
                since_date=since_date,
                max_requests=max_requests,
                log_collector=logs,
            )
            stats["violations_fetched"] = len(all_violations)
            logs.log(f"Fetched {len(all_violations)} total violations from API")

            if not all_violations:
                logs.log("No violations found")
                stats["logs"] = logs.get_logs()
                return stats

            # Step 3: Group violations by activity_nr for batch processing
            violations_by_activity: Dict[str, List[Dict[str, Any]]] = {}
            for viol in all_violations:
                activity_nr = str(viol.get("activity_nr", ""))
                if activity_nr:
                    if activity_nr not in violations_by_activity:
                        violations_by_activity[activity_nr] = []
                    violations_by_activity[activity_nr].append(viol)

            logs.log(f"Violations span {len(violations_by_activity)} unique inspections")

            # Step 4: Bulk upsert to database
            with get_db_session() as db:
                # Get all activity_nrs that exist in our inspections table (ONE query)
                all_activity_nrs = list(violations_by_activity.keys())
                existing_activity_nrs = set(
                    row[0] for row in db.execute(
                        select(Inspection.activity_nr).where(
                            Inspection.activity_nr.in_(all_activity_nrs)
                        )
                    ).all()
                )
                logs.log(f"Found {len(existing_activity_nrs)} matching inspections in our database")

                # Filter to only violations for inspections we track
                relevant_activity_nrs = [a for a in all_activity_nrs if a in existing_activity_nrs]
                skipped_activity_nrs = [a for a in all_activity_nrs if a not in existing_activity_nrs]
                for a in skipped_activity_nrs:
                    stats["violations_skipped"] += len(violations_by_activity[a])

                if not relevant_activity_nrs:
                    logs.log("No violations match tracked inspections")
                    stats["logs"] = logs.get_logs()
                    return stats

                # Fetch ALL existing violations for relevant activity_nrs in ONE query
                logs.log(f"Fetching existing violations for {len(relevant_activity_nrs)} inspections...")
                existing_violations = db.execute(
                    select(Violation.activity_nr, Violation.citation_id).where(
                        Violation.activity_nr.in_(relevant_activity_nrs)
                    )
                ).all()

                # Build a set of (activity_nr, citation_id) for fast lookup
                # Normalize citation_id by stripping leading zeros to match API format
                existing_keys: Set[Tuple[str, str]] = set()
                for row in existing_violations:
                    normalized_citation = str(row[1]).lstrip("0") or "0"
                    existing_keys.add((row[0], normalized_citation))
                logs.log(f"Found {len(existing_keys)} existing violations in database")

                # Process violations - determine inserts vs updates
                new_violations = []
                updates_to_apply: List[Dict[str, Any]] = []
                inspections_updated: Set[str] = set()

                for activity_nr in relevant_activity_nrs:
                    for api_viol in violations_by_activity[activity_nr]:
                        citation_id = str(api_viol.get("citation_id", "")).lstrip("0") or "0"
                        if not citation_id:
                            continue

                        key = (activity_nr, citation_id)
                        parsed = self._parse_violation(api_viol, activity_nr)

                        if key in existing_keys:
                            # Existing - queue for bulk update
                            updates_to_apply.append(parsed)
                        else:
                            # New violation - add to batch insert
                            new_violations.append(Violation(**parsed))
                            inspections_updated.add(activity_nr)

                # Bulk insert new violations
                if new_violations:
                    logs.log(f"Inserting {len(new_violations)} new violations...")
                    db.add_all(new_violations)
                    db.commit()
                    stats["violations_inserted"] = len(new_violations)
                    logs.log(f"Inserted {len(new_violations)} new violations")

                # Bulk update existing violations
                if updates_to_apply:
                    logs.log(f"Updating {len(updates_to_apply)} existing violations...")
                    from sqlalchemy.dialects.postgresql import insert

                    # Use PostgreSQL upsert (ON CONFLICT DO UPDATE)
                    stmt = insert(Violation).values(updates_to_apply)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['activity_nr', 'citation_id'],
                        set_={
                            'standard': stmt.excluded.standard,
                            'viol_type': stmt.excluded.viol_type,
                            'issuance_date': stmt.excluded.issuance_date,
                            'abate_date': stmt.excluded.abate_date,
                            'abate_complete': stmt.excluded.abate_complete,
                            'current_penalty': stmt.excluded.current_penalty,
                            'initial_penalty': stmt.excluded.initial_penalty,
                            'contest_date': stmt.excluded.contest_date,
                            'final_order_date': stmt.excluded.final_order_date,
                            'nr_instances': stmt.excluded.nr_instances,
                            'nr_exposed': stmt.excluded.nr_exposed,
                            'rec': stmt.excluded.rec,
                            'gravity': stmt.excluded.gravity,
                            'emphasis': stmt.excluded.emphasis,
                            'hazcat': stmt.excluded.hazcat,
                            'updated_at': datetime.utcnow(),
                        }
                    )
                    db.execute(stmt)
                    db.commit()
                    stats["violations_updated"] = len(updates_to_apply)
                    logs.log(f"Updated {len(updates_to_apply)} existing violations")

                # Update inspection metadata for those with new violations
                if inspections_updated:
                    logs.log(f"Updating {len(inspections_updated)} inspections with new violations...")
                    for activity_nr in inspections_updated:
                        try:
                            inspection = db.execute(
                                select(Inspection).where(Inspection.activity_nr == activity_nr)
                            ).scalar_one_or_none()

                            if inspection:
                                inspection.new_violations_detected = True
                                inspection.new_violations_date = datetime.utcnow()
                                self._update_inspection_penalties(db, inspection)
                                self._update_last_violation_check(db, inspection)

                        except Exception as e:
                            logs.error(f"Error updating inspection {activity_nr}", e)

                stats["inspections_with_new_violations"] = len(inspections_updated)

            logs.log(
                f"Bulk sync complete: {stats['violations_inserted']} inserted, "
                f"{stats['violations_updated']} already existed, {stats['violations_skipped']} skipped (no matching inspection)"
            )

        except Exception as e:
            logs.error("Bulk violation sync failed", e)
            stats["errors"] += 1

        stats["logs"] = logs.get_logs()
        return stats

    def _upsert_violations(
        self,
        db: Session,
        activity_nr: str,
        api_violations: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        """
        Insert or update violations for an inspection.

        Args:
            db: Database session
            activity_nr: Inspection activity number
            api_violations: List of violation records from API

        Returns:
            Tuple of (new_count, updated_count)
        """
        new_count = 0
        updated_count = 0

        for api_viol in api_violations:
            citation_id = str(api_viol.get("citation_id", "")).lstrip("0") or "0"
            if not citation_id:
                continue

            # Check if violation already exists
            existing = db.execute(
                select(Violation).where(
                    and_(
                        Violation.activity_nr == activity_nr,
                        Violation.citation_id == citation_id
                    )
                )
            ).scalar_one_or_none()

            parsed = self._parse_violation(api_viol, activity_nr)

            if existing:
                # Update existing violation if anything changed
                updated = False
                for key, value in parsed.items():
                    if key not in ["activity_nr", "citation_id"]:
                        current_value = getattr(existing, key, None)
                        if current_value != value:
                            setattr(existing, key, value)
                            updated = True

                if updated:
                    existing.updated_at = datetime.utcnow()
                    updated_count += 1
            else:
                # Insert new violation
                new_violation = Violation(**parsed)
                db.add(new_violation)
                new_count += 1

        if new_count > 0 or updated_count > 0:
            db.commit()

        return new_count, updated_count


# Singleton instance
violation_sync_service = ViolationSyncService()
