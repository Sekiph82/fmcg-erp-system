# M20.S01.T001 — Independent ChatGPT Audit V03

Repository: `Sekiph82/fmcg-erp-system`; branch: `main`.
Implementation: `cd552bffe8056279da67c828566ea9ee2d3a2c65`.
Builder log commit: `ab4c2144b8c42c8f1dd879bfc35c8ae2bb904e62`.
Criteria: `CHATGPT_AUDIT_CRITERIA_V03.md`.
**Verdict: CHANGES_REQUIRED / NOT ACCEPTED.**

## Independently verified GitHub evidence
- The implementation diff changes `backend/app/services/mps_service.py` and adds `backend/tests/test_m20_s01_t001_v03_mps_remediation.py`; builder log is a separate commit.
- The release completion expression now checks the full positive unreleased set, rejects skipped eligible and ineligible lines, and does not use `created > 0`. The response exposes truthful counters.
- Product missing and invalid UOM now raise instead of silently using KG.
- The added tests include mixed partial release and UOM negative cases.
- Tracker files and auditor criteria were not changed in the inspected implementation diff.
- Builder-reported results: focused V02+V03 21 passed; base regression 169 passed/3 failed; dirty workspace 168 passed/9 failed; compilation/import and Alembic heads succeeded. These are **log claims**, not independently rerun CI evidence.

## Frozen findings for V04

### F-V03-001 — P1 — No actual database rollback proof
V03 criterion M20S01-V03-031 explicitly requires endpoint/transaction-level behavioral rollback proof beyond source inspection, and V03-032 requires persisted state consistency. The test uses a custom `_TransactionalReleaseDB` fake whose `begin()` exception handler itself clears `pending_orders`, resets links, and sets `plan.status=APPROVED`. Therefore the test verifies the fake's own programmed rollback, not SQLAlchemy/asyncpg/PostgreSQL transaction behavior. The log candidly acknowledges Docker daemon unavailable. **NOT PROVEN**. Add a real SQLAlchemy transactional integration test on a usable DB (prefer PostgreSQL, potentially CI service), asserting persisted orders, links and plan status after late failure. Do not invent PASS if runtime unavailable.

### F-V03-002 — P1 — No clean-head regression evidence
Builder's broad test results are 168 passed/9 failed on a dirty workspace, versus 169 passed/3 failed on old V02 base. The log attributes six new failures to preserved owner modifications without a clean exact-V03-head run or independently verified isolation. The comparison does not prove the six failures are unrelated to V03. Add a non-destructive clean checkout/CI run at exact V03 commit, compare identical commands against exact parent/base, and record failing test identities and tracebacks. No test weakening.

### F-V03-003 — P2 — Partial release persists partial orders while plan remains APPROVED
Source currently creates and flushes POs for eligible lines before discovering skipped recipes or ineligible lines; `release_complete=False` leaves plan APPROVED but the transaction commits the created orders on a normal return. This creates a partially released plan with linked POs, even though the workflow has only APPROVED/RELEASED, and may make retries/order accounting surprising. The V03 prompt allowed an explicit truthful partial-release rule, but no persistence-level test proves the state and idempotent recovery are safe. Decide and document **atomic all-or-none** versus explicitly supported partial release; prefer atomic all-or-none if existing state machine has no partial state. Test mixed eligibility, retry, linkage and counters with a real DB.

### F-V03-004 — P2 — Concurrent PO numbering remains unprotected
`po_seq = (select count(ProductionOrder)) + 1` and `PO-MPS-{po_seq:06d}` can collide on simultaneous releases. This predates V03 but becomes relevant to production release correctness. Determine existing canonical PO-number allocator and reuse it if present; otherwise scope a safe minimal DB-backed uniqueness/retry mechanism. Provide concurrent release tests or explicitly record as a separate later M20 gate if implementation would exceed V04 frozen scope.

## Criteria decision
- Governance and scope: PASS from inspected diff.
- Whole-plan completion/counts: PASS at service-source and mocked behavioral level.
- Product/UOM validation: PASS at service-source and mocked behavioral level.
- Persistent rollback: NOT PROVEN.
- Full regression attribution: NOT PROVEN.
- Transactional partial-success semantics: PARTIAL / further closure proof required.
- Concurrent numbering: pre-existing risk, NOT ACCEPTED as production-ready.
- Independent execution of builder's tests: not performed by this audit; no runtime-green claim.

**Closure:** `M20.S01.T001` remains IN_PROGRESS; `TASKS.md` must not advance to T002. Codex must address frozen V04 findings with factual evidence; ChatGPT independently audits the next revision.
