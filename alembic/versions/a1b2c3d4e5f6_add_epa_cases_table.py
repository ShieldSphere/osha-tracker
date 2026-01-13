"""Add EPA cases table

Revision ID: a1b2c3d4e5f6
Revises: 9d4e7f2a3b1c
Create Date: 2026-01-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9d4e7f2a3b1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create EPA cases table
    op.create_table(
        'epa_cases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('case_number', sa.String(50), nullable=False),
        sa.Column('activity_id', sa.String(50), nullable=True),

        # Case identification
        sa.Column('case_name', sa.String(500), nullable=True),
        sa.Column('case_category', sa.String(10), nullable=True),
        sa.Column('case_category_desc', sa.String(100), nullable=True),
        sa.Column('case_status', sa.String(50), nullable=True),
        sa.Column('case_status_desc', sa.String(100), nullable=True),
        sa.Column('civil_criminal', sa.String(10), nullable=True),

        # Case lead
        sa.Column('case_lead', sa.String(10), nullable=True),
        sa.Column('lead_agency', sa.String(100), nullable=True),
        sa.Column('region', sa.String(10), nullable=True),

        # Dates
        sa.Column('date_filed', sa.Date(), nullable=True),
        sa.Column('settlement_date', sa.Date(), nullable=True),
        sa.Column('date_lodged', sa.Date(), nullable=True),
        sa.Column('date_closed', sa.Date(), nullable=True),

        # Financial data
        sa.Column('fed_penalty', sa.Float(), nullable=True, default=0),
        sa.Column('state_local_penalty', sa.Float(), nullable=True, default=0),
        sa.Column('cost_recovery', sa.Float(), nullable=True, default=0),
        sa.Column('compliance_action_cost', sa.Float(), nullable=True, default=0),
        sa.Column('sep_cost', sa.Float(), nullable=True, default=0),

        # Facility/Company info
        sa.Column('primary_naics', sa.String(10), nullable=True),
        sa.Column('primary_sic', sa.String(10), nullable=True),
        sa.Column('facility_name', sa.String(255), nullable=True),
        sa.Column('facility_city', sa.String(100), nullable=True),
        sa.Column('facility_state', sa.String(2), nullable=True),
        sa.Column('facility_zip', sa.String(10), nullable=True),

        # Environmental laws violated (boolean flags)
        sa.Column('caa_flag', sa.Boolean(), nullable=True, default=False),
        sa.Column('cwa_flag', sa.Boolean(), nullable=True, default=False),
        sa.Column('rcra_flag', sa.Boolean(), nullable=True, default=False),
        sa.Column('sdwa_flag', sa.Boolean(), nullable=True, default=False),
        sa.Column('cercla_flag', sa.Boolean(), nullable=True, default=False),
        sa.Column('epcra_flag', sa.Boolean(), nullable=True, default=False),
        sa.Column('tsca_flag', sa.Boolean(), nullable=True, default=False),
        sa.Column('fifra_flag', sa.Boolean(), nullable=True, default=False),

        # Primary law
        sa.Column('primary_law', sa.String(50), nullable=True),
        sa.Column('primary_section', sa.String(100), nullable=True),

        # Additional flags
        sa.Column('federal_facility', sa.Boolean(), nullable=True, default=False),
        sa.Column('tribal_land', sa.Boolean(), nullable=True, default=False),
        sa.Column('multimedia', sa.Boolean(), nullable=True, default=False),

        # Settlement info
        sa.Column('settlement_count', sa.Integer(), nullable=True, default=0),
        sa.Column('enforcement_outcome', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_epa_cases_case_number', 'epa_cases', ['case_number'], unique=True)
    op.create_index('ix_epa_cases_activity_id', 'epa_cases', ['activity_id'])
    op.create_index('ix_epa_cases_facility_state', 'epa_cases', ['facility_state'])
    op.create_index('ix_epa_cases_date_filed', 'epa_cases', ['date_filed'])
    op.create_index('ix_epa_cases_primary_law', 'epa_cases', ['primary_law'])


def downgrade() -> None:
    op.drop_index('ix_epa_cases_primary_law', 'epa_cases')
    op.drop_index('ix_epa_cases_date_filed', 'epa_cases')
    op.drop_index('ix_epa_cases_facility_state', 'epa_cases')
    op.drop_index('ix_epa_cases_activity_id', 'epa_cases')
    op.drop_index('ix_epa_cases_case_number', 'epa_cases')
    op.drop_table('epa_cases')
