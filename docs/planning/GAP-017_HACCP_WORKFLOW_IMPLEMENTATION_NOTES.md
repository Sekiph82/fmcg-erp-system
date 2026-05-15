# GAP-017 HACCP Audit-Grade Workflow Completion — Implementation Notes

## Summary

GAP-017 extended the existing HACCP/QMS implementation with PDCA cycle closure tracking, audit checklist scheduling, and a batch CCP monitoring report. The core HACCP workflow was already complete; this GAP added the three highest-priority missing fields and one new reporting endpoint.

---

## Implemented Scope

| Sub-area | What was done |
|---|---|
| Audit | `docs/planning/GAP-017_HACCP_WORKFLOW_AUDIT.md` |
| Schema Design | `docs/planning/GAP-017_HACCP_WORKFLOW_SCHEMA_DESIGN.md` |
| Migration | Added `backend/alembic/versions/20260515_0050_haccp_pdca_audit_scheduling.py` |
| Models | Added 3 columns to `backend/app/models/quality.py` |
| Schemas | Extended `backend/app/schemas/qms.py` |
| Services | Extended `backend/app/services/qms_service.py` |
| Endpoints | Extended `backend/app/api/v1/endpoints/qms.py` |
| Frontend | SKIPPED — all 16 QMS pages and nav links already exist |
| Permissions | SKIPPED — quality module actions already cover all new routes |
| Tests | `backend/tests/test_gap017_haccp_workflow.py` — 10 passed |

---

## Changes Made

### Migration: `20260515_0050_haccp_pdca_audit_scheduling.py`

| Table | Column | Type |
|---|---|---|
| `corrective_actions` | `pdca_closed_at` | TIMESTAMPTZ (nullable) |
| `qms_audit_checklists` | `scheduled_date` | DATE (nullable) |
| `qms_audit_checklists` | `recurrence_days` | INTEGER (nullable) |

Down_revision: `20260515_0030`. Offline SQL generation verified.

### Models: `backend/app/models/quality.py`

- `CorrectiveAction.pdca_closed_at` — DateTime(timezone=True), nullable
- `QualityAuditChecklist.scheduled_date` — Date, nullable
- `QualityAuditChecklist.recurrence_days` — Integer, nullable

### Schemas: `backend/app/schemas/qms.py`

- `CorrectiveActionUpdate.pdca_closed_at` — Optional[datetime]
- `CorrectiveActionRead.pdca_closed_at` — Optional[datetime]
- Added import: `AuditStandard, AuditType, AuditResult`
- New classes: `AuditChecklistBase`, `AuditChecklistCreate`, `AuditChecklistUpdate`, `AuditChecklistRead`

### Services: `backend/app/services/qms_service.py`

| Function | Purpose |
|---|---|
| `close_pdca(db, ca_id)` | Sets `pdca_closed_at`; validates CA must be VERIFIED first |
| `ccp_monitoring_batch_report(db, production_order_id)` | Aggregates CCPMonitoringLog by production order; returns deviation rate |

### Endpoints: `backend/app/api/v1/endpoints/qms.py`

| Route | Description |
|---|---|
| `GET /audit-checklists/{checklist_id}` | Full detail view including scheduling fields |
| `PATCH /audit-checklists/{checklist_id}` | Update `scheduled_date`, `recurrence_days`, `notes` |
| `POST /corrective-actions/{ca_id}/close-pdca` | Close PDCA cycle (validates VERIFIED status) |
| `GET /reports/ccp-batch/{production_order_id}` | Batch CCP monitoring summary report |

---

## PDCA Cycle Mapping

| Phase | Field |
|---|---|
| Plan | `created_at` |
| Do | `completed_at` (all steps done) |
| Check | `verified_at` + `effectiveness_check` |
| Act | `pdca_closed_at` (new) |

---

## Known Limitations

| Item | Detail |
|---|---|
| Live migration | Blocked until Docker/PostgreSQL available in dev environment |
| Recall integration | CCP critical violation → recall trigger is out of scope (separate GAP) |
| Regulatory export | No PDF/CSV export for regulatory submission |
| Lab API | CoA is manual upload; no webhook integration |
| Recurring audit auto-scheduling | `recurrence_days` is stored but no background task creates next audit automatically |
