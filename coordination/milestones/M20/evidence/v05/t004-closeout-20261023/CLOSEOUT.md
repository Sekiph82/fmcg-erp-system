# M20.S05.T004 local closeout — 2026-10-23

## Scope

Prepare the M20 evidence index, refresh the 20-task coverage matrix, reconcile the V05 findings, and state remaining risks and objective milestone exit criteria. This closes the evidence-preparation task only. M20 remains OPEN / PARTIAL; this closeout is not an independent milestone acceptance.

## Evidence refreshed

- Updated `coordination/milestones/M20/CODEX_M20_FINAL_EXECUTION_LOG_V03.md` with the current T002 and T003 receipts, the T004 coverage row, findings F14–F16, the evidence index, unresolved risks, and M20 acceptance criteria.
- Added PostgreSQL regression boundaries in `backend/tests/test_m20_v03_acceptance.py` for aggregate SHIFT_ADD against a full-day calendar, MERGE across mismatched MRP source allocation, chained MERGE of consumed lines, and a locked MERGE source.
- Reused the T002 browser/API receipt and T003 integration/migration receipt; neither is relabeled as independent audit acceptance.

## Verification

- Confirmed the exact task-owned PostgreSQL container `fmcg-m20-s05-t004-e35eabb7537440709df0551e8b3267e5`, labeled `codex.task=M20.S05.T004`, published PostgreSQL only on loopback port 55436, and targeted database `fmcg_m20_t004_e35eabb7537440709df0551e8b3267e5`.
- Ran from `backend/` with `M20_DISPOSABLE_TEST_DATABASE=1`, the exact matching `M20_DISPOSABLE_TEST_DATABASE_NAME`, and `DATABASE_URL=postgresql+asyncpg://m20_test@127.0.0.1:55436/fmcg_m20_t004_e35eabb7537440709df0551e8b3267e5`:
  `venv/Scripts/python.exe -m pytest -q tests/test_m20_v03_acceptance.py`
- Result: **16 passed, 69 existing warnings, 50.43 seconds; exit code 0.** The run includes the four added boundary assertions and the T003 rollback-audit assertion. No owner database or factory data was used.
- `git diff --check` — PASS, exit 0 after the task changes.
- Independent read-only review confirmed T004 may be marked complete as an evidence-preparation task while M20 remains OPEN; the reviewer did not run tests or edit files.
- No GitHub Actions or remote CI were run.

## Evidence index

- `evidence/v05/t002-local-20261023/CLOSEOUT.md` — local frontend checks and disposable-PostgreSQL-backed browser/API scenario persistence evidence.
- `evidence/v05/t003-local-20261023/CLOSEOUT.md` — PostgreSQL cross-module suite and migration downgrade/re-upgrade evidence.
- `backend/tests/test_m20_v03_acceptance.py` — current disposable-PostgreSQL integration and boundary suite.
- `frontend/e2e/m20-scenario-backend-roundtrip.spec.ts` — browser/API scenario persistence test source.
- `evidence/v04/` — screenshots and sanitized traces listed in the execution log; visual/trace acceptance remains pending independent review.
- `CHATGPT_M20_STRICT_AUDIT_V05.md` and `CHATGPT_M20_STRICT_AUDIT_CRITERIA_V01.md` — latest independent verdict and required acceptance criteria.
- `CODEX_M20_FINAL_EXECUTION_LOG_V03.md` — consolidated 20-task matrix and current evidence/risk summary.

## Remaining gates

M20 cannot be represented as accepted or closed until the independent auditor rechecks the current evidence pins and all mandatory criteria. Remaining items include owner-provided minimum-run quantity, CIP durations, and approved currency/cost policy; broader tenant/company/warehouse and concurrency permutations; independent review of UI screenshots and sanitized traces; the development dependency advisories; and remote CI, which is deferred through 2026-10-30. The wider Playwright suite remains blocked by the unavailable valid local E2E account. M21 depends on M20 acceptance, so no successor implementation task is dependency-ready now.

No production data, owner decision, screenshot approval, or independent milestone PASS was fabricated. The owner authorized Codex to maintain the task tracker; that authorization does not change the independent acceptance gate.
