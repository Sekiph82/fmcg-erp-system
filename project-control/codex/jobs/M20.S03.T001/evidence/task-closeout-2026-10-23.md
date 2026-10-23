# M20.S03.T001 Closeout

- Task: Validate work-center/machine capacity calculations
- Status: COMPLETE
- Evidence date: 2026-10-23
- Acceptance: `coordination/milestones/M20/CODEX_M20_MASTER_PROMPT_V04.md`, M20.S03.T001
- Applicable strict audit: `coordination/milestones/M20/CHATGPT_M20_STRICT_AUDIT_V05.md`

## Implemented

- Finite capacity uses configured work-center rates converted into the product unit, explicit shift calendars, maintenance/holiday flags, and downtime intervals clipped to shift windows.
- Calendar declarations fail closed when hours, shift pairs, shift overlap, cross-date overnight overlap, or downtime intervals are invalid. Overnight downtime is attributed to the shift that spans it.
- Concurrent lines share aggregate work-center capacity. Locked commitments allocate first and keep their persisted line state unchanged; overload attribution follows that allocation order so an unlocked line cannot appear feasible after a locked commitment consumes its capacity.
- Infinite mode clears stale finite-capacity slots without claiming line feasibility. Invalid ranges, quantities, rates, resources, calendars, and downtime produce persisted line diagnostics.
- Capacity diagnostics are represented by the API schema and surfaced in the MPS constraints UI with per-line hours and dates.

## Verification

- `backend/tests/test_m20_v03_acceptance.py`: 13 passed, 67 warnings. Ran against a newly created loopback-only PostgreSQL container and uniquely named `fmcg_m20_t001_<random>` database with `M20_DISPOSABLE_TEST_DATABASE=1`; the container and database were removed after the run. The fixture data used synthetic `M20-CAP-*` identifiers.
- `backend/tests/test_m20_remaining_engine.py`: 31 passed.
- `frontend`: `npm run type-check` passed.
- `python -m py_compile` for the edited backend service, schema, and tests passed.
- `git diff --check` passed.
- Independent read-only review: no remaining concrete findings after fixes for overload attribution, per-line hours, overnight shifts, cross-date shift overlap, and malformed downtime.
- GitHub Actions were not dispatched.

The PostgreSQL suite emitted 67 existing/runtime warnings; the test result itself was successful. No owner-provided business data or credentials were used.
