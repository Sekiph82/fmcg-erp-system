# GAP-020 Consumer Complaint and Recall Linkage Implementation Notes

## Summary

GAP-020 promotes Consumer Complaints into a dedicated, permissioned ERP module surface and hardens the complaint endpoint and frontend guards. The existing complaint and recall data models remain unchanged.

## Audit Findings From GAP-020A

The audit found that consumer complaints already support complaint intake, filtering, stats, lot lookup, status updates, recall trigger flags, and regulatory reporting flags.

The recall workflow is already deeper and lives under traceability, with recall headers, scope lines, actions, customer impact, returns, evidence, status logs, and regulatory report generation.

The main gap was not missing CRUD. It was module ownership and authorization: `consumer_complaints` was only a loose endpoint route, no dedicated permission family existed, and the frontend nav borrowed `quality.view`.

## Design Decision From GAP-020B

No database migration was added.

No ORM model change was added.

No schema extraction or service-layer refactor was added in this slice. The current endpoint schemas and inline CRUD logic are functional and small enough for the present hardening goal. A later cleanup can extract schemas/services if complaint logic grows.

## Module Registry Changes

`consumer_complaints` is now a `ModuleDefinition` with the stable route prefix `/consumer-complaints` and import path `app.api.v1.endpoints.consumer_complaints`.

The old loose endpoint-route ownership entry was removed and replaced with a comment to avoid duplicate route ownership.

## Permissions and Seed Role Grants

Dedicated permission codes are registered:

- `consumer_complaints.view`
- `consumer_complaints.create`
- `consumer_complaints.edit`
- `consumer_complaints.delete`
- `consumer_complaints.approve`
- `consumer_complaints.close`
- `consumer_complaints.link_recall`
- `consumer_complaints.export`

Admin receives the full permission set, including delete.

Quality Manager receives operational complaint handling and recall linkage permissions, excluding delete.

Quality Officer and sales-facing manager roles receive complaint intake/update permissions but not delete or recall linkage.

Read-only Auditor receives view/export only.

## API Endpoint Protection Changes

Complaint list, detail, stats, and lot lookup now require `consumer_complaints.view`.

Complaint creation now requires `consumer_complaints.create`.

Complaint updates now require `consumer_complaints.edit`.

Updates that resolve, compensate, or close a complaint additionally require `consumer_complaints.close`.

Updates that escalate a complaint, set the recall flag, or write a recall reference additionally require `consumer_complaints.link_recall`.

## Frontend Nav and Page Guard Changes

The Consumer Complaints sidebar item now uses `consumer_complaints.view` instead of `quality.view`.

The consumer complaint page now uses `RequirePermission` for page-level view access.

The Log Complaint action is guarded by `consumer_complaints.create`.

The Update action is guarded by `consumer_complaints.edit`.

## Recall Linkage Behavior and Current Limits

The current linkage remains explicit/manual: complaint severity can flag recall review, and recall records can store `linked_complaint_id`, but this slice does not auto-create recalls.

Deferred follow-ups include an FK constraint, reverse lookup endpoint, escalation audit trail, and complaint-aware recall scope calculation.

## Tests Added and Commands Run

Focused tests were added in `backend/tests/test_gap020_consumer_complaint_recall.py`.

Verification commands for GAP-020 are recorded in `CODEX_PROGRESS.md`.

## Known Limitations and Follow-Ups

The frontend consumer complaints page still uses direct `fetch` calls instead of a shared API client.

No delete endpoint currently exists for complaints, although the permission is reserved for future admin-only destructive handling.

`consumer_complaints.approve` is registered for future investigation outcome approval, but no dedicated approval endpoint exists yet.

Recall linkage remains soft and manual until a later recall workflow enhancement.

## Acceptance Criteria Snapshot

- Consumer Complaints is module-owned.
- Dedicated consumer complaint permissions are registered and seeded.
- Backend complaint endpoints use dedicated permissions.
- Frontend nav and page/action guards use dedicated permissions.
- Normal operational roles do not receive unsafe delete or recall-linkage permissions.
- Focused GAP-020 tests pass.
