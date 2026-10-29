# M27.S03.T004 — Gate Audit History

## Outcome

Added durable, append-only quality-gate evaluation history for receiving, production release/in-process, finished-goods release, and dispatch decisions. History captures PASS, BLOCKED, WAIVED, and NO_GATE outcomes with evaluation correlation, actor, gate version/code, scope/business identifiers, required-template and inspection/waiver references, reason, policy snapshot, and timestamp. The separate audit session commits a blocked decision even when the calling business transaction rolls back.

The read-only `GET /qms/gate-audit-history` endpoint supports scope, business object, gate, result, and bounded limit filters. Results use the same global and warehouse-scoped quality visibility rules as waiver history. Database triggers reject UPDATE, DELETE, and TRUNCATE operations on the history table. Lot-release secondary mandatory-inspection denials also append a BLOCKED outcome sharing the evaluation ID and actor with the gate check.

## Changed Files

- `backend/app/models/quality.py`
- `backend/app/models/__init__.py`
- `backend/alembic/versions/20261029_0033_quality_gate_audit_events.py`
- `backend/app/schemas/qms.py`
- `backend/app/services/qms_service.py`
- `backend/app/services/procurement_service.py`
- `backend/app/services/production_service.py`
- `backend/app/services/quality_service.py`
- `backend/app/services/sales_service.py`
- `backend/app/api/v1/endpoints/qms.py`
- `backend/app/api/v1/endpoints/production.py`
- `backend/tests/test_m27_s03_t004_gate_audit_db.py`
- `backend/tests/test_m27_s02_t001_receiving_gate.py`
- `backend/tests/test_m27_s02_t002_production_gate.py`
- `backend/tests/test_m27_s02_t003_finished_goods_release_gate.py`
- `backend/tests/test_m27_s02_t004_dispatch_gate.py`
- `backend/tests/test_m27_s03_t001_hold_quarantine.py`
- `coordination/sessions/M27.S03.T004/run_disposable_gate_audit_tests.ps1`

## Verification Evidence

- `python -m compileall -q backend/app backend/alembic/versions/20261029_0033_quality_gate_audit_events.py backend/tests/test_m27_s03_t004_gate_audit_db.py` — passed.
- `git diff --check` — passed.
- Focused quality gate and preceding-sprint contract regressions across receiving, production, finished-goods, dispatch, hold/quarantine, waiver, and NCR/CAPA — **47 passed**.
- Fresh task-owned disposable PostgreSQL 16 database migrated through `20261029_0033`; `test_m27_s03_t004_gate_audit_db.py` — **3 passed**. Coverage verifies blocked history survives outer rollback, scoped API filtering, PASS plus final BLOCKED correlation on lot release, NO_GATE capture, and DB rejection of UPDATE/DELETE/TRUNCATE. Synthetic data only. Container: `codex-m27-s03-t004-d878b83f452647a2a5a1`; database: `fmcg_m27_s03_t004_d878b83f452647a2a5a1`; local image ID: `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`.
- Runner verified loopback-only PostgreSQL binding, no volume mounts, and task-container cleanup.
- Independent read-only review found and verified the fix for a secondary lot-release denial that had initially lacked a BLOCKED event; no remaining blocker was reported.

## Limits

This is local code and synthetic disposable-database evidence. It does not claim deployment, production-factory use, external audit acceptance, or live operational readiness. No GitHub Actions were dispatched.
