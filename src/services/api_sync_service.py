"""
API-based sync service for fetching NEW OSHA records only.

This service:
1. Queries Supabase for MAX(open_date) to find the most recent inspection
2. Uses DOL API filter_object to only fetch inspections with open_date > that date
3. Fetches violations for new inspections using "in" filter on activity_nr
4. Includes rate limiting guardrails and exponential backoff

For bulk/initial loads, use the CSV-based sync instead.
"""
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert

from src.database.models import Inspection, Violation
from src.database.connection import get_db_session
from src.services.osha_client import OSHAClient, ACTIVITY_NR_BATCH_SIZE

logger = logging.getLogger(__name__)

# Southeast states filter
SOUTHEAST_STATES = {
    "AL", "AR", "FL", "GA", "KY", "LA", "MS", "NC", "SC", "TN", "VA", "WV"
}
MIN_INSPECTION_DATE = date(2023, 1, 1)


class APISyncService:
    """
    Service for syncing new records from the OSHA API.

    Uses server-side filtering to only fetch NEW records since the last sync.
    """

    def __init__(self):
        self.client = OSHAClient()

    def get_max_open_date(self) -> Optional[date]:
        """Query database for the most recent inspection open_date."""
        with get_db_session() as db:
            result = db.execute(
                select(func.max(Inspection.open_date))
            ).scalar()
            return result

    async def sync_new_records(
        self,
        max_requests: int = 50,
        include_violations: bool = True,
    ) -> Dict:
        """
        Sync new inspections and violations from the API.

        Args:
            max_requests: Maximum API requests per run (guardrail)
            include_violations: Whether to fetch violations for new inspections

        Returns:
            Stats dictionary with sync results
        """
        stats = {
            "started_at": datetime.now().isoformat(),
            "max_open_date_before": None,
            "api_inspections_fetched": 0,
            "new_inspections_added": 0,
            "skipped_non_se": 0,
            "skipped_exists": 0,
            "api_violations_fetched": 0,
            "new_violations_added": 0,
            "api_requests_made": 0,
            "errors": [],
        }

        # Step 1: Get the most recent open_date from our database
        max_open_date = self.get_max_open_date()
        stats["max_open_date_before"] = max_open_date.isoformat() if max_open_date else None

        if not max_open_date:
            # No data in database - use 90 days ago as default
            max_open_date = date.today() - timedelta(days=90)
            logger.warning(f"No existing data found, using {max_open_date} as cutoff")
        elif max_open_date < MIN_INSPECTION_DATE:
            max_open_date = MIN_INSPECTION_DATE
            logger.info(f"Using minimum inspection cutoff: {MIN_INSPECTION_DATE}")

        logger.info("=" * 60)
        logger.info("API SYNC: Fetching new records")
        logger.info(f"Most recent open_date in DB: {max_open_date}")
        logger.info(f"Filtering for: SE states only")
        logger.info(f"Max requests: {max_requests}")
        logger.info("=" * 60)

        # Step 2: Fetch inspections with open_date > max_open_date using API filter
        try:
            raw_inspections = await self.client.fetch_all_new_inspections(
                since_date=max_open_date,
                max_requests=max_requests,
            )
            stats["api_inspections_fetched"] = len(raw_inspections)
            stats["api_requests_made"] = self.client.request_count
        except Exception as e:
            logger.error(f"Error fetching inspections: {e}")
            stats["errors"].append(f"Inspection fetch error: {str(e)}")
            return stats

        if not raw_inspections:
            logger.info("No new inspections found from API")
            stats["completed_at"] = datetime.now().isoformat()
            return stats

        logger.info(f"API returned {len(raw_inspections)} inspections with open_date > {max_open_date}")

        # Step 3: Filter and bulk insert new inspections
        candidate_map: Dict[str, Dict] = {}
        for raw in raw_inspections:
            try:
                parsed = self.client.parse_inspection(raw)
                activity_nr = parsed.get("activity_nr")
                if not activity_nr:
                    continue

                open_date = parsed.get("open_date")
                if open_date and open_date < MIN_INSPECTION_DATE:
                    stats["skipped_old"] += 1
                    continue

                # Filter: SE states only
                site_state = (parsed.get("site_state") or "").upper()
                if site_state not in SOUTHEAST_STATES:
                    stats["skipped_non_se"] += 1
                    continue

                parsed["estab_name"] = parsed.get("estab_name") or "Unknown"
                candidate_map[activity_nr] = parsed
            except Exception as e:
                logger.error(f"Error processing inspection: {e}")
                stats["errors"].append(f"Inspection parse error: {str(e)}")

        candidate_inspections = list(candidate_map.values())
        candidate_inspections.sort(key=lambda r: r.get("open_date") or date.min, reverse=True)
        new_activity_nrs: List[str] = []
        if candidate_inspections:
            with get_db_session() as db:
                insert_stmt = (
                    insert(Inspection)
                    .values(candidate_inspections)
                    .on_conflict_do_nothing(index_elements=["activity_nr"])
                    .returning(Inspection.activity_nr)
                )
                inserted = db.execute(insert_stmt).scalars().all()
                new_activity_nrs = inserted

            stats["new_inspections_added"] = len(new_activity_nrs)
            stats["skipped_exists"] = max(len(candidate_inspections) - len(new_activity_nrs), 0)

        logger.info(f"Added {stats['new_inspections_added']} new inspections")

        # Step 4: Fetch violations for new inspections
        if include_violations and new_activity_nrs:
            remaining_requests = max_requests - self.client.request_count
            if remaining_requests <= 0:
                logger.warning("No remaining API requests for violations")
            else:
                logger.info(f"Fetching violations for {len(new_activity_nrs)} new inspections")

                try:
                    raw_violations = await self.client.fetch_all_violations_for_inspections(
                        activity_nrs=new_activity_nrs,
                        max_requests=remaining_requests,
                    )
                    stats["api_violations_fetched"] = len(raw_violations)
                    stats["api_requests_made"] = self.client.request_count
                except Exception as e:
                    logger.error(f"Error fetching violations: {e}")
                    stats["errors"].append(f"Violation fetch error: {str(e)}")
                    raw_violations = []

                # Insert violations in batches using upsert
                violation_records: List[Dict] = []
                for raw in raw_violations:
                    try:
                        parsed = self.client.parse_violation(raw)
                        activity_nr = parsed.get("activity_nr")
                        citation_id = parsed.get("citation_id")

                        if not activity_nr or not citation_id:
                            continue

                        violation_records.append(parsed)
                    except Exception as e:
                        logger.error(f"Error processing violation: {e}")
                        stats["errors"].append(f"Violation parse error: {str(e)}")

                if violation_records:
                    batch_size = 1000
                    with get_db_session() as db:
                        for i in range(0, len(violation_records), batch_size):
                            batch = violation_records[i:i + batch_size]
                            insert_stmt = (
                                insert(Violation)
                                .values(batch)
                                .on_conflict_do_nothing(index_elements=["activity_nr", "citation_id"])
                            )
                            result = db.execute(insert_stmt)
                            stats["new_violations_added"] += result.rowcount or 0

                logger.info(f"Added {stats['new_violations_added']} new violations")

                # Update penalty totals for new inspections
                self._update_penalty_totals(new_activity_nrs)

        stats["completed_at"] = datetime.now().isoformat()
        stats["api_requests_made"] = self.client.request_count

        logger.info("=" * 60)
        logger.info("API SYNC COMPLETE")
        logger.info(f"New inspections: {stats['new_inspections_added']}")
        logger.info(f"New violations: {stats['new_violations_added']}")
        logger.info(f"API requests made: {stats['api_requests_made']}")
        if stats["errors"]:
            logger.warning(f"Errors: {len(stats['errors'])}")
        logger.info("=" * 60)

        return stats

    def _update_penalty_totals(self, activity_nrs: List[str]):
        """Update penalty totals for specified inspections."""
        if not activity_nrs:
            return

        logger.info(f"Updating penalty totals for {len(activity_nrs)} inspections")

        with get_db_session() as db:
            for activity_nr in activity_nrs:
                inspection = db.execute(
                    select(Inspection).where(Inspection.activity_nr == activity_nr)
                ).scalar_one_or_none()

                if inspection:
                    violations = db.execute(
                        select(Violation).where(Violation.activity_nr == activity_nr)
                    ).scalars().all()

                    if violations:
                        inspection.total_current_penalty = sum(
                            v.current_penalty or 0 for v in violations
                        )
                        inspection.total_initial_penalty = sum(
                            v.initial_penalty or 0 for v in violations
                        )

            db.commit()


async def run_api_sync(max_requests: int = 50) -> Dict:
    """Run the API sync service."""
    service = APISyncService()
    return await service.sync_new_records(max_requests=max_requests)


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    max_req = int(sys.argv[1]) if len(sys.argv) > 1 else 50

    print(f"\nRunning API sync (max {max_req} requests)...\n")
    stats = asyncio.run(run_api_sync(max_requests=max_req))

    print(f"\nResults:")
    print(f"  API inspections fetched: {stats['api_inspections_fetched']}")
    print(f"  New inspections added: {stats['new_inspections_added']}")
    print(f"  Skipped (non-SE state): {stats['skipped_non_se']}")
    print(f"  Skipped (already exists): {stats['skipped_exists']}")
    print(f"  API violations fetched: {stats['api_violations_fetched']}")
    print(f"  New violations added: {stats['new_violations_added']}")
    print(f"  Total API requests: {stats['api_requests_made']}")
    if stats['errors']:
        print(f"  Errors: {len(stats['errors'])}")
        for err in stats['errors'][:5]:
            print(f"    - {err}")
