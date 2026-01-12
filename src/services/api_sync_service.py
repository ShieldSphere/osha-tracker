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

from src.database.models import Inspection, Violation
from src.database.connection import get_db_session
from src.services.osha_client import OSHAClient, ACTIVITY_NR_BATCH_SIZE

logger = logging.getLogger(__name__)

# Southeast states filter
SOUTHEAST_STATES = {
    "AL", "AR", "FL", "GA", "KY", "LA", "MS", "NC", "SC", "TN", "VA", "WV"
}


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

    def get_existing_activity_nrs(self) -> set:
        """Get all existing activity_nr values from database."""
        with get_db_session() as db:
            result = db.execute(select(Inspection.activity_nr)).scalars().all()
            return set(result)

    def get_existing_violation_keys(self) -> set:
        """Get all existing (activity_nr, citation_id) pairs."""
        with get_db_session() as db:
            result = db.execute(
                select(Violation.activity_nr, Violation.citation_id)
            ).all()
            return {f"{r[0]}_{r[1]}" for r in result}

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

        # Step 3: Filter and insert new inspections
        existing_nrs = self.get_existing_activity_nrs()
        new_activity_nrs = []

        with get_db_session() as db:
            for raw in raw_inspections:
                try:
                    parsed = self.client.parse_inspection(raw)
                    activity_nr = parsed.get("activity_nr")

                    if not activity_nr:
                        continue

                    # Skip if already exists
                    if activity_nr in existing_nrs:
                        stats["skipped_exists"] += 1
                        continue

                    # Filter: SE states only
                    site_state = (parsed.get("site_state") or "").upper()
                    if site_state not in SOUTHEAST_STATES:
                        stats["skipped_non_se"] += 1
                        continue

                    # Add new inspection
                    inspection = Inspection(
                        activity_nr=activity_nr,
                        reporting_id=parsed.get("reporting_id"),
                        state_flag=parsed.get("state_flag"),
                        estab_name=parsed.get("estab_name") or "Unknown",
                        site_address=parsed.get("site_address"),
                        site_city=parsed.get("site_city"),
                        site_state=parsed.get("site_state"),
                        site_zip=parsed.get("site_zip"),
                        mail_street=parsed.get("mail_street"),
                        mail_city=parsed.get("mail_city"),
                        mail_state=parsed.get("mail_state"),
                        mail_zip=parsed.get("mail_zip"),
                        open_date=parsed.get("open_date"),
                        case_mod_date=parsed.get("case_mod_date"),
                        close_conf_date=parsed.get("close_conf_date"),
                        close_case_date=parsed.get("close_case_date"),
                        sic_code=parsed.get("sic_code"),
                        naics_code=parsed.get("naics_code"),
                        insp_type=parsed.get("insp_type"),
                        insp_scope=parsed.get("insp_scope"),
                        why_no_insp=parsed.get("why_no_insp"),
                        owner_type=parsed.get("owner_type"),
                        owner_code=parsed.get("owner_code"),
                        adv_notice=parsed.get("adv_notice"),
                        safety_hlth=parsed.get("safety_hlth"),
                        union_status=parsed.get("union_status"),
                        safety_manuf=parsed.get("safety_manuf"),
                        safety_const=parsed.get("safety_const"),
                        safety_marit=parsed.get("safety_marit"),
                        health_manuf=parsed.get("health_manuf"),
                        health_const=parsed.get("health_const"),
                        health_marit=parsed.get("health_marit"),
                        migrant=parsed.get("migrant"),
                        nr_in_estab=parsed.get("nr_in_estab"),
                        host_est_key=parsed.get("host_est_key"),
                        load_dt=parsed.get("load_dt"),
                    )
                    db.add(inspection)
                    existing_nrs.add(activity_nr)
                    new_activity_nrs.append(activity_nr)
                    stats["new_inspections_added"] += 1

                    logger.info(
                        f"NEW: {activity_nr} - {parsed.get('estab_name')} "
                        f"({site_state}) - {parsed.get('open_date')}"
                    )

                except Exception as e:
                    logger.error(f"Error processing inspection: {e}")
                    stats["errors"].append(f"Inspection parse error: {str(e)}")

            db.commit()

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

                # Insert violations
                existing_viol_keys = self.get_existing_violation_keys()

                with get_db_session() as db:
                    for raw in raw_violations:
                        try:
                            parsed = self.client.parse_violation(raw)
                            activity_nr = parsed.get("activity_nr")
                            citation_id = parsed.get("citation_id")

                            if not activity_nr or not citation_id:
                                continue

                            key = f"{activity_nr}_{citation_id}"
                            if key in existing_viol_keys:
                                continue

                            violation = Violation(
                                activity_nr=activity_nr,
                                citation_id=citation_id,
                                delete_flag=parsed.get("delete_flag"),
                                standard=parsed.get("standard"),
                                viol_type=parsed.get("viol_type"),
                                issuance_date=parsed.get("issuance_date"),
                                abate_date=parsed.get("abate_date"),
                                abate_complete=parsed.get("abate_complete"),
                                current_penalty=parsed.get("current_penalty"),
                                initial_penalty=parsed.get("initial_penalty"),
                                contest_date=parsed.get("contest_date"),
                                final_order_date=parsed.get("final_order_date"),
                                nr_instances=parsed.get("nr_instances"),
                                nr_exposed=parsed.get("nr_exposed"),
                                rec=parsed.get("rec"),
                                gravity=parsed.get("gravity"),
                                emphasis=parsed.get("emphasis"),
                                hazcat=parsed.get("hazcat"),
                                fta_insp_nr=parsed.get("fta_insp_nr"),
                                fta_issuance_date=parsed.get("fta_issuance_date"),
                                fta_penalty=parsed.get("fta_penalty"),
                                fta_contest_date=parsed.get("fta_contest_date"),
                                fta_final_order_date=parsed.get("fta_final_order_date"),
                                hazsub1=parsed.get("hazsub1"),
                                hazsub2=parsed.get("hazsub2"),
                                hazsub3=parsed.get("hazsub3"),
                                hazsub4=parsed.get("hazsub4"),
                                hazsub5=parsed.get("hazsub5"),
                            )
                            db.add(violation)
                            existing_viol_keys.add(key)
                            stats["new_violations_added"] += 1

                        except Exception as e:
                            logger.error(f"Error processing violation: {e}")
                            stats["errors"].append(f"Violation parse error: {str(e)}")

                    db.commit()

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
