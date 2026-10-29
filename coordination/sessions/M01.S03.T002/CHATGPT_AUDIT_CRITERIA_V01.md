# M01.S03.T002 — Migration Ownership on a Fresh Live-Like Database V01

## Authority and latest applicable audit

The sole active task row is `M01.S03.T002 — Validate migration ownership on live-like database` in root `TASKS.md`. The latest applicable repository learning is `ERP-AL-013` in `coordination/AUDIT_INDEX.md`: model presence alone does not prove migration ownership; verify Alembic ownership, one head, a fresh database, and representative upgrade behavior. Previous evidence includes `docs/planning/GAP-DB-001_LIVE_MIGRATION_VERIFICATION.md` (older local development DB, revision `20260511_0040`), `coordination/sessions/M01.S03.T004/CODEX_LOG_V02.md` (disposable fresh DB upgraded to `20261028_0017`), `backend/alembic/env.py`, and the squashed baseline migration. Reconcile that evidence with the current migration head before claiming anything.

## Acceptance criteria

1. Inspect the current revision graph and prove it has exactly one Alembic head; record the exact head and its ancestor chain evidence.
2. Apply the complete migration chain from an empty, uniquely named task-owned PostgreSQL database. The instance must be disposable, loopback-bound, no-volume, no production/owner credentials, and no real data.
3. Confirm the database's `alembic_version` equals the exact current head after upgrade. Record PostgreSQL version and exact commands/results.
4. Import the complete application model registry and compare its declared table names with the fresh migrated database. Record any missing or unexpected tables rather than assuming the baseline owns them.
5. Check representative high-risk schema objects (primary/foreign keys and indexes on selected auth, inventory, finance, webhook and event tables) against current ORM/migration definitions. Do not report model presence alone as proof.
6. Run `alembic check` against the disposable database to surface pending schema operations. If it reports real missing ownership, reconcile additively and rerun the required fresh-database evidence; never edit owner/live databases or destructively reset a database.
7. Keep this task local and synthetic. Do not claim production migration acceptance, make deployment policy decisions, run GitHub Actions, or expose credentials. Remove only the exact task-owned container/database after evidence capture and verify cleanup.
8. Record exact hashes, commands, failures/corrections, migration ownership conclusion, cleanup, and independent read-only review in `CODEX_LOG_V01.md`.

## Scope boundary

An additive migration repair is within scope only if fresh-database evidence proves a current application table or required schema object lacks migration ownership and the fix requires no unresolved destructive or business-policy choice. Otherwise record the concrete finding and continue only with independent dependency-ready work.
