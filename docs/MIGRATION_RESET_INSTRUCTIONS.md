# Migration Reset Instructions

## For fresh databases (new environment / CI)

```bash
# Production
alembic upgrade head
# This now works on a completely empty database.
# Migration 20260517_0000 (squashed baseline) runs first and creates all tables.
```

## For existing dev databases

No action required. Just run:

```bash
alembic upgrade head
```

Alembic applies only the migrations AFTER your current `alembic_version` entry.
The baseline (`20260517_0000`) is not in your history — Alembic won't try to
re-run it. Your data is safe.

## To completely reset a dev database

```bash
docker compose --env-file .env.development down -v
docker compose --env-file .env.development up -d
```

The container CMD runs `python scripts/dev_migrate.py` on startup, which
handles the fresh DB via `create_all + stamp head` (fast dev shortcut).
Alternatively you can run `alembic upgrade head` directly after `up -d`.

## Troubleshooting: "multiple heads" error

If `alembic heads` shows more than 1 head, a merge migration is needed:

```bash
alembic merge heads -m "merge_heads"
alembic upgrade head
```

## Troubleshooting: existing DB at an old revision

If your DB's `alembic_version` shows a revision that no longer exists in the
migration files, stamp to a known good revision:

```bash
# Stamp to the current head without running migrations:
alembic stamp head
```

Only do this if you are certain the schema is already up to date (e.g., just
created via `create_all`).
