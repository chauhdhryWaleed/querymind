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
