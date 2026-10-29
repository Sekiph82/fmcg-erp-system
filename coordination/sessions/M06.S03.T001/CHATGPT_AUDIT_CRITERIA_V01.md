# M06.S03.T001 — Audit criteria V01

## Task scope

Verify the existing PO → GRN → supplier-invoice three-way matching transaction chain using only synthetic records in a fresh, task-owned PostgreSQL database. This is a verification and narrowly scoped defect-correction task, not production acceptance.

## Required behaviors

1. A supplier invoice linked to a purchase order is matched by its item against that PO's line and its goods-receipt lines.
2. Only a posted GRN may contribute accepted quantities or appear as a source link in a payable match. A draft receipt must not make an invoice payable.
3. Posting a valid GRN updates the receipt/PO/inventory ledger once. A subsequent match identifies the exact PO line and posted GRN line, and calculates ordered, received/accepted, previously billed, billable, and invoiced quantities consistently.
4. An invoice for more than the accepted, not-yet-billed quantity is held from payment. A matched invoice can be re-read without duplicating match rows or GRN links; an intentional rerun replaces the prior derived lines cleanly.
5. The supplier on the invoice must be the supplier on its linked PO. A mismatch must not produce a payable result.
6. Verify transaction effects and rollback at the database level. Do not claim that invoice matching posts AP/GL, clears GRNI, pays the supplier, or implements a finance policy: these remain separately identified gaps unless independently evidenced in canonical source.

## Adversarial coverage

- Draft GRN with otherwise matching invoice.
- Posted GRN, exact quantity and price.
- Cumulative billing: a second invoice is checked against the accepted quantity remaining after an earlier fully matched invoice.
- Linked PO belongs to another supplier.
- Repeat match without rerun and explicit rerun.
- Direct persisted assertions for header/line status, payable hold, PO/GRN source identity, PO/GRN state and received quantity, stock movement/quantity and row counts.
- Injected late failure after match-line writes followed by rollback and no persisted match side effects.
- Exact disposable database guard: task-prefixed database name, passwordless loopback PostgreSQL only, plus independent negative guard cases.

## Boundaries

- No production, owner, supplier, customer, or real factory data; no credentials; no live API/provider use.
- No accounting journal/AP/GRNI behavior invented or claimed. The existing GAP-002 audit explicitly records these integrations as incomplete.
- No schema/migration, frontend, unrelated procurement, or authentication redesign unless a concrete in-scope defect requires it.
- Keep unrelated pre-existing working-tree files untouched and unstaged.

## Evidence required for task completion

- Fresh PostgreSQL migration to the single current Alembic head.
- Focused task tests and named existing regressions, with exact commands/results.
- `py_compile` (or equivalent) and `git diff --check`.
- One independent read-only source review after implementation; reviewer must not edit, execute tests, or access the database.
- Exact disposable database/container cleanup and absence verification.
- Implementer log with starting/published SHAs, changed files, failures and corrections, checks, review, and limits of the evidence.
