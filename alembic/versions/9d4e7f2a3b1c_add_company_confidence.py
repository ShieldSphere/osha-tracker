"""Add confidence column to companies table

Revision ID: 9d4e7f2a3b1c
Revises: 7b3c5d9e1f2a
Create Date: 2026-01-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d4e7f2a3b1c'
down_revision: Union[str, None] = '7b3c5d9e1f2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add confidence column to companies table
    op.add_column('companies', sa.Column('confidence', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'confidence')
