# FMCG ERP — Documents & Communication Manual v2

**Version:** 2.0 (post-recovery)  
**Date:** 2026-05-24  
**Audience:** All staff, Department Managers, Administrators, Knowledge Management Officers  
**Modules Covered:** Documents · Compliance Documents · Knowledge Base · Communication · Helpdesk · Approvals · Logs

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Documents Module](#2-documents-module)
3. [Compliance Documents](#3-compliance-documents)
4. [Knowledge Base](#4-knowledge-base)
5. [Communication](#5-communication)
6. [Helpdesk](#6-helpdesk)
7. [Approvals](#7-approvals)
8. [System Logs](#8-system-logs)
9. [Security Logs](#9-security-logs)
10. [Common Mistakes & Troubleshooting](#10-common-mistakes--troubleshooting)
11. [Related Modules](#11-related-modules)

---

## 1. Module Overview

**What it does:** Central document management — store, version, and share business documents. Internal communications, helpdesk ticketing, approval workflow management, and audit log review.

**Who uses it:**
- All staff — access documents, raise helpdesk tickets, submit approvals
- Administrators — manage document library, configure approvals
- Managers — approve requests and review audit logs
- Knowledge Officers — maintain knowledge base and SOPs

**Modules at a glance:**

| Feature | Route | Purpose |
|---------|-------|---------|
| Documents | `/dashboard/documents` | Document library |
| Communication | `/dashboard/communication` | Internal messaging |
| Helpdesk | `/dashboard/helpdesk` | IT and support tickets |
| Approvals | `/dashboard/approvals` | Pending approval queue |
| Logs | `/dashboard/logs` | System audit trail |

---

## 2. Documents Module

**Route:** `/dashboard/documents`

![Documents Overview](../../user-manual/screenshots/captured/115_documents.png)
*Documents module — document library and compliance documents.*

### What it does
Store, version control, and share business documents — contracts, SOPs, certifications, policies, and reports.

### Tabs

| Tab | Purpose |
|-----|---------|
| Library | General document library |
| Compliance | Compliance-specific documents |
| Knowledge Base | SOPs and how-to articles |

### Document Library

**Uploading a Document:**
1. Documents → Library → **+ Upload Document**
2. Select file (PDF, Word, Excel, image)
3. Set:

| Field | Required | Notes |
|-------|----------|-------|
| Title | Yes | Descriptive name |
| Category | Yes | Contract / Policy / SOP / Certificate / Report / Other |
| Department | No | Owning department |
| Tags | No | Searchable keywords |
| Version | No | e.g. "v2.1" |
| Expiry Date | No | For time-limited documents |
| Access Level | Yes | Public / Department / Restricted |
| Notes | No | Description |

**Version Control:**
- Upload new version → previous version archived automatically
- All versions retained; version history viewable on document detail
- Cannot delete a document if it is referenced by another record

**Document Access Levels:**
| Level | Visibility |
|-------|-----------|
| Public | All authenticated users |
| Department | Only members of the assigned department |
| Restricted | Only named users or roles |

---

## 3. Compliance Documents

**Tab:** Compliance

![Compliance Documents](../../user-manual/screenshots/captured/116_documents-compliance.png)
*Compliance document library — regulatory documents with expiry tracking.*

### What it does
Stores compliance-critical documents — regulatory licenses, permits, certifications, audit reports, and quality standards.

**Fields:**
- Document type: License / Permit / Certificate / Audit Report / Standard
- Issuing authority
- Reference number
- Issue date and expiry date
- Applicable product/facility
- Status: Valid / Expiring Soon / Expired

**Expiry alerts:** System sends email alerts 30 and 7 days before expiry to document owner and compliance manager.

---

## 4. Knowledge Base

**Tab:** Knowledge Base · Route: `/dashboard/documents/knowledge-base`

![Knowledge Base](../../user-manual/screenshots/captured/117_documents-knowledge-base.png)
*Knowledge base — SOPs, training guides, FAQs, and how-to articles.*

### What it does
Searchable internal knowledge repository — standard operating procedures, training materials, troubleshooting guides, and FAQs.

**Article types:** SOP / Work Instruction / Policy / FAQ / Training Guide / Troubleshooting

**Creating a Knowledge Article:**
1. Knowledge Base → **+ New Article**
2. Write in rich-text editor (supports headers, tables, images, links)
3. Set category, tags, and audience
4. Publish — immediately searchable

**Search:** Full-text search across all article titles, content, and tags. Results ranked by relevance.

**Article versioning:** Updates create a new version. Previous versions retained for audit trail.

---

## 5. Communication

**Route:** `/dashboard/communication`

![Communication Module](../../user-manual/screenshots/captured/139_communication.png)
*Internal communication hub — announcements, messaging, and notifications.*

### What it does
Internal messaging and announcements — system-wide broadcasts, department notices, and individual messages.

**Communication types:**
- **System Announcement** — broadcasts to all users (admin only)
- **Department Notice** — visible to a specific department
- **Direct Message** — user-to-user messaging

**Creating an Announcement:**
1. Communication → **+ New Announcement**
2. Set title, message body (rich text)
3. Select audience: All Users / Department / Role
4. Set expiry date (announcement disappears from feed after this date)
5. Post — users see it in their notification feed

---

## 6. Helpdesk

**Route:** `/dashboard/helpdesk`

![Helpdesk](../../user-manual/screenshots/captured/140_helpdesk.png)
*Helpdesk — support ticket queue with status, priority, and SLA tracking.*

### What it does
Internal IT and operational support ticketing — log issues, track resolution, SLA monitoring.

**Raising a Ticket:**
1. Helpdesk → **+ New Ticket**
2. Set:

| Field | Required | Notes |
|-------|----------|-------|
| Title | Yes | Brief description of issue |
| Category | Yes | IT / Finance / HR / Operations / Other |
| Priority | Yes | Low / Normal / High / Critical |
| Description | Yes | Full details |
| Attachment | No | Screenshot or file |
| Related Module | No | Which ERP module is affected |

**Ticket Status Flow:** `OPEN → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED`

**SLA targets:**
| Priority | First Response | Resolution |
|----------|---------------|-----------|
| Critical | 1 hour | 4 hours |
| High | 4 hours | 24 hours |
| Normal | 1 business day | 3 business days |
| Low | 3 business days | 1 week |

**Viewing your tickets:** Helpdesk → My Tickets tab shows all tickets you raised.

---

## 7. Approvals

**Route:** `/dashboard/approvals`

![Approvals](../../user-manual/screenshots/captured/135_approvals.png)
*Approvals queue — pending approval requests from all modules.*

### What it does
Central approval inbox — all approval requests routed here regardless of originating module (Purchase Orders, Leave, Payroll, Journals, etc.).

**Approval types that appear here:**
- Purchase Requisition approval
- Purchase Order approval
- Leave request
- Expense claim
- Journal entry
- Payroll approval
- Credit note approval
- Vendor payment

**Approving a Request:**
1. Approvals → click pending request
2. Review details (full document shown)
3. Click **Approve** or **Reject**
4. Add rejection reason (required if rejecting)
5. Requestor notified automatically

**Delegation:** If you are away, delegate approvals to a colleague in Settings → Approval Delegation.

**Approval chains:** Multi-level approvals configured per document type (e.g. PO > KES 500,000 requires Finance Director approval after Procurement Manager). Configured in Admin → Approvals.

---

## 8. System Logs

**Route:** `/dashboard/logs`

![Logs](../../user-manual/screenshots/captured/136_logs.png)
*System audit log — all user actions with timestamp, user, action type, and affected record.*

### What it does
Complete audit trail of all system actions — who did what, when, and to which record.

**Log entry fields:**
- Timestamp (date and time)
- User
- Action (Create / Update / Delete / Login / Export)
- Module
- Record ID
- Previous Value (for updates)
- New Value (for updates)
- IP Address

**Filtering logs:**
- By date range
- By user
- By action type
- By module

**Export:** Logs can be exported to CSV for external audit.

### Common log queries

| Query | Filter settings |
|-------|----------------|
| All deletes this week | Action = DELETE, Date = last 7 days |
| User login history | Action = LOGIN, User = [select user] |
| Invoice changes | Module = Sales, Action = UPDATE |
| Who approved this PO | Module = Procurement, Action = APPROVE, Record ID = [PO number] |

---

## 9. Security Logs

**Route:** `/dashboard/logs/security`

![Security Logs](../../user-manual/screenshots/captured/137_logs-security.png)
*Security event log — failed logins, password changes, permission changes, and suspicious activity.*

### What it does
Security-focused audit events:
- Failed login attempts (shows username and IP)
- Successful logins (with IP and device)
- Password reset events
- Permission changes (who granted/revoked what)
- Account lockouts
- Bulk export events
- API key creation/revocation

**Alert thresholds:** 5 failed logins from same IP triggers admin alert. Configurable in Admin → Security.

---

## 10. Common Mistakes & Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Document not visible | Access level set to Restricted | Request access from document owner or admin |
| Approval not appearing in queue | Approval chain misconfigured | Admin → Approvals → check chain for that document type |
| Helpdesk ticket stuck at OPEN | No support agent assigned | Admin assigns ticket in Helpdesk admin view |
| Knowledge base article not found | Tags not set | Edit article and add relevant tags |
| Compliance doc showing as expired | Renewal not uploaded | Upload new certificate and update expiry date |
| Log export blocked | Export permission not granted | Admin → Roles → enable `logs.export` permission |

---

## 11. Related Modules

| This Action | Connects To |
|-------------|-------------|
| PR/PO submitted | Approvals queue → Procurement Manager |
| Leave submitted | Approvals queue → Line Manager |
| QMS document | Quality → QMS tab (linked) |
| Regulatory certificate | Compliance → Regulatory Certs |
| Security log anomaly | Admin → Users (investigate account) |
| Helpdesk ticket resolved | Communication → notification to requestor |

---

*End of Documents & Communication Manual v2*
