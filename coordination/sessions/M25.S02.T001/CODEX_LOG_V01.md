# M25.S02.T001 — Freight/insurance/customs/port/local charges

## Scope

The existing landed-cost screens and model already had the practical charge catalogue: sea/air/land freight, insurance, customs duty and import tax, port handling, clearing agent, inspection, inland transport, storage, demurrage, detention, and other. The gap was that the create schema accepted arbitrary strings despite the UI/model catalogue.

The request schema now validates new landed-cost lines against the existing `LandedCostType` enum and the service stores its canonical string value. The response schema deliberately keeps `cost_type` as a string so previously saved custom labels remain readable. The supply-chain manual lists the supported types and describes `OTHER` as a documented user choice, not an enforced description rule. No new parallel model, currency policy, allocation algorithm, estimate/actual workflow, or inventory/GL posting behavior was added; those concerns belong to other existing flows or M25.S02 follow-up tasks.

## Verification

- `backend/tests/test_m25_s02_t001_landed_cost_charge_types.py`: **16 passed** — all 14 supported categories accepted and serialize to canonical values; an unknown new category is rejected; a historical custom label remains readable through the response schema.
- `compileall` passed for the changed schema, landed-cost service, and test.
- `git diff --check` passed; Git reports only the existing root `TASKS.md` LF-to-CRLF normalization warning.
- Independent read-only review passed; no remaining blocker.

## Limits

These are software charge categories and synthetic ERP records. They do not assert real freight invoices, customs assessments, port charges, or actual supplier/currency data. Allocation and accounting/inventory posting remain separate workflows.
