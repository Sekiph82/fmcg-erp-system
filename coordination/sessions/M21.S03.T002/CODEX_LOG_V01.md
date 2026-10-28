# M21.S03.T002 — Multi-output/co-product/by-product semantics

## Owner decision and behavior

The owner answered Q-M21-S03-T002-COSTING-BASIS: keep cost totals unchanged and track co-product/by-product quantities as separate outputs. No secondary-output cost allocation or credit is authorized.

The BOM costing service now separates `CO_PRODUCT` and `BY_PRODUCT` lines from cost-bearing BOM lines. It reports each secondary output's BOM line, master identity, declared quantity, and UOM in separate response collections. Output unit-cost fields do not affect costing. Raw, intermediate, packaging, and utility totals continue to determine batch cost. The legacy `by_product_credit` response/database field remains for compatibility and is zero on new costing calculations. The costing screen shows co-products and by-products separately and does not subtract a credit. The BOM manual documents that outputs are per declared BOM batch and do not reduce cost totals.

## Verification

- `python -m pytest -q backend/tests/test_bom_costing_multi_output.py` — passed, 1 test.
- `powershell -NoProfile -ExecutionPolicy Bypass -File ..\coordination\sessions\M21.S03.T002\run_disposable_multi_output_tests.ps1` from `backend` — passed; fresh task-owned PostgreSQL migrated to Alembic head and pytest reported 1 passed.
- The database integration stored a synthetic BOM with 10 KG raw input at 2 cost units/KG and separate 3.5 L co-product / 1.25 KG by-product rows, each carrying nonzero unit cost. The computed/persisted total stayed 20.0000, output quantities remained separate, and the legacy credit stayed zero.
- Frontend `npm.cmd run type-check` — passed.
- Python compilation and `git diff --check` — passed.
- Verified no container bearing `codex.task=M21.S03.T002` remained.
- Independent read-only review found no blocker in costing behavior, response/UI shape, or runner safety.

The runner used only synthetic records, the local `postgres:16-alpine` image (`sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`), a random task-owned database, an ephemeral loopback-only port, and no volume mounts. No migration, production data, or GitHub Actions were used.
