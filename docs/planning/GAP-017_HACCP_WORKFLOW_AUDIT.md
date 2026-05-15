# GAP-017 HACCP Audit-Grade Workflow Completion — Audit

## Summary

HACCP system is structurally complete. Core workflow (hazard analysis → CCP → monitoring → corrective action → verification → audit) exists end-to-end. Gaps are in reporting, traceability integration, and frontend pages — not core domain modeling.

---

## What Exists

### Models (`backend/app/models/qms.py`, `quality.py`)

| Model | Purpose |
|---|---|
| `HazardAnalysis` | Hazard identification with severity/likelihood risk matrix |
| `CriticalControlPoint` | CCP with critical limits (min/max), measurement unit, control measure |
| `CCPMonitoringLog` | Per-measurement record with `is_deviation` flag and auto-corrective action trigger |
| `AllergenValidationRecord` | Allergen presence verification per product/lot |
| `LotQualityStatus` | Lot-level quality disposition (pass/fail/hold/quarantine) |
| `QCDeviation` | Deviation record linked to CCP monitoring logs |
| `CorrectiveAction` | Multi-step CA with root cause, CAPA fields, due dates |
| `CorrectiveActionStep` | Individual step within a corrective action |
| `QualityAuditChecklist` | Audit checklist with scoring (BRC/FSSC/ISO22000/HALAL/HACCP_CODEX/SQF) |
| `SupplierFoodSafetyApproval` | Supplier approval record with expiry tracking |
| `InstrumentCalibration` | Calibration record for monitoring instruments |
| `AQLSamplingPlan` | Acceptance Quality Limit plans for incoming goods |
| `CertificateOfAnalysis` | Lab CoA linked to lots |
| `QMSAIRecommendation` | AI-generated QMS recommendations |

### Endpoints

- **66 endpoints** across `quality.py` and `qms.py`
- Full CRUD for all core models
- Workflow transitions: deviation → corrective action → verification → close
- Checklist scoring with section-level breakdown
- Supplier approval renewal workflow

### AI Agents

| Agent | Capability |
|---|---|
| `quality_risk_predictor` | Predict quality risk from CCP trends |
| `deviation_analyzer` | Analyze deviation root causes |
| `haccp_assistant` | General HACCP Q&A and guidance |

### Migration

- `f1a2b3c4d5e6_qms_haccp_system.py` — creates all HACCP/QMS tables

### Module Registry

- Registered as `ModuleDefinition` (not loose endpoint)
- `critical=True`
- `ai_mode=AIMode.RULE_BASED`
- Permission actions: view, create, edit, delete, approve, report, admin

---

## What Is Partial or Missing

### Backend Gaps

| Gap | Detail |
|---|---|
| HACCP document version control | No versioned HACCP plan documents; CCP changes have no audit trail |
| Batch-wise CCP monitoring reports | No endpoint aggregates monitoring logs by production batch |
| Microbiological sampling structure | No dedicated micro sampling model beyond AQL |
| Environmental monitoring program | No swab/surface test records |
| Sanitation records | Only allergen validation; no general sanitation verification |
| PDCA cycle closure | CorrectiveAction has no `effectiveness_verified_at` / `pdca_closed_at` fields |
| Traceability integration | CCP violation not linked to `LotTrace` or recall trigger |
| Crisis/recall trigger | No endpoint or field escalates CCP critical violation to recall workflow |
| Internal audit scheduling | QualityAuditChecklist has no scheduled date / recurrence fields |
| Regulatory export | No PDF/CSV export endpoint for regulatory submission |
| Third-party lab integration | CoA is manual upload; no lab API webhook |

### Frontend Gaps

| Gap | Detail |
|---|---|
| Dedicated HACCP plan page | No `/dashboard/quality/haccp-plans` |
| CCP monitoring dashboard | No `/dashboard/quality/ccp-monitoring` |
| Deviations list/detail | No `/dashboard/quality/deviations` |
| Corrective actions board | No `/dashboard/quality/corrective-actions` |
| Audit checklist page | No `/dashboard/quality/audits` |
| 6 quality pages exist | Generic quality pages exist but none are HACCP/CCP-specific |

---

## Risk Assessment

| Risk | Severity |
|---|---|
| PDCA closure gap | Medium — CA can be closed without effectiveness verification |
| No recall trigger from CCP violation | High for food safety — critical deviation has no escalation path |
| No regulatory export | Medium — audit submission is manual |
| Frontend gap | Low for backend audit; blocks end-user adoption |

---

## Recommended Scope for GAP-017

### Do (minimal additions)
1. Add `effectiveness_verified_at` and `pdca_status` to `CorrectiveAction` (migration)
2. Add `scheduled_date` / `recurrence_days` to `QualityAuditChecklist` (migration)
3. Add batch CCP monitoring report endpoint (no new table)
4. Add HACCP frontend pages: plans, CCP monitoring, deviations, corrective actions, audits

### Skip (out of scope)
- Recall trigger integration (separate GAP touching warehouse/inventory)
- Third-party lab API (external dependency)
- Regulatory PDF export (separate reporting GAP)
- Microbiological/environmental monitoring models (separate extension GAP)

---

## Files of Interest

| File | Purpose |
|---|---|
| `backend/app/models/qms.py` | All HACCP/QMS models |
| `backend/app/api/v1/endpoints/quality.py` | Quality endpoints (hazard, CCP, monitoring, deviations) |
| `backend/app/api/v1/endpoints/qms.py` | QMS endpoints (CA, checklists, supplier, instruments) |
| `backend/alembic/versions/f1a2b3c4d5e6_qms_haccp_system.py` | Original HACCP migration |
| `frontend/src/app/dashboard/quality/` | Existing frontend quality pages |
