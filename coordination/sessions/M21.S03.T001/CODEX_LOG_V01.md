# M21.S03.T001 — Nested/intermediate BOM support verification

## Findings and changes

The public BOM explosion service already recursed through child BOMs, but inspection found silent truncation for a missing child, a cycle, or depth overflow. It also treated a non-positive base quantity as a scale factor of one, did not check the parent line UOM against the child BOM UOM, and used a global visited set that dropped repeated use of the same intermediate BOM.

The service now fails closed with a descriptive BOM explosion error for missing children, incompatible child UOM, cycles, depth overflow, non-positive/non-finite BOM base quantity, and non-positive/non-finite target quantity. The API maps invalid nested structures to HTTP 422 while retaining HTTP 404 for an unknown root BOM. Cycle detection now follows the active recursion path, allowing a valid intermediate BOM to appear in multiple branches and contribute to aggregate leaf quantities.

## Verification evidence

- Focused Python suite: 40 passed, 1 disposable-PostgreSQL test skipped in the non-disposable run. It included existing M20 engine tests plus nested scaling, repeated child aggregation, missing child, UOM mismatch, zero base, cycle, depth, and API status tests.
- Task-owned disposable PostgreSQL runner passed all 10 tests, including an ORM-backed root → repeated intermediate → leaf scenario with exact quantity/loss assertions and rollback cleanup.
- Disposable PostgreSQL image: `postgres:16-alpine`, image ID `sha256:16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229`.
- Disposable database: `fmcg_m21_s03_t001_77d7d3f73e614a7dbf78035f`; Alembic reached `20261028_0021`. Container used a loopback-only published port, no volume mounts, and was removed by the runner.
- Python compilation and `git diff --check` passed.
- Independent read-only review found no remaining blocker after the zero-base validation was added.

## Scope limits

The generic explosion preview does not establish policy for co-products, substitutions, or lifecycle/effectivity enforcement. The M20 strict audit continues to describe nested BOM evidence as bounded; this task verifies the M21 public explosion path and does not claim M20 milestone acceptance.
