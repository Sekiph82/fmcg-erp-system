# Standalone Operational Pages

**Date:** 2026-05-18

This chapter covers workspaces that serve specific operational functions and do not fit neatly into the main module clusters.

---

## NPD (New Product Development)

**URL:** `/dashboard/npd`  
**Tab:** npd  
**Permission:** `npd.view`

![NPD Workspace](../screenshots/captured/118_npd.png)

Manages new product development projects from concept to launch:
- Project pipeline with stage gates
- Formula development linked to BOM
- Regulatory approval tracking
- Launch readiness checklist

---

## Maintenance

**URL:** `/dashboard/maintenance`  
**Permission:** `maintenance.view`

![Maintenance — Assets Tab](../screenshots/captured/120_maintenance-assets.png)

| Tab | Purpose |
|---|---|
| Overview | Maintenance KPI summary |
| Assets | Equipment register |
| Breakdowns | Corrective maintenance jobs |
| Plans | Preventive maintenance schedules |
| Predictive | Predictive maintenance (sensor data) |
| Spares | Spare parts inventory |
| Reports | Maintenance reports |

Linked to Production OEE — downtime in Production links to Maintenance breakdown records.

---

## Utility Management

**URL:** `/dashboard/utility-management`  
**Permission:** `utility_management.view`

![Utility Management](../screenshots/captured/122_utility-management.png)

| Tab | Purpose |
|---|---|
| Assets | Utility assets (meters, generators) |
| Electricity | kWh readings, cost, alerts |
| Water | Water consumption per process |
| Solar | Solar generation vs consumption |
| Steam | Steam boiler readings |
| Wastewater | Effluent discharge monitoring |
| Soft Water | Softener readings |
| Compressor | Air compressor records |
| Chemical Treatment | Water treatment records |
| Machine Utility | Per-machine utility allocation |
| Readings | Manual meter entry |
| Devices | IoT device configuration |
| KPI Center | Utility KPI dashboard |
| Alarm Center | Active alarms |
| Alarm Rules | Alarm threshold setup |
| Billing | Utility billing |
| Transactions | Utility cost transactions |
| Reports | Utility reports |
| Integration | External system sync |
| IoT | IoT stream config |
| ESG | Environmental metrics for ESG report |

---

## Helpdesk

**URL:** `/dashboard/helpdesk`  
**Permission:** `quality.view`

![Helpdesk Workspace](../screenshots/captured/140_helpdesk.png)

| Tab | Purpose |
|---|---|
| All | All tickets |
| Open | Open/unresolved tickets |
| Escalated | Escalated tickets |
| SLA | SLA compliance |
| Tickets | Ticket list |

Used for internal IT support and customer service tickets. Links to Consumer Complaints (Quality workspace).

---

## Documents

**URL:** `/dashboard/documents`
**Permission:** `documents.view`

> Hover over the ? icon in the page header for quick field, status, and workflow guidance.

![Documents Workspace](../screenshots/captured/115_documents.png)
*Documents workspace showing document library with permission-gated upload and management actions.*

| Tab | Purpose |
|---|---|
| Documents | General document library |
| Compliance | Compliance documents |
| Expiring | Documents expiring soon |
| Knowledge Base | SOPs, guides, FAQs |
| E-Sign | Electronic signature queue |

### Document Management

The documents module stores file metadata (name, category, status, tags, owner). File content storage requires a storage adapter (S3, local, or Azure) — this is not yet configured in the default installation. Documents currently track metadata only.

### Knowledge Base — Permission Requirements

The Knowledge Base tab requires dedicated permissions added in TASK-027:

| Action | Permission required |
|---|---|
| View KB articles | `knowledge_base.view` |
| Create KB article | `knowledge_base.create` |
| Edit KB article | `knowledge_base.edit` |
| Delete KB article | `knowledge_base.delete` |

![Documents — Knowledge Base](../screenshots/captured/117_documents-knowledge-base.png)
*Knowledge Base tab showing permission-gated article list. Users without `knowledge_base.view` see an access-denied message.*

**Before TASK-027:** KB endpoints used `get_current_user` only — any authenticated user could access all KB routes.
**After TASK-027:** All KB endpoints require `require_permission("knowledge_base.*")`. Frontend KB navigation is guarded with `RequirePermission("knowledge_base.view")`.

The article creation page at `/dashboard/knowledge-base/articles/new` is wrapped with `RequirePermission("knowledge_base.create")`. Users without this permission see the standard access-denied screen.

### E-Sign — Permission Requirements

The E-Sign page at `/dashboard/esign` requires:

| Action | Permission required |
|---|---|
| View signature queue | `esign.view` |
| Sign or decline a document | `esign.sign` |
| Request a signature | `esign.request` |

**Before TASK-027:** E-sign request, list, and dashboard endpoints were unguarded.
**After TASK-027:** All 4 e-sign endpoints require `require_permission("esign.*")`. Frontend e-sign page is wrapped with `RequirePermission("esign.view")`.

> **Note:** There is no dedicated `/dashboard/esign` route separate from the Documents workspace. The E-Sign tab is nested inside `/dashboard/documents`. The `esign/page.tsx` exists but is accessed via the Documents module. Captures of the Documents page cover the E-Sign access path.

### File Upload Limitation

Document file upload (actual file content) is deferred — requires storage adapter configuration (S3 bucket, local volume, or Azure Blob). Until a storage adapter is configured, documents store metadata only. File upload fields in the UI reflect this limitation.

### Deferred Items

| Feature | Status | Blocker |
|---|---|---|
| File storage adapter | Not configured | Storage provider decision (S3/local/Azure) |
| E-sign cryptographic hash | Not implemented | Security design decision |
| E-sign expiry automation | Not implemented | Scheduler integration decision |
| Documents service layer refactor | Low priority | Inline CRUD currently used; no blocker |

---

## Communication

**URL:** `/dashboard/communication`

![Communication Workspace](../screenshots/captured/139_communication.png)

| Tab | Purpose |
|---|---|
| Messages | Internal direct messages |
| Chatter | Record-linked comments |
| Email | Email integration |
| WhatsApp | WhatsApp business messaging |
| Calls | VoIP call log |
| Meetings | Meeting scheduler |
| Calendar | Shared calendar |
| Notifications | Notification settings |

---

## Shop Floor

**URL:** `/dashboard/shop-floor`  
**Permission:** `production.view`

![Shop Floor — Terminal](../screenshots/captured/051_shop-floor-terminal.png)

| Tab | Purpose |
|---|---|
| Overview | Line summary |
| Terminal | Operator job card confirm/reject |
| Supervisor | Supervisor floor view |
| Queue | Work queue board |
| Downtime | Live downtime logging |
| Handover | Shift handover notes |

Designed for touchscreen use on the factory floor. Large buttons, minimal text.
