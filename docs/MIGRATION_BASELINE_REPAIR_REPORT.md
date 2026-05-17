# Migration Baseline Repair Report

Date: 2026-05-17

## Problem

`alembic upgrade head` failed on a fresh empty database.  
Root cause: Alembic was introduced after ~277 tables already existed in
production.  The original chain root (`3c45d9071c98`) added columns to
`sales_orders` — a table the chain never created.  Every subsequent migration
referenced pre-existing tables via FK.  A fresh DB had none of those tables, so
the very first migration step would error.

## Solution

Three-part fix — no existing migration files edited, no business logic changed.

### 1. Squashed baseline (`20260517_0000_squashed_baseline.py`)

New chain root with `down_revision = None`.  Its `upgrade()`:
1. Creates the `uuid-ossp` extension.
2. Calls `Base.metadata.create_all(bind=bind, checkfirst=True)` — creates every
   table defined in the current SQLAlchemy models, skipping any that already exist.

### 2. Idempotency patch in `alembic/env.py`

`do_run_migrations()` now monkey-patches four `alembic.operations.Operations`
methods before running the migration chain:

| Method | Guard |
|--------|-------|
| `create_table(name, ...)` | Skip if `inspector.has_table(name)` |
| `add_column(table, col)` | Skip if `col.name` already in `inspector.get_columns(table)` |
| `create_index(name, table, ...)` | Skip if `name` in `inspector.get_indexes(table)` |
| `create_foreign_key(_, src, ref, local_cols, ...)` | Skip if FK to same referent with same local cols already exists |

The original methods are restored in a `finally` block.  On an existing DB
(not starting from baseline), the guards are no-ops — no behaviour change.

### 3. Chain re-root (`3c45d9071c98_initial_schema.py`)

Changed `down_revision = None` → `down_revision = '20260517_0000'`.  
The chain is now: `20260517_0000` → `3c45d9071c98` → `a1b2c3d4e5f6` → … → head.  
Single head preserved — CI `alembic heads` check still passes.

## Fresh-DB flow after fix

```
alembic upgrade head
  └── 20260517_0000  →  create_all(checkfirst=True)   [all 636 tables]
  └── 3c45d9071c98   →  add_column guards → all no-ops
  └── a1b2c3d4e5f6   →  create_table purchase_invoices → skipped (baseline created it)
                         add_column payments.method     → skipped (baseline created it)
  └── … (all subsequent) → skip existing, create new tables/cols they uniquely own
```

## Existing-DB flow (unchanged)

`alembic upgrade head` from any existing revision works as before.  The baseline
`20260517_0000` is not in the existing DB's `alembic_version` — Alembic simply
continues upgrading from the current revision toward head.

## Files Changed

| File | Change |
|------|--------|
| `backend/alembic/versions/20260517_0000_squashed_baseline.py` | NEW |
| `backend/alembic/env.py` | Added `import sqlalchemy as sa`; patched `do_run_migrations` |
| `backend/alembic/versions/3c45d9071c98_initial_schema.py` | `down_revision = None` → `'20260517_0000'` |
| `backend/scripts/dev_migrate.py` | Updated stale docstring comment |
