# QueryMind

A developer-grade SQL workbench. Sign up, connect your own database, plug in your
own LLM key, and ask questions in natural language. An agent drafts SQL,
validates it, runs it read-only, self-corrects on error, and explains the result.

Two design principles:

- **Safety as a feature** — read-only connections by default, AST-level
  validation, an `EXPLAIN` dry-run before execution, and hard row caps.
- **Scales to real schemas** — only the relevant slice of the schema is retrieved
  (vector + lexical + FK-graph), so per-query cost stays flat as the database grows.

## Stack

| Layer | Choice |
| --- | --- |
| Backend | FastAPI, SQLAlchemy (async), Pydantic v2 |
| App database | PostgreSQL 16 + `pgvector` + `pg_trgm` |
| Cache / queue | Redis 7, `arq` workers |
| Agent | LangGraph state machine, `sqlglot` for SQL parsing |
| Embeddings | `BAAI/bge-small-en-v1.5` (CPU, local) |
| LLMs (BYOK) | Anthropic, OpenAI, Gemini — direct SDKs |
| Frontend | Next.js (App Router), TypeScript, Tailwind, TanStack Query |
| Auth | Email + password (Argon2id), cookie sessions, CSRF |
| Crypto | Password-derived AES-GCM envelope for stored credentials |

## Quick start

```bash
cp backend/.env.example backend/.env        # set APP_SECRET etc.
docker compose up -d                        # postgres, redis, backend, worker
cd backend && uv run alembic upgrade head   # migrate the app database

cd ../frontend && pnpm install && pnpm dev  # http://localhost:3000
```

Services: frontend `:3000`, backend `:8001`, Postgres `:5433`, Redis `:6380`.
The compose stack seeds a separate `demo` database (e-commerce data) you can add
as a connection to try the workbench immediately.

## Layout

```
backend/        FastAPI app, agent, services, arq jobs, Alembic migrations
frontend/       Next.js app (auth, connections, keys, workbench)
docker-compose.yml
ARCHITECTURE.md detailed design
```

## Development

```bash
# Backend
cd backend
uv run uvicorn app.main:app --reload
uv run --extra dev pytest                   # unit + integration (needs Postgres + Redis)
uv run --no-sync ruff check app tests

# Frontend
cd frontend
pnpm build                                  # type-checked production build
pnpm gen:types                              # regenerate API types from the backend OpenAPI
pnpm exec playwright test                   # e2e (needs the stack running)
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the request flow, security model, and
schema-retrieval pipeline.
