# Changelog

## [0.1.0] – 2026-01-17
- async SQLAlchemy engine with configurable pool
- Alembic migration scaffold, initial schema

## [0.2.0] – 2026-01-22
- argon2id password hashing (time_cost=2, mem=64 MB)
- `needs_rehash` check on login
