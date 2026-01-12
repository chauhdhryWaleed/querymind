"""initial consolidated Phase 1 schema

Creates the full multi-tenant schema (PLAN §6): auth, workspaces, encrypted
connections + BYOK keys, the schema-index/FK-graph tables with pgvector
embeddings, and per-user activity + audit tables.

Revision ID: 0001
Revises:
Create Date: 2026-05-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)
_GEN_UUID = sa.text("gen_random_uuid()")
_NOW = sa.text("now()")


def upgrade() -> None:
    # Extensions are also created by docker init, but a migration must stand alone
    # (testcontainers, managed Postgres, etc.). IF NOT EXISTS keeps it idempotent.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ---- users & auth -------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", _UUID, server_default=_GEN_UUID, nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("kdf_salt", sa.LargeBinary(), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "email_tokens",
        sa.Column("id", _UUID, server_default=_GEN_UUID, nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("purpose", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("purpose IN ('verify','reset')", name="ck_email_tokens_purpose"),
    )
    op.create_index("ix_email_tokens_user_id", "email_tokens", ["user_id"])
    op.create_index("ix_email_tokens_token_hash", "email_tokens", ["token_hash"])

    op.create_table(
        "sessions",
        sa.Column("id", _UUID, server_default=_GEN_UUID, nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("refresh_token_hash", sa.String(), nullable=False),
        sa.Column("csrf_token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    # ---- workspaces ---------------------------------------------------------
    op.create_table(
        "workspaces",
        sa.Column("id", _UUID, server_default=_GEN_UUID, nullable=False),
        sa.Column("owner_user_id", _UUID, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workspaces_owner_user_id", "workspaces", ["owner_user_id"])

    op.create_table(
        "workspace_members",
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("user_id", _UUID, nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workspace_id", "user_id"),
        sa.CheckConstraint("role IN ('owner','editor','viewer')", name="ck_workspace_members_role"),
    )

    # ---- connections & BYOK keys -------------------------------------------
    op.create_table(
        "connections",
        sa.Column("id", _UUID, server_default=_GEN_UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("dialect", sa.String(), nullable=False),
        sa.Column("wrapped_dek", sa.LargeBinary(), nullable=False),
        sa.Column("host_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("port_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("database_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("username_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("password_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("ssl_mode", sa.String(), nullable=True),
        sa.Column("read_only", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("schema_hash", sa.String(), nullable=True),
        sa.Column("last_introspected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("index_status", sa.String(), server_default="pending", nullable=False),
        sa.Column("index_error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("dialect IN ('postgres','mysql')", name="ck_connections_dialect"),
        sa.CheckConstraint(
            "index_status IN ('pending','indexing','ready','failed')",
            name="ck_connections_index_status",
        ),
    )
    op.create_index("ix_connections_workspace_id", "connections", ["workspace_id"])

    op.create_table(
        "llm_keys",
        sa.Column("id", _UUID, server_default=_GEN_UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("wrapped_dek", sa.LargeBinary(), nullable=False),
        sa.Column("api_key_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("model_override", sa.String(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "provider IN ('anthropic','openai','gemini')", name="ck_llm_keys_provider"
        ),
    )
    op.create_index("ix_llm_keys_workspace_id", "llm_keys", ["workspace_id"])

    # ---- schema index + FK graph -------------------------------------------
    op.create_table(
        "connection_tables",
        sa.Column("id", _UUID, server_default=_GEN_UUID, nullable=False),
        sa.Column("connection_id", _UUID, nullable=False),
        sa.Column("schema_name", sa.String(), server_default="public", nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("row_count", sa.BigInteger(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("priority", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("signature_hash", sa.String(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("query_count", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("connection_id", "schema_name", "name", name="uq_connection_tables_ident"),
        sa.CheckConstraint(
            "kind IN ('table','view','mview','partition')", name="ck_connection_tables_kind"
        ),
    )
    op.create_index("ix_connection_tables_connection_id", "connection_tables", ["connection_id"])
    op.create_index(
        "ix_connection_tables_embedding_hnsw",
        "connection_tables",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_connection_tables_name_trgm",
        "connection_tables",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )

    op.create_table(
        "connection_columns",
        sa.Column("id", _UUID, server_default=_GEN_UUID, nullable=False),
        sa.Column("table_id", _UUID, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("data_type", sa.String(), nullable=False),
        sa.Column("is_nullable", sa.Boolean(), nullable=True),
        sa.Column("is_pk", sa.Boolean(), nullable=True),
        sa.Column("is_fk", sa.Boolean(), nullable=True),
        sa.Column("default_expr", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.ForeignKeyConstraint(["table_id"], ["connection_tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_connection_columns_table_id", "connection_columns", ["table_id"])
    op.create_index(
        "ix_connection_columns_embedding_hnsw",
        "connection_columns",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "connection_fk_edges",
        sa.Column("id", _UUID, server_default=_GEN_UUID, nullable=False),
        sa.Column("from_table_id", _UUID, nullable=False),
        sa.Column("from_column", sa.String(), nullable=False),
        sa.Column("to_table_id", _UUID, nullable=False),
        sa.Column("to_column", sa.String(), nullable=False),
        sa.Column("weight", sa.Float(), server_default="1.0", nullable=False),
        sa.ForeignKeyConstraint(["from_table_id"], ["connection_tables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_table_id"], ["connection_tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_connection_fk_edges_from_table_id", "connection_fk_edges", ["from_table_id"])
    op.create_index("ix_connection_fk_edges_to_table_id", "connection_fk_edges", ["to_table_id"])

    # ---- per-user activity --------------------------------------------------
    # Tenant FKs nullable until M4 wires the query path to auth, then tightened.
    op.create_table(
        "query_history",
        sa.Column("id", _UUID, server_default=_GEN_UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=True),
        sa.Column("user_id", _UUID, nullable=True),
        sa.Column("connection_id", _UUID, nullable=True),
        sa.Column("llm_key_id", _UUID, nullable=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("generated_sql", sa.Text(), nullable=True),
        sa.Column("final_sql", sa.Text(), nullable=True),
        sa.Column("retrieved_tables", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("execution_time_ms", sa.Float(), server_default="0", nullable=False),
        sa.Column("row_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("llm_provider", sa.String(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["connection_id"], ["connections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["llm_key_id"], ["llm_keys.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_query_history_workspace_id", "query_history", ["workspace_id"])
    op.create_index("ix_query_history_user_id", "query_history", ["user_id"])
    op.create_index("ix_query_history_session_id", "query_history", ["session_id"])
    op.create_index("ix_query_history_request_id", "query_history", ["request_id"])

    op.create_table(
        "saved_queries",
        sa.Column("id", _UUID, server_default=_GEN_UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=True),
        sa.Column("user_id", _UUID, nullable=True),
        sa.Column("connection_id", _UUID, nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("sql", sa.Text(), nullable=False),
        sa.Column("tags", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["connection_id"], ["connections.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_queries_workspace_id", "saved_queries", ["workspace_id"])
    op.create_index("ix_saved_queries_user_id", "saved_queries", ["user_id"])

    op.create_table(
        "query_feedback",
        sa.Column("id", _UUID, server_default=_GEN_UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=True),
        sa.Column("user_id", _UUID, nullable=True),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("rating", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("rating IN ('up','down')", name="ck_query_feedback_rating"),
    )
    op.create_index("ix_query_feedback_workspace_id", "query_feedback", ["workspace_id"])
    op.create_index("ix_query_feedback_user_id", "query_feedback", ["user_id"])
    op.create_index("ix_query_feedback_request_id", "query_feedback", ["request_id"])
    op.create_index("ix_query_feedback_session_id", "query_feedback", ["session_id"])

    # ---- audit --------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", _UUID, server_default=_GEN_UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=True),
        sa.Column("user_id", _UUID, nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_workspace_id", "audit_log", ["workspace_id"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])


def downgrade() -> None:
    for table in (
        "audit_log",
        "query_feedback",
        "saved_queries",
        "query_history",
        "connection_fk_edges",
        "connection_columns",
        "connection_tables",
        "llm_keys",
        "connections",
        "workspace_members",
        "workspaces",
        "sessions",
        "email_tokens",
        "users",
    ):
        op.drop_table(table)
