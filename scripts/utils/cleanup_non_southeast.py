"""
Cleanup script to remove inspections from non-southeast states.
This keeps the database focused on the target region.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.connection import get_db_session
from src.database.models import Inspection, Violation
from src.services.sync_service import SOUTHEAST_STATES
from sqlalchemy import select, delete, func

def cleanup_non_southeast():
    """Remove inspections not in southeast states."""

    print("=" * 60)
    print("Cleaning Up Non-Southeast State Data")
    print("=" * 60)

    print(f"\nSoutheast states to keep: {', '.join(sorted(SOUTHEAST_STATES))}")

    with get_db_session() as db:
        # Count current data by state
        state_counts = db.execute(
            select(Inspection.site_state, func.count(Inspection.id))
            .group_by(Inspection.site_state)
            .order_by(func.count(Inspection.id).desc())
        ).all()

        print(f"\nCurrent data by state:")
        se_count = 0
        non_se_count = 0
        for state, count in state_counts:
            is_se = state in SOUTHEAST_STATES if state else False
            marker = "[SE]" if is_se else "    "
            print(f"  {marker} {state or 'None'}: {count:,}")
            if is_se:
                se_count += count
            else:
                non_se_count += count

        print(f"\nSummary:")
        print(f"  Southeast states: {se_count:,} inspections")
        print(f"  Non-southeast states: {non_se_count:,} inspections")

        if non_se_count == 0:
            print("\nNo non-southeast data to remove.")
            return

        # Get non-SE inspections
        non_se_inspections = db.execute(
            select(Inspection)
            .where(~Inspection.site_state.in_(SOUTHEAST_STATES))
        ).scalars().all()

        # Get activity numbers for violation cleanup
        non_se_activity_nrs = [insp.activity_nr for insp in non_se_inspections]

        # Count related violations
        non_se_violations = db.execute(
            select(func.count(Violation.id))
            .where(Violation.activity_nr.in_(non_se_activity_nrs))
        ).scalar() if non_se_activity_nrs else 0

        print(f"\nWill delete:")
        print(f"  {non_se_count:,} inspections from non-southeast states")
        print(f"  {non_se_violations:,} related violations")

        # Confirm deletion
        response = input(f"\nProceed with deletion? (yes/no): ")

        if response.lower() != 'yes':
            print("Cancelled.")
            return

        print("\nDeleting non-southeast data...")

        # Delete violations first (foreign key constraint)
        if non_se_violations > 0:
            db.execute(
                delete(Violation)
                .where(Violation.activity_nr.in_(non_se_activity_nrs))
            )
            db.commit()
            print(f"  Deleted {non_se_violations:,} violations")

        # Delete inspections
        db.execute(
            delete(Inspection)
            .where(~Inspection.site_state.in_(SOUTHEAST_STATES))
        )
        db.commit()
        print(f"  Deleted {non_se_count:,} inspections")

        # Show remaining counts
        remaining_insps = db.execute(select(func.count(Inspection.id))).scalar()
        remaining_viols = db.execute(select(func.count(Violation.id))).scalar()

        print(f"\nRemaining in database:")
        print(f"  Inspections: {remaining_insps:,}")
        print(f"  Violations: {remaining_viols:,}")

        # Show state breakdown
        print(f"\nRemaining states:")
        state_counts = db.execute(
            select(Inspection.site_state, func.count(Inspection.id))
            .group_by(Inspection.site_state)
            .order_by(func.count(Inspection.id).desc())
        ).all()
        for state, count in state_counts:
            print(f"  {state}: {count:,}")

        print("\nCleanup complete!")
        print("=" * 60)

if __name__ == "__main__":
    cleanup_non_southeast()
