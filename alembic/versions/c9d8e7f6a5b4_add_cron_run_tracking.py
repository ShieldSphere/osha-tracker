"""Add cron run tracking table

Revision ID: c9d8e7f6a5b4
Revises: b3e2c1d4f5a6
Create Date: 2026-01-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, None] = "b3e2c1d4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cron_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_name", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cron_runs_job_name", "cron_runs", ["job_name"])
    op.create_index("ix_cron_runs_status", "cron_runs", ["status"])
    op.create_index("ix_cron_runs_started_at", "cron_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_cron_runs_started_at", table_name="cron_runs")
    op.drop_index("ix_cron_runs_status", table_name="cron_runs")
    op.drop_index("ix_cron_runs_job_name", table_name="cron_runs")
    op.drop_table("cron_runs")
