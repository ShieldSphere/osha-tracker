from src.database.connection import get_db_session
from src.database.models import Inspection
from sqlalchemy import select, func, desc, asc
from datetime import datetime

print("=" * 60)
print("Checking Database for New Data")
print("=" * 60)

with get_db_session() as db:
    # Count total
    total = db.execute(select(func.count(Inspection.id))).scalar()
    print(f"\nTotal inspections: {total:,}")

    # Check oldest and newest by open_date
    oldest = db.execute(
        select(Inspection)
        .where(Inspection.open_date.isnot(None))
        .order_by(asc(Inspection.open_date))
        .limit(1)
    ).scalar_one_or_none()

    newest = db.execute(
        select(Inspection)
        .where(Inspection.open_date.isnot(None))
        .order_by(desc(Inspection.open_date))
        .limit(1)
    ).scalar_one_or_none()

    if oldest and newest:
        print(f"\nDate range (by open_date):")
        print(f"  Oldest: {oldest.open_date} - {oldest.estab_name[:50]}")
        print(f"  Newest: {newest.open_date} - {newest.estab_name[:50]}")

    # Check load_dt field
    with_load_dt = db.execute(
        select(func.count(Inspection.id))
        .where(Inspection.load_dt.isnot(None))
    ).scalar()

    print(f"\nInspections with load_dt populated: {with_load_dt:,}")

    if with_load_dt > 0:
        # Show sample with load_dt
        sample_load = db.execute(
            select(Inspection)
            .where(Inspection.load_dt.isnot(None))
            .order_by(desc(Inspection.load_dt))
            .limit(5)
        ).scalars().all()

        print(f"\nMost recent by load_dt (when published to OSHA):")
        for i, insp in enumerate(sample_load):
            days_ago = (datetime.now() - insp.load_dt).days if insp.load_dt else None
            print(f"  [{i+1}] {insp.activity_nr} - {insp.estab_name[:40]} - {insp.load_dt} ({days_ago} days ago)")

    # Check for inspections by year
    print(f"\nInspections by year (open_date):")
    for year in range(2016, 2027):
        count = db.execute(
            select(func.count(Inspection.id))
            .where(
                Inspection.open_date >= f"{year}-01-01",
                Inspection.open_date < f"{year+1}-01-01"
            )
        ).scalar()
        if count > 0:
            print(f"  {year}: {count:,}")

print("\n" + "=" * 60)
