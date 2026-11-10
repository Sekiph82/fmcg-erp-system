# M23.S03.T002 — Decide and document offline requirement

## Decision

The initial virtual Shop Floor release is online-only for live reads and authoritative writes. Offline mutations will not be queued or automatically replayed. A request interrupted after submission is unconfirmed until the server state is refreshed and reconciled. The full policy, rationale, and follow-on requirements are in `coordination/milestones/M23/M23_S03_T002_OFFLINE_POLICY_V01.md`.

## Changes

- Added the canonical M23 offline policy and linked it from the Shop Floor user manual.
- Updated the M23 execution plan to remove the unresolved owner-answer note, record the selected policy, and correct its stale current-task checkpoint.
- The policy identifies idempotency/retry and operator exception feedback as follow-on M23 tasks; it does not claim offline functionality or real-factory acceptance.

## Verification and limits

- `git diff --check` passed for the task files.
- This is a product-policy/documentation task; no test suite was run.
- The choice is a conservative assumption for the virtual ERP requested by the owner. No physical network, tablet, or live facility was tested.
