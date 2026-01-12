"""
Check database size and performance metrics.
"""
from src.database.connection import get_db_session
from src.database.models import Inspection, Violation
from sqlalchemy import select, func, text
from datetime import date

print("=" * 60)
print("Database Size and Performance Check")
print("=" * 60)

with get_db_session() as db:
    # Count records
    total_inspections = db.execute(select(func.count(Inspection.id))).scalar()
    total_violations = db.execute(select(func.count(Violation.id))).scalar()

    print(f"\nRecord Counts:")
    print(f"  Inspections: {total_inspections:,}")
    print(f"  Violations: {total_violations:,}")

    # Date range
    oldest = db.execute(
        select(Inspection.open_date)
        .where(Inspection.open_date.isnot(None))
        .order_by(Inspection.open_date.asc())
        .limit(1)
    ).scalar()

    newest = db.execute(
        select(Inspection.open_date)
        .where(Inspection.open_date.isnot(None))
        .order_by(Inspection.open_date.desc())
        .limit(1)
    ).scalar()

    if oldest and newest:
        print(f"\nDate Range:")
        print(f"  Oldest: {oldest}")
        print(f"  Newest: {newest}")
        print(f"  Span: {(newest - oldest).days} days ({(newest - oldest).days / 365:.1f} years)")

    # Breakdown by year
    print(f"\nInspections by Year:")
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

    # Check table sizes (PostgreSQL specific)
    try:
        result = db.execute(text("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY size_bytes DESC;
        """))

        print(f"\nTable Sizes:")
        for row in result:
            print(f"  {row.tablename}: {row.size}")

        # Total database size
        db_size = db.execute(text("""
            SELECT pg_size_pretty(pg_database_size(current_database())) as size;
        """)).scalar()
        print(f"\nTotal Database Size: {db_size}")

    except Exception as e:
        print(f"\n(Could not fetch table sizes: {e})")

    # Check for potential issues
    print(f"\nData Quality Checks:")

    # Inspections without dates
    no_date = db.execute(
        select(func.count(Inspection.id))
        .where(Inspection.open_date.is_(None))
    ).scalar()
    print(f"  Inspections without open_date: {no_date:,}")

    # Inspections with load_dt
    with_load_dt = db.execute(
        select(func.count(Inspection.id))
        .where(Inspection.load_dt.isnot(None))
    ).scalar()
    print(f"  Inspections with load_dt: {with_load_dt:,}")

    # Old data (pre-2020)
    old_data = db.execute(
        select(func.count(Inspection.id))
        .where(Inspection.open_date < date(2020, 1, 1))
    ).scalar()
    if old_data > 0:
        print(f"  [WARNING] Old data (pre-2020): {old_data:,} - consider running cleanup_old_data.py")
    else:
        print(f"  [OK] No old data (pre-2020)")

    # Recent data (2020+)
    recent_data = db.execute(
        select(func.count(Inspection.id))
        .where(Inspection.open_date >= date(2020, 1, 1))
    ).scalar()
    print(f"  Recent data (2020+): {recent_data:,}")

print("\n" + "=" * 60)
