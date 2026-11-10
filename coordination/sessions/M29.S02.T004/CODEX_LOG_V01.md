# M29.S02.T004 — Calibration certificates/history

## Implementation

- Added an append-only calibration event history with the actual calibration date, authority, certificate/report reference, explicit PASS or FAIL outcome, interval snapshot, next-due snapshot, actor, and notes.
- Recording a PASS event updates the instrument's current calibration details and derives its status from the existing due-date rules. Recording a FAIL event marks the instrument OUT_OF_SERVICE. An older backfilled event is retained in history but cannot roll the current instrument state back.
- Added permission-gated history read and record endpoints and a registry history view. The form requires entered source details and does not create, upload, or claim a certificate file.
- Closed alternate status/evidence mutation paths: registering an instrument cannot assert calibration evidence; PATCH rejects calibration date, authority, certificate reference, status, and unknown fields. Interval edits and event writes lock the same instrument row to keep due-date calculations consistent.
- New event rows reference their instrument with delete restriction. Existing calibration data and history were not fabricated or backfilled.
- Added migration 20261108_0023 for the append-only event table and its constraints/index.

## Review and verification

- Independent read-only review found and verified fixes for direct evidence/status mutation, historical instrument identity after deletion, and concurrent interval/event updates. Final review reported no blocker and made no edits or test runs.
- Python syntax/import checks passed. Focused ESLint passed for the calibration registry page and QMS API client. Alembic heads reports 20261108_0023 as the single head. Scoped git diff --check reported no whitespace errors.
- No automated test suite or database migration was executed for this task. Comprehensive M29 verification and migration execution remain assigned to M29.S04.

## Queue status

Implementation is recorded as pending M29 milestone verification; this is not a claim that M29.S04 passed.
