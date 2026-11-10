# M29.S02.T002 — Calibration schedule/status

## Implementation

- Reused the existing QMS `InstrumentCalibration` records and derive the next due date from the recorded last-calibration date plus the configured interval. Missing calibration evidence remains `NOT_VERIFIED`; no instrument history or facility data was invented.
- Derived status is `OVERDUE` after the due date, `DUE_SOON` on the due date through the following 30 days, and `CURRENT` after that window. The existing 365-day interval default and 30-day warning window are software defaults, not regulatory or owner-approved standards.
- Added a read-only schedule report with a selectable due window, overdue/not-verified/out-of-service counts, and due instrument rows. It creates no appointments, calibration events, or certificates.
- Added the registry schedule view and an explicit way to preserve or clear the `OUT_OF_SERVICE` override. Clearing it recomputes status from recorded dates on the server.

## Review and verification

- Independent read-only review found and then confirmed the fix for clearing the service override; final review reported no blocker. The reviewer did not edit files or run tests.
- Scoped `git diff --check` reported no whitespace errors. Git also emitted its informational LF-to-CRLF notice for the frontend page.
- No automated test suite or database migration was run for this task. Comprehensive M29 checks and migration execution remain assigned to M29.S04.

## Queue status

Implementation is recorded as pending M29 milestone verification; this is not a claim that M29.S04 passed.
