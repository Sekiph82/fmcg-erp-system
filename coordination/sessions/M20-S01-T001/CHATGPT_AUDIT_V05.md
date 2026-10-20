# M20.S01.T001 — ChatGPT Independent Audit V05

Verdict: **CHANGES_REQUIRED**. Implementation `16c4bea`; builder log `CODEX_LOG_V05.md`; published head reported `f0b4e43`. Independently checked source diff and GitHub Actions run `39285256727` (also run `39284832263`).

## Verified
- Migration `20261019_0010` creates `mps_po_number_seq` and seeds it from existing PO-MPS numeric maximum.
- MPS service replaces count+1 with PostgreSQL `nextval()` per order.
- Real PostgreSQL fixture code was improved, but local focused tests reported `37 passed, 2 skipped`; the skips are NOT proof.
- GitHub Actions run 39285256727 completed: backend **FAILURE**, frontend **FAILURE**, docker-config SUCCESS. Backend job 118169258946 executed PostgreSQL 16; migrations passed; pytest result **640 passed, 8 failed, 1 skipped**. Postgres service log explicitly reports `null value in column mps_id of relation mps_lines violates not-null constraint` for V04-C test fixture. Run 39284832263 likewise backend FAILURE and frontend FAILURE.

## Frozen V06 findings
**F-V05-001 P1:** Real PostgreSQL concurrency fixture fails during setup: `MPSLine.mps_id` is NULL because MPSPlan ID was not flushed before MPSLine construction. Inspect full CI traceback, fix both rollback/concurrency fixtures' dependency ordering, re-run actual PostgreSQL tests, and show persisted-state assertions.
**F-V05-002 P1:** Eight backend CI test failures remain. Categorize all eight exact names/tracebacks into M20-related versus pre-existing; resolve M20 regressions. Do not hide, skip or weaken failures. Provide exact PostgreSQL test PASS counts, not merely full-suite aggregate.
**F-V05-003 P1:** PostgreSQL rollback/concurrency/deletion-gap acceptance is still unproven until the tests actually execute to completion and pass. Verify sequence migration on fresh DB and existing PO-MPS records, and verify no reuse after deletion and safe parallel releases.
**F-V05-004 P2:** Frontend CI fails at dependency audit before typecheck/build. Investigate and report actual dependency audit details; remediate only if safely scoped and avoid unrelated unreviewed dependency changes. Record independent follow-up if out of M20 scope.

## Decision
M20.S01.T001 stays IN_PROGRESS. Do not advance to T002. V06 must produce real GitHub-hosted PostgreSQL evidence, complete backend failure classification and factual builder log. Audit is source/CI-evidence based; no local pytest was executed by ChatGPT.
