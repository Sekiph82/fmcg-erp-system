# M34.S05.T001 — CODEX Work Log

## Task

Sourcing workflow tests, as the exact current `TASKS.md` task.

## Work completed

- Added a task-specific PostgreSQL integration test that exercises the existing sourcing workflow through FastAPI's registered routes and JSON request/response validation.
- Used synthetic users, suppliers, bids, and approval rules only. Verified unauthenticated denial; invitations; forbidden uninvited bids; mandatory technical failure and re-evaluation; award protection before qualification; and two-level approval before final RFQ/response state changes.
- Added a disposable PostgreSQL runner that creates a unique task-prefixed database/container, publishes PostgreSQL only on loopback, sets the exact disposable-database guard, migrates to head, runs the test module, and verifies container removal.
- No production workflow, schema, or supplier data was changed.

## Verification

See `verification-V01.md` and the final run artifacts `disposable-postgres-run-V05.log` and `container-cleanup-V05.log`.

## Review and boundaries

Independent read-only review found an initial gap because handler functions were called directly. The test was changed to ASGI requests through registered FastAPI routes and the actual cookie/JWT authentication dependency; the reviewer then reported no substantive findings. The test uses synthetic pre-enrolled TOTP state with minted test tokens; it does not exercise the login or 2FA challenge journey. It ends at the approved RFQ award and does not test PO conversion.
