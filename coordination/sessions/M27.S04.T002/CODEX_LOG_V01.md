# M27.S04.T002 — Cross-module blocking tests

## Outcome

Added a disposable-PostgreSQL integration test spanning QMS lot hold, Inventory stock disposition, and Sales shipment dispatch. A synthetic quality hold blocks shipment dispatch even when no separate dispatch-gate definition exists; the test verifies the denial leaves the packed shipment, sales order, shipment-line movement link, and stock issue ledger unchanged while the lot remains held and stock remains blocked. The runner creates a random task-labelled PostgreSQL 16 container, binds its port only to loopback, migrates that isolated database, uses synthetic records, and verifies container cleanup.

## Changed Files

- `backend/tests/test_m27_s04_t002_cross_module_blocking_db.py`
- `coordination/sessions/M27.S04.T002/run_cross_module_blocking_tests.ps1`
- `coordination/sessions/M27.S04.T002/CODEX_LOG_V01.md`

## Verification Evidence

- `backend/venv/Scripts/python.exe -m pytest -q tests/test_m27_s04_t002_cross_module_blocking_db.py` — skipped as expected unless the task-owned disposable database flag is enabled.
- `coordination/sessions/M27.S04.T002/run_cross_module_blocking_tests.ps1` — passed: fresh PostgreSQL 16 migration through `20261029_0033`, integration test **1 passed**, runner confirmed loopback-only binding, no volume mounts, synthetic data, and removed its task-labelled container. Container/database: `codex-m27-s04-t002-2e279f81b60048eb95f3` / `fmcg_m27_s04_t002_2e279f81b60048eb95f3`; image ID `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`.
- `backend/venv/Scripts/python.exe -m compileall -q tests/test_m27_s04_t002_cross_module_blocking_db.py` — passed.
- `git diff --check` — passed.
- Focused M27 gate contract/unit regressions across definition, receiving, production, finished-goods, dispatch, hold/quarantine, waiver, NCR/CAPA, and T001 gate-engine tests — **118 passed**.
- Independent read-only review cleared the test and runner: it confirmed the held lot preserves stock reservations, blocks shipment dispatch before sales/stock issue mutations, and the runner constrains and cleans up its exact disposable database container.

## Limits

This covers the QMS hold → Inventory → Sales dispatch boundary with synthetic records on a disposable database. It does not claim UI/E2E, deployment, production-factory, or live operational acceptance; those remain separate M27.S04 tasks.

No GitHub Actions were dispatched.
