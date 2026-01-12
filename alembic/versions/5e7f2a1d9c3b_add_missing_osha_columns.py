"""add_missing_osha_columns

Revision ID: 5e7f2a1d9c3b
Revises: 4bcbb3c3fb36
Create Date: 2026-01-09

Adds missing OSHA columns to inspections and violations tables
for complete CSV data import.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e7f2a1d9c3b'
down_revision: Union[str, None] = '4bcbb3c3fb36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing columns to inspections table
    op.add_column('inspections', sa.Column('reporting_id', sa.String(20), nullable=True))
    op.add_column('inspections', sa.Column('state_flag', sa.String(5), nullable=True))
    op.add_column('inspections', sa.Column('mail_street', sa.String(255), nullable=True))
    op.add_column('inspections', sa.Column('mail_city', sa.String(100), nullable=True))
    op.add_column('inspections', sa.Column('mail_state', sa.String(2), nullable=True))
    op.add_column('inspections', sa.Column('mail_zip', sa.String(10), nullable=True))
    op.add_column('inspections', sa.Column('case_mod_date', sa.Date(), nullable=True))
    op.add_column('inspections', sa.Column('why_no_insp', sa.String(10), nullable=True))
    op.add_column('inspections', sa.Column('owner_code', sa.String(10), nullable=True))
    op.add_column('inspections', sa.Column('union_status', sa.String(10), nullable=True))
    op.add_column('inspections', sa.Column('safety_manuf', sa.String(5), nullable=True))
    op.add_column('inspections', sa.Column('safety_const', sa.String(5), nullable=True))
    op.add_column('inspections', sa.Column('safety_marit', sa.String(5), nullable=True))
    op.add_column('inspections', sa.Column('health_manuf', sa.String(5), nullable=True))
    op.add_column('inspections', sa.Column('health_const', sa.String(5), nullable=True))
    op.add_column('inspections', sa.Column('health_marit', sa.String(5), nullable=True))
    op.add_column('inspections', sa.Column('migrant', sa.String(5), nullable=True))
    op.add_column('inspections', sa.Column('nr_in_estab', sa.Integer(), nullable=True))
    op.add_column('inspections', sa.Column('host_est_key', sa.String(50), nullable=True))

    # Add missing columns to violations table
    op.add_column('violations', sa.Column('delete_flag', sa.String(5), nullable=True))
    op.add_column('violations', sa.Column('fta_insp_nr', sa.String(20), nullable=True))
    op.add_column('violations', sa.Column('fta_issuance_date', sa.Date(), nullable=True))
    op.add_column('violations', sa.Column('fta_penalty', sa.Float(), nullable=True))
    op.add_column('violations', sa.Column('fta_contest_date', sa.Date(), nullable=True))
    op.add_column('violations', sa.Column('fta_final_order_date', sa.Date(), nullable=True))
    op.add_column('violations', sa.Column('hazsub1', sa.String(50), nullable=True))
    op.add_column('violations', sa.Column('hazsub2', sa.String(50), nullable=True))
    op.add_column('violations', sa.Column('hazsub3', sa.String(50), nullable=True))
    op.add_column('violations', sa.Column('hazsub4', sa.String(50), nullable=True))
    op.add_column('violations', sa.Column('hazsub5', sa.String(50), nullable=True))
    op.add_column('violations', sa.Column('load_dt', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove columns from violations table
    op.drop_column('violations', 'load_dt')
    op.drop_column('violations', 'hazsub5')
    op.drop_column('violations', 'hazsub4')
    op.drop_column('violations', 'hazsub3')
    op.drop_column('violations', 'hazsub2')
    op.drop_column('violations', 'hazsub1')
    op.drop_column('violations', 'fta_final_order_date')
    op.drop_column('violations', 'fta_contest_date')
    op.drop_column('violations', 'fta_penalty')
    op.drop_column('violations', 'fta_issuance_date')
    op.drop_column('violations', 'fta_insp_nr')
    op.drop_column('violations', 'delete_flag')

    # Remove columns from inspections table
    op.drop_column('inspections', 'host_est_key')
    op.drop_column('inspections', 'nr_in_estab')
    op.drop_column('inspections', 'migrant')
    op.drop_column('inspections', 'health_marit')
    op.drop_column('inspections', 'health_const')
    op.drop_column('inspections', 'health_manuf')
    op.drop_column('inspections', 'safety_marit')
    op.drop_column('inspections', 'safety_const')
    op.drop_column('inspections', 'safety_manuf')
    op.drop_column('inspections', 'union_status')
    op.drop_column('inspections', 'owner_code')
    op.drop_column('inspections', 'why_no_insp')
    op.drop_column('inspections', 'case_mod_date')
    op.drop_column('inspections', 'mail_zip')
    op.drop_column('inspections', 'mail_state')
    op.drop_column('inspections', 'mail_city')
    op.drop_column('inspections', 'mail_street')
    op.drop_column('inspections', 'state_flag')
    op.drop_column('inspections', 'reporting_id')
