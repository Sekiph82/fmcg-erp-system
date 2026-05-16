# GAP-020 Consumer Complaint and Recall Linkage Schema Design

## Summary

GAP-020 should harden the existing consumer complaint and recall linkage surface without introducing new tables in this slice. The current complaint model, recall model, recall service, and frontend pages already cover the core workflow. The immediate enterprise gap is ownership and authorization: consumer complaints are registered as a loose endpoint route, lack dedicated permission codes, and the sidebar currently borrows `quality.view`.

## Current Schema Baseline

`backend/app/models/consumer_complaints.py` already defines `ConsumerComplaint` with complaint reference, consumer details, product and lot fields, severity/status enums, investigation fields, recall trigger flag, manual recall reference, regulatory reporting flag, and lifecycle timestamps.

`backend/app/models/traceability.py` already defines recall records with `RecallHeader.linked_complaint_id`, `trigger_source`, recall scope lines, actions, customer impact, returns, status logs, evidence, and AI recommendations.

## Design Decision

No Alembic migration is required for this GAP-020 slice.

No ORM model change is required for this GAP-020 slice.

Inline endpoint schemas remain acceptable for now because the endpoint is small, functional, and not duplicated elsewhere. Extracting `ComplaintCreate`, `ComplaintUpdate`, and read schemas into `backend/app/schemas/consumer_complaints.py` is a future cleanup, not a dependency for permission hardening.

No dedicated consumer complaint service layer is required in this slice. The endpoint logic is simple CRUD/filter/stat behavior, and a full service extraction would increase the change surface without improving the immediate RBAC and module-ownership risk.

## Module Ownership Design

Promote `consumer_complaints` from `ENDPOINT_ROUTE_DEFINITIONS` into `MODULE_DEFINITIONS`.

Use the stable backend route:

- route prefix: `/consumer-complaints`
- import path: `app.api.v1.endpoints.consumer_complaints`
- frontend path: `/dashboard/quality/consumer-complaints`

## Permission Design

Register dedicated permission actions:

- `consumer_complaints.view`
- `consumer_complaints.create`
- `consumer_complaints.edit`
- `consumer_complaints.delete`
- `consumer_complaints.approve`
- `consumer_complaints.close`
- `consumer_complaints.link_recall`
- `consumer_complaints.export`

Endpoint protection should use these actions directly instead of `quality.view`.

Read endpoints use `consumer_complaints.view`. Creation uses `consumer_complaints.create`. General updates use `consumer_complaints.edit`, while close/resolution statuses require `consumer_complaints.close`, and recall escalation/linkage fields require `consumer_complaints.link_recall`.

## Role Grant Design

Owner keeps full access through wildcard permissions.

Admin receives all consumer complaint permissions, including delete.

Quality Manager receives view, create, edit, approve, close, link recall, and export, but not delete.

Quality Officer and Sales roles may receive view/create/edit for complaint intake and investigation handoff, but not delete or recall linkage.

Read-only Auditor may receive view/export only.

## Deferred Items

The following are intentionally out of scope for this controlled hardening slice:

- new FK from `recall_headers.linked_complaint_id` to `consumer_complaints.id`
- automatic recall creation from a SAFETY complaint
- complaint-to-recall reverse lookup endpoint
- dedicated complaint schema module
- dedicated complaint service module
- lot complaint surfacing inside recall scope calculation

## Acceptance Criteria for GAP-020B

GAP-020B is complete when this design records that no DB/model migration is needed for the current slice, preserves the existing complaint/recall schemas, and directs the implementation toward module ownership, dedicated permissions, endpoint guards, frontend guards, tests, and documentation.
