import sqlglot
import sqlglot.expressions as exp
from sqlalchemy.ext.asyncio import AsyncSession

from app.validators.base import BaseValidator, ValidationResult

_SYSTEM_SCHEMAS = {"information_schema", "pg_catalog"}


def _is_system_table(node: exp.Table) -> bool:
    """Read-only system catalogs (qualified, or unqualified pg_* on the search path)."""
    if node.db and node.db.lower() in _SYSTEM_SCHEMAS:
        return True
    return bool(node.name) and node.name.lower().startswith("pg_")


class SchemaValidator(BaseValidator):
    """Walks the SQL AST and checks every referenced table and column exists in the introspected schema dict."""

    @property
    def stage_name(self) -> str:
        return "schema"

    async def validate(
        self,
        sql: str,
        schema: dict,
        session: AsyncSession | None = None,
    ) -> ValidationResult:
        try:
            tree = sqlglot.parse_one(sql, dialect="postgres")
        except Exception:
            return self._pass()

        tables = schema.get("tables", {})
        columns_by_table = {
            name.lower(): {col.lower() for col in meta.get("columns", {})}
            for name, meta in tables.items()
        }
        cte_names = {cte.alias.lower() for cte in tree.find_all(exp.CTE) if cte.alias}
        known_tables = set(columns_by_table) | cte_names
        errors: list[str] = []

        referenced_tables: dict[str, str] = {}

        for node in tree.walk():
            if isinstance(node, exp.Table):
                if _is_system_table(node):
                    continue
                table_name = node.name.lower() if node.name else ""
                alias = node.alias.lower() if node.alias else table_name
                if table_name and table_name not in ("dual",):
                    referenced_tables[alias] = table_name
                    if table_name not in known_tables:
                        errors.append(
                            f"Table '{table_name}' does not exist. "
                            f"Available tables: {sorted(tables)}"
                        )

        for node in tree.walk():
            if isinstance(node, exp.Column):
                col_name = node.name.lower() if node.name else ""
                table_alias = node.table.lower() if node.table else ""

                if not col_name or col_name == "*":
                    continue

                if table_alias:
                    real_table = referenced_tables.get(table_alias, table_alias)
                    known_cols = columns_by_table.get(real_table)
                    if known_cols and col_name not in known_cols:
                        errors.append(
                            f"Column '{col_name}' does not exist in table '{real_table}'. "
                            f"Available: {sorted(known_cols)}"
                        )

        if errors:
            return self._fail(*errors)
        return self._pass()
