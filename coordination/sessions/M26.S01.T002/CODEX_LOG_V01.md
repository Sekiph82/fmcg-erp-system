# M26.S01.T002 — Skill/certification expiry

## Implementation

- Preserved the existing 30-day `EXPIRING_SOON` rule and made its threshold a named constant; certifications remain valid through their expiry date, then become `EXPIRED` the following day.
- Recalculate derived status when listing certificates so stale stored values cannot keep expired certifications out of the expiring filter or appear current in the API response. The read path refreshes the ORM's loaded value without committing from a GET request.
- Expanded the explicit status refresh to cover all certification rows, including transitions when a certification is no longer required.
- Updated dashboard expiry counts to use current expiry dates instead of stale persisted status values.
- Added focused boundary cases for missing, expired, expiring today, the 30-day limit, the next day, and non-required certifications. They are included in milestone validation and have not been run yet.

## Lightweight evidence

- `python -m compileall -q app/services/machine_operator_service.py tests/test_m26_s01_t002_cert_expiry.py` — passed.
- Direct six-case expiry boundary smoke check — passed.
- `git diff --check` — passed.

## Pending milestone acceptance

The focused pytest, PostgreSQL persistence/filter behavior, consolidated M26 regression suite, and independent review remain pending M26 acceptance.
