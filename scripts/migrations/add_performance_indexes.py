"""
Migration: Add performance indexes to improve database query speed.

Run this script to add indexes for common queries.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.connection import get_db_session
from sqlalchemy import text


def run_migration():
    """Add performance indexes to database tables."""

    indexes_to_add = [
        # Inspections table - frequently filtered/sorted columns
        ("idx_inspections_estab_name", "inspections", "estab_name"),
        ("idx_inspections_site_city", "inspections", "site_city"),
        ("idx_inspections_total_penalty", "inspections", "total_current_penalty"),
        ("idx_inspections_enrichment_status", "inspections", "enrichment_status"),

        # Composite indexes for common filter combinations
        ("idx_inspections_state_date", "inspections", "site_state, open_date DESC"),
        ("idx_inspections_state_penalty", "inspections", "site_state, total_current_penalty DESC"),

        # Violations table
        ("idx_violations_current_penalty", "violations", "current_penalty"),

        # Companies table
        ("idx_companies_inspection_id", "companies", "inspection_id"),

        # Contacts table
        ("idx_contacts_company_id", "contacts", "company_id"),

        # Prospects table (CRM)
        ("idx_prospects_inspection_id", "prospects", "inspection_id"),
        ("idx_prospects_status", "prospects", "status"),

        # EPA cases table
        ("idx_epa_cases_facility_state", "epa_cases", "facility_state"),
        ("idx_epa_cases_case_status", "epa_cases", "case_status"),
    ]

    print("=" * 60)
    print("Migration: Add Performance Indexes")
    print("=" * 60)

    with get_db_session() as db:
        for index_name, table_name, columns in indexes_to_add:
            try:
                # Check if index already exists
                check_sql = text("""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = :table AND indexname = :idx
                """)
                result = db.execute(check_sql, {"table": table_name, "idx": index_name}).fetchone()

                if result:
                    print(f"  [SKIP] Index '{index_name}' already exists")
                else:
                    # Create index
                    create_sql = text(f"CREATE INDEX {index_name} ON {table_name} ({columns})")
                    db.execute(create_sql)
                    print(f"  [ADD]  Index '{index_name}' on {table_name}({columns})")
            except Exception as e:
                error_msg = str(e)
                if "does not exist" in error_msg:
                    print(f"  [SKIP] Table '{table_name}' does not exist yet")
                else:
                    print(f"  [ERROR] Index '{index_name}': {e}")

        db.commit()

    print("=" * 60)
    print("Migration complete!")
    print("=" * 60)
    print("\nNote: You can also run these directly in Supabase SQL Editor:")
    print("""
-- Inspections indexes
CREATE INDEX IF NOT EXISTS idx_inspections_estab_name ON inspections(estab_name);
CREATE INDEX IF NOT EXISTS idx_inspections_site_city ON inspections(site_city);
CREATE INDEX IF NOT EXISTS idx_inspections_total_penalty ON inspections(total_current_penalty);
CREATE INDEX IF NOT EXISTS idx_inspections_enrichment_status ON inspections(enrichment_status);
CREATE INDEX IF NOT EXISTS idx_inspections_state_date ON inspections(site_state, open_date DESC);
CREATE INDEX IF NOT EXISTS idx_inspections_state_penalty ON inspections(site_state, total_current_penalty DESC);

-- Violations indexes
CREATE INDEX IF NOT EXISTS idx_violations_current_penalty ON violations(current_penalty);

-- Companies indexes
CREATE INDEX IF NOT EXISTS idx_companies_inspection_id ON companies(inspection_id);

-- Contacts indexes
CREATE INDEX IF NOT EXISTS idx_contacts_company_id ON contacts(company_id);

-- Prospects indexes (CRM)
CREATE INDEX IF NOT EXISTS idx_prospects_inspection_id ON prospects(inspection_id);
CREATE INDEX IF NOT EXISTS idx_prospects_status ON prospects(status);

-- EPA cases indexes
CREATE INDEX IF NOT EXISTS idx_epa_cases_facility_state ON epa_cases(facility_state);
CREATE INDEX IF NOT EXISTS idx_epa_cases_case_status ON epa_cases(case_status);
""")


if __name__ == "__main__":
    run_migration()
