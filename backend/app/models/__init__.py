"""SQLAlchemy ORM models. Importing the module registers each table on Base."""

from app.models.audit_log import AuditLog
from app.models.connection import Connection
from app.models.favorite import SavedQuery
from app.models.feedback import QueryFeedback
from app.models.history import QueryHistory
from app.models.llm_key import LlmKey
from app.models.schema_index import (
    ConnectionColumn,
    ConnectionFkEdge,
    ConnectionTable,
)
from app.models.session import UserSession
from app.models.user import EmailToken, User
from app.models.workspace import Workspace, WorkspaceMember

__all__ = [
    "AuditLog",
    "Connection",
    "ConnectionColumn",
    "ConnectionFkEdge",
    "ConnectionTable",
    "EmailToken",
    "LlmKey",
    "QueryFeedback",
    "QueryHistory",
    "SavedQuery",
    "User",
    "UserSession",
    "Workspace",
    "WorkspaceMember",
]
