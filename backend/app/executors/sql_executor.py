import asyncio
import time

import sqlglot
import sqlglot.expressions as exp
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class ExecutionResult(BaseModel):
    rows: list[dict]
    row_count: int
    columns: list[str]
    execution_time_ms: float
    truncated: bool


class QueryTimeoutError(Exception):
    pass


class QueryExecutionError(Exception):
    pass


class SqlExecutor:
    """Executes read-only SQL with a hard timeout, automatic LIMIT injection, and row cap enforcement."""

    def __init__(self, max_rows: int = 1000, timeout_seconds: float = 30.0) -> None:
        self._max_rows = max_rows
        self._timeout = timeout_seconds

    async def execute(self, sql: str, session: AsyncSession) -> ExecutionResult:
        bounded_sql = self._inject_limit(sql)
        start = time.perf_counter()

        try:
            result = await asyncio.wait_for(
                self._run_query(bounded_sql, session),
                timeout=self._timeout,
            )
        except TimeoutError as exc:
            raise QueryTimeoutError(
                f"Query exceeded the {self._timeout}s timeout. "
                "Try adding a more restrictive WHERE clause or a smaller LIMIT."
            ) from exc

        elapsed_ms = (time.perf_counter() - start) * 1000

        rows = [dict(row._mapping) for row in result]
        columns = list(result.keys()) if result.keys() else []
        truncated = len(rows) >= self._max_rows

        return ExecutionResult(
            rows=rows,
            row_count=len(rows),
            columns=columns,
            execution_time_ms=round(elapsed_ms, 2),
            truncated=truncated,
        )

    async def _run_query(self, sql: str, session: AsyncSession):  # type: ignore[return]
        return await session.execute(text(sql))

    def _inject_limit(self, sql: str) -> str:
        """Add LIMIT if not present, and cap any existing LIMIT to MAX_ROWS."""
        try:
            tree = sqlglot.parse_one(sql, dialect="postgres")
        except Exception:
            # If we can't parse, pass through and let the DB surface the error.
            return sql

        has_limit = any(isinstance(n, exp.Limit) for n in tree.walk())
        if has_limit:
            for node in tree.walk():
                if isinstance(node, exp.Limit):
                    limit_expr = node.expression
                    if (
                        isinstance(limit_expr, exp.Literal)
                        and limit_expr.is_number
                        and int(limit_expr.this) > self._max_rows
                    ):
                        node.set("expression", exp.Literal.number(self._max_rows))
            return tree.sql(dialect="postgres")

        tree = tree.limit(self._max_rows)
        return tree.sql(dialect="postgres")
