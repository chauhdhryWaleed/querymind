"""asyncpg-backed Postgres driver for user-supplied databases."""

from __future__ import annotations

import asyncio
import ssl as ssl_module
import time

import asyncpg

from app.drivers.base import (
    ConnectionCredentials,
    ConnectionTestResult,
    IntrospectedColumn,
    IntrospectedFk,
    IntrospectedSchema,
    IntrospectedTable,
)

# Catalogs we never index.
_SYSTEM_SCHEMAS = ("pg_catalog", "information_schema")

_TABLES_SQL = """
SELECT n.nspname AS schema, c.relname AS name,
       CASE c.relkind WHEN 'r' THEN 'table' WHEN 'v' THEN 'view'
                      WHEN 'm' THEN 'mview' WHEN 'p' THEN 'table' END AS kind,
       c.reltuples::bigint AS row_count,
       obj_description(c.oid) AS description
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'v', 'm', 'p')
  AND NOT c.relispartition                       -- exclude partition children
  AND n.nspname <> ALL($1::text[])
  AND n.nspname NOT LIKE 'pg_temp%'
  AND n.nspname NOT LIKE 'pg_toast%'
ORDER BY n.nspname, c.relname
"""

_COLUMNS_SQL = """
SELECT n.nspname AS schema, c.relname AS table_name, a.attname AS name,
       format_type(a.atttypid, a.atttypmod) AS data_type,
       NOT a.attnotnull AS is_nullable,
       pg_get_expr(d.adbin, d.adrelid) AS default_expr,
       col_description(c.oid, a.attnum) AS description,
       a.attnum AS ordinal
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
WHERE a.attnum > 0 AND NOT a.attisdropped
  AND c.relkind IN ('r', 'v', 'm', 'p') AND NOT c.relispartition
  AND n.nspname <> ALL($1::text[])
  AND n.nspname NOT LIKE 'pg_temp%' AND n.nspname NOT LIKE 'pg_toast%'
ORDER BY n.nspname, c.relname, a.attnum
"""

_PK_SQL = """
SELECT n.nspname AS schema, c.relname AS table_name, a.attname AS column_name
FROM pg_index i
JOIN pg_class c ON c.oid = i.indrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = ANY(i.indkey)
WHERE i.indisprimary AND n.nspname <> ALL($1::text[])
"""

_FK_SQL = """
SELECT ns.nspname  AS from_schema, cl.relname  AS from_table,  att.attname  AS from_column,
       fns.nspname AS to_schema,   fcl.relname AS to_table,    fatt.attname AS to_column
FROM pg_constraint con
JOIN pg_class cl ON cl.oid = con.conrelid
JOIN pg_namespace ns ON ns.oid = cl.relnamespace
JOIN pg_class fcl ON fcl.oid = con.confrelid
JOIN pg_namespace fns ON fns.oid = fcl.relnamespace
JOIN LATERAL unnest(con.conkey, con.confkey) WITH ORDINALITY AS k(conkey, confkey, ord) ON true
JOIN pg_attribute att  ON att.attrelid  = con.conrelid  AND att.attnum  = k.conkey
JOIN pg_attribute fatt ON fatt.attrelid = con.confrelid AND fatt.attnum = k.confkey
WHERE con.contype = 'f' AND ns.nspname <> ALL($1::text[])
"""


def _ssl_arg(ssl_mode: str | None):
    """Translate a libpq-style sslmode into asyncpg's ``ssl`` argument."""
    if ssl_mode in (None, "", "disable", "prefer"):
        return False
    # require / verify-ca / verify-full → use TLS. We don't pin a CA in Phase 1.
    ctx = ssl_module.create_default_context()
    if ssl_mode == "require":
        ctx.check_hostname = False
        ctx.verify_mode = ssl_module.CERT_NONE
    return ctx


class PostgresDriver:
    dialect = "postgres"

    async def _connect(self, creds: ConnectionCredentials, timeout: float) -> asyncpg.Connection:
        return await asyncio.wait_for(
            asyncpg.connect(
                host=creds.host,
                port=creds.port,
                user=creds.username,
                password=creds.password,
                database=creds.database,
                ssl=_ssl_arg(creds.ssl_mode),
                timeout=timeout,
            ),
            timeout=timeout,
        )

    async def test(
        self, creds: ConnectionCredentials, *, timeout: float = 8.0
    ) -> ConnectionTestResult:
        start = time.perf_counter()
        conn = None
        try:
            conn = await self._connect(creds, timeout)
            version = await conn.fetchval("SELECT version()")
            latency_ms = (time.perf_counter() - start) * 1000
            return ConnectionTestResult(
                ok=True,
                message="Connection successful",
                server_version=version,
                latency_ms=round(latency_ms, 1),
            )
        except TimeoutError:
            return ConnectionTestResult(
                ok=False, message=f"Connection timed out after {timeout:.0f}s"
            )
        except (asyncpg.PostgresError, OSError) as exc:
            return ConnectionTestResult(ok=False, message=f"{type(exc).__name__}: {exc}")
        finally:
            if conn is not None:
                await conn.close()

    async def introspect(
        self, creds: ConnectionCredentials, *, timeout: float = 30.0
    ) -> IntrospectedSchema:
        conn = await self._connect(creds, timeout)
        try:
            sys_schemas = list(_SYSTEM_SCHEMAS)
            table_rows = await conn.fetch(_TABLES_SQL, sys_schemas)
            column_rows = await conn.fetch(_COLUMNS_SQL, sys_schemas)
            pk_rows = await conn.fetch(_PK_SQL, sys_schemas)
            fk_rows = await conn.fetch(_FK_SQL, sys_schemas)
        finally:
            await conn.close()

        pk_set = {(r["schema"], r["table_name"], r["column_name"]) for r in pk_rows}
        fk_col_set = {(r["from_schema"], r["from_table"], r["from_column"]) for r in fk_rows}

        cols_by_table: dict[tuple[str, str], list[IntrospectedColumn]] = {}
        for r in column_rows:
            key = (r["schema"], r["table_name"])
            cols_by_table.setdefault(key, []).append(
                IntrospectedColumn(
                    name=r["name"],
                    data_type=r["data_type"],
                    is_nullable=r["is_nullable"],
                    is_pk=(r["schema"], r["table_name"], r["name"]) in pk_set,
                    is_fk=(r["schema"], r["table_name"], r["name"]) in fk_col_set,
                    default_expr=r["default_expr"],
                    description=r["description"],
                )
            )

        tables = [
            IntrospectedTable(
                schema_name=r["schema"],
                name=r["name"],
                kind=r["kind"],
                row_count=int(r["row_count"])
                if r["row_count"] is not None and r["row_count"] >= 0
                else None,
                description=r["description"],
                columns=cols_by_table.get((r["schema"], r["name"]), []),
            )
            for r in table_rows
        ]
        fks = [
            IntrospectedFk(
                from_schema=r["from_schema"],
                from_table=r["from_table"],
                from_column=r["from_column"],
                to_schema=r["to_schema"],
                to_table=r["to_table"],
                to_column=r["to_column"],
            )
            for r in fk_rows
        ]
        return IntrospectedSchema(tables=tables, fks=fks)
