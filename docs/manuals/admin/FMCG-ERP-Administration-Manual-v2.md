# FMCG ERP — Administration Manual v2

**Version:** 2.0 (post-recovery)  
**Date:** 2026-05-24  
**Audience:** System Administrators, IT Managers, ERP Implementation Teams  
**Modules Covered:** Admin · Users · Roles · Permissions · Security · System Configuration · Companies · Approval Chains · Integrations · AI

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Admin Dashboard](#2-admin-dashboard)
3. [User Management](#3-user-management)
4. [Roles & Permissions](#4-roles--permissions)
5. [Security Settings](#5-security-settings)
6. [System Configuration](#6-system-configuration)
7. [Company Management](#7-company-management)
8. [Approval Chain Configuration](#8-approval-chain-configuration)
9. [Audit Logs (Admin View)](#9-audit-logs-admin-view)
10. [Integrations](#10-integrations)
11. [AI Configuration](#11-ai-configuration)
12. [Products & Materials Master](#12-products--materials-master)
13. [Common Mistakes & Troubleshooting](#13-common-mistakes--troubleshooting)
14. [Security Best Practices](#14-security-best-practices)

---

## 1. Module Overview

**What it does:** Full system administration — user accounts, roles, permissions, security policies, system configuration, company setup, approval workflows, and external integrations.

**Who uses it:**
- System Administrator — manages all users, roles, and system settings
- IT Manager — configures integrations, security, and system parameters
- Implementation Team — initial setup of company, chart of accounts, master data

**When to use it:**
- When onboarding a new user
- When configuring a new department's approval chain
- When troubleshooting a permission error
- When setting up an integration (eTIMS, M-Pesa, bank)
- When resetting a user password

**Modules at a glance:**

| Feature | Route | Purpose |
|---------|-------|---------|
| Admin | `/dashboard/admin` | Full admin workspace |
| Products | `/dashboard/products` | Product master |
| Materials | `/dashboard/materials` | Materials master |
| Integrations | `/dashboard/integrations` | External system connections |
| AI | `/dashboard/ai` | AI assistant and configuration |
| Approvals | `/dashboard/approvals` | Approval queue |

---

## 2. Admin Dashboard

**Route:** `/dashboard/admin`

![Admin Dashboard](../../user-manual/screenshots/captured/003_admin.png)
*Admin hub — user counts, recent logins, pending approvals, system health.*

### Tabs

| Tab | Purpose |
|-----|---------|
| Users | User account management |
| Roles | Role definitions |
| Permissions | Permission matrix |
| Security | Password policy, 2FA, session settings |
| System Config | Core system parameters |
| Companies | Multi-company configuration |
| Approvals | Approval chain configuration |
| Logs | System audit log |

---

## 3. User Management

**Tab:** Users  
**Route:** `/dashboard/admin/users`

![Users Tab](../../user-manual/screenshots/captured/004_admin-users.png)
*User management — all user accounts with status, role, last login, and actions.*

### Creating a New User

Click **+ New User**:

| Field | Required | Notes |
|-------|----------|-------|
| Full Name | Yes | |
| Email | Yes | Used as login username |
| Password | Yes | Must meet password policy |
| Role | Yes | Select from configured roles |
| Department | No | For filtering and approval routing |
| Employee Link | No | Link to HR employee record |
| Is Active | Yes | Default true |
| Must Change Password | No | Force password change on first login |

**User Status:**
| Status | Meaning |
|--------|---------|
| Active | Can log in |
| Inactive | Login blocked (retain record) |
| Locked | Auto-locked after failed logins |

### Managing Users

- **Reset password** — Admin → Users → select user → Reset Password → sends email link
- **Unlock account** — select user → Unlock
- **Deactivate** — set Is Active = false (does not delete; retains audit history)
- **Never delete** users — deactivate instead. Deletion removes audit trail.

---

## 4. Roles & Permissions

**Tab:** Roles  
**Route:** `/dashboard/admin/roles`

![Roles Tab](../../user-manual/screenshots/captured/005_admin-roles.png)
*Roles list — system roles with user count and permission summary.*

![Permissions Tab](../../user-manual/screenshots/captured/006_admin-permissions.png)
*Permissions matrix — full list of permissions by module and role.*

### Role Design

**Default roles included:**

| Role | Typical User |
|------|-------------|
| Super Admin | IT Administrator |
| Finance Manager | Finance lead |
| Finance User | Accountant / payroll officer |
| Procurement Manager | Procurement lead |
| Procurement User | Purchasing officer |
| Production Manager | Factory/production lead |
| Production User | Production planner |
| Quality Manager | Quality lead |
| Quality User | QC officer |
| HR Manager | HR lead |
| HR User | HR officer |
| Sales Manager | Sales lead |
| Sales User | Sales rep |
| Warehouse Manager | Warehouse lead |
| Warehouse User | Storekeeper |
| View Only | Auditor / read-only access |

### Creating a Custom Role

1. Admin → Roles → **+ New Role**
2. Set name and description
3. Go to Permissions tab → select role → assign permissions per module
4. Save

**Permission granularity:** Each module has: view / create / edit / delete / approve / export. Assign only what the role needs.

### Permission Examples

| Permission | Grants |
|-----------|--------|
| `procurement.purchase_orders.approve` | Approve POs in Procurement module |
| `finance.journals.post` | Post journal entries |
| `hr.payroll.view` | View payroll data |
| `inventory.stock.adjust` | Post stock adjustments |
| `sales.invoices.void` | Void a posted invoice |

---

## 5. Security Settings

**Tab:** Security  
**Route:** `/dashboard/admin/security`

![Security Tab](../../user-manual/screenshots/captured/007_admin-security.png)
*Security configuration — password policy, session settings, and 2FA.*

### Password Policy

| Setting | Default | Recommended |
|---------|---------|-------------|
| Minimum length | 8 | 12 |
| Require uppercase | No | Yes |
| Require number | No | Yes |
| Require special char | No | Yes |
| Expiry (days) | None | 90 |
| History (prevent reuse) | None | 5 |

### Session Settings

| Setting | Default |
|---------|---------|
| Session timeout (minutes) | 480 (8 hours) |
| Concurrent sessions | 1 |
| Remember me duration | 30 days |

### Failed Login Policy

| Setting | Default |
|---------|---------|
| Max failed attempts | 5 |
| Lockout duration (minutes) | 30 |
| Notify admin on lockout | Yes |

### Two-Factor Authentication (2FA)
- Enable 2FA system-wide: Security → 2FA → Enable
- Users enroll via authenticator app (Google Authenticator, Microsoft Authenticator)
- Admin can reset 2FA for a user if they lose their device

---

## 6. System Configuration

**Tab:** System Config  
**Route:** `/dashboard/admin/system-config`

![System Config Tab](../../user-manual/screenshots/captured/008_admin-system-config.png)
*System configuration — timezone, currency, date format, company name, and core settings.*

### Core Settings

| Setting | Notes |
|---------|-------|
| Company Name | Displayed on all documents and reports |
| Default Currency | KES (Kenyan Shilling); can enable multi-currency |
| Timezone | Africa/Nairobi (UTC+3) |
| Date Format | DD/MM/YYYY (default for Kenya) |
| Fiscal Year Start | January (default); change if fiscal year differs |
| VAT Rate (Standard) | 16% (Kenya) |
| PAYE calculation method | KRA graduated bands |
| Notification Email | System emails sent from this address |
| ERP Version | Current version string |

### Number Series (Document Numbering)

Configure auto-numbering sequences per document type:

| Document | Default Format |
|----------|---------------|
| Purchase Requisition | PR-{YYYY}-{0001} |
| Purchase Order | PO-{YYYY}-{0001} |
| Sales Order | SO-{YYYY}-{0001} |
| Invoice | INV-{YYYY}-{0001} |
| Journal | JNL-{YYYY}-{0001} |
| Work Order | WO-{YYYY}-{0001} |

Number series can be reset at year start. Never reuse numbers — breaks audit trail.

---

## 7. Company Management

**Tab:** Companies  
**Route:** `/dashboard/admin/companies`

![Companies Tab](../../user-manual/screenshots/captured/009_admin-companies.png)
*Company management — multi-entity setup with subsidiary and branch configuration.*

### Single vs. Multi-Company

- **Single company:** Default setup — one entity, one chart of accounts
- **Multi-company:** Separate legal entities sharing the ERP; intercompany transactions supported

### Adding a Company

| Field | Required | Notes |
|-------|----------|-------|
| Company Name | Yes | Legal entity name |
| Registration Number | Yes | Companies Registry number |
| KRA PIN | Yes | Tax identification number |
| VAT Registration | No | If VAT registered |
| Address | Yes | Registered address |
| Currency | Yes | Primary currency |
| Fiscal Year | Yes | Start month |

---

## 8. Approval Chain Configuration

**Tab:** Approvals  
**Route:** `/dashboard/admin/approvals`

![Approvals Config](../../user-manual/screenshots/captured/010_admin-approvals.png)
*Approval chain configuration — define multi-level approvals per document type and amount threshold.*

### Configuring an Approval Chain

1. Admin → Approvals → **+ New Chain**
2. Select document type (PR, PO, Leave, Expense, Journal)
3. Set conditions (e.g. PO Amount > KES 500,000)
4. Add approval levels:
   - Level 1: Approver role or specific user
   - Level 2 (if needed): Escalation approver
   - Parallel approval (if needed): Both approvers must approve

**Example PO approval chain:**

| Condition | Level 1 | Level 2 |
|-----------|---------|---------|
| PO < KES 100,000 | Procurement Officer | — |
| PO KES 100,000–500,000 | Procurement Manager | — |
| PO > KES 500,000 | Procurement Manager | Finance Director |

### Approval Notifications
Approvers receive email notification when a document enters their queue. Reminder sent after 24 hours if not actioned.

---

## 9. Audit Logs (Admin View)

**Tab:** Logs  
**Route:** `/dashboard/admin/logs`

![Admin Logs](../../user-manual/screenshots/captured/011_admin-logs.png)
*Admin audit log — full system event history with search and filter.*

Admin view has full export capability. Standard users can only view logs for their own actions.

---

## 10. Integrations

**Route:** `/dashboard/integrations`

![Integrations](../../user-manual/screenshots/captured/133_integrations.png)
*Integrations hub — all external system connections.*

### M-Pesa Integration

**Route:** `/dashboard/integrations/mpesa`

![M-Pesa Integration](../../user-manual/screenshots/captured/134_integrations-mpesa.png)
*M-Pesa Daraja API configuration — consumer key, secret, and shortcode.*

**Setup steps:**
1. Go to Safaricom Developer Portal — create app
2. Get Consumer Key, Consumer Secret, Shortcode
3. Enter in Integrations → M-Pesa
4. Set callback URL to `https://your-erp-domain/api/v1/mpesa/callback`
5. Test with a small transaction
6. Set to **Live** environment

**M-Pesa transaction flow:**
- Customer pays to shortcode → Daraja callback → ERP auto-receives
- Matched to invoice by reference → invoice marked PAID

### eTIMS Integration
Configured in Finance → eTIMS tab. Requires:
- KRA control unit number
- eTIMS API credentials
- Each invoice auto-submitted on posting

### Bank API
Configured in Finance → Bank API tab. See Finance & Payroll Manual for setup.

---

## 11. AI Configuration

**Route:** `/dashboard/ai`

![AI Module](../../user-manual/screenshots/captured/131_ai.png)
*AI assistant module — intelligent recommendations and automated insights.*

![AI Chat](../../user-manual/screenshots/captured/132_ai-chat.png)
*AI chat interface — ask questions about your ERP data in natural language.*

### AI Features

| Feature | Description |
|---------|-------------|
| AI Chat | Ask questions about data: "What is our best selling product this month?" |
| Demand Forecast | AI-powered sales demand prediction |
| Procurement Suggestions | Smart reorder recommendations |
| Quality Alerts | Anomaly detection in QC data |
| Financial Insights | Automated variance commentary |

**AI chat examples:**
- "Show me all purchase orders above KES 1M this year"
- "Which products are below reorder level right now?"
- "What is the OEE for Line 2 this week?"
- "List employees whose contracts expire in 60 days"

---

## 12. Products & Materials Master

**Route:** `/dashboard/products` and `/dashboard/materials`

![Products](../../user-manual/screenshots/captured/012_products.png)
*Products master — finished goods, semi-finished, and trading products.*

![Materials](../../user-manual/screenshots/captured/013_materials.png)
*Materials master — raw materials, packaging, and consumables.*

### Products

| Field | Required | Notes |
|-------|----------|-------|
| Product Name | Yes | |
| SKU | Yes | Unique product code |
| Product Type | Yes | Finished Good / Semi-Finished / Trading / Service |
| Category | Yes | Product category |
| Unit of Measure | Yes | Primary sales UOM |
| Standard Cost | No | For costing |
| Sales Price | No | Default sales price |
| VAT Code | Yes | Tax classification |
| Is Active | Yes | Default true |
| Shelf Life (days) | No | For perishable products |
| Track Batches | No | Enable batch/lot tracking |
| Min Stock | No | Reorder trigger |

### Materials

Same fields as Products plus:
- `material_type`: Raw Material / Packaging / Chemical / Consumable
- `purity_spec`: Specification for food-grade materials
- `hazardous`: Boolean flag for dangerous goods

---

## 13. Common Mistakes & Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| User can't log in | Account locked after failed attempts | Admin → Users → Unlock account |
| User can't see a module | Missing role permission | Admin → Permissions → add view permission for that module |
| Approval chain not triggering | Chain not linked to document type | Admin → Approvals → check document type assignment |
| Document numbering gap | Manual number used | Numbers auto-increment; investigate if gap existed before your change |
| M-Pesa not receiving | Wrong callback URL | Set callback URL to production URL; not localhost |
| eTIMS submissions failing | KRA API credentials expired | Renew credentials on KRA eTIMS portal; update in ERP |
| Two-factor showing for user who lost phone | User unable to enroll | Admin → Users → Reset 2FA → user re-enrolls |

---

## 14. Security Best Practices

1. **Never share accounts** — each user must have their own login
2. **Principle of least privilege** — grant minimum permissions needed
3. **Enable 2FA** for all admin accounts and finance roles
4. **Audit logs weekly** — review security logs for anomalies
5. **Rotate API keys** — refresh M-Pesa and eTIMS credentials every 6 months
6. **Password policy enforcement** — minimum 12 chars, quarterly rotation for financial roles
7. **Deactivate leavers immediately** — run offboarding checklist the day an employee leaves
8. **Backup regularly** — database backup should run daily; test restores quarterly
9. **Session timeouts** — set to 2 hours for finance roles (shorter than default)
10. **Review user list** monthly — deactivate any account not used in 90 days

---

*End of Administration Manual v2*
