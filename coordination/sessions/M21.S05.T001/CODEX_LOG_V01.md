# M21.S05.T001 — Unit/conversion/yield tests

## Verification

- Focused conversion/profile/yield unit invocation: 62 passed.
- The task runner passed six isolated PostgreSQL integration groups after each database migrated to head: density/UOM conversion (17), package components by SKU (7), profile version/effective dates (6), expected process yield (8), loss categories (10), and recipe-standard loss snapshots (10).
- Supplemental conversion API-contract and yield-cost variance unit group: 27 passed.
- All PostgreSQL databases were synthetic and task-owned. The runner used `postgres:16-alpine`, a loopback-only ephemeral port, no volume mounts, and separate random databases whose names matched each integration suite's required prefix and gate.
- The test container used label `codex.task=M21.S05.T001`; cleanup verified the exact label before stop, and a post-run container query confirmed none remained. No task-labeled Docker volume remained.
- Independent read-only review found no blocker in scope coverage or runner isolation/cleanup.

## Scope limits

- The repository's `backend/venv` was unavailable, so tests and migrations used the installed Python 3.12 environment, which already had pytest, SQLAlchemy, asyncpg, and Alembic.
- No production database, owner data, or external data was used. No GitHub Actions were run.
