"""Check recent data in database."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.connection import get_db_session
from src.database.models import Inspection, Violation
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta

print("=" * 60)
print("Checking Recent Data in Database")
print("=" * 60)

with get_db_session() as db:
    # Check inspections
    print("\n1. INSPECTIONS:")

    # Count total
    total = db.execute(select(func.count(Inspection.id))).scalar()
    print(f"   Total inspections: {total:,}")

    # Check most recent by open_date
    recent_open = db.execute(
        select(Inspection)
        .where(Inspection.open_date.isnot(None))
        .order_by(desc(Inspection.open_date))
        .limit(5)
    ).scalars().all()

    print(f"\n   Most recent by open_date:")
    for i, insp in enumerate(recent_open):
        print(f"   [{i+1}] {insp.activity_nr} - {insp.estab_name[:40]} - {insp.open_date}")

    # Check most recent by load_dt
    recent_load = db.execute(
        select(Inspection)
        .where(Inspection.load_dt.isnot(None))
        .order_by(desc(Inspection.load_dt))
        .limit(5)
    ).scalars().all()

    print(f"\n   Most recent by load_dt (when published to OSHA):")
    for i, insp in enumerate(recent_load):
        days_ago = (datetime.now() - insp.load_dt).days if insp.load_dt else None
        print(f"   [{i+1}] {insp.activity_nr} - {insp.estab_name[:40]} - {insp.load_dt} ({days_ago} days ago)")

    # Count inspections in last 7 days by open_date
    cutoff = datetime.now().date() - timedelta(days=7)
    recent_count = db.execute(
        select(func.count(Inspection.id))
        .where(Inspection.open_date >= cutoff)
    ).scalar()
    print(f"\n   Inspections opened in last 7 days: {recent_count}")

    # Check violations
    print("\n2. VIOLATIONS:")

    # Count total
    total_viol = db.execute(select(func.count(Violation.id))).scalar()
    print(f"   Total violations: {total_viol:,}")

    # Check most recent by issuance_date
    recent_viol = db.execute(
        select(Violation)
        .where(Violation.issuance_date.isnot(None))
        .order_by(desc(Violation.issuance_date))
        .limit(5)
    ).scalars().all()

    print(f"\n   Most recent by issuance_date:")
    for i, viol in enumerate(recent_viol):
        print(f"   [{i+1}] {viol.activity_nr} - {viol.citation_id} - {viol.issuance_date}")

    # Count violations in last 30 days
    cutoff_viol = datetime.now().date() - timedelta(days=30)
    recent_viol_count = db.execute(
        select(func.count(Violation.id))
        .where(Violation.issuance_date >= cutoff_viol)
    ).scalar()
    print(f"\n   Violations issued in last 30 days: {recent_viol_count}")

print("\n" + "=" * 60)
