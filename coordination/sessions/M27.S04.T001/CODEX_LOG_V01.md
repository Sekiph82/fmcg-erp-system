# M27.S04.T001 — Gate-engine unit tests

## Outcome

Added focused unit coverage for quality-gate definition routing and core gate-engine rules without changing production behavior. Tests verify that each receiving, production, finished-goods, and dispatch selector uses the correct module/event/effective date; unknown production events do not query definitions; waiver scope is tied to supported module/event pairs; linked templates use the required QC type; and policy/effective-window helpers enforce severity, waiver, and inclusive-date rules.

## Changed Files

- `backend/tests/test_m27_s04_t001_gate_engine_unit.py`
- `coordination/sessions/M27.S04.T001/CODEX_LOG_V01.md`

## Verification Evidence

- `backend/venv/Scripts/python.exe -m pytest -q tests/test_m27_s04_t001_gate_engine_unit.py` — **37 passed**.
- `backend/venv/Scripts/python.exe -m compileall -q app/services/qms_service.py tests/test_m27_s04_t001_gate_engine_unit.py` — passed.
- `git diff --check` — passed.
- Independent read-only review: cleared; selector parameters, supported waiver scopes, QC types, policy cases, and date-window expectations match the implementation, with adjacent coverage already present for gate decisions and specification validation.

## Limits

These are local unit tests over synthetic in-memory values. They do not claim database migration, cross-module transaction, UI/E2E, deployment, or live-factory acceptance; those remain separate M27.S04 tasks.

No GitHub Actions were dispatched.
