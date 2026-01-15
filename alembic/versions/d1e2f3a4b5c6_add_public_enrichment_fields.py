"""add public enrichment fields

Revision ID: d1e2f3a4b5c6
Revises: c9d8e7f6a5b4
Create Date: 2026-01-14 16:12:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d1e2f3a4b5c6"
down_revision = "c9d8e7f6a5b4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("companies", sa.Column("public_enrichment_data", sa.Text(), nullable=True))
    op.add_column("companies", sa.Column("public_enriched_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("companies", "public_enriched_at")
    op.drop_column("companies", "public_enrichment_data")
