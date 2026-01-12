"""add_crm_tables

Revision ID: 6a2c4d8e9f1b
Revises: 5e7f2a1d9c3b
Create Date: 2026-01-12

Adds CRM tables for prospect management:
- prospects: Links to inspections, tracks pipeline status
- activities: Tracks calls, emails, meetings, notes, tasks
- callbacks: Scheduled follow-ups and reminders
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a2c4d8e9f1b'
down_revision: Union[str, None] = '5e7f2a1d9c3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create prospects table
    op.create_table(
        'prospects',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('inspection_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('new_lead', 'contacted', 'qualified', 'won', 'lost', name='prospectstatus'), nullable=False, server_default='new_lead'),
        sa.Column('priority', sa.String(20), nullable=True),
        sa.Column('estimated_value', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('next_action', sa.String(255), nullable=True),
        sa.Column('next_action_date', sa.Date(), nullable=True),
        sa.Column('lost_reason', sa.String(255), nullable=True),
        sa.Column('won_date', sa.Date(), nullable=True),
        sa.Column('won_value', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('inspection_id')
    )
    op.create_index('ix_prospects_status', 'prospects', ['status'])
    op.create_index('ix_prospects_next_action_date', 'prospects', ['next_action_date'])

    # Create activities table
    op.create_table(
        'activities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('prospect_id', sa.Integer(), nullable=False),
        sa.Column('activity_type', sa.Enum('call', 'email', 'meeting', 'note', 'task', name='activitytype'), nullable=False),
        sa.Column('subject', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('outcome', sa.String(255), nullable=True),
        sa.Column('activity_date', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('task_due_date', sa.Date(), nullable=True),
        sa.Column('task_completed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('task_completed_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_activities_prospect_id', 'activities', ['prospect_id'])
    op.create_index('ix_activities_activity_date', 'activities', ['activity_date'])
    op.create_index('ix_activities_activity_type', 'activities', ['activity_type'])

    # Create callbacks table
    op.create_table(
        'callbacks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('prospect_id', sa.Integer(), nullable=False),
        sa.Column('callback_date', sa.DateTime(), nullable=False),
        sa.Column('callback_type', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'completed', 'cancelled', name='callbackstatus'), nullable=False, server_default='pending'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_callbacks_prospect_id', 'callbacks', ['prospect_id'])
    op.create_index('ix_callbacks_callback_date', 'callbacks', ['callback_date'])
    op.create_index('ix_callbacks_status', 'callbacks', ['status'])


def downgrade() -> None:
    # Drop callbacks table
    op.drop_index('ix_callbacks_status', table_name='callbacks')
    op.drop_index('ix_callbacks_callback_date', table_name='callbacks')
    op.drop_index('ix_callbacks_prospect_id', table_name='callbacks')
    op.drop_table('callbacks')

    # Drop activities table
    op.drop_index('ix_activities_activity_type', table_name='activities')
    op.drop_index('ix_activities_activity_date', table_name='activities')
    op.drop_index('ix_activities_prospect_id', table_name='activities')
    op.drop_table('activities')

    # Drop prospects table
    op.drop_index('ix_prospects_next_action_date', table_name='prospects')
    op.drop_index('ix_prospects_status', table_name='prospects')
    op.drop_table('prospects')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS callbackstatus')
    op.execute('DROP TYPE IF EXISTS activitytype')
    op.execute('DROP TYPE IF EXISTS prospectstatus')
