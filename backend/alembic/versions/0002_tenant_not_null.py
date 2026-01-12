"""tighten activity tenant FKs to NOT NULL

M1 created query_history / saved_queries / query_feedback with nullable
workspace_id + user_id (the query path wasn't auth-wired yet). M4 wires it, so
these are now always populated. Drop any pre-auth NULL rows, then enforce.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("query_history", "saved_queries", "query_feedback")


def upgrade() -> None:
    for table in _TABLES:
        # Remove orphan pre-auth rows that can't be back-filled with a tenant.
        op.execute(f"DELETE FROM {table} WHERE workspace_id IS NULL OR user_id IS NULL")
        op.alter_column(table, "workspace_id", nullable=False)
        op.alter_column(table, "user_id", nullable=False)


def downgrade() -> None:
    for table in _TABLES:
        op.alter_column(table, "user_id", nullable=True)
        op.alter_column(table, "workspace_id", nullable=True)
