# Changelog

## [0.1.0] – 2026-01-17
- async SQLAlchemy engine with configurable pool
- Alembic migration scaffold, initial schema

## [0.2.0] – 2026-01-22
- argon2id password hashing (time_cost=2, mem=64 MB)
- `needs_rehash` check on login

## [0.3.0] – 2026-01-28
- httpOnly session cookies with CSRF tokens
- `X-CSRF-Token` header enforcement on mutating routes

## [0.4.0] – 2026-02-03
- /health endpoint returns db and redis status
- structured logging via structlog

## [0.5.0] – 2026-02-08
- Connection model with AES-GCM credential encryption
- connection CRUD endpoints

## [0.6.0] – 2026-02-14
- SQL safety validator: blocks DROP/DELETE/INSERT/UPDATE
- syntax validator via sqlglot

## [0.7.0] – 2026-02-18
- email verification flow with signed tokens
- password reset via emailed link

## [0.8.0] – 2026-02-22
- Next.js app router setup
- auth layout with login/signup pages

## [0.9.0] – 2026-02-26
- workspace CRUD API
- user <-> workspace membership model

## [0.10.0] – 2026-03-03
- per-user LLM API key storage (encrypted)
- support for Anthropic, OpenAI, Gemini providers

## [0.11.0] – 2026-03-08
- database schema introspection (tables, columns, FK graph)
- schema indexing to vector store

## [0.12.0] – 2026-03-12
- local embeddings via BAAI/bge-small-en-v1.5
- pgvector integration for semantic search

## [0.13.0] – 2026-03-17
- hybrid retrieval: pgvector cosine + pg_trgm lexical
- RRF fusion ranking

## [0.14.0] – 2026-03-22
- LangGraph state machine: plan -> generate -> validate -> execute -> explain
- retry loop on validation failure

## [0.15.0] – 2026-03-26
- server-sent events streaming for SQL generation steps
- frontend EventSource integration with TanStack Query

## [0.16.0] – 2026-04-01
- arq Redis queue for async jobs
- schema re-index worker, query history cleanup

## [0.17.0] – 2026-04-06
- query history stored per workspace
- CSV/JSON export endpoint

## [0.18.0] – 2026-04-10
- slowapi rate limiting on query endpoints
- per-user limits stored in Redis

## [0.19.0] – 2026-04-15
- chart suggestions from query result shape
- bar / line / pie auto-selection

## [0.20.0] – 2026-04-20
- favorite queries per user
- shareable read-only query links

## [0.21.0] – 2026-04-25
- multiple DB connections per workspace
- connection health-check on save

## [0.21.1] – 2026-04-30
- fix: refresh token not rotated on reuse attempt
- fix: clear stale sessions on logout

## [0.22.0] – 2026-05-05
- thumbs up/down feedback on generated SQL
- feedback used to improve few-shot examples

## [0.23.0] – 2026-05-10
- workbench split-pane layout
- mobile responsive sidebar

## [0.24.0] – 2026-05-16
- settings page: API keys, preferences, danger zone
- delete account flow

## [0.24.1] – 2026-05-22
- tune db pool size to 10 under load testing
- reduce token streaming latency
