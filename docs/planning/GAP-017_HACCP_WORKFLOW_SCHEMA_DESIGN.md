# GAP-017 HACCP Audit-Grade Workflow Completion — Schema Design

## Decision: Minimal Additive Migration

Core HACCP models are complete. Two small additive column sets close the most critical audit gaps identified in GAP-017A. No new tables.

---

## Existing Relevant Fields (do NOT re-add)

### `CorrectiveAction`

| Field | Type | Note |
|---|---|---|
| `status` | Enum(CorrectiveActionStatus) | OPEN/IN_PROGRESS/COMPLETED/VERIFIED/OVERDUE |
| `verified_at` | DateTime | Action verification timestamp |
| `verified_by_id` | UUID FK | Who verified the action |
| `effectiveness_check` | Text | Narrative effectiveness assessment |
| `completed_at` | DateTime | When all steps are done |

### `QualityAuditChecklist`

| Field | Type | Note |
|---|---|---|
| `audit_date` | Date | Date the audit was conducted |
| `next_audit_date` | Date | Follow-up or repeat audit date |
| `result` | Enum(AuditResult) | IN_PROGRESS/PASS/CONDITIONAL_PASS/FAIL |

---

## Proposed Additions

### `corrective_actions` table

| Column | Type | Nullable | Default | Reason |
|---|---|---|---|---|
| `pdca_closed_at` | TIMESTAMP WITH TIME ZONE | YES | NULL | Marks PDCA cycle fully closed (Act phase done). Distinct from `verified_at` (action verified) and `completed_at` (steps done). |

PDCA cycle mapping:
- **Plan** → CA created (`created_at`)
- **Do** → Steps completed (`completed_at`)
- **Check** → Effectiveness assessed (`verified_at`, `effectiveness_check`)
- **Act** → Preventive measures applied, cycle closed (`pdca_closed_at`)

### `qms_audit_checklists` table

| Column | Type | Nullable | Default | Reason |
|---|---|---|---|---|
| `scheduled_date` | DATE | YES | NULL | When the audit is planned to occur (before `audit_date` is set on completion). Enables scheduling views. |
| `recurrence_days` | INTEGER | YES | NULL | If set, auto-schedule follow-up at `audit_date + recurrence_days`. 365 = annual, 180 = semi-annual, 90 = quarterly. |

---

## What Is NOT in Scope for GAP-017

| Item | Reason |
|---|---|
| Recall trigger from CCP violation | Touches inventory/lot workflow — separate GAP |
| Microbiological/environmental monitoring models | New domain models — separate extension GAP |
| Third-party lab API webhooks | External dependency — out of scope |
| Regulatory PDF export | Reporting concern — separate GAP |
| PDCA status enum column | Derivable from existing fields — no extra column needed |

---

## Migration Plan

Single migration file: `20260515_0050_haccp_pdca_audit_scheduling.py`

```sql
-- corrective_actions: add pdca_closed_at
ALTER TABLE corrective_actions ADD COLUMN pdca_closed_at TIMESTAMP WITH TIME ZONE;

-- qms_audit_checklists: add scheduled_date, recurrence_days
ALTER TABLE qms_audit_checklists ADD COLUMN scheduled_date DATE;
ALTER TABLE qms_audit_checklists ADD COLUMN recurrence_days INTEGER;
```

Guards: use `_has_column()` before each ALTER to make the migration re-entrant.

---

## Schema Changes Summary

| Table | Column | Type | Change |
|---|---|---|---|
| `corrective_actions` | `pdca_closed_at` | TIMESTAMPTZ | ADD |
| `qms_audit_checklists` | `scheduled_date` | DATE | ADD |
| `qms_audit_checklists` | `recurrence_days` | INTEGER | ADD |

Total: 3 additive nullable columns. Zero breaking changes.
