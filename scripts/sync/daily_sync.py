"""
Daily OSHA Data Sync

This script syncs OSHA inspection and violation data from CSV files to the database.
It filters for Southeast states and inspections from 2020+.

USAGE:
------
1. Automatic (looks for latest CSV in data/ folder):
   python daily_sync.py

2. With specific files:
   python daily_sync.py -i osha_inspection.csv -v osha_violation.csv

3. Try automatic download (may not work due to JavaScript requirement):
   python daily_sync.py --download

MANUAL DOWNLOAD:
----------------
OSHA's website requires JavaScript, so automatic downloads may fail.
To manually download:
1. Go to: https://enforcedata.dol.gov/views/data_catalogs.php
2. Click "OSHA" in the left menu
3. Download "OSHA Inspection" CSV and save to data/osha_inspection.csv
4. Download "OSHA Violation" CSV and save to data/osha_violation.csv
5. Run: python daily_sync.py

The script will automatically find the latest CSV files in the data/ folder.
"""
import os
import sys
import logging
import requests
import zipfile
import csv
from io import BytesIO
from datetime import datetime, date, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.connection import get_db_session
from src.database.models import Inspection, Violation
from src.services.sync_service import SOUTHEAST_STATES
from sqlalchemy import select

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# OSHA Data URLs - Direct download links for CSV data
# These URLs download ZIP files containing the CSV data
INSPECTION_CSV_URL = "https://enforcedata.dol.gov/views/data_summary.php?agency=osha&form=osha_inspection&type=csv"
VIOLATION_CSV_URL = "https://enforcedata.dol.gov/views/data_summary.php?agency=osha&form=osha_violation&type=csv"

# Backup: Manual download page
DOWNLOAD_PAGE = "https://enforcedata.dol.gov/views/data_catalogs.php"


def download_csv(url: str, output_path: str) -> bool:
    """
    Download CSV file from URL.

    Returns True if successful.
    """
    logger.info(f"Downloading from {url}...")

    try:
        response = requests.get(url, timeout=600, stream=True)
        response.raise_for_status()

        # Check if it's a zip file
        content_type = response.headers.get('content-type', '')

        if 'zip' in content_type or url.endswith('.zip'):
            # Extract from zip
            logger.info("Extracting from ZIP file...")
            with zipfile.ZipFile(BytesIO(response.content)) as z:
                # Find CSV file in zip
                csv_files = [f for f in z.namelist() if f.endswith('.csv')]
                if csv_files:
                    with z.open(csv_files[0]) as src, open(output_path, 'wb') as dst:
                        dst.write(src.read())
                    logger.info(f"Extracted {csv_files[0]} to {output_path}")
                    return True
                else:
                    logger.error("No CSV file found in ZIP")
                    return False
        else:
            # Direct CSV download
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Downloaded to {output_path}")
            return True

    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False


def sync_inspections_from_csv(csv_path: str, min_year: int = 2020) -> dict:
    """
    Import inspections from OSHA CSV file.
    """
    stats = {
        "total_rows": 0,
        "skipped_state": 0,
        "skipped_old": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "errors": 0
    }

    logger.info(f"Syncing inspections from {csv_path}")
    logger.info(f"Filter: SE states only, {min_year}+ only")

    # Read and filter records
    records = []
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total_rows"] += 1

            state = row.get('site_state', '').strip().upper()
            if state not in SOUTHEAST_STATES:
                stats["skipped_state"] += 1
                continue

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

            records.append(row)

    logger.info(f"Total rows: {stats['total_rows']:,}, Processing: {len(records):,}")

    # Process records
    with get_db_session() as db:
        existing = {r.activity_nr: r for r in db.execute(select(Inspection)).scalars().all()}

        for i, row in enumerate(records):
            try:
                activity_nr = row.get('activity_nr', '').strip()
                if not activity_nr:
                    continue

                def safe_date(val):
                    if not val:
                        return None
                    val_str = str(val).strip()
                    try:
                        return datetime.strptime(val_str[:10], '%Y-%m-%d').date()
                    except:
                        pass
                    try:
                        return datetime.strptime(val_str, '%m/%d/%Y').date()
                    except:
                        pass
                    return None

                def safe_str(val):
                    return str(val).strip() if val else None

                def safe_int(val):
                    try:
                        return int(val) if val else None
                    except:
                        return None

                parsed = {
                    "activity_nr": activity_nr,
                    "reporting_id": safe_str(row.get('reporting_id')),
                    "state_flag": safe_str(row.get('state_flag')),
                    "estab_name": safe_str(row.get('estab_name')),
                    "site_address": safe_str(row.get('site_address')),
                    "site_city": safe_str(row.get('site_city')),
                    "site_state": safe_str(row.get('site_state')),
                    "site_zip": safe_str(row.get('site_zip')),
                    "mail_street": safe_str(row.get('mail_street')),
                    "mail_city": safe_str(row.get('mail_city')),
                    "mail_state": safe_str(row.get('mail_state')),
                    "mail_zip": safe_str(row.get('mail_zip')),
                    "open_date": safe_date(row.get('open_date')),
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
                }

                if activity_nr in existing:
                    insp = existing[activity_nr]
                    changed = False
                    for key, value in parsed.items():
                        if key != 'activity_nr' and getattr(insp, key, None) != value:
                            setattr(insp, key, value)
                            changed = True
                    if changed:
                        insp.updated_at = datetime.utcnow()
                        stats["updated"] += 1
                    else:
                        stats["unchanged"] += 1
                else:
                    insp = Inspection(**parsed)
                    db.add(insp)
                    existing[activity_nr] = insp
                    stats["created"] += 1

                if (i + 1) % 1000 == 0:
                    db.commit()
                    logger.info(f"Processed {i + 1:,} / {len(records):,}")

            except Exception as e:
                stats["errors"] += 1

        db.commit()

    logger.info(f"Inspections: {stats['created']} created, {stats['updated']} updated")
    return stats


def sync_violations_from_csv(csv_path: str, min_year: int = 2020) -> dict:
    """
    Import violations from OSHA CSV file.
    Only imports violations for inspections that exist in the database.
    """
    stats = {
        "total_rows": 0,
        "skipped_no_inspection": 0,
        "skipped_old": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "errors": 0
    }

    logger.info(f"Syncing violations from {csv_path}")

    # Get existing inspection activity numbers
    with get_db_session() as db:
        inspection_nrs = set(
            db.execute(select(Inspection.activity_nr)).scalars().all()
        )
    logger.info(f"Found {len(inspection_nrs):,} inspections in database")

    # Read and filter records
    records = []
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total_rows"] += 1

            activity_nr = row.get('activity_nr', '').strip()
            if activity_nr not in inspection_nrs:
                stats["skipped_no_inspection"] += 1
                continue

            issuance_date_str = row.get('issuance_date', '').strip()
            if issuance_date_str:
                try:
                    issuance_date = datetime.strptime(issuance_date_str[:10], '%Y-%m-%d').date()
                    if issuance_date.year < min_year:
                        stats["skipped_old"] += 1
                        continue
                except:
                    pass

            records.append(row)

    logger.info(f"Total rows: {stats['total_rows']:,}, Processing: {len(records):,}")

    # Process records
    with get_db_session() as db:
        existing = {}
        for v in db.execute(select(Violation)).scalars().all():
            key = f"{v.activity_nr}_{v.citation_id}"
            existing[key] = v

        for i, row in enumerate(records):
            try:
                activity_nr = row.get('activity_nr', '').strip()
                citation_id = row.get('citation_id', '').strip()

                if not activity_nr or not citation_id:
                    continue

                def safe_date(val):
                    if not val:
                        return None
                    val_str = str(val).strip()
                    try:
                        return datetime.strptime(val_str[:10], '%Y-%m-%d').date()
                    except:
                        pass
                    try:
                        return datetime.strptime(val_str, '%m/%d/%Y').date()
                    except:
                        pass
                    return None

                def safe_str(val):
                    return str(val).strip() if val else None

                def safe_float(val):
                    try:
                        return float(val) if val else 0.0
                    except:
                        return 0.0

                def safe_int(val):
                    try:
                        return int(val) if val else None
                    except:
                        return None

                parsed = {
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
                    "fta_penalty": safe_float(row.get('fta_penalty')),
                    "fta_contest_date": safe_date(row.get('fta_contest_date')),
                    "fta_final_order_date": safe_date(row.get('fta_final_order_date')),
                    "hazsub1": safe_str(row.get('hazsub1')),
                    "hazsub2": safe_str(row.get('hazsub2')),
                    "hazsub3": safe_str(row.get('hazsub3')),
                    "hazsub4": safe_str(row.get('hazsub4')),
                    "hazsub5": safe_str(row.get('hazsub5')),
                }

                key = f"{activity_nr}_{citation_id}"

                if key in existing:
                    viol = existing[key]
                    changed = False
                    for k, v in parsed.items():
                        if k not in ('activity_nr', 'citation_id') and getattr(viol, k, None) != v:
                            setattr(viol, k, v)
                            changed = True
                    if changed:
                        stats["updated"] += 1
                    else:
                        stats["unchanged"] += 1
                else:
                    viol = Violation(**parsed)
                    db.add(viol)
                    existing[key] = viol
                    stats["created"] += 1

                if (i + 1) % 1000 == 0:
                    db.commit()
                    logger.info(f"Processed {i + 1:,} / {len(records):,}")

            except Exception as e:
                stats["errors"] += 1

        db.commit()

    logger.info(f"Violations: {stats['created']} created, {stats['updated']} updated")
    return stats


def update_inspection_penalties():
    """Update total penalties on inspections from violations."""
    logger.info("Updating inspection penalty totals...")

    with get_db_session() as db:
        inspections = db.execute(select(Inspection)).scalars().all()

        updated = 0
        for insp in inspections:
            violations = db.execute(
                select(Violation).where(Violation.activity_nr == insp.activity_nr)
            ).scalars().all()

            if violations:
                total_current = sum(v.current_penalty or 0 for v in violations)
                total_initial = sum(v.initial_penalty or 0 for v in violations)

                if insp.total_current_penalty != total_current or insp.total_initial_penalty != total_initial:
                    insp.total_current_penalty = total_current
                    insp.total_initial_penalty = total_initial
                    updated += 1

        db.commit()

    logger.info(f"Updated penalties on {updated} inspections")


def daily_sync(
    inspection_csv: str = None,
    violation_csv: str = None,
    download: bool = False
):
    """
    Run the daily sync process.

    Args:
        inspection_csv: Path to inspection CSV (or None to download)
        violation_csv: Path to violation CSV (or None to download)
        download: Whether to download fresh CSVs
    """
    logger.info("=" * 60)
    logger.info("Starting Daily OSHA Sync")
    logger.info(f"Time: {datetime.now()}")
    logger.info("=" * 60)

    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)

    # Download if requested
    if download:
        logger.info("\nDownloading latest CSV files...")
        logger.info("Note: If automatic download fails, manually download from:")
        logger.info(f"  {DOWNLOAD_PAGE}")

        inspection_csv = str(data_dir / "osha_inspection_latest.csv")
        violation_csv = str(data_dir / "osha_violation_latest.csv")

        # Try to download (may not work if OSHA requires manual download)
        download_csv(INSPECTION_CSV_URL, inspection_csv)
        download_csv(VIOLATION_CSV_URL, violation_csv)

    # Sync inspections
    if inspection_csv and os.path.exists(inspection_csv):
        logger.info("\n" + "-" * 40)
        sync_inspections_from_csv(inspection_csv)
    else:
        logger.warning("No inspection CSV provided or file not found")

    # Sync violations
    if violation_csv and os.path.exists(violation_csv):
        logger.info("\n" + "-" * 40)
        sync_violations_from_csv(violation_csv)
    else:
        logger.warning("No violation CSV provided or file not found")

    # Update penalties
    logger.info("\n" + "-" * 40)
    update_inspection_penalties()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Daily Sync Complete")
    logger.info("=" * 60)

    with get_db_session() as db:
        from sqlalchemy import func
        total_insp = db.execute(select(func.count(Inspection.id))).scalar()
        total_viol = db.execute(select(func.count(Violation.id))).scalar()
        logger.info(f"Total Inspections: {total_insp:,}")
        logger.info(f"Total Violations: {total_viol:,}")


def find_latest_csv(pattern: str, search_dirs: list) -> str:
    """Find the most recently modified CSV file matching the pattern."""
    latest_file = None
    latest_time = 0

    for search_dir in search_dirs:
        search_path = Path(search_dir)
        if not search_path.exists():
            continue
        for f in search_path.glob(pattern):
            mtime = f.stat().st_mtime
            if mtime > latest_time:
                latest_time = mtime
                latest_file = str(f)

    return latest_file


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Daily OSHA Data Sync")
    parser.add_argument("--inspection", "-i", help="Path to inspection CSV file")
    parser.add_argument("--violation", "-v", help="Path to violation CSV file")
    parser.add_argument("--download", "-d", action="store_true", help="Try to download latest CSVs")

    args = parser.parse_args()

    # Search directories for CSV files
    script_dir = Path(__file__).parent
    search_dirs = [
        script_dir,                          # Project root
        script_dir / "data",                 # data subfolder
        Path.home() / "Downloads",           # Downloads folder
    ]

    # If no args, find latest CSV files
    if not args.inspection and not args.violation and not args.download:
        args.inspection = find_latest_csv("*inspection*.csv", search_dirs)
        args.violation = find_latest_csv("*violation*.csv", search_dirs)

        if args.inspection:
            logger.info(f"Found inspection CSV: {args.inspection}")
        else:
            logger.warning("No inspection CSV found. Download from https://enforcedata.dol.gov/views/data_catalogs.php")

        if args.violation:
            logger.info(f"Found violation CSV: {args.violation}")
        else:
            logger.warning("No violation CSV found. Download from https://enforcedata.dol.gov/views/data_catalogs.php")

    daily_sync(
        inspection_csv=args.inspection,
        violation_csv=args.violation,
        download=args.download
    )
