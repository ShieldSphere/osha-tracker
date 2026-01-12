"""
Quick OSHA Data Sync - Efficient incremental update

This script efficiently syncs new/changed records by:
1. Only loading activity_nr keys from DB (not full records)
2. Processing CSV and identifying new records
3. Batch inserting new records
4. Only updating records where key fields have changed

Much faster than full comparison sync.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import csv
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, text
from src.database.connection import get_db_session
from src.database.models import Inspection, Violation
from src.services.sync_service import SOUTHEAST_STATES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MIN_YEAR = 2020


def safe_date(val):
    """Parse date from various formats."""
    if not val:
        return None
    val_str = str(val).strip()
    # Try YYYY-MM-DD
    try:
        return datetime.strptime(val_str[:10], '%Y-%m-%d').date()
    except:
        pass
    # Try MM/DD/YYYY
    try:
        return datetime.strptime(val_str, '%m/%d/%Y').date()
    except:
        pass
    return None


def safe_str(val) -> Optional[str]:
    return str(val).strip() if val else None


def safe_int(val) -> Optional[int]:
    try:
        return int(val) if val else None
    except:
        return None


def safe_float(val) -> float:
    try:
        return float(val) if val else 0.0
    except:
        return 0.0


def quick_sync_inspections(csv_path: str) -> dict:
    """
    Efficiently sync inspections - only insert new records.
    """
    stats = {"total": 0, "new": 0, "skipped_state": 0, "skipped_old": 0, "exists": 0}

    logger.info(f"Quick sync inspections from: {csv_path}")

    # Get existing activity_nr set (fast query)
    with get_db_session() as db:
        existing = set(db.execute(select(Inspection.activity_nr)).scalars().all())
    logger.info(f"Existing inspections in DB: {len(existing):,}")

    # Read CSV and find new records
    new_records = []
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total"] += 1

            activity_nr = row.get('activity_nr', '').strip()
            if not activity_nr:
                continue

            # Skip if exists
            if activity_nr in existing:
                stats["exists"] += 1
                continue

            # Filter by state
            state = row.get('site_state', '').strip().upper()
            if state not in SOUTHEAST_STATES:
                stats["skipped_state"] += 1
                continue

            # Filter by date
            open_date = safe_date(row.get('open_date'))
            if not open_date or open_date.year < MIN_YEAR:
                stats["skipped_old"] += 1
                continue

            # New record
            new_records.append({
                "activity_nr": activity_nr,
                "reporting_id": safe_str(row.get('reporting_id')),
                "state_flag": safe_str(row.get('state_flag')),
                "estab_name": safe_str(row.get('estab_name')) or "Unknown",
                "site_address": safe_str(row.get('site_address')),
                "site_city": safe_str(row.get('site_city')),
                "site_state": safe_str(row.get('site_state')),
                "site_zip": safe_str(row.get('site_zip')),
                "mail_street": safe_str(row.get('mail_street')),
                "mail_city": safe_str(row.get('mail_city')),
                "mail_state": safe_str(row.get('mail_state')),
                "mail_zip": safe_str(row.get('mail_zip')),
                "open_date": open_date,
                "case_mod_date": safe_date(row.get('case_mod_date')),
                "close_conf_date": safe_date(row.get('close_conf_date')),
                "close_case_date": safe_date(row.get('close_case_date')),
                "sic_code": safe_str(row.get('sic_code')),
                "naics_code": safe_str(row.get('naics_code')),
                "insp_type": safe_str(row.get('insp_type')),
                "insp_scope": safe_str(row.get('insp_scope')),
                "why_no_insp": safe_str(row.get('why_no_insp')),
                "owner_type": safe_str(row.get('owner_type')),
                "owner_code": safe_str(row.get('owner_code')),
                "adv_notice": safe_str(row.get('adv_notice')),
                "safety_hlth": safe_str(row.get('safety_hlth')),
                "union_status": safe_str(row.get('union_status')),
                "safety_manuf": safe_str(row.get('safety_manuf')),
                "safety_const": safe_str(row.get('safety_const')),
                "safety_marit": safe_str(row.get('safety_marit')),
                "health_manuf": safe_str(row.get('health_manuf')),
                "health_const": safe_str(row.get('health_const')),
                "health_marit": safe_str(row.get('health_marit')),
                "migrant": safe_str(row.get('migrant')),
                "nr_in_estab": safe_int(row.get('nr_in_estab')),
                "host_est_key": safe_str(row.get('host_est_key')),
            })
            existing.add(activity_nr)  # Prevent duplicates in same file

    logger.info(f"CSV rows: {stats['total']:,}, New to add: {len(new_records):,}")

    # Batch insert new records
    if new_records:
        with get_db_session() as db:
            for i, record in enumerate(new_records):
                db.add(Inspection(**record))
                if (i + 1) % 500 == 0:
                    db.commit()
                    logger.info(f"  Inserted {i + 1:,} / {len(new_records):,}")
            db.commit()
        stats["new"] = len(new_records)

    logger.info(f"Inspections: {stats['new']} new, {stats['exists']} already existed")
    return stats


def quick_sync_violations(csv_path: str) -> dict:
    """
    Efficiently sync violations - only insert new records.
    """
    stats = {"total": 0, "new": 0, "skipped_no_insp": 0, "exists": 0}

    logger.info(f"Quick sync violations from: {csv_path}")

    # Get existing inspection activity_nrs
    with get_db_session() as db:
        inspection_nrs = set(db.execute(select(Inspection.activity_nr)).scalars().all())
    logger.info(f"Inspections in DB: {len(inspection_nrs):,}")

    # Get existing violation keys
    with get_db_session() as db:
        existing_viols = set()
        for v in db.execute(select(Violation.activity_nr, Violation.citation_id)).all():
            existing_viols.add(f"{v[0]}_{v[1]}")
    logger.info(f"Existing violations in DB: {len(existing_viols):,}")

    # Read CSV and find new records
    new_records = []
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total"] += 1

            activity_nr = row.get('activity_nr', '').strip()
            citation_id = row.get('citation_id', '').strip()

            if not activity_nr or not citation_id:
                continue

            # Skip if inspection doesn't exist
            if activity_nr not in inspection_nrs:
                stats["skipped_no_insp"] += 1
                continue

            # Skip if violation exists
            key = f"{activity_nr}_{citation_id}"
            if key in existing_viols:
                stats["exists"] += 1
                continue

            # New record
            new_records.append({
                "activity_nr": activity_nr,
                "citation_id": citation_id,
                "delete_flag": safe_str(row.get('delete_flag')),
                "standard": safe_str(row.get('standard')),
                "viol_type": safe_str(row.get('viol_type')),
                "issuance_date": safe_date(row.get('issuance_date')),
                "abate_date": safe_date(row.get('abate_date')),
                "abate_complete": safe_str(row.get('abate_complete')),
                "current_penalty": safe_float(row.get('current_penalty')),
                "initial_penalty": safe_float(row.get('initial_penalty')),
                "contest_date": safe_date(row.get('contest_date')),
                "final_order_date": safe_date(row.get('final_order_date')),
                "nr_instances": safe_int(row.get('nr_instances')) or 1,
                "nr_exposed": safe_int(row.get('nr_exposed')) or 0,
                "rec": safe_str(row.get('rec')),
                "gravity": safe_str(row.get('gravity')),
                "emphasis": safe_str(row.get('emphasis')),
                "hazcat": safe_str(row.get('hazcat')),
                "fta_insp_nr": safe_str(row.get('fta_insp_nr')),
                "fta_issuance_date": safe_date(row.get('fta_issuance_date')),
                "fta_penalty": safe_float(row.get('fta_penalty')) if row.get('fta_penalty') else None,
                "fta_contest_date": safe_date(row.get('fta_contest_date')),
                "fta_final_order_date": safe_date(row.get('fta_final_order_date')),
                "hazsub1": safe_str(row.get('hazsub1')),
                "hazsub2": safe_str(row.get('hazsub2')),
                "hazsub3": safe_str(row.get('hazsub3')),
                "hazsub4": safe_str(row.get('hazsub4')),
                "hazsub5": safe_str(row.get('hazsub5')),
            })
            existing_viols.add(key)

    logger.info(f"CSV rows: {stats['total']:,}, New to add: {len(new_records):,}")

    # Batch insert new records
    if new_records:
        with get_db_session() as db:
            for i, record in enumerate(new_records):
                db.add(Violation(**record))
                if (i + 1) % 1000 == 0:
                    db.commit()
                    logger.info(f"  Inserted {i + 1:,} / {len(new_records):,}")
            db.commit()
        stats["new"] = len(new_records)

    logger.info(f"Violations: {stats['new']} new, {stats['exists']} already existed")
    return stats


def update_penalty_totals():
    """Update penalty totals for inspections with new violations."""
    logger.info("Updating penalty totals...")

    with get_db_session() as db:
        # Get inspections that have violations but might have outdated totals
        result = db.execute(text("""
            UPDATE inspections SET
                total_current_penalty = COALESCE(v.total_current, 0),
                total_initial_penalty = COALESCE(v.total_initial, 0),
                updated_at = NOW()
            FROM (
                SELECT activity_nr,
                       SUM(current_penalty) as total_current,
                       SUM(initial_penalty) as total_initial
                FROM violations
                GROUP BY activity_nr
            ) v
            WHERE inspections.activity_nr = v.activity_nr
              AND (inspections.total_current_penalty IS DISTINCT FROM COALESCE(v.total_current, 0)
                   OR inspections.total_initial_penalty IS DISTINCT FROM COALESCE(v.total_initial, 0))
        """))
        db.commit()
        logger.info(f"Updated penalty totals")


def main(inspection_csv: str, violation_csv: str):
    logger.info("=" * 60)
    logger.info("QUICK OSHA SYNC")
    logger.info(f"Time: {datetime.now()}")
    logger.info("=" * 60)

    # Sync inspections
    if inspection_csv and Path(inspection_csv).exists():
        logger.info("")
        insp_stats = quick_sync_inspections(inspection_csv)

    # Sync violations
    if violation_csv and Path(violation_csv).exists():
        logger.info("")
        viol_stats = quick_sync_violations(violation_csv)

    # Update penalty totals
    logger.info("")
    update_penalty_totals()

    # Final counts
    logger.info("")
    logger.info("=" * 60)
    with get_db_session() as db:
        from sqlalchemy import func
        total_insp = db.execute(select(func.count(Inspection.id))).scalar()
        total_viol = db.execute(select(func.count(Violation.id))).scalar()
        logger.info(f"Total Inspections: {total_insp:,}")
        logger.info(f"Total Violations: {total_viol:,}")
    logger.info("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3:
        main(sys.argv[1], sys.argv[2])
    else:
        # Auto-find CSVs
        script_dir = Path(__file__).parent
        inspection = None
        violation = None

        for pattern in ["osha_inspection*.csv", "*inspection*.csv"]:
            matches = list(script_dir.glob(pattern))
            if matches:
                inspection = str(max(matches, key=lambda p: p.stat().st_mtime))
                break

        for pattern in ["osha_violation*.csv", "*violation*.csv"]:
            matches = list(script_dir.glob(pattern))
            if matches:
                violation = str(max(matches, key=lambda p: p.stat().st_mtime))
                break

        if inspection and violation:
            logger.info(f"Auto-detected: {inspection}")
            logger.info(f"Auto-detected: {violation}")
            main(inspection, violation)
        else:
            print("Usage: python quick_sync.py <inspection.csv> <violation.csv>")