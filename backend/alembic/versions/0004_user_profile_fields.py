"""user profile fields

Adds the richer signup profile: first/last name, job role, company, country and
use case. All nullable at the DB layer so pre-existing users (who predate these
fields) remain valid; the API requires them for new signups.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    "first_name",
    "last_name",
    "job_role",
    "company",
    "country",
    "use_case",
)


def upgrade() -> None:
    for col in _COLUMNS:
        op.add_column("users", sa.Column(col, sa.String(), nullable=True))


def downgrade() -> None:
    for col in reversed(_COLUMNS):
        op.drop_column("users", col)
