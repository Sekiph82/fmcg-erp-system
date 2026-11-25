# M43 gate — step 5: real local app walkthrough (2026-11-25)

## Setup

- Backend: uvicorn on :8020, connected to the disposable DB `m43_walk` (head 0073 plus synthetic seed). The owner's dev DB was not used.
- Frontend: `next dev` on :3220.
- `PROVIDER_EGRESS=local`; no provider keys are set.

## Personas

- `synth-rep`: non-admin, permissions crm.view / crm.edit / crm.create only.
- `synth-crm-manager`: crm.*_all, sales.view, integrations.view, marketing.view.

The manager was not made a superuser: a superuser login is correctly forced into 2FA enrolment by policy.

## Results

- **Rep on desktop:**
  - "My work", Contacts, Quotas, Playbooks and "Routing & approvals" render.
  - Adding a contact through the UI works: lifecycle LEAD is written to the history.
  - The Communication tabs stay hidden for this role (RBAC as configured).
- **Manager on desktop:**
  - Meetings shows Connected accounts as "Waiting for setup". This is honest: no OAuth client is configured.
  - A booking page is created through the UI.
- **Visitor at phone width (375×812):**
  - Public `/book/povu-intro`: the evening of the current day correctly shows no slots; the next day lists 08:00–16:30 in the visitor's zone.
  - Booked 09:30. Afterwards 09:00 and 09:30 disappear (10-minute buffer), so there is no double booking.
- **Server and console:**
  - Backend error log: no errors.
  - Console: three 401s from the pre-login session probe only.

## Defect found and fixed

The booking confirmation said "a calendar invitation is on its way" even when the host had no connected mailbox (nothing was sent).

- The API now returns `invitation: SENT | NO_MAILBOX | FAILED`.
- The page claims an invitation only when it was SENT.

## Not covered in this walkthrough

- The manage-link reschedule/cancel UI: the page reloaded after the fix. The API is covered by `test_m43_s01_t005_booking_db.py`.
- Provider round-trips (OAuth consent, Gmail, calendar, voice): these are covered by the simulator tests.

## Screenshots

See `screenshots/01`–`11`.
