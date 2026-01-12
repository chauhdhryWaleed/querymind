"""RetrievalService: pick the relevant schema slice via reranked search and FK expansion."""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.embedder import EmbedderProtocol
from app.models.schema_index import ConnectionColumn, ConnectionFkEdge, ConnectionTable

# Rerank weights (PLAN §9.3).
W_LEXICAL = 0.4
W_VECTOR = 0.4
W_RECENCY = 0.1
W_PRIORITY = 0.1

DEFAULT_SEED_K = 8
DEFAULT_MAX_TABLES = 15
DEFAULT_TOKEN_BUDGET = 5000
_GRAPH_DEPTH = 2


@dataclass
class RetrievedTable:
    table_id: uuid.UUID
    schema_name: str
    name: str
    lexical: float
    vector: float
    recency: float
    priority: float
    score: float
    via: str  # "seed" | "fk-expand"
    tier: int = 0


@dataclass
class RetrievalResult:
    tables: list[RetrievedTable]
    formatted_schema: str
    token_estimate: int
    raw_schema: dict = field(default_factory=dict)  # for SchemaValidator
    seed_count: int = 0
    expanded_count: int = 0


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


class RetrievalService:
    def __init__(self, db: AsyncSession, embedder: EmbedderProtocol) -> None:
        self._db = db
        self._embedder = embedder

    async def retrieve(
        self,
        connection_id: uuid.UUID,
        question: str,
        *,
        seed_k: int = DEFAULT_SEED_K,
        max_tables: int = DEFAULT_MAX_TABLES,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
    ) -> RetrievalResult:
        qvec = self._embedder.encode_query(question)

        # One pass: per-table cosine similarity + trigram word-similarity to the question.
        dist = ConnectionTable.embedding.cosine_distance(qvec)
        lex = func.word_similarity(question, ConnectionTable.name)
        rows = (
            await self._db.execute(
                select(
                    ConnectionTable.id,
                    ConnectionTable.schema_name,
                    ConnectionTable.name,
                    ConnectionTable.priority,
                    ConnectionTable.query_count,
                    (1 - dist).label("vscore"),
                    lex.label("lscore"),
                ).where(ConnectionTable.connection_id == connection_id)
            )
        ).all()
        if not rows:
            return RetrievalResult(tables=[], formatted_schema="", token_estimate=0)

        max_qc = max((r.query_count or 0) for r in rows) or 1
        scored: dict[uuid.UUID, RetrievedTable] = {}
        for r in rows:
            lexical = float(r.lscore or 0.0)
            vector = max(0.0, float(r.vscore or 0.0))
            recency = (r.query_count or 0) / max_qc
            priority = min((r.priority or 0) / 5.0, 1.0)
            score = (
                W_LEXICAL * lexical
                + W_VECTOR * vector
                + W_RECENCY * recency
                + W_PRIORITY * priority
            )
            scored[r.id] = RetrievedTable(
                table_id=r.id,
                schema_name=r.schema_name,
                name=r.name,
                lexical=round(lexical, 3),
                vector=round(vector, 3),
                recency=round(recency, 3),
                priority=round(priority, 3),
                score=round(score, 3),
                via="seed",
            )

        seeds = sorted(scored.values(), key=lambda t: t.score, reverse=True)[:seed_k]
        seed_ids = {t.table_id for t in seeds}

        # FK-graph expansion (undirected BFS, depth 2) among the connection's tables.
        expanded_ids = await self._expand(connection_id, seed_ids, scored)
        for tid in expanded_ids:
            scored[tid].via = "fk-expand"

        final_ids = list(seed_ids) + [tid for tid in expanded_ids if tid not in seed_ids]
        final = [scored[tid] for tid in final_ids]
        final.sort(key=lambda t: (t.via != "seed", -t.score))  # seeds first, then by score
        final = final[:max_tables]

        formatted, used, raw_schema = await self._format_tiered(final, token_budget)
        return RetrievalResult(
            tables=used,
            formatted_schema=formatted,
            token_estimate=_estimate_tokens(formatted),
            raw_schema=raw_schema,
            seed_count=len(seed_ids),
            expanded_count=len(final) - len(seed_ids & {t.table_id for t in final}),
        )

    async def _expand(
        self,
        connection_id: uuid.UUID,
        seed_ids: set[uuid.UUID],
        scored: dict[uuid.UUID, RetrievedTable],
    ) -> set[uuid.UUID]:
        valid = set(scored.keys())
        edges = (
            await self._db.execute(
                select(ConnectionFkEdge.from_table_id, ConnectionFkEdge.to_table_id).where(
                    ConnectionFkEdge.from_table_id.in_(valid)
                )
            )
        ).all()
        adj: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
        for a, b in edges:
            if a in valid and b in valid:
                adj[a].add(b)
                adj[b].add(a)

        reached: set[uuid.UUID] = set()
        queue: deque[tuple[uuid.UUID, int]] = deque((s, 0) for s in seed_ids)
        visited = set(seed_ids)
        while queue:
            node, depth = queue.popleft()
            if depth >= _GRAPH_DEPTH:
                continue
            for nb in adj[node]:
                if nb not in visited:
                    visited.add(nb)
                    if nb not in seed_ids:
                        reached.add(nb)
                    queue.append((nb, depth + 1))
        return reached

    async def _format_tiered(
        self, tables: list[RetrievedTable], token_budget: int
    ) -> tuple[str, list[RetrievedTable], dict]:
        """Render tables by tier and return the lowercased raw_schema the SchemaValidator needs."""
        if not tables:
            return "", [], {"tables": {}}
        table_ids = [t.table_id for t in tables]
        cols = (
            await self._db.scalars(
                select(ConnectionColumn).where(ConnectionColumn.table_id.in_(table_ids))
            )
        ).all()
        cols_by_table: dict[uuid.UUID, list[ConnectionColumn]] = defaultdict(list)
        for c in cols:
            cols_by_table[c.table_id].append(c)

        # FK reference labels for Tier 1 (column -> target.table.column).
        edges = (
            await self._db.scalars(
                select(ConnectionFkEdge).where(ConnectionFkEdge.from_table_id.in_(table_ids))
            )
        ).all()
        name_by_id = {t.table_id: t.name for t in tables}
        ref_by_col: dict[tuple[uuid.UUID, str], str] = {}
        for e in edges:
            ref_by_col[(e.from_table_id, e.from_column)] = (
                f"{name_by_id.get(e.to_table_id, '?')}.{e.to_column}"
            )

        blocks: list[str] = []
        used: list[RetrievedTable] = []
        raw_tables: dict[str, dict] = {}
        tokens = 0
        for idx, t in enumerate(tables):
            tier = 1 if idx < 3 else (2 if idx < 8 else 3)
            t.tier = tier
            tcols = cols_by_table.get(t.table_id, [])
            block = self._render(t, tcols, ref_by_col, tier)
            btok = _estimate_tokens(block)
            if tokens + btok > token_budget and used:
                break  # budget exhausted; drop the low-priority tail
            blocks.append(block)
            used.append(t)
            tokens += btok
            raw_tables[t.name.lower()] = {
                "columns": {
                    c.name.lower(): {
                        "type": c.data_type,
                        "nullable": c.is_nullable,
                        "primary_key": c.is_pk,
                    }
                    for c in tcols
                },
                "foreign_keys": [
                    {
                        "from_column": col,
                        "to_table": ref.split(".")[0],
                        "to_column": ref.split(".")[1],
                    }
                    for (tid, col), ref in ref_by_col.items()
                    if tid == t.table_id and "." in ref
                ],
            }
        return "\n\n".join(blocks), used, {"tables": raw_tables}

    @staticmethod
    def _render(
        t: RetrievedTable,
        cols: list[ConnectionColumn],
        ref_by_col: dict[tuple[uuid.UUID, str], str],
        tier: int,
    ) -> str:
        if tier == 3:
            key_cols = [c for c in cols if c.is_pk or c.is_fk] or cols[:3]
            inner = ", ".join(
                f"{c.name} {c.data_type}" + (" PK" if c.is_pk else "") for c in key_cols
            )
            return f"TABLE {t.name} ({inner})"

        lines = [f"TABLE {t.name} ("]
        shown = cols if tier == 1 else cols  # tier 2 also lists columns+types
        for c in shown:
            parts = [f"  {c.name}", c.data_type]
            if tier == 1:
                if c.is_pk:
                    parts.append("PK")
                ref = ref_by_col.get((t.table_id, c.name))
                if ref:
                    parts.append(f"-> {ref}")
            lines.append("  ".join(parts))
        lines.append(")")
        return "\n".join(lines)
