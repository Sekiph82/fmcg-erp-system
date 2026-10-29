# M13.S03.T001 — Implementation prompt V01

Implement and verify the landed-cost posting chain under the exact root `TASKS.md` row and the acceptance criteria in `CHATGPT_AUDIT_CRITERIA_V01.md`.

Inspect the landed-cost service, GRN linkage, cost layers, inventory-account mappings and finance posting helpers first. Reuse existing fields and configured mappings; never hardcode business account IDs or modify stock quantity directly. Keep work within landed-cost posting, its focused regression tests and this task's evidence. Do not change unrelated operational posting modules or add a schema migration without a demonstrated requirement.

Run the full path against a disposable loopback PostgreSQL database with synthetic data. Prove valuation, balanced GL, period and permission gates, idempotency, concurrency/atomic rollback, and exact cleanup. Keep failures in the evidence log. Obtain an independent read-only review before marking complete. Do not claim production or live-provider readiness.
