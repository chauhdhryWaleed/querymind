"""query history answer

Stores the agent's natural-language answer alongside each query-history row so the
History view can show the result description without re-running the query.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("query_history", sa.Column("answer", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("query_history", "answer")
