"""
Migration: Add web enrichment columns to companies table.

Run this script to add the new columns for DBA names, enrichment tracking, etc.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.connection import get_db_session
from sqlalchemy import text


def run_migration():
    """Add new columns to companies table for web enrichment."""

    # Columns to add with their types
    columns_to_add = [
        ("legal_name", "VARCHAR(255)"),
        ("operating_name", "VARCHAR(255)"),
        ("dba_names", "TEXT"),
        ("parent_company", "VARCHAR(255)"),
        ("enrichment_source", "VARCHAR(50)"),
        ("web_enrichment_data", "TEXT"),
        ("web_enriched_at", "TIMESTAMP"),
        ("apollo_enriched_at", "TIMESTAMP"),
    ]

    print("=" * 60)
    print("Migration: Add Web Enrichment Columns to Companies Table")
    print("=" * 60)

    with get_db_session() as db:
        for column_name, column_type in columns_to_add:
            try:
                # Check if column exists
                check_sql = text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'companies' AND column_name = :col
                """)
                result = db.execute(check_sql, {"col": column_name}).fetchone()

                if result:
                    print(f"  [SKIP] Column '{column_name}' already exists")
                else:
                    # Add column
                    alter_sql = text(f"ALTER TABLE companies ADD COLUMN {column_name} {column_type}")
                    db.execute(alter_sql)
                    print(f"  [ADD]  Column '{column_name}' ({column_type})")
            except Exception as e:
                print(f"  [ERROR] Column '{column_name}': {e}")

        db.commit()

    print("=" * 60)
    print("Migration complete!")
    print("=" * 60)


if __name__ == "__main__":
    run_migration()
