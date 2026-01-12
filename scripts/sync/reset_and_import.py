"""
Reset database and import fresh data from CSV files.

This script:
1. Truncates inspections, violations, and companies tables
2. Imports inspections from CSV (SE states, 2020+ only)
3. Imports violations from CSV (only for imported inspections)
4. Updates penalty totals

Usage:
    python reset_and_import.py osha_inspection5.csv osha_violation13.csv
"""
import csv
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text, select, func

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.connection import get_db_session
from src.database.models import Inspection, Violation, Company
from src.services.sync_service import SOUTHEAST_STATES

MIN_YEAR = 2020


def safe_str(val):
    """Convert to string or None."""
    if not val:
        return None
    s = str(val).strip()
    return s if s else None


def safe_int(val):
    """Convert to int or None."""
    if not val:
        return None
    try:
        return int(val)
    except:
        return None


def safe_float(val):
    """Convert to float or 0."""
    if not val:
        return 0.0
    try:
        return float(val)
    except:
        return 0.0


def safe_date(val):
    """Convert to date or None. Handles YYYY-MM-DD and MM/DD/YYYY formats."""
    if not val:
        return None
    val_str = str(val).strip()
    # Try YYYY-MM-DD format first
    try:
        return datetime.strptime(val_str[:10], '%Y-%m-%d').date()
    except:
        pass
    # Try MM/DD/YYYY format
    try:
        return datetime.strptime(val_str, '%m/%d/%Y').date()
    except:
        pass
    return None


def safe_datetime(val):
    """Convert to datetime or None."""
    if not val:
        return None
    try:
        val_str = str(val).strip()
        # Handle format: "2026-01-08 00:21:57 EST"
        if ' ' in val_str and len(val_str) > 19:
            val_str = val_str[:19]
        # Handle "T" separator
        if 'T' in val_str:
            return datetime.strptime(val_str[:19], '%Y-%m-%dT%H:%M:%S')
        elif len(val_str) >= 19:
            return datetime.strptime(val_str[:19], '%Y-%m-%d %H:%M:%S')
        else:
            return datetime.strptime(val_str[:10], '%Y-%m-%d')
    except:
        return None


def truncate_tables():
    """Truncate all data tables."""
    print("=" * 60)
    print("TRUNCATING TABLES")
    print("=" * 60)

    with get_db_session() as db:
        # Get counts before
        insp_count = db.execute(select(func.count(Inspection.id))).scalar()
        viol_count = db.execute(select(func.count(Violation.id))).scalar()
        comp_count = db.execute(select(func.count(Company.id))).scalar()

        print(f"Current counts:")
        print(f"  Inspections: {insp_count:,}")
        print(f"  Violations: {viol_count:,}")
        print(f"  Companies: {comp_count:,}")

        # Truncate in order (respecting foreign keys)
        print("\nTruncating tables...")
        db.execute(text("TRUNCATE TABLE companies CASCADE"))
        db.execute(text("TRUNCATE TABLE violations CASCADE"))
        db.execute(text("TRUNCATE TABLE inspections CASCADE"))
        db.commit()

        print("Tables truncated successfully!")


def import_inspections(csv_path: str) -> set:
    """
    Import inspections from CSV.
    Returns set of imported activity_nr values.
    """
    print("\n" + "=" * 60)
    print(f"IMPORTING INSPECTIONS FROM: {csv_path}")
    print(f"Filter: SE states only, {MIN_YEAR}+ only")
    print("=" * 60)

    stats = {
        "total": 0,
        "skipped_state": 0,
        "skipped_old": 0,
        "imported": 0,
        "errors": 0
    }

    imported_activity_nrs = set()
    records = []

    # Read and filter CSV
    print("\nReading CSV...")
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)

        for row in reader:
            stats["total"] += 1

            # Filter by state
            state = safe_str(row.get('site_state'))
            if not state or state.upper() not in SOUTHEAST_STATES:
                stats["skipped_state"] += 1
                continue

            # Filter by date
            open_date = safe_date(row.get('open_date'))
            if not open_date or open_date.year < MIN_YEAR:
                stats["skipped_old"] += 1
                continue

            records.append(row)

    print(f"Total rows: {stats['total']:,}")
    print(f"Skipped (non-SE): {stats['skipped_state']:,}")
    print(f"Skipped (pre-{MIN_YEAR}): {stats['skipped_old']:,}")
    print(f"Records to import: {len(records):,}")

    # Import records
    print("\nImporting...")
    with get_db_session() as db:
        batch = []

        for i, row in enumerate(records):
            try:
                activity_nr = safe_str(row.get('activity_nr'))
                if not activity_nr:
                    continue

                inspection = Inspection(
                    activity_nr=activity_nr,
                    reporting_id=safe_str(row.get('reporting_id')),
                    state_flag=safe_str(row.get('state_flag')),
                    estab_name=safe_str(row.get('estab_name')) or 'Unknown',
                    site_address=safe_str(row.get('site_address')),
                    site_city=safe_str(row.get('site_city')),
                    site_state=safe_str(row.get('site_state')),
                    site_zip=safe_str(row.get('site_zip')),
                    mail_street=safe_str(row.get('mail_street')),
                    mail_city=safe_str(row.get('mail_city')),
                    mail_state=safe_str(row.get('mail_state')),
                    mail_zip=safe_str(row.get('mail_zip')),
                    open_date=safe_date(row.get('open_date')),
                    case_mod_date=safe_date(row.get('case_mod_date')),
                    close_conf_date=safe_date(row.get('close_conf_date')),
                    close_case_date=safe_date(row.get('close_case_date')),
                    sic_code=safe_str(row.get('sic_code')),
                    naics_code=safe_str(row.get('naics_code')),
                    insp_type=safe_str(row.get('insp_type')),
                    insp_scope=safe_str(row.get('insp_scope')),
                    why_no_insp=safe_str(row.get('why_no_insp')),
                    owner_type=safe_str(row.get('owner_type')),
                    owner_code=safe_str(row.get('owner_code')),
                    union_status=safe_str(row.get('union_status')),
                    safety_manuf=safe_str(row.get('safety_manuf')),
                    safety_const=safe_str(row.get('safety_const')),
                    safety_marit=safe_str(row.get('safety_marit')),
                    health_manuf=safe_str(row.get('health_manuf')),
                    health_const=safe_str(row.get('health_const')),
                    health_marit=safe_str(row.get('health_marit')),
                    migrant=safe_str(row.get('migrant')),
                    adv_notice=safe_str(row.get('adv_notice')),
                    safety_hlth=safe_str(row.get('safety_hlth')),
                    nr_in_estab=safe_int(row.get('nr_in_estab')),
                    host_est_key=safe_str(row.get('host_est_key')),
                    load_dt=safe_datetime(row.get('ld_dt')),
                )

                batch.append(inspection)
                imported_activity_nrs.add(activity_nr)
                stats["imported"] += 1

                # Batch insert
                if len(batch) >= 500:
                    db.add_all(batch)
                    db.commit()
                    batch = []
                    print(f"  Imported {stats['imported']:,}...")

            except Exception as e:
                stats["errors"] += 1
                if stats["errors"] <= 5:
                    print(f"  Error: {e}")

        # Final batch
        if batch:
            db.add_all(batch)
            db.commit()

    print(f"\nImported: {stats['imported']:,}")
    print(f"Errors: {stats['errors']:,}")

    return imported_activity_nrs


def import_violations(csv_path: str, valid_activity_nrs: set):
    """Import violations from CSV for existing inspections."""
    print("\n" + "=" * 60)
    print(f"IMPORTING VIOLATIONS FROM: {csv_path}")
    print("=" * 60)

    stats = {
        "total": 0,
        "skipped_no_inspection": 0,
        "skipped_old": 0,
        "imported": 0,
        "errors": 0
    }

    records = []

    # Read and filter CSV
    print("\nReading CSV...")
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)

        for row in reader:
            stats["total"] += 1

            # Filter by inspection
            activity_nr = safe_str(row.get('activity_nr'))
            if activity_nr not in valid_activity_nrs:
                stats["skipped_no_inspection"] += 1
                continue

            # Filter by date (optional - violations from 2020+)
            issuance_date = safe_date(row.get('issuance_date'))
            if issuance_date and issuance_date.year < MIN_YEAR:
                stats["skipped_old"] += 1
                continue

            records.append(row)

    print(f"Total rows: {stats['total']:,}")
    print(f"Skipped (no inspection): {stats['skipped_no_inspection']:,}")
    print(f"Skipped (pre-{MIN_YEAR}): {stats['skipped_old']:,}")
    print(f"Records to import: {len(records):,}")

    # Import records
    print("\nImporting...")
    with get_db_session() as db:
        batch = []

        for i, row in enumerate(records):
            try:
                activity_nr = safe_str(row.get('activity_nr'))
                citation_id = safe_str(row.get('citation_id'))

                if not activity_nr or not citation_id:
                    continue

                violation = Violation(
                    activity_nr=activity_nr,
                    citation_id=citation_id,
                    delete_flag=safe_str(row.get('delete_flag')),
                    standard=safe_str(row.get('standard')),
                    viol_type=safe_str(row.get('viol_type')),
                    issuance_date=safe_date(row.get('issuance_date')),
                    abate_date=safe_date(row.get('abate_date')),
                    abate_complete=safe_str(row.get('abate_complete')),
                    current_penalty=safe_float(row.get('current_penalty')),
                    initial_penalty=safe_float(row.get('initial_penalty')),
                    contest_date=safe_date(row.get('contest_date')),
                    final_order_date=safe_date(row.get('final_order_date')),
                    nr_instances=safe_int(row.get('nr_instances')),
                    nr_exposed=safe_int(row.get('nr_exposed')),
                    rec=safe_str(row.get('rec')),
                    gravity=safe_str(row.get('gravity')),
                    emphasis=safe_str(row.get('emphasis')),
                    hazcat=safe_str(row.get('hazcat')),
                    fta_insp_nr=safe_str(row.get('fta_insp_nr')),
                    fta_issuance_date=safe_date(row.get('fta_issuance_date')),
                    fta_penalty=safe_float(row.get('fta_penalty')) if row.get('fta_penalty') else None,
                    fta_contest_date=safe_date(row.get('fta_contest_date')),
                    fta_final_order_date=safe_date(row.get('fta_final_order_date')),
                    hazsub1=safe_str(row.get('hazsub1')),
                    hazsub2=safe_str(row.get('hazsub2')),
                    hazsub3=safe_str(row.get('hazsub3')),
                    hazsub4=safe_str(row.get('hazsub4')),
                    hazsub5=safe_str(row.get('hazsub5')),
                    load_dt=safe_datetime(row.get('load_dt')),
                )

                batch.append(violation)
                stats["imported"] += 1

                # Batch insert
                if len(batch) >= 1000:
                    db.add_all(batch)
                    db.commit()
                    batch = []
                    print(f"  Imported {stats['imported']:,}...")

            except Exception as e:
                stats["errors"] += 1
                if stats["errors"] <= 5:
                    print(f"  Error: {e}")

        # Final batch
        if batch:
            db.add_all(batch)
            db.commit()

    print(f"\nImported: {stats['imported']:,}")
    print(f"Errors: {stats['errors']:,}")


def update_penalties():
    """Update total penalties on inspections from violations."""
    print("\n" + "=" * 60)
    print("UPDATING PENALTY TOTALS")
    print("=" * 60)

    with get_db_session() as db:
        # Get all inspections with violations
        result = db.execute(text("""
            UPDATE inspections i
            SET
                total_current_penalty = COALESCE(v.current_total, 0),
                total_initial_penalty = COALESCE(v.initial_total, 0)
            FROM (
                SELECT
                    activity_nr,
                    SUM(current_penalty) as current_total,
                    SUM(initial_penalty) as initial_total
                FROM violations
                GROUP BY activity_nr
            ) v
            WHERE i.activity_nr = v.activity_nr
        """))
        db.commit()

        # Count inspections with penalties
        with_penalties = db.execute(text("""
            SELECT COUNT(*) FROM inspections
            WHERE total_current_penalty > 0 OR total_initial_penalty > 0
        """)).scalar()

        print(f"Updated {with_penalties:,} inspections with penalty totals")


def main():
    if len(sys.argv) < 3:
        print("Usage: python reset_and_import.py <inspection_csv> <violation_csv>")
        print("Example: python reset_and_import.py osha_inspection5.csv osha_violation13.csv")
        sys.exit(1)

    inspection_csv = sys.argv[1]
    violation_csv = sys.argv[2]

    print("\n" + "=" * 60)
    print("OSHA DATABASE RESET AND IMPORT")
    print(f"Time: {datetime.now()}")
    print("=" * 60)
    print(f"Inspection CSV: {inspection_csv}")
    print(f"Violation CSV: {violation_csv}")
    print(f"SE States: {', '.join(sorted(SOUTHEAST_STATES))}")
    print(f"Min Year: {MIN_YEAR}")

    # Confirm
    response = input("\nThis will DELETE ALL existing data. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        sys.exit(0)

    # Run import
    truncate_tables()
    activity_nrs = import_inspections(inspection_csv)
    import_violations(violation_csv, activity_nrs)
    update_penalties()

    # Summary
    print("\n" + "=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)

    with get_db_session() as db:
        insp_count = db.execute(select(func.count(Inspection.id))).scalar()
        viol_count = db.execute(select(func.count(Violation.id))).scalar()

        total_penalties = db.execute(
            select(func.sum(Inspection.total_current_penalty))
        ).scalar() or 0

        print(f"Total Inspections: {insp_count:,}")
        print(f"Total Violations: {viol_count:,}")
        print(f"Total Penalties: ${total_penalties:,.0f}")


if __name__ == "__main__":
    main()
