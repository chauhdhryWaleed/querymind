"""Dialect-specific drivers for user-supplied target databases; distinct from ``app.database`` (the app's own engines)."""

from app.drivers.base import (
    ConnectionCredentials,
    ConnectionTestResult,
    DBDriver,
    IntrospectedColumn,
    IntrospectedFk,
    IntrospectedSchema,
    IntrospectedTable,
    get_driver,
)

__all__ = [
    "ConnectionCredentials",
    "ConnectionTestResult",
    "DBDriver",
    "IntrospectedColumn",
    "IntrospectedFk",
    "IntrospectedSchema",
    "IntrospectedTable",
    "get_driver",
]
