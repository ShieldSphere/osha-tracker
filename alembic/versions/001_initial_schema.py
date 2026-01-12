"""Initial schema with inspections, companies, and contacts

Revision ID: 001
Revises:
Create Date: 2025-01-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enrichment_status enum
    enrichment_status = sa.Enum(
        'pending', 'in_progress', 'completed', 'failed', 'not_found',
        name='enrichmentstatus'
    )
    enrichment_status.create(op.get_bind(), checkfirst=True)

    # Create inspections table
    op.create_table(
        'inspections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('activity_nr', sa.String(length=20), nullable=False),
        sa.Column('estab_name', sa.String(length=255), nullable=False),
        sa.Column('site_address', sa.String(length=255), nullable=True),
        sa.Column('site_city', sa.String(length=100), nullable=True),
        sa.Column('site_state', sa.String(length=2), nullable=True),
        sa.Column('site_zip', sa.String(length=10), nullable=True),
        sa.Column('open_date', sa.Date(), nullable=True),
        sa.Column('close_case_date', sa.Date(), nullable=True),
        sa.Column('sic_code', sa.String(length=10), nullable=True),
        sa.Column('naics_code', sa.String(length=10), nullable=True),
        sa.Column('insp_type', sa.String(length=10), nullable=True),
        sa.Column('insp_scope', sa.String(length=10), nullable=True),
        sa.Column('total_current_penalty', sa.Float(), nullable=True),
        sa.Column('total_initial_penalty', sa.Float(), nullable=True),
        sa.Column('owner_type', sa.String(length=50), nullable=True),
        sa.Column('adv_notice', sa.String(length=10), nullable=True),
        sa.Column('safety_hlth', sa.String(length=10), nullable=True),
        sa.Column('enrichment_status', sa.Enum('pending', 'in_progress', 'completed', 'failed', 'not_found', name='enrichmentstatus'), nullable=False, server_default='pending'),
        sa.Column('enrichment_error', sa.Text(), nullable=True),
        sa.Column('enrichment_attempts', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_enrichment_attempt', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_inspections_activity_nr', 'inspections', ['activity_nr'], unique=True)
    op.create_index('ix_inspections_open_date', 'inspections', ['open_date'], unique=False)

    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('inspection_id', sa.Integer(), nullable=False),
        sa.Column('apollo_org_id', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('industry', sa.String(length=255), nullable=True),
        sa.Column('sub_industry', sa.String(length=255), nullable=True),
        sa.Column('employee_count', sa.Integer(), nullable=True),
        sa.Column('employee_range', sa.String(length=50), nullable=True),
        sa.Column('annual_revenue', sa.Float(), nullable=True),
        sa.Column('revenue_range', sa.String(length=50), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('linkedin_url', sa.String(length=500), nullable=True),
        sa.Column('facebook_url', sa.String(length=500), nullable=True),
        sa.Column('twitter_url', sa.String(length=500), nullable=True),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create contacts table
    op.create_table(
        'contacts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('apollo_person_id', sa.String(length=100), nullable=True),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('full_name', sa.String(length=200), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('email_status', sa.String(length=50), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('mobile_phone', sa.String(length=50), nullable=True),
        sa.Column('linkedin_url', sa.String(length=500), nullable=True),
        sa.Column('seniority', sa.String(length=50), nullable=True),
        sa.Column('departments', sa.String(length=255), nullable=True),
        sa.Column('contact_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'apollo_person_id', name='uq_company_person')
    )


def downgrade() -> None:
    op.drop_table('contacts')
    op.drop_table('companies')
    op.drop_index('ix_inspections_open_date', table_name='inspections')
    op.drop_index('ix_inspections_activity_nr', table_name='inspections')
    op.drop_table('inspections')

    # Drop enum
    sa.Enum(name='enrichmentstatus').drop(op.get_bind(), checkfirst=True)
