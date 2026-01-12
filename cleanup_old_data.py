"""
Cleanup script to remove inspections older than 2020 from the database.
This keeps the database focused on recent, relevant data.
"""
from src.database.connection import get_db_session
from src.database.models import Inspection, Violation
from sqlalchemy import select, delete
from datetime import date

def cleanup_old_inspections():
    """Remove inspections opened before 2020."""

    cutoff_date = date(2020, 1, 1)

    print("=" * 60)
    print("Cleaning Up Old Data (pre-2020)")
    print("=" * 60)

    with get_db_session() as db:
        # First, count what we'll be removing
        old_inspections = db.execute(
            select(Inspection)
            .where(Inspection.open_date < cutoff_date)
        ).scalars().all()

        old_count = len(old_inspections)

        if old_count == 0:
            print("\nNo old inspections to remove.")
            return

        print(f"\nFound {old_count:,} inspections from before 2020")

        # Get activity numbers for violation cleanup
        old_activity_nrs = [insp.activity_nr for insp in old_inspections]

        # Count related violations
        old_violations_count = db.execute(
            select(Violation)
            .where(Violation.activity_nr.in_(old_activity_nrs))
        ).scalars().all()
        old_viol_count = len(old_violations_count)

        print(f"Found {old_viol_count:,} related violations")

        # Show breakdown by year
        print("\nBreakdown by year:")
        years = {}
        for insp in old_inspections:
            if insp.open_date:
                year = insp.open_date.year
                years[year] = years.get(year, 0) + 1

        for year in sorted(years.keys()):
            print(f"  {year}: {years[year]:,}")

        # Confirm deletion
        response = input(f"\nDelete {old_count:,} inspections and {old_viol_count:,} violations? (yes/no): ")

        if response.lower() != 'yes':
            print("Cancelled.")
            return

        print("\nDeleting old data...")

        # Delete violations first (foreign key constraint)
        if old_viol_count > 0:
            deleted_viols = db.execute(
                delete(Violation)
                .where(Violation.activity_nr.in_(old_activity_nrs))
            )
            db.commit()
            print(f"  Deleted {old_viol_count:,} violations")

        # Delete inspections
        deleted_insps = db.execute(
            delete(Inspection)
            .where(Inspection.open_date < cutoff_date)
        )
        db.commit()
        print(f"  Deleted {old_count:,} inspections")

        # Show remaining counts
        remaining_insps = db.execute(select(Inspection)).scalars().all()
        remaining_viols = db.execute(select(Violation)).scalars().all()

        print(f"\nRemaining in database:")
        print(f"  Inspections: {len(remaining_insps):,}")
        print(f"  Violations: {len(remaining_viols):,}")

        # Show date range of remaining data
        oldest = db.execute(
            select(Inspection)
            .where(Inspection.open_date.isnot(None))
            .order_by(Inspection.open_date.asc())
            .limit(1)
        ).scalar_one_or_none()

        newest = db.execute(
            select(Inspection)
            .where(Inspection.open_date.isnot(None))
            .order_by(Inspection.open_date.desc())
            .limit(1)
        ).scalar_one_or_none()

        if oldest and newest:
            print(f"\nDate range: {oldest.open_date} to {newest.open_date}")

        print("\nCleanup complete!")
        print("=" * 60)

if __name__ == "__main__":
    cleanup_old_inspections()
