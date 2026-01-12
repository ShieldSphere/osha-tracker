"""Import OSHA inspection data from local CSV file."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import csv
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert

from src.config import settings
from src.database.models import Base, Inspection


def parse_date(value: str) -> Optional[datetime]:
    """Parse date string to date object."""
    if not value or value.strip() == '':
        return None
    try:
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


def upsert_batch(session, records: list) -> int:
    """Upsert a batch of records."""
    if not records:
        return 0

    stmt = insert(Inspection).values(records)
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
    session.execute(stmt)
    return len(records)


# States to include in import
TARGET_STATES = {'GA', 'FL', 'SC', 'AL', 'NC', 'TN'}


def import_file(filepath: str, batch_size: int = 200):
    """Import from local CSV file, filtered by target states."""
    print(f"Importing from: {filepath}")
    print(f"Filtering for states: {', '.join(sorted(TARGET_STATES))}")

    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    session = Session()
    records = []
    total_processed = 0
    total_matched = 0
    total_inserted = 0

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)

            for row in reader:
                total_processed += 1

                # Filter by state
                state = safe_str(row.get('site_state', ''), 2)
                if state not in TARGET_STATES:
                    continue

                total_matched += 1

                record = {
                    'activity_nr': safe_str(row.get('activity_nr', '')),
                    'estab_name': safe_str(row.get('estab_name', ''), 255) or '',
                    'site_address': safe_str(row.get('site_address', ''), 255),
                    'site_city': safe_str(row.get('site_city', ''), 100),
                    'site_state': state,
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

                if len(records) >= batch_size:
                    try:
                        inserted = upsert_batch(session, records)
                        session.commit()
                        total_inserted += inserted
                    except Exception as e:
                        session.rollback()
                        session.close()
                        session = Session()
                        print(f"  Reconnecting...")
                        inserted = upsert_batch(session, records)
                        session.commit()
                        total_inserted += inserted

                    records = []
                    if total_matched % 5000 == 0:
                        print(f"  Progress: {total_matched:,} matched, {total_inserted:,} inserted")

        # Final batch
        if records:
            inserted = upsert_batch(session, records)
            session.commit()
            total_inserted += inserted

        print(f"Complete: {total_processed:,} rows scanned, {total_matched:,} matched, {total_inserted:,} inserted")

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    # Import the most recent data file (filtered by target states)
    import_file(r"c:\Users\matt\Downloads\osha_inspection_20260108.csv\osha_inspection5.csv")
