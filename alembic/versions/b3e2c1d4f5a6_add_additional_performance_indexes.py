"""Add additional performance indexes

Revision ID: b3e2c1d4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-01-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3e2c1d4f5a6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Inspections
    op.create_index("ix_inspections_site_city", "inspections", ["site_city"], if_not_exists=True)
    op.create_index("ix_inspections_enrichment_status", "inspections", ["enrichment_status"], if_not_exists=True)
    op.create_index("ix_inspections_insp_type", "inspections", ["insp_type"], if_not_exists=True)
    op.create_index(
        "ix_inspections_state_penalty",
        "inspections",
        ["site_state", "total_current_penalty"],
        if_not_exists=True,
    )

    # Violations
    op.create_index("ix_violations_current_penalty", "violations", ["current_penalty"], if_not_exists=True)

    # Companies / Contacts
    op.create_index("ix_companies_inspection_id", "companies", ["inspection_id"], if_not_exists=True)
    op.create_index("ix_contacts_company_id", "contacts", ["company_id"], if_not_exists=True)

    # Prospects
    op.create_index("ix_prospects_status", "prospects", ["status"], if_not_exists=True)

    # EPA cases
    op.create_index("ix_epa_cases_case_status", "epa_cases", ["case_status"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_epa_cases_case_status", table_name="epa_cases", if_exists=True)
    op.drop_index("ix_prospects_status", table_name="prospects", if_exists=True)
    op.drop_index("ix_contacts_company_id", table_name="contacts", if_exists=True)
    op.drop_index("ix_companies_inspection_id", table_name="companies", if_exists=True)
    op.drop_index("ix_violations_current_penalty", table_name="violations", if_exists=True)
    op.drop_index("ix_inspections_state_penalty", table_name="inspections", if_exists=True)
    op.drop_index("ix_inspections_insp_type", table_name="inspections", if_exists=True)
    op.drop_index("ix_inspections_enrichment_status", table_name="inspections", if_exists=True)
    op.drop_index("ix_inspections_site_city", table_name="inspections", if_exists=True)
