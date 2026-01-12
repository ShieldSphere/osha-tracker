"""Import OSHA violation data from local CSV file."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import csv
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert

from src.config import settings
from src.database.models import Base, Violation


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


def parse_int(value: str) -> Optional[int]:
    """Parse integer from string."""
    if not value or value.strip() == '':
        return None
    try:
        return int(float(value.strip()))
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
    """Upsert a batch of violation records."""
    if not records:
        return 0

    stmt = insert(Violation).values(records)
    update_dict = {
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
    stmt = stmt.on_conflict_do_update(
        constraint='uq_activity_citation',
        set_=update_dict
    )
    session.execute(stmt)
    return len(records)


def import_violations(filepath: str, batch_size: int = 200):
    """Import violations from local CSV file, only for existing inspections."""
    print(f"Importing violations from: {filepath}")

    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    Session = sessionmaker(bind=engine)

    # Ensure tables exist
    Base.metadata.create_all(engine)

    session = Session()

    # Get set of activity_nr values that exist in our inspections table
    print("Loading existing inspection activity numbers...")
    result = session.execute(text("SELECT activity_nr FROM inspections"))
    valid_activity_nrs = {row[0] for row in result}
    print(f"Found {len(valid_activity_nrs):,} inspections to match against")

    records = []
    total_processed = 0
    total_matched = 0
    total_inserted = 0
    total_skipped = 0

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)

            for row in reader:
                total_processed += 1

                # Only import violations for inspections we have
                activity_nr = safe_str(row.get('activity_nr', ''), 20)
                if activity_nr not in valid_activity_nrs:
                    total_skipped += 1
                    continue

                # Skip deleted records
                if row.get('delete_flag', '').strip():
                    total_skipped += 1
                    continue

                total_matched += 1

                record = {
                    'activity_nr': activity_nr,
                    'citation_id': safe_str(row.get('citation_id', ''), 20) or '',
                    'standard': safe_str(row.get('standard', ''), 50),
                    'viol_type': safe_str(row.get('viol_type', ''), 10),
                    'issuance_date': parse_date(row.get('issuance_date', '')),
                    'abate_date': parse_date(row.get('abate_date', '')),
                    'abate_complete': safe_str(row.get('abate_complete', ''), 10),
                    'current_penalty': parse_float(row.get('current_penalty', '')),
                    'initial_penalty': parse_float(row.get('initial_penalty', '')),
                    'contest_date': parse_date(row.get('contest_date', '')),
                    'final_order_date': parse_date(row.get('final_order_date', '')),
                    'nr_instances': parse_int(row.get('nr_instances', '')),
                    'nr_exposed': parse_int(row.get('nr_exposed', '')),
                    'rec': safe_str(row.get('rec', ''), 10),
                    'gravity': safe_str(row.get('gravity', ''), 20),
                    'emphasis': safe_str(row.get('emphasis', ''), 50),
                    'hazcat': safe_str(row.get('hazcat', ''), 50),
                }

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
                        print(f"  Reconnecting after error: {e}")
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

        print(f"\nComplete:")
        print(f"  Rows scanned: {total_processed:,}")
        print(f"  Matched to inspections: {total_matched:,}")
        print(f"  Skipped (no matching inspection): {total_skipped:,}")
        print(f"  Violations inserted: {total_inserted:,}")

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    import_violations(r"c:\Users\matt\TSG Safety\Applications\OSHA Tracker\osha_violation13.csv")
