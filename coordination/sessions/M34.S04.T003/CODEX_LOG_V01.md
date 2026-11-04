# M34.S04.T003 — Landed-cost linkage

## Scope and source evidence

The root `TASKS.md` row is the only task-specific scope: `M34.S04.T003 — Landed-cost linkage`; it has no separate linked acceptance file. The generated queue spec named this exact task. The applicable procurement finding in `docs/planning/GAP-009_PROCUREMENT_SUPPLIER_MANAGEMENT_AUDIT.md` says the landed-cost lifecycle must connect to PO/GRN before final costing. Existing M25 work already supplied the allocation and accounting chain, but the current service accepted unrelated GRN IDs and caller-provided PO/GRN display numbers without proving their source relationship.

## Implementation

- Landed-cost creation now resolves and locks the referenced shipment, purchase orders, and goods receipts, and rejects missing source records, duplicate GRNs, GRNs outside a PO-scoped document, or a header PO not linked to its selected shipment.
- Shipment-scoped documents can link only receipts whose POs are actually linked to that shipment. PO and GRN display snapshots are copied from their source rows, not trusted from request values.
- Adding a GRN link applies the same source checks and rejects duplicates while serializing edits on the landed-cost header.
- Allocation revalidates all stored links and requires every linked GRN to be posted before replacing any prior allocation rows. This prevents a mixed posted/draft shipment from silently reallocating the full charge to only the posted subset, and preserves previous allocations when validation fails.
- Invalid source references from create, add-link, and allocation map to client-visible HTTP 400 responses. No schema migration was needed; existing foreign keys and shipment/PO link records supply the authoritative identities.

## Verification

- Fresh task-owned PostgreSQL 16.6 migration and integration run: **5 passed**, Alembic `20261104_0001 (head)`, container cleanup verified. Final command output is preserved in the matching `*-V03.log` files in this session directory.
- Existing landed-cost allocation-basis unit regressions: **18 passed**.
- Targeted Ruff, Python compileall, and `git diff --check` passed.
- Independent read-only review found no actionable issue. The reviewer specifically checked canonical source snapshots, shipment/PO/GRN consistency, stable lock ordering, preservation of prior allocation rows, and HTTP error mapping.
- The first PostgreSQL attempt exposed a test-fixture setup-order issue in the mixed-status case. The fixture was corrected, and the final V03 run passed all five cases against the final source.

## Limits

All records were generated in an isolated, passwordless, loopback-only disposable database. No supplier invoice, import, shipment, GRN, company, or financial records from a real operation were used. This verifies software linkage and allocation guards; it does not authenticate freight/customs bills or assert live logistics or production acceptance.
