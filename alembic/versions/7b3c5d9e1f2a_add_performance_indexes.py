"""add_performance_indexes

Revision ID: 7b3c5d9e1f2a
Revises: 6a2c4d8e9f1b
Create Date: 2026-01-12

Adds indexes to improve query performance on frequently filtered/sorted columns.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '7b3c5d9e1f2a'
down_revision: Union[str, None] = '6a2c4d8e9f1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Inspections table indexes for common filters and sorts
    op.create_index('ix_inspections_open_date', 'inspections', ['open_date'], if_not_exists=True)
    op.create_index('ix_inspections_site_state', 'inspections', ['site_state'], if_not_exists=True)
    op.create_index('ix_inspections_total_current_penalty', 'inspections', ['total_current_penalty'], if_not_exists=True)
    op.create_index('ix_inspections_estab_name', 'inspections', ['estab_name'], if_not_exists=True)

    # Composite index for common filter combinations
    op.create_index('ix_inspections_state_date', 'inspections', ['site_state', 'open_date'], if_not_exists=True)

    # Violations table index for activity_nr lookups
    op.create_index('ix_violations_activity_nr', 'violations', ['activity_nr'], if_not_exists=True)


def downgrade() -> None:
    op.drop_index('ix_violations_activity_nr', table_name='violations', if_exists=True)
    op.drop_index('ix_inspections_state_date', table_name='inspections', if_exists=True)
    op.drop_index('ix_inspections_estab_name', table_name='inspections', if_exists=True)
    op.drop_index('ix_inspections_total_current_penalty', table_name='inspections', if_exists=True)
    op.drop_index('ix_inspections_site_state', table_name='inspections', if_exists=True)
    op.drop_index('ix_inspections_open_date', table_name='inspections', if_exists=True)
