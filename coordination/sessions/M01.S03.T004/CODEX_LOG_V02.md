# M01.S03.T004 — Disposable Backup/Restore Rehearsal V02

## Scope and accepted boundary

The canonical task row asks for operational backup/restore rehearsal evidence but provides no linked task-specific acceptance criteria. `docs/DEPLOYMENT.md` contains generic PostgreSQL dump/restore examples; the audit index/policy contain no specific M01.S03.T004 criteria. Şekip opened Docker Desktop after being offered the local-only alternative; this was recorded as acceptance that a synthetic disposable local PostgreSQL rehearsal satisfies this task. This interpretation and the exact Q-ID answer are in `TASKS.md`.

This result proves only a local disposable restore rehearsal. It does not claim production/staging acceptance, off-site protection, backup retention policy, or RPO/RTO compliance.

## Reproducible rehearsal

- Runner: `coordination/sessions/M01.S03.T004/run_disposable_rehearsal.ps1`.
- Used the already-present `postgres:16-alpine` image, ID `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`; no image pull occurred.
- The runner created a uniquely named task-labelled container with `--restart=no`, no volume mounts, and a random host port bound to `127.0.0.1` only. It used an isolated trust-authenticated throwaway instance with no password and overrode only `DATABASE_URL` for the migration process.
- Alembic upgraded the empty source database to head `20261028_0017`.
- Added two synthetic parent records and two child records (JSONB, FK linkage, and bytea payload); no owner or business data was loaded.
- Created a custom-format `pg_dump` archive inside the ephemeral container. `pg_restore --list` included `alembic_version` and both rehearsal tables.
- Restored into a separate `template0` database with `pg_restore --exit-on-error`.
- Compared Alembic migration state and deterministic ordered row-count/content hashes before/after restore; all matched:
  - Migration state: `20261028_0017`.
  - Parent rows: `2|fa9e65507a8945aac7564f77b4f893bc`.
  - Child rows: `2|60abcedb041c09efe5abfd1f6914e2a0`.
- Final runner result: `PASS`. The run's temporary container, both databases, and in-container archive were removed; a separate exact task-prefix container query confirmed none remained. No persistent volume or host backup file was created.
- PowerShell parser and `git diff --check` passed for the runner.

## Corrections during rehearsal development

Earlier disposable attempts exposed and corrected a Docker Go-template quoting issue in the cleanup guard, PowerShell native stderr handling, JSON fixture argument quoting, the expected `pg_restore --list` schema-qualified table names, and explicit restore role selection. Each failed run used only its uniquely named disposable container; cleanup was verified before retry. Only the final run is counted as PASS.

## Independent read-only review and limits

The independent reviewer found no blocking issue in the final script or the reported run. The cleanup path verifies the exact task label, stops only that container, and confirms the exact anchored name is gone. If the Docker daemon becomes unavailable during cleanup, the script fails loudly but cannot guarantee removal; the resulting container would require its exact task name to be inspected. The reviewer did not run the rehearsal or inspect unrelated containers.

No production/staging database, deployment, GitHub Actions, or owner data was accessed. The local rehearsal decision does not define or meet production backup destination, retention, off-site protection, RPO, or RTO requirements.
