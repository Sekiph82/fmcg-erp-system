# M34.S01.T003 — Commercial/technical evaluation matrix

Status: implementation complete; disposable database and focused verification complete; independent read-only review found no remaining actionable issues.

## Scope and decisions

- Extended the existing RFQ/bid aggregate; did not create a parallel procurement workflow.
- Added per-RFQ buyer-configured technical and commercial criteria. The buyer's selected weights must total exactly 100.00%; both dimensions are required. The 50/50 values shown initially in the UI are editable examples, not company policy or a claimed industry standard.
- Each criterion is scored from 0 to 100. Mandatory criteria require an explicit pass/fail gate; a failed mandatory gate disqualifies the bid while retaining its weighted numeric score for comparison and audit.
- Matrices can be configured after invitation issuance and before the first bid is received. They then remain immutable for that RFQ to prevent criteria being changed after seeing offers.
- Evaluation revisions append actor/time-attributed score, gate, and comment rows. The RFQ detail response and UI show the latest scores and the complete revision history.
- Existing procurement permission and record-scope enforcement applies to matrix creation, scoring, and RFQ detail. UI mutation controls are shown only when the access hint permits editing.
- No real supplier, factory, or employee records were added. Integration data was synthetic and task-scoped.

## Changes

- `backend/app/models/procurement.py`: evaluation dimensions/status, per-RFQ criteria, revision rows, and constraints.
- `backend/alembic/versions/20261030_0007_rfq_evaluation_matrix.py`: additive schema reconciliation, exact shape validation for adopted columns/enums/checks/uniques/indexes/PKs/FKs, and ownership-aware downgrade guards.
- `backend/app/schemas/procurement.py` and `backend/app/api/v1/endpoints/procurement.py`: matrix validation, scoped configuration, exact criterion coverage, weighted scoring, mandatory gates, append-only revisions, latest result, and full history.
- `frontend/src/lib/procurement.ts` and `frontend/src/app/dashboard/procurement/rfq/page.tsx`: editable per-RFQ matrix, score/gate entry, and visible evaluation history.
- `backend/tests/test_m34_s01_t003_rfq_evaluation_matrix.py`: validation, authorization, lifecycle, scoring, gate, actor, revision, and disposable-target coverage.
- `run_disposable_postgres.ps1`: task-owned loopback PostgreSQL migration and evaluation acceptance run.

## Verification evidence

- `disposable-postgres-run-V09.log` and `disposable-postgres-command-output-V09.log`: PostgreSQL 16 task-owned database; `20261030_0007` head; migration adoption rejected an incompatible same-named weight check and an incompatible primary key; synthetic pre-evaluation schema creation path; 4 focused tests passed; downgrade/re-upgrade returned to head; exact container cleanup verified.
- No-database focused suite: `tests/test_m34_s01_t003_rfq_evaluation_matrix.py` — 3 passed, 1 database-guarded skip.
- Python compilation passed for the touched models, schemas, endpoint, migration, and focused tests.
- Frontend `npm run type-check` passed; targeted ESLint passed for the RFQ page and procurement client.
- `git diff --check` passed for the task source and control files (Git emitted only the existing Windows line-ending conversion warning for `TASKS.md`).
- Independent read-only review: no remaining actionable findings.

## Retained failed trials

Earlier trial logs are retained, not rewritten. V01 caught a test-cleanup lazy-load error; V04 caught a same-session stale relationship expectation; V06 caught lazy loading in the bid-submission response after history fields were added; V08 caught a PostgreSQL fixture dependency while attempting the incompatible-PK case. The source or disposable-run fixture was corrected for each, and the final V09 run passed. V09's two Alembic errors were deliberate negative assertions confirming fail-closed adoption of bad constraints and primary keys.

No GitHub Actions were run. No external invitation email or other publication was sent.
