"""
Import OSHA inspection and violation data from CSV files.

Filters:
- SE Region: AL, FL, GA, KY, MS, NC, SC, TN
- Plus: TX
- Date range: 2023-01-01 onwards
- Processes most recent first
- Skips existing records (no duplicates)

Usage:
    python -m scripts.import_csv_data [--inspections-only] [--violations-only] [--batch-size 100] [--dry-run]
"""
import sys
import csv
import argparse
from pathlib import Path
from datetime import datetime, date
from typing import Set, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import get_db_session
from src.database.models import Inspection, Violation


# Target states: SE Region + TX
TARGET_STATES = {"AL", "FL", "GA", "KY", "MS", "NC", "SC", "TN", "TX"}

# Minimum date (2023-01-01)
MIN_DATE = date(2023, 1, 1)


def parse_date(date_str: str) -> Optional[date]:
    """Parse date string to date object."""
    if not date_str or date_str.strip() == "":
        return None
    try:
        # Try common formats
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"]:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None
    except Exception:
        return None


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse datetime string."""
    if not dt_str or dt_str.strip() == "":
        return None
    try:
        # Format: "2026-01-14 00:22:00 EST"
        dt_str = dt_str.strip()
        # Remove timezone suffix if present
        for tz in [" EST", " EDT", " CST", " CDT", " PST", " PDT", " UTC"]:
            if dt_str.endswith(tz):
                dt_str = dt_str[:-len(tz)]
                break
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def parse_float(val: str) -> float:
    """Parse float value."""
    if not val or val.strip() == "":
        return 0.0
    try:
        return float(val.strip())
    except (ValueError, TypeError):
        return 0.0


def parse_int(val: str) -> Optional[int]:
    """Parse integer value."""
    if not val or val.strip() == "":
        return None
    try:
        return int(val.strip())
    except (ValueError, TypeError):
        return None


def get_existing_activity_nrs(db, filtered_only: bool = False) -> Set[str]:
    """Get existing activity_nr values from database.

    Args:
        db: Database session
        filtered_only: If True, only return activity_nrs for inspections
                      matching TARGET_STATES and MIN_DATE filters
    """
    print("  Fetching existing inspection activity numbers...")
    if filtered_only:
        results = db.query(Inspection.activity_nr).filter(
            Inspection.site_state.in_(TARGET_STATES),
            Inspection.open_date >= MIN_DATE
        ).all()
    else:
        results = db.query(Inspection.activity_nr).all()
    return {r[0] for r in results}


def normalize_citation_id(citation_id: str) -> str:
    """Normalize citation ID by removing leading zeros from numeric prefix.

    Examples: '01001' -> '1001', '01001A' -> '1001A', '02001' -> '2001'
    """
    if not citation_id:
        return citation_id
    normalized = citation_id.lstrip('0')
    # Handle case where citation is all zeros or empty after stripping
    if not normalized or not normalized[0].isdigit():
        return citation_id
    return normalized


def get_existing_violations(db) -> Set[tuple]:
    """Get all existing (activity_nr, normalized_citation_id) pairs from database."""
    print("  Fetching existing violation keys...")
    results = db.query(Violation.activity_nr, Violation.citation_id).all()
    # Return normalized citation IDs for comparison
    return {(r[0], normalize_citation_id(r[1])) for r in results}


def import_inspections(
    csv_path: str,
    batch_size: int = 100,
    dry_run: bool = False
) -> dict:
    """Import inspections from CSV."""
    stats = {
        "total_rows": 0,
        "filtered_state": 0,
        "filtered_date": 0,
        "skipped_existing": 0,
        "imported": 0,
        "errors": 0,
    }

    print(f"\n{'='*60}")
    print("IMPORTING INSPECTIONS")
    print(f"{'='*60}")
    print(f"Source: {csv_path}")
    print(f"Target states: {', '.join(sorted(TARGET_STATES))}")
    print(f"Min date: {MIN_DATE}")
    print(f"Batch size: {batch_size}")
    print(f"Dry run: {dry_run}")

    # Read all rows and filter
    print("\nReading and filtering CSV...")
    filtered_rows = []

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total_rows"] += 1

            # Filter by state
            state = row.get("site_state", "").strip().upper()
            if state not in TARGET_STATES:
                stats["filtered_state"] += 1
                continue

            # Filter by date (open_date >= 2023-01-01)
            open_date = parse_date(row.get("open_date", ""))
            if not open_date or open_date < MIN_DATE:
                stats["filtered_date"] += 1
                continue

            filtered_rows.append((open_date, row))

    print(f"  Total rows in CSV: {stats['total_rows']:,}")
    print(f"  Filtered by state: {stats['filtered_state']:,}")
    print(f"  Filtered by date: {stats['filtered_date']:,}")
    print(f"  Rows to process: {len(filtered_rows):,}")

    # Sort by date descending (most recent first)
    filtered_rows.sort(key=lambda x: x[0], reverse=True)

    if not filtered_rows:
        print("\nNo rows to import after filtering.")
        return stats

    # Import in batches
    with get_db_session() as db:
        existing_activity_nrs = get_existing_activity_nrs(db)
        print(f"  Existing inspections in DB: {len(existing_activity_nrs):,}")

        batch = []
        for open_date, row in filtered_rows:
            activity_nr = row.get("activity_nr", "").strip()

            # Skip if already exists
            if activity_nr in existing_activity_nrs:
                stats["skipped_existing"] += 1
                continue

            try:
                inspection = Inspection(
                    activity_nr=activity_nr,
                    reporting_id=row.get("reporting_id", "").strip() or None,
                    state_flag=row.get("state_flag", "").strip() or None,
                    estab_name=row.get("estab_name", "").strip()[:255],
                    site_address=row.get("site_address", "").strip()[:255] or None,
                    site_city=row.get("site_city", "").strip()[:100] or None,
                    site_state=row.get("site_state", "").strip().upper()[:2] or None,
                    site_zip=row.get("site_zip", "").strip()[:10] or None,
                    mail_street=row.get("mail_street", "").strip()[:255] or None,
                    mail_city=row.get("mail_city", "").strip()[:100] or None,
                    mail_state=row.get("mail_state", "").strip().upper()[:2] or None,
                    mail_zip=row.get("mail_zip", "").strip()[:10] or None,
                    open_date=open_date,
                    case_mod_date=parse_date(row.get("case_mod_date", "")),
                    close_conf_date=parse_date(row.get("close_conf_date", "")),
                    close_case_date=parse_date(row.get("close_case_date", "")),
                    sic_code=row.get("sic_code", "").strip()[:10] or None,
                    naics_code=row.get("naics_code", "").strip()[:10] or None,
                    insp_type=row.get("insp_type", "").strip()[:10] or None,
                    insp_scope=row.get("insp_scope", "").strip()[:10] or None,
                    why_no_insp=row.get("why_no_insp", "").strip()[:10] or None,
                    owner_type=row.get("owner_type", "").strip()[:50] or None,
                    owner_code=row.get("owner_code", "").strip()[:10] or None,
                    union_status=row.get("union_status", "").strip()[:10] or None,
                    safety_manuf=row.get("safety_manuf", "").strip()[:5] or None,
                    safety_const=row.get("safety_const", "").strip()[:5] or None,
                    safety_marit=row.get("safety_marit", "").strip()[:5] or None,
                    health_manuf=row.get("health_manuf", "").strip()[:5] or None,
                    health_const=row.get("health_const", "").strip()[:5] or None,
                    health_marit=row.get("health_marit", "").strip()[:5] or None,
                    migrant=row.get("migrant", "").strip()[:5] or None,
                    adv_notice=row.get("adv_notice", "").strip()[:10] or None,
                    safety_hlth=row.get("safety_hlth", "").strip()[:10] or None,
                    nr_in_estab=parse_int(row.get("nr_in_estab", "")),
                    host_est_key=row.get("host_est_key", "").strip()[:50] or None,
                    load_dt=parse_datetime(row.get("ld_dt", "")),
                    total_current_penalty=0,  # Will be calculated from violations
                    total_initial_penalty=0,
                )

                batch.append(inspection)
                existing_activity_nrs.add(activity_nr)  # Track to avoid duplicates in same run

                # Commit batch
                if len(batch) >= batch_size:
                    if not dry_run:
                        db.add_all(batch)
                        db.commit()
                    stats["imported"] += len(batch)
                    print(f"  Imported batch: {stats['imported']:,} inspections...")
                    batch = []

            except Exception as e:
                stats["errors"] += 1
                print(f"  ERROR on activity_nr {activity_nr}: {e}")

        # Final batch
        if batch:
            if not dry_run:
                db.add_all(batch)
                db.commit()
            stats["imported"] += len(batch)

    print(f"\n{'='*60}")
    print("INSPECTION IMPORT SUMMARY")
    print(f"{'='*60}")
    print(f"  Skipped (already exist): {stats['skipped_existing']:,}")
    print(f"  Imported: {stats['imported']:,}")
    print(f"  Errors: {stats['errors']:,}")

    return stats


def import_violations(
    csv_path: str,
    batch_size: int = 100,
    dry_run: bool = False
) -> dict:
    """Import violations from CSV (only for inspections that exist in DB)."""
    stats = {
        "total_rows": 0,
        "skipped_no_inspection": 0,
        "skipped_existing": 0,
        "imported": 0,
        "errors": 0,
    }

    print(f"\n{'='*60}")
    print("IMPORTING VIOLATIONS")
    print(f"{'='*60}")
    print(f"Source: {csv_path}")
    print(f"Target states: {', '.join(sorted(TARGET_STATES))}")
    print(f"Min date: {MIN_DATE}")
    print(f"Batch size: {batch_size}")
    print(f"Dry run: {dry_run}")

    with get_db_session() as db:
        # Get FILTERED inspection activity_nrs (only import violations for these)
        # This ensures we only import violations for SE region + TX, 2023+ inspections
        filtered_activity_nrs = get_existing_activity_nrs(db, filtered_only=True)
        print(f"  Filtered inspections in DB (SE+TX, 2023+): {len(filtered_activity_nrs):,}")

        # Get existing violations to skip duplicates
        existing_violations = get_existing_violations(db)
        print(f"  Existing violations in DB: {len(existing_violations):,}")

        # Read and filter CSV
        print("\nReading and processing CSV...")
        batch = []
        penalty_updates = {}  # activity_nr -> (current_sum, initial_sum)

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats["total_rows"] += 1

                activity_nr = row.get("activity_nr", "").strip()
                citation_id_raw = row.get("citation_id", "").strip()
                citation_id_normalized = normalize_citation_id(citation_id_raw)

                # Skip if inspection doesn't match our filters (SE+TX, 2023+)
                if activity_nr not in filtered_activity_nrs:
                    stats["skipped_no_inspection"] += 1
                    continue

                # Skip if violation already exists (compare normalized citation IDs)
                if (activity_nr, citation_id_normalized) in existing_violations:
                    stats["skipped_existing"] += 1
                    continue

                try:
                    current_penalty = parse_float(row.get("current_penalty", ""))
                    initial_penalty = parse_float(row.get("initial_penalty", ""))

                    # Store normalized citation_id to prevent future duplicates
                    violation = Violation(
                        activity_nr=activity_nr,
                        citation_id=citation_id_normalized,
                        delete_flag=row.get("delete_flag", "").strip()[:5] or None,
                        standard=row.get("standard", "").strip()[:50] or None,
                        viol_type=row.get("viol_type", "").strip()[:10] or None,
                        issuance_date=parse_date(row.get("issuance_date", "")),
                        abate_date=parse_date(row.get("abate_date", "")),
                        abate_complete=row.get("abate_complete", "").strip()[:10] or None,
                        current_penalty=current_penalty,
                        initial_penalty=initial_penalty,
                        contest_date=parse_date(row.get("contest_date", "")),
                        final_order_date=parse_date(row.get("final_order_date", "")),
                        nr_instances=parse_int(row.get("nr_instances", "")),
                        nr_exposed=parse_int(row.get("nr_exposed", "")),
                        rec=row.get("rec", "").strip()[:10] or None,
                        gravity=row.get("gravity", "").strip()[:20] or None,
                        emphasis=row.get("emphasis", "").strip()[:50] or None,
                        hazcat=row.get("hazcat", "").strip()[:50] or None,
                        fta_insp_nr=row.get("fta_insp_nr", "").strip()[:20] or None,
                        fta_issuance_date=parse_date(row.get("fta_issuance_date", "")),
                        fta_penalty=parse_float(row.get("fta_penalty", "")),
                        fta_contest_date=parse_date(row.get("fta_contest_date", "")),
                        fta_final_order_date=parse_date(row.get("fta_final_order_date", "")),
                        hazsub1=row.get("hazsub1", "").strip()[:50] or None,
                        hazsub2=row.get("hazsub2", "").strip()[:50] or None,
                        hazsub3=row.get("hazsub3", "").strip()[:50] or None,
                        hazsub4=row.get("hazsub4", "").strip()[:50] or None,
                        hazsub5=row.get("hazsub5", "").strip()[:50] or None,
                        load_dt=parse_datetime(row.get("load_dt", "")),
                    )

                    batch.append(violation)
                    existing_violations.add((activity_nr, citation_id_normalized))  # Track normalized

                    # Track penalty sums for inspection updates
                    if activity_nr not in penalty_updates:
                        penalty_updates[activity_nr] = [0.0, 0.0]
                    penalty_updates[activity_nr][0] += current_penalty
                    penalty_updates[activity_nr][1] += initial_penalty

                    # Commit batch
                    if len(batch) >= batch_size:
                        if not dry_run:
                            db.add_all(batch)
                            db.commit()
                        stats["imported"] += len(batch)
                        print(f"  Imported batch: {stats['imported']:,} violations...")
                        batch = []

                except Exception as e:
                    stats["errors"] += 1
                    if stats["errors"] <= 5:
                        print(f"  ERROR on {activity_nr}/{citation_id_normalized}: {e}")

        # Final batch
        if batch:
            if not dry_run:
                db.add_all(batch)
                db.commit()
            stats["imported"] += len(batch)

        # Update inspection penalty totals
        if not dry_run and penalty_updates:
            print(f"\nUpdating penalty totals for {len(penalty_updates):,} inspections...")
            for activity_nr, (current_sum, initial_sum) in penalty_updates.items():
                db.query(Inspection).filter(
                    Inspection.activity_nr == activity_nr
                ).update({
                    "total_current_penalty": Inspection.total_current_penalty + current_sum,
                    "total_initial_penalty": Inspection.total_initial_penalty + initial_sum,
                })
            db.commit()
            print("  Penalty totals updated.")

    print(f"\n{'='*60}")
    print("VIOLATION IMPORT SUMMARY")
    print(f"{'='*60}")
    print(f"  Total rows in CSV: {stats['total_rows']:,}")
    print(f"  Skipped (no matching inspection): {stats['skipped_no_inspection']:,}")
    print(f"  Skipped (already exist): {stats['skipped_existing']:,}")
    print(f"  Imported: {stats['imported']:,}")
    print(f"  Errors: {stats['errors']:,}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Import OSHA data from CSV files"
    )
    parser.add_argument(
        "--inspections-only",
        action="store_true",
        help="Only import inspections (skip violations)"
    )
    parser.add_argument(
        "--violations-only",
        action="store_true",
        help="Only import violations (skip inspections)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of records per batch (default: 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without making changes"
    )
    parser.add_argument(
        "--inspection-csv",
        type=str,
        default="osha_inspection5.csv",
        help="Path to inspection CSV file"
    )
    parser.add_argument(
        "--violation-csv",
        type=str,
        default="osha_violation13.csv",
        help="Path to violation CSV file"
    )

    args = parser.parse_args()

    # Resolve paths relative to project root
    project_root = Path(__file__).parent.parent
    inspection_csv = project_root / args.inspection_csv
    violation_csv = project_root / args.violation_csv

    print("="*60)
    print("TSG Safety Tracker - CSV Data Import")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")

    # Import inspections first (violations need matching inspections)
    if not args.violations_only:
        if inspection_csv.exists():
            import_inspections(
                str(inspection_csv),
                batch_size=args.batch_size,
                dry_run=args.dry_run
            )
        else:
            print(f"\nWARNING: Inspection CSV not found: {inspection_csv}")

    # Import violations
    if not args.inspections_only:
        if violation_csv.exists():
            import_violations(
                str(violation_csv),
                batch_size=args.batch_size,
                dry_run=args.dry_run
            )
        else:
            print(f"\nWARNING: Violation CSV not found: {violation_csv}")

    print(f"\n{'='*60}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)


if __name__ == "__main__":
    main()
