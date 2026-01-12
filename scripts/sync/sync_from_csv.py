"""
Sync inspections from OSHA CSV file.
This is more reliable than the API which doesn't support date filtering.

Download latest CSV from: https://enforcedata.dol.gov/views/data_catalogs.php
Look for "OSHA Inspection" dataset
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import csv
from datetime import datetime, date
from src.database.connection import get_db_session
from src.database.models import Inspection
from src.services.sync_service import SOUTHEAST_STATES
from sqlalchemy import select

def sync_inspections_from_csv(csv_path: str, min_year: int = 2020):
    """
    Import inspections from OSHA CSV file.

    Args:
        csv_path: Path to the CSV file
        min_year: Only import inspections from this year onwards
    """
    print("=" * 60)
    print(f"Syncing Inspections from CSV: {csv_path}")
    print(f"Filter: SE states only, {min_year}+ only")
    print("=" * 60)

    stats = {
        "total_rows": 0,
        "skipped_state": 0,
        "skipped_old": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "errors": 0
    }

    # Read all records from CSV
    records_to_process = []

    print("\nReading CSV file...")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            stats["total_rows"] += 1

            # Filter by state
            state = row.get('site_state', '').strip().upper()
            if state not in SOUTHEAST_STATES:
                stats["skipped_state"] += 1
                continue

            # Filter by date
            open_date_str = row.get('open_date', '').strip()
            if not open_date_str:
                stats["skipped_old"] += 1
                continue

            try:
                open_date = datetime.strptime(open_date_str[:10], '%Y-%m-%d').date()
                if open_date.year < min_year:
                    stats["skipped_old"] += 1
                    continue
            except:
                stats["errors"] += 1
                continue

            records_to_process.append(row)

    print(f"Total rows in CSV: {stats['total_rows']:,}")
    print(f"Records to process (SE, {min_year}+): {len(records_to_process):,}")
    print(f"Skipped (non-SE): {stats['skipped_state']:,}")
    print(f"Skipped (pre-{min_year}): {stats['skipped_old']:,}")

    # Process records
    print("\nProcessing records...")

    with get_db_session() as db:
        # Get existing activity numbers for quick lookup
        existing = {
            r.activity_nr: r for r in
            db.execute(select(Inspection)).scalars().all()
        }
        print(f"Existing inspections in DB: {len(existing):,}")

        batch_size = 500
        for i, row in enumerate(records_to_process):
            try:
                activity_nr = row.get('activity_nr', '').strip()
                if not activity_nr:
                    stats["errors"] += 1
                    continue

                # Parse fields
                def safe_date(val):
                    if not val:
                        return None
                    try:
                        return datetime.strptime(str(val).strip()[:10], '%Y-%m-%d').date()
                    except:
                        return None

                def safe_str(val):
                    if not val:
                        return None
                    s = str(val).strip()
                    return s if s else None

                def safe_float(val):
                    if not val:
                        return None
                    try:
                        return float(val)
                    except:
                        return None

                parsed = {
                    "activity_nr": activity_nr,
                    "estab_name": safe_str(row.get('estab_name')),
                    "site_address": safe_str(row.get('site_address')),
                    "site_city": safe_str(row.get('site_city')),
                    "site_state": safe_str(row.get('site_state')),
                    "site_zip": safe_str(row.get('site_zip')),
                    "open_date": safe_date(row.get('open_date')),
                    "close_case_date": safe_date(row.get('close_case_date')),
                    "sic_code": safe_str(row.get('sic_code')),
                    "naics_code": safe_str(row.get('naics_code')),
                    "insp_type": safe_str(row.get('insp_type')),
                    "insp_scope": safe_str(row.get('insp_scope')),
                    "owner_type": safe_str(row.get('owner_type')),
                    "adv_notice": safe_str(row.get('adv_notice')),
                    "safety_hlth": safe_str(row.get('safety_hlth')),
                }

                if activity_nr in existing:
                    # Update existing
                    inspection = existing[activity_nr]
                    changed = False
                    for key, value in parsed.items():
                        if key != 'activity_nr' and getattr(inspection, key, None) != value:
                            setattr(inspection, key, value)
                            changed = True

                    if changed:
                        inspection.updated_at = datetime.utcnow()
                        stats["updated"] += 1
                    else:
                        stats["unchanged"] += 1
                else:
                    # Create new
                    inspection = Inspection(**parsed)
                    db.add(inspection)
                    existing[activity_nr] = inspection
                    stats["created"] += 1

                # Commit in batches
                if (i + 1) % batch_size == 0:
                    db.commit()
                    print(f"  Processed {i + 1:,} / {len(records_to_process):,}...")

            except Exception as e:
                stats["errors"] += 1
                if stats["errors"] <= 5:
                    print(f"  Error on row {i}: {e}")

        # Final commit
        db.commit()

    print("\n" + "=" * 60)
    print("SYNC COMPLETE")
    print("=" * 60)
    print(f"Created: {stats['created']:,}")
    print(f"Updated: {stats['updated']:,}")
    print(f"Unchanged: {stats['unchanged']:,}")
    print(f"Errors: {stats['errors']:,}")
    print()

    # Show final count
    with get_db_session() as db:
        total = db.execute(select(Inspection)).scalars().all()
        print(f"Total inspections in database: {len(total):,}")

    return stats

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = "osha_inspection5.csv"

    sync_inspections_from_csv(csv_path)
