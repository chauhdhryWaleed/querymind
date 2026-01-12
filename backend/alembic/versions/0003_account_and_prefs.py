"""account profile + workspace preferences

Adds a display name to users and per-workspace query preferences
(default model override, result row cap, statement timeout). All nullable so
existing rows fall back to the global defaults in Settings.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(), nullable=True))
    op.add_column("workspaces", sa.Column("default_model", sa.String(), nullable=True))
    op.add_column("workspaces", sa.Column("max_rows", sa.Integer(), nullable=True))
    op.add_column("workspaces", sa.Column("statement_timeout_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("workspaces", "statement_timeout_ms")
    op.drop_column("workspaces", "max_rows")
    op.drop_column("workspaces", "default_model")
    op.drop_column("users", "name")
