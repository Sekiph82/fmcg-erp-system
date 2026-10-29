# M01.S03.T002 — Fresh-Database Migration Ownership V01

## Scope and synchronized baseline

- Canonical checkout: `C:\Users\sekip\Desktop\fmcg-erp-system`, branch `main`.
- Task: `M01.S03.T002 — Validate migration ownership on live-like database` from root `TASKS.md`.
- Baseline after preceding task closure: `46fa87b2d5972ade94e4c87def576fa439c64a36`; `origin/main` matched before claiming this task.
- Active criteria/prompt: `CHATGPT_AUDIT_CRITERIA_V01.md`, `CHATGPT_PROMPT_V01.md`.
- Latest applicable migration evidence was reconciled from `coordination/AUDIT_INDEX.md` / `AUDIT_POLICY.md` (`ERP-AL-013`), `docs/planning/GAP-DB-001_LIVE_MIGRATION_VERIFICATION.md` (historical head `20260511_0040`), and `coordination/sessions/M01.S03.T004/CODEX_LOG_V02.md` (fresh disposable DB reached `20261028_0017`). The current source has advanced to `20261029_0025`.
- No owner, application, staging, production, or provider database/credentials were used. Unrelated dirty/untracked owner work remains unstaged and untouched.

## Disposable PostgreSQL setup

- PostgreSQL image: `postgres:16.6-alpine`, image ID prefix `1d04b9ba1d49`; server reported `PostgreSQL 16.6`.
- Exact task container: `codex-m01-s03-t002-20261029-9f31`, ID `37f4e1e55dae72f97139f2f1057ce8be91b910e1177c7bef6e9c376b81f6bdb0`.
- Labels: `codex.task=M01.S03.T002`, `codex.disposable=true`; restart policy `no`; host mapping bound to `127.0.0.1:59085`; storage was 512 MiB `tmpfs` at the PostgreSQL data directory and `docker inspect` reported no volume mounts.
- Database: `fmcg_m01_s03_t002_20261029_9f31`, initialized empty. Local trust authentication was used; no password was created.
- One initial container attempt used the PostgreSQL image's default anonymous volume. It was removed immediately with its exact task label and volume before migration work began. The final container used only tmpfs; no persistent volume was attached.

## Migration ownership evidence

- `python -m alembic heads` reported one head: `20261029_0025 (head)`.
- `python -m alembic history --indicate-current` output is preserved in `alembic-history.log`: it contains the complete 99-revision ancestry from `<base> -> 20260517_0000` through `20261028_0024 -> 20261029_0025`, with exactly one `(head)` and one `(current)` marker.
- `python -m alembic upgrade head` succeeded from the empty database through the complete history. `python -m alembic current` and direct `alembic_version` query both reported `20261029_0025`.
- The revision chain contains 99 version scripts and historical branch merges; Alembic resolves them to the single current head above.
- The reproducible, read-only `verify_schema_parity.py` checks the exact task opt-in, loopback-only URL, exact disposable DB name, absent password, exact revision, all model tables, and selected schema constraints. Its output is preserved in `schema-parity.log`. It found 645 current model tables, 661 public tables including `alembic_version`, 0 current model tables missing, and 15 legacy tables absent from current ORM metadata.
- The 15 extra tables are explicitly created by existing revisions: `ai_anomalies`/`ai_suggestions` by `d9e0f1a2b3c4_production_ai.py`; the three `kb_*` tables by `20260515_0030_document_knowledge_reconciliation.py`; seven `iot_*` tables by `20260516_0020_iot_machine_streaming_reconciliation.py`; and three `npd_*` tables by `20260516_0010_npd_formula_governance_reconciliation.py`. They are migration-owned historical schema objects, not missing current model tables.
- Representative tables (`users`, `roles`, `stocks`, `stock_movements`, `cost_layers`, `journal_entries`, `journal_lines`, `webhook_event_logs`, `webhook_delivery_attempts`) had matching ORM/database primary keys, no missing ORM foreign keys, and no missing ORM-declared indexes, as directly asserted by the saved script and output.
- The first execution attempt of the parity script failed before connecting because invoking a script outside the backend directory did not place the backend package on Python's import path. This is preserved in `schema-parity-attempt01.log`; the script now adds its repository-relative backend path and the immediate rerun passed. The failed attempt made no database change.
- The exact container was stopped and removed after evidence capture. A follow-up inspection confirmed that `codex-m01-s03-t002-20261029-9f31` no longer exists; the final run had no Docker volume mounts and its tmpfs was container-local.

## Autogenerate drift and limits

- `python -m alembic check` **failed** with `New upgrade operations detected`: it proposed removing 15 migration-owned tables that are no longer in current ORM metadata and 187 indexes no longer declared in current metadata. It proposed zero added tables, indexes, or columns. Full output is preserved in `alembic-check.log`.
- This failure is not hidden or reported as PASS. The fresh database contains every current model table, the historical tables have explicit migration ownership, and sampled active schema objects match. The removal proposals are not applied: dropping historical tables/indexes would be destructive and no accepted scope identifies them as safe to remove. Current metadata/migration drift remains an explicit finding; a future cleanup needs a table/index retention decision and migration-specific audit.
- No application service was started, no business rows were created, and no tests were run. The task verifies migration history and schema ownership only; it does not establish production migration acceptance.

## Commands and review

- `python -m alembic heads` — one head, `20261029_0025`.
- `python -m alembic upgrade head` — passed on the empty disposable PostgreSQL database.
- `python -m alembic current` — `20261029_0025 (head)`.
- `python -m alembic history --indicate-current` — full history preserved in `alembic-history.log`, one head/current marker.
- `python ..\coordination\sessions\M01.S03.T002\verify_schema_parity.py` with task-specific disposable opt-in, exact matching DB name, and loopback URL — passed; complete output in `schema-parity.log`.
- `python -m alembic check` — failed as detailed above; no destructive operation was applied.
- `node scripts/codex/validate-task-state.mjs` — passed before and after task claim.
- `node scripts/codex/task-queue.mjs --apply-answers` — no unanswered matching owner decision.
- Task start commit: `991a2e9dc839a201c56070ebdf1d3657944aa5dc` (`[skip ci]`), pushed to `origin/main`.
- Independent read-only review: reviewer examined the evidence draft and identified the contradictory cleanup line and missing artifact hashes. Both findings were remediated; final re-review is pending. Reviewer did not access the database, run tests, start services, or modify files.
- Disposable container/database cleanup: complete; the only container was task-labelled, tmpfs-only, and verified absent after removal.
- Container cleanup and exact absence verification: complete; the task-labeled container was absent on the final Docker inspection.


## Evidence SHA-256

SHA-256 is recorded for the criteria, prompt, command outputs, and executable parity checker. The log itself is excluded because self-hashing is not meaningful.

| Artifact | SHA-256 |
|---|---|
| `CHATGPT_AUDIT_CRITERIA_V01.md` | `4D2E71213B8F6A4FE6EE876B3D57B13C4386E94812B21EF438E73591DE61A12D` |
| `CHATGPT_PROMPT_V01.md` | `F52D21858E811D258760E20A946E0AF6C4C508171F0FBD7F419A81989291E1CF` |
| `alembic-history.log` | `6AEA1D2EE962FE819CE22D8033C906DF8CA0C14A64BEB7548A326E79BEEF3F73` |
| `alembic-check.log` | `17F68AF17837193E01BE234F30A4445EC0ED8A2F4A0F1958840345E94E41D390` |
| `schema-parity.log` | `0B7E93C4194F9BD4AB286E245C3AE29E9FA91D0229E67EF64D9AE8720DB63CCE` |
| `schema-parity-attempt01.log` | `AE6F03BEA6F49D8BEF0922FFB1276084DCF887D9C3915D1912957E084E8CF54C` |
| `verify_schema_parity.py` | `D38A4F895AE5D9B3D0B5C16A76C58B60CA4D9F833B6AF1797811DD657260A711` |
