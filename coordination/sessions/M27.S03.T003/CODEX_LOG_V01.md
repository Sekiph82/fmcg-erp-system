# M27.S03.T003 — NCR/CAPA Escalation Linkage

## Outcome

Implemented NCR/deviation to CAPA linkage using the existing `QCDeviation` and `CorrectiveAction` records. No parallel NCR table or schema migration was needed: the deviation already had a CAPA foreign key and the CAPA already supported generic trigger type/ID fields.

The synthetic virtual-factory operating rule is that HIGH and CRITICAL deviations receive a CAPA in the same transaction; LOW and MEDIUM deviations may receive one when requested. Every linked pair has a reciprocal pointer and `DEVIATION` trigger, matching lot/order/product/material context, and a CAPA severity at least as high as the deviation. A deviation cannot be resolved or closed while its linked CAPA is unverified. Linking is serialized on the deviation and CAPA rows, is one-to-one through the service workflow, and rejects verified CAPAs, duplicate links, mismatched triggers, scope, and severity downgrades. CAPA create/link endpoints enforce quality create/edit permission for the deviation's scope.

Automatic QC inspection failures use the same escalation path. Recall/recall-trigger integration remains out of scope per the GAP-017 audit.

## Changed Files

- `backend/app/services/qms_service.py`
- `backend/app/api/v1/endpoints/qms.py`
- `backend/tests/test_m27_s03_t003_ncr_capa_contract.py`
- `backend/tests/test_m27_s03_t003_ncr_capa_db.py`
- `coordination/sessions/M27.S03.T003/run_disposable_ncr_capa_tests.ps1`

## Verification Evidence

- `python -m compileall -q app/services/qms_service.py app/api/v1/endpoints/qms.py tests/test_m27_s03_t003_ncr_capa_db.py tests/test_m27_s03_t003_ncr_capa_contract.py` — passed.
- Focused quality regression command covering T003 contract/database tests, T002 waiver contract, T001 hold/quarantine, and GAP-017 workflow — **22 passed, 1 skipped**. The database-gated T003 test is intentionally skipped without its task-specific disposable database flag.
- Fresh task-owned disposable PostgreSQL 16 database at migration head `20261029_0032`; `test_m27_s03_t003_ncr_capa_db.py` — **1 passed**. Test data was synthetic. Database name: `fmcg_m27_s03_t003_884f760e4fb64faa86ec`; container: `codex-m27-s03-t003-884f760e4fb64faa86ec`.
- Task container cleanup — verified; no container with label `codex.task=M27.S03.T003` remained.
- `git diff --check` for task-owned changes — passed.
- Independent read-only review — no remaining blocker. Review specifically found and verified the fix for a combined PATCH that attaches an unverified CAPA while resolving a deviation.

## Limits

This is local code/test evidence only. It does not claim deployment, live-factory operation, external audit acceptance, or recall workflow integration.
