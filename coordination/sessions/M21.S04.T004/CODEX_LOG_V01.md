# M21.S04.T004 — Permissions/audit/history

## Changes

- Kept conversion-profile creation behind the existing `bom.create` permission and records a `CONVERSION_PROFILE_CREATED` audit event in the same database transaction as the profile.
- Audit entries identify the actor, profile, BOM module, event time, and a limited after-snapshot of profile code, version, target product, conversion ratio, and effective dates.
- Added a selected-profile history panel to the conversion page. It queries the existing audit endpoint by `target_type=conversion_profile` and profile ID, and is rendered only for users with `audit.view`.
- Added the event's readable label to the shared audit event labels.
- Audit IP attribution uses only a validated socket-peer address. Client-provided forwarded headers are ignored; invalid peer values are omitted.

## Verification

- Frontend `npm run type-check` passed.
- Python compilation passed for the audit event model constants and BOM endpoint.
- `git diff --check` passed.
- Independent read-only review found a spoofable forwarded-IP issue in the first pass. The endpoint was corrected to validate and normalize only the socket-peer address; follow-up review found no remaining blocker.

## Scope limits

- No database-backed profile creation or audit-history request was run.
- No update/deactivate/delete operations were introduced; the history shown consists of events the application currently records for conversion profiles.
- No production or owner data was accessed or changed.
