"""Import OSHA inspection data from CSV files."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import csv
import io
import zipfile
import httpx
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert

from src.config import settings
from src.database.models import Base, Inspection

# CSV download URLs (updated daily, date in filename)
INSPECTION_CSV_URL = "https://enfxfr.dol.gov/data_catalog/OSHA/osha_inspection_20260108.csv.zip"


def download_and_extract_all_csvs(url: str) -> list:
    """Download zip file and extract all CSV files."""
    print(f"Downloading {url}...")

    with httpx.Client(timeout=300.0, verify=False) as client:
        response = client.get(url)
        response.raise_for_status()

    print(f"Downloaded {len(response.content) / 1024 / 1024:.1f} MB")

    # Extract all CSV files from zip
    csv_contents = []
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        csv_files = sorted([f for f in zf.namelist() if f.endswith('.csv')])
        if not csv_files:
            raise ValueError("No CSV files found in archive")

        print(f"Found {len(csv_files)} CSV files: {csv_files}")

        for csv_filename in csv_files:
            print(f"Extracting {csv_filename}...")
            with zf.open(csv_filename) as f:
                content = f.read().decode('utf-8', errors='replace')
                csv_contents.append((csv_filename, content))

    return csv_contents


def parse_date(value: str) -> Optional[datetime]:
    """Parse date string to date object."""
    if not value or value.strip() == '':
        return None
    try:
        # Try common formats
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
        return None
    except Exception:
        return None


def parse_float(value: str) -> Optional[float]:
    """Parse float from string."""
    if not value or value.strip() == '':
        return None
    try:
        return float(value.strip())
    except (ValueError, TypeError):
        return None


def safe_str(value: str, max_len: int = None) -> Optional[str]:
    """Clean string value."""
    if not value or value.strip() == '':
        return None
    s = value.strip()
    if max_len and len(s) > max_len:
        s = s[:max_len]
    return s


def import_inspections(csv_content: str, batch_size: int = 200):
    """Import inspection records from CSV content."""
    # Use connection pooling with settings for Supabase
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    Session = sessionmaker(bind=engine)

    # Ensure tables exist
    Base.metadata.create_all(engine)

    reader = csv.DictReader(io.StringIO(csv_content))

    records = []
    total_processed = 0
    total_inserted = 0

    session = Session()

    try:
        for row in reader:
            total_processed += 1

            record = {
                'activity_nr': safe_str(row.get('activity_nr', '')),
                'estab_name': safe_str(row.get('estab_name', ''), 255) or '',
                'site_address': safe_str(row.get('site_address', ''), 255),
                'site_city': safe_str(row.get('site_city', ''), 100),
                'site_state': safe_str(row.get('site_state', ''), 2),
                'site_zip': safe_str(row.get('site_zip', ''), 10),
                'open_date': parse_date(row.get('open_date', '')),
                'close_conf_date': parse_date(row.get('close_conf_date', '')),
                'close_case_date': parse_date(row.get('close_case_date', '')),
                'sic_code': safe_str(row.get('sic_code', ''), 10),
                'naics_code': safe_str(row.get('naics_code', ''), 10),
                'insp_type': safe_str(row.get('insp_type', ''), 10),
                'insp_scope': safe_str(row.get('insp_scope', ''), 10),
                'owner_type': safe_str(row.get('owner_type', ''), 50),
                'adv_notice': safe_str(row.get('adv_notice', ''), 10),
                'safety_hlth': safe_str(row.get('safety_hlth', ''), 10),
                'total_current_penalty': parse_float(row.get('total_current_penalty', '')),
                'total_initial_penalty': parse_float(row.get('total_initial_penalty', '')),
            }

            if not record['activity_nr']:
                continue

            records.append(record)

            # Smaller batches, commit each batch
            if len(records) >= batch_size:
                try:
                    inserted, _ = upsert_batch(session, records)
                    session.commit()
                    total_inserted += inserted
                except Exception as e:
                    session.rollback()
                    session.close()
                    session = Session()
                    print(f"  Reconnecting after error...")
                    inserted, _ = upsert_batch(session, records)
                    session.commit()
                    total_inserted += inserted

                records = []
                if total_processed % 50000 == 0:
                    print(f"  Progress: {total_processed:,} rows, {total_inserted:,} inserted")

        # Final batch
        if records:
            inserted, _ = upsert_batch(session, records)
            session.commit()
            total_inserted += inserted

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
        engine.dispose()

    print(f"  Complete: {total_processed:,} rows, {total_inserted:,} inserted")
    return total_processed, total_inserted, 0


def upsert_batch(session, records: list) -> tuple:
    """Upsert a batch of records. Returns (inserted, updated) counts."""
    if not records:
        return 0, 0

    # Use PostgreSQL upsert (INSERT ... ON CONFLICT)
    stmt = insert(Inspection).values(records)

    # On conflict, update all fields except id and activity_nr
    update_dict = {
        'estab_name': stmt.excluded.estab_name,
        'site_address': stmt.excluded.site_address,
        'site_city': stmt.excluded.site_city,
        'site_state': stmt.excluded.site_state,
        'site_zip': stmt.excluded.site_zip,
        'open_date': stmt.excluded.open_date,
        'close_conf_date': stmt.excluded.close_conf_date,
        'close_case_date': stmt.excluded.close_case_date,
        'sic_code': stmt.excluded.sic_code,
        'naics_code': stmt.excluded.naics_code,
        'insp_type': stmt.excluded.insp_type,
        'insp_scope': stmt.excluded.insp_scope,
        'owner_type': stmt.excluded.owner_type,
        'adv_notice': stmt.excluded.adv_notice,
        'safety_hlth': stmt.excluded.safety_hlth,
        'total_current_penalty': stmt.excluded.total_current_penalty,
        'total_initial_penalty': stmt.excluded.total_initial_penalty,
        'updated_at': datetime.utcnow(),
    }

    stmt = stmt.on_conflict_do_update(
        index_elements=['activity_nr'],
        set_=update_dict
    )

    result = session.execute(stmt)

    # PostgreSQL doesn't easily distinguish inserts vs updates in upsert
    # Return total as "inserted" for simplicity
    return len(records), 0


def main():
    """Main entry point."""
    print("OSHA Inspection CSV Import")
    print("=" * 50)
    print()

    # Check database connection
    print(f"Database: {settings.DATABASE_URL[:50]}...")
    print()

    # Download and import all CSV files
    try:
        csv_files = download_and_extract_all_csvs(INSPECTION_CSV_URL)

        grand_total_processed = 0
        grand_total_inserted = 0

        for i, (filename, csv_content) in enumerate(csv_files):
            print()
            print(f"=" * 50)
            print(f"Processing file {i+1}/{len(csv_files)}: {filename}")
            print(f"=" * 50)

            line_count = csv_content.count('\n')
            print(f"CSV has approximately {line_count:,} lines")
            print()

            processed, inserted, updated = import_inspections(csv_content)
            grand_total_processed += processed
            grand_total_inserted += inserted

        print()
        print("=" * 50)
        print("ALL FILES COMPLETE")
        print(f"  Grand total processed: {grand_total_processed:,}")
        print(f"  Grand total inserted: {grand_total_inserted:,}")
        print("=" * 50)

    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
