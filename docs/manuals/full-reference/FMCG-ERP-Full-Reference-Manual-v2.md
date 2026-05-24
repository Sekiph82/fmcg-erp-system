# FMCG ERP — Full Reference Manual v2

**Version:** 2.0 (post-recovery)  
**Date:** 2026-05-24  
**Audience:** All staff, Implementation Teams, Auditors, System Administrators  
**Purpose:** Complete reference guide covering all 140+ routes, every module, all permissions, API endpoints, and cross-module data flows.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Complete Route Reference](#2-complete-route-reference)
3. [Module Reference Index](#3-module-reference-index)
4. [Permission Reference](#4-permission-reference)
5. [Data Flow Reference](#5-data-flow-reference)
6. [API Endpoints Reference](#6-api-endpoints-reference)
7. [Status Code Reference](#7-status-code-reference)
8. [Field Reference — Common Fields](#8-field-reference--common-fields)
9. [Keyboard Shortcuts & UI Tips](#9-keyboard-shortcuts--ui-tips)
10. [Configuration Reference](#10-configuration-reference)
11. [Glossary](#11-glossary)

---

## 1. System Architecture Overview

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 (App Router) + React + TypeScript |
| UI Components | Tailwind CSS + shadcn/ui |
| Backend | FastAPI (Python) |
| Database | PostgreSQL |
| Auth | Cookie-based sessions (`erp_access_token`) |
| API Pattern | REST; base URL: `http://localhost:8000/api/v1/` |

### Application Ports

| Service | Port |
|---------|------|
| Next.js (frontend) | 3000 |
| FastAPI (backend) | 8000 |
| PostgreSQL | 5432 |

### Frontend Architecture

- **App Router:** All pages in `frontend/src/app/dashboard/`
- **Middleware:** `frontend/src/middleware.ts` — handles auth guard and redirects
- **API Client:** `frontend/src/lib/api.ts` — Axios instance with base URL from `NEXT_PUBLIC_API_URL`
- **Auth cookie:** `erp_access_token` — required for all protected routes

---

## 2. Complete Route Reference

All 141 application routes (excluding login):

### Admin Routes

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard/admin` | Admin Hub | Administration dashboard |
| `/dashboard/admin/users` | Users | User account management |
| `/dashboard/admin/roles` | Roles | Role configuration |
| `/dashboard/admin/permissions` | Permissions | Permission matrix |
| `/dashboard/admin/security` | Security | Security policy settings |
| `/dashboard/admin/system-config` | System Config | Core system parameters |
| `/dashboard/admin/companies` | Companies | Multi-company setup |
| `/dashboard/admin/approvals` | Approval Config | Approval chain configuration |
| `/dashboard/admin/logs` | Admin Logs | Full audit log |

### Products & Materials

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard/products` | Products | Finished goods and trading items |
| `/dashboard/materials` | Materials | Raw materials and packaging |

### Supply Chain Routes

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard/procurement` | Procurement Hub | All procurement functions |
| `/dashboard/procurement/requests` | PRs | Purchase requisitions |
| `/dashboard/procurement/orders` | POs | Purchase orders |
| `/dashboard/procurement/rfq` | RFQ | Request for quotation |
| `/dashboard/procurement/deliveries` | Deliveries | Goods receipt |
| `/dashboard/procurement/suppliers` | Suppliers | Supplier master |
| `/dashboard/procurement/blanket` | Blanket | Framework agreements |
| `/dashboard/procurement/reorder` | Reorder | Reorder policies |
| `/dashboard/procurement/suggestions` | Suggestions | Auto-reorder suggestions |
| `/dashboard/procurement/subcontracting` | Subcontracting | Outsourced orders |
| `/dashboard/procurement/landed-cost` | Landed Cost | Import cost allocation |
| `/dashboard/suppliers` | Suppliers Master | Full supplier management |
| `/dashboard/warehouses` | Warehouses | Warehouse configuration |
| `/dashboard/warehouses/wms` | WMS | Warehouse management |
| `/dashboard/inventory` | Inventory | Stock management |
| `/dashboard/inventory/stock` | Stock | Current stock levels |
| `/dashboard/inventory/movements` | Movements | Transaction history |
| `/dashboard/inventory/cycle-count` | Cycle Count | Physical stock count |
| `/dashboard/inventory/shelf-life` | Shelf Life | Expiry tracking |
| `/dashboard/inventory/traceability` | Traceability | Batch/lot trace |
| `/dashboard/inventory/serials` | Serials | Serial number tracking |
| `/dashboard/inventory/valuation` | Valuation | Stock valuation |
| `/dashboard/wms` | WMS Hub | WMS main |
| `/dashboard/wms/zones` | Zones | Warehouse zones |
| `/dashboard/wms/locations` | Locations | Bin locations |
| `/dashboard/wms/quarantine` | Quarantine | Quarantine hold |
| `/dashboard/logistics` | Logistics | Shipment tracking |

### Manufacturing Routes

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard/recipes` | Recipes | Product formulations |
| `/dashboard/recipes/{id}` | Recipe Detail | Recipe detail and BOM items |
| `/dashboard/bom` | BOM | Bill of materials |
| `/dashboard/production` | Production Hub | Production workspace |
| `/dashboard/production/orders` | Work Orders | Production orders |
| `/dashboard/production/execution` | Execution | Real-time execution |
| `/dashboard/production/material-flow` | Material Flow | Material consumption |
| `/dashboard/production/costing` | Costing | Actual cost tracking |
| `/dashboard/shop-floor` | Shop Floor | Shop floor management |
| `/dashboard/planning` | Planning | MRP/MPS/capacity |
| `/dashboard/planning/mrp` | MRP | Material requirements |
| `/dashboard/planning/mps` | MPS | Master production schedule |
| `/dashboard/npd` | NPD | New product development |
| `/dashboard/quality` | Quality | QC management |
| `/dashboard/quality/inspections` | Inspections | QC inspections |
| `/dashboard/quality/certificates` | Certificates | Quality certificates |
| `/dashboard/quality/parameters` | Parameters | Test parameters |
| `/dashboard/compliance` | Compliance | Regulatory compliance |
| `/dashboard/compliance?tab=gs1` | GS1 Labels | Barcode generation |
| `/dashboard/compliance?tab=regulatory-certs` | Reg Certs | Regulatory certificates |

### Sales Routes

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard/sales` | Sales Hub | Full sales workspace |
| `/dashboard/sales/orders` | Orders | Sales orders |
| `/dashboard/sales/invoices` | Invoices | Customer invoices |
| `/dashboard/sales/customers` | Customers | Customer master |
| `/dashboard/sales/quotes` | Quotes | Quotations |
| `/dashboard/sales/pricing` | Pricing | Price management |
| `/dashboard/sales/contracts` | Contracts | Sales agreements |
| `/dashboard/sales/recurring-orders` | Recurring | Auto-scheduled orders |
| `/dashboard/sales/van-sales` | Van Sales | Van sales management |
| `/dashboard/sales/van-sales/vans/{id}` | Van Detail | Individual van |
| `/dashboard/sales/distributors` | Distributors | Distributor management |
| `/dashboard/sales/field-sales` | Field Sales | Field rep management |
| `/dashboard/pos` | POS | Point of sale |

### Finance Routes

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard/finance` | Finance Hub | Full finance workspace |
| `/dashboard/cashbook` | Cashbook | Cash and bank accounts |
| `/dashboard/payroll` | Payroll | Payroll management |
| `/dashboard/expenses` | Expenses | Expense claims |
| `/dashboard/fixed-assets` | Fixed Assets | Asset register |
| `/dashboard/bank-reconciliation` | Bank Recon | Bank reconciliation |
| `/dashboard/bank-api` | Bank API | Bank feed integration |
| `/dashboard/tax` | Tax | Tax management |
| `/dashboard/contracts` | Contracts | Financial contracts |
| `/dashboard/invoice-match` | Invoice Match | 3-way match |
| `/dashboard/etims` | eTIMS | KRA tax submissions |
| `/dashboard/integrations` | Integrations | External systems |
| `/dashboard/integrations/mpesa` | M-Pesa | M-Pesa configuration |

### HR Routes

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard/hr` | HR Hub | Full HR workspace |
| `/dashboard/hr/employees` | Employees | Employee master |

### CRM & Marketing Routes

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard/crm` | CRM | Customer relationship management |
| `/dashboard/marketing` | Marketing | Campaign and TPM management |

### Maintenance & Utilities Routes

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard/maintenance` | Maintenance | Equipment maintenance |
| `/dashboard/maintenance/assets` | Assets | Asset register |
| `/dashboard/maintenance/breakdowns` | Breakdowns | Breakdown log |
| `/dashboard/utility-management` | Utilities | Electricity and water |

### Analytics & AI Routes

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard/analytics` | Analytics | Business intelligence |
| `/dashboard/analytics/sales` | Sales Analytics | Sales analysis |
| `/dashboard/analytics/production` | Production Analytics | Manufacturing KPIs |
| `/dashboard/analytics/inventory` | Inventory Analytics | Stock analysis |
| `/dashboard/analytics/finance` | Finance Analytics | Financial reporting |
| `/dashboard/analytics/report-builder` | Report Builder | Custom reports |
| `/dashboard/ai` | AI | AI assistant |

### Documents & Communication Routes

| Route | Page | Description |
|-------|------|-------------|
| `/dashboard/documents` | Documents | Document library |
| `/dashboard/documents/knowledge-base` | Knowledge Base | SOPs and articles |
| `/dashboard/communication` | Communication | Internal messaging |
| `/dashboard/helpdesk` | Helpdesk | Support tickets |
| `/dashboard/approvals` | Approvals | Approval queue |
| `/dashboard/logs` | Logs | System audit log |
| `/dashboard/logs/security` | Security Logs | Security events |

---

## 3. Module Reference Index

Quick-reference table of all modules with their manual, route, and primary audience:

| Module | Manual | Primary Route | Primary User |
|--------|--------|--------------|-------------|
| Manufacturing | Manufacturing Manual | `/dashboard/production` | Production Manager |
| Recipes | Manufacturing Manual | `/dashboard/recipes` | Production / NPD |
| BOM | Manufacturing Manual | `/dashboard/bom` | Production Manager |
| Planning | Manufacturing Manual | `/dashboard/planning` | Planning Manager |
| Shop Floor | Manufacturing Manual | `/dashboard/shop-floor` | Supervisor |
| NPD | Manufacturing Manual | `/dashboard/npd` | NPD Manager |
| Quality | Manufacturing Manual | `/dashboard/quality` | Quality Officer |
| Compliance | Manufacturing Manual | `/dashboard/compliance` | Quality / Regulatory |
| Procurement | Supply Chain Manual | `/dashboard/procurement` | Procurement Officer |
| Inventory | Supply Chain Manual | `/dashboard/inventory` | Warehouse Manager |
| WMS | Supply Chain Manual | `/dashboard/wms` | Warehouse Manager |
| Logistics | Supply Chain Manual | `/dashboard/logistics` | Logistics Officer |
| Sales | Sales Manual | `/dashboard/sales` | Sales Manager |
| POS | Sales Manual | `/dashboard/pos` | Cashier |
| Finance | Finance Manual | `/dashboard/finance` | Accountant |
| Payroll | Finance Manual | `/dashboard/payroll` | Payroll Officer |
| HR | HR Manual | `/dashboard/hr` | HR Officer |
| CRM | Commercial Manual | `/dashboard/crm` | Sales / CRM |
| Marketing | Commercial Manual | `/dashboard/marketing` | Marketing Manager |
| Maintenance | Maintenance Manual | `/dashboard/maintenance` | Engineer |
| Utilities | Maintenance Manual | `/dashboard/utility-management` | Utility Manager |
| Analytics | Intelligence Manual | `/dashboard/analytics` | All Managers |
| AI | Intelligence Manual | `/dashboard/ai` | All Staff |
| Admin | Admin Manual | `/dashboard/admin` | System Admin |
| Documents | Documents Manual | `/dashboard/documents` | All Staff |
| Helpdesk | Documents Manual | `/dashboard/helpdesk` | All Staff |

---

## 4. Permission Reference

### Permission Naming Convention
`<module>.<resource>.<action>`

Examples: `procurement.purchase_orders.approve`, `inventory.stock.adjust`, `hr.payroll.view`

### Actions Available Per Resource

| Action | Meaning |
|--------|---------|
| view | Read access — see lists and details |
| create | Create new records |
| edit | Update existing records |
| delete | Delete records (usually DRAFT only) |
| approve | Approve workflows (journals, POs, leave) |
| export | Export to Excel/CSV/PDF |
| admin | Full access including configuration |

### Critical Permissions

| Permission | Risk Level | Who Should Have |
|-----------|-----------|----------------|
| `finance.journals.post` | High | Finance Manager only |
| `finance.invoices.void` | High | Finance Manager only |
| `sales.invoices.void` | High | Sales Manager + Finance |
| `inventory.stock.adjust` | Medium | Warehouse Manager |
| `hr.payroll.approve` | High | Finance Manager / MD |
| `admin.users.create` | High | System Admin only |
| `admin.permissions.edit` | Critical | System Admin only |
| `logs.export` | Medium | Finance Manager + Admin |

---

## 5. Data Flow Reference

### Order-to-Cash Flow

```
CRM Lead → Opportunity → 
Sales Quote → Sales Order (Confirmed) →
WMS Pick Wave → Dispatch (Inventory decrease) →
Delivery Confirmation →
Sales Invoice (Posted) →
eTIMS Submission (KRA) →
Customer Payment (Collection) →
Bank Reconciliation →
AR Cleared
```

### Procure-to-Pay Flow

```
MRP/Suggestion → Purchase Requisition (Draft) →
PR Approval →
Purchase Order (Sent to Supplier) →
Goods Receipt (GRN) → Inventory Increase →
Invoice Match (3-way: PO + GRN + Supplier Invoice) →
AP Invoice Posted →
Supplier Payment →
Bank Reconciliation →
AP Cleared
```

### Production Flow

```
MPS/Demand → Production Plan →
Work Order (Released) →
Shop Floor Execution →
Material Issue (Inventory Decrease) →
Work Order Completion →
Finished Goods Inventory Increase →
QC Inspection →
PASS: Available for Sale | FAIL: Quarantine
```

### Payroll Flow

```
Employee Master Data →
Attendance Records →
Leave Records →
Payroll Profile (Salary + Deductions) →
Payroll Run (PAYE / NSSF / NHIF computed) →
Payroll Approval →
GL Journal Post (Salaries Payable) →
Bank Payment File Generated →
Employee Payment →
Payslip Available on ESS
```

---

## 6. API Endpoints Reference

**Base URL:** `http://localhost:8000/api/v1/`

### Core Endpoint Patterns

| Resource | List | Create | Get | Update | Delete |
|----------|------|--------|-----|--------|--------|
| Products | GET /products/ | POST /products/ | GET /products/{id} | PATCH /products/{id} | DELETE /products/{id} |
| Materials | GET /materials/ | POST /materials/ | GET /materials/{id} | PATCH /materials/{id} | DELETE /materials/{id} |
| Suppliers | GET /suppliers/ | POST /suppliers/ | GET /suppliers/{id} | PATCH /suppliers/{id} | — |
| Purchase Orders | GET /purchase-orders/ | POST /purchase-orders/ | GET /purchase-orders/{id} | PATCH /purchase-orders/{id} | — |
| Sales Orders | GET /sales-orders/ | POST /sales-orders/ | GET /sales-orders/{id} | PATCH /sales-orders/{id} | — |
| Recipes | GET /recipes/ | POST /recipes/ | GET /recipes/{id} | PATCH /recipes/{id} | DELETE /recipes/{id} (DRAFT only) |
| Work Orders | GET /work-orders/ | POST /work-orders/ | GET /work-orders/{id} | PATCH /work-orders/{id} | — |
| Employees | GET /employees/ | POST /employees/ | GET /employees/{id} | PATCH /employees/{id} | — |
| Inventory Stock | GET /inventory/stock/ | POST /inventory/stock/ | GET /inventory/stock/{id} | PATCH /inventory/stock/{id} | — |
| Invoices | GET /invoices/ | POST /invoices/ | GET /invoices/{id} | PATCH /invoices/{id} | — |
| QC Inspections | GET /quality/inspections/ | POST /quality/inspections/ | GET /quality/inspections/{id} | PATCH /quality/inspections/{id} | — |
| Regulatory Certs | GET /regulatory-certs/ | POST /regulatory-certs/ | GET /regulatory-certs/{id} | PATCH /regulatory-certs/{id} | DELETE /regulatory-certs/{id} |

### Authentication

All API calls require authentication. The frontend uses cookie-based auth (`erp_access_token`). For direct API calls, include the cookie in the request header.

**Login:** `POST /api/v1/auth/login` with `{email, password}` → returns cookie

### API Response Formats

**Success (200):** `{data: {...}, status: "success"}`  
**List (200):** `{data: [...], total: N, page: N, per_page: N}`  
**Create (201):** `{data: {...}, status: "created"}`  
**Error (4xx/5xx):** `{detail: "error message", status: "error"}`

---

## 7. Status Code Reference

### Universal Status Patterns

| Status | HTTP | Meaning |
|--------|------|---------|
| DRAFT | — | Record created but not submitted |
| SUBMITTED / PENDING | — | Awaiting approval |
| APPROVED | — | Approved and ready |
| ACTIVE | — | In use / live |
| COMPLETED | — | Process finished |
| CLOSED | — | Fully reconciled and locked |
| CANCELLED | — | Cancelled; no further action |
| VOID | — | Voided; reversed |

### Document-Specific Statuses

**Purchase Orders:** DRAFT → SENT → ACKNOWLEDGED → PARTIAL_DELIVERY → DELIVERED → INVOICED → CLOSED

**Sales Orders:** DRAFT → CONFIRMED → PICKING → DISPATCHED → DELIVERED → INVOICED → CLOSED

**Work Orders:** DRAFT → CONFIRMED → RELEASED → IN_PROGRESS → COMPLETED → CLOSED

**Recipes:** DRAFT → APPROVED → OBSOLETE

**Invoices:** DRAFT → POSTED → PARTIALLY_PAID → PAID → VOID

**Leave:** DRAFT → SUBMITTED → APPROVED → REJECTED

**Payroll:** DRAFT → GENERATED → APPROVED → POSTED → PAID

---

## 8. Field Reference — Common Fields

Fields used across many modules:

| Field | Type | Pattern |
|-------|------|---------|
| `id` | UUID | Unique identifier — never reused |
| `created_at` | datetime | ISO 8601, UTC |
| `updated_at` | datetime | ISO 8601, UTC |
| `is_active` | bool | Default true; false = soft-deleted/inactive |
| `status` | str | Module-specific status string |
| `reference` | str | Human-readable reference number |
| `notes` | str | Free text annotation |
| `company_id` | UUID | Multi-company isolation |

**Soft Delete Pattern:** Most records use `is_active = false` rather than hard delete. This preserves audit trail.

**Currency Fields:** Stored as Decimal(15,2). Always in the document's currency. Multi-currency: separate `amount_base` field stores KES equivalent.

---

## 9. Keyboard Shortcuts & UI Tips

### Navigation
- **Ctrl+K** or **/**: Open global search
- **Esc**: Close modal or dialog
- **Tab**: Move between form fields
- **Enter**: Submit focused button

### Tips
- **Filter persistence:** Date range filters persist within a session — check them when results look wrong
- **Tab memory:** The ERP remembers your last open tab per module within a session
- **Notifications:** Bell icon top-right shows count of pending approvals and alerts
- **Export all lists:** Every list has an Export button → downloads current filtered view as Excel
- **Print PDFs:** Open document → Print → select "Save as PDF" in browser print dialog

---

## 10. Configuration Reference

### Environment Variables (Frontend)

| Variable | Purpose | Default |
|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` |
| `NEXT_PUBLIC_APP_NAME` | Application title | `FMCG ERP` |

### Environment Variables (Backend)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing key |
| `API_V1_STR` | API prefix (`/api/v1`) |
| `MPESA_CONSUMER_KEY` | Safaricom Daraja key |
| `MPESA_CONSUMER_SECRET` | Safaricom Daraja secret |
| `MPESA_SHORTCODE` | Till/Paybill number |
| `ETIMS_API_KEY` | KRA eTIMS credential |

### Middleware Configuration

`frontend/src/middleware.ts` — handles:
1. Auth guard: Redirect to `/login` if no `erp_access_token` cookie
2. Dashboard consolidation: Redirect legacy routes to canonical paths
3. All redirects use HTTP 302 with `Cache-Control: no-store` headers

---

## 11. Glossary

| Term | Definition |
|------|-----------|
| **3-Way Match** | Verification that Purchase Order, Goods Receipt, and Supplier Invoice agree before payment |
| **BOM** | Bill of Materials — list of components and quantities to produce a product |
| **COA** | Chart of Accounts — numbered list of all GL accounts |
| **DSO** | Days Sales Outstanding — average days to collect payment after invoicing |
| **eTIMS** | Electronic Tax Invoice Management System — KRA's electronic invoicing system |
| **GRN** | Goods Receipt Note — document confirming goods received from supplier |
| **MTBF** | Mean Time Between Failures — average time equipment runs between breakdowns |
| **MTTR** | Mean Time To Repair — average time to restore equipment after failure |
| **MPS** | Master Production Schedule — planned production quantities by period |
| **MRP** | Material Requirements Planning — calculation of what to purchase based on demand |
| **NCMR** | Non-Conformance Material Report — record of product failing QC |
| **OEE** | Overall Equipment Effectiveness — Availability × Performance × Quality |
| **OTIF** | On Time In Full — % of deliveries arriving on scheduled date with full quantity |
| **PAYE** | Pay As You Earn — employee income tax deducted at source |
| **PO** | Purchase Order — formal order sent to a supplier |
| **PR / PRQ** | Purchase Requisition — internal request to purchase something |
| **RFQ** | Request for Quotation — soliciting price quotes from suppliers |
| **SKU** | Stock Keeping Unit — unique product identifier |
| **SLA** | Service Level Agreement — committed response/resolution time |
| **SOH** | Stock on Hand — physical inventory quantity currently in warehouse |
| **TPM** | Trade Promotion Management — management of promotional spend in retail channels |
| **UOM** | Unit of Measure — e.g. KG, Litre, Each, Carton |
| **VAT** | Value Added Tax — 16% standard rate in Kenya |
| **WIP** | Work in Process — materials committed to a work order but not yet completed |
| **WMS** | Warehouse Management System — software for managing warehouse operations |

---

*End of Full Reference Manual v2*

---

## Quick Module Cross-Reference

For detailed guides on each module, refer to the respective manual:

| Manual | File |
|--------|------|
| Manufacturing | `docs/manuals/manufacturing/FMCG-ERP-Manufacturing-Manual-v2.md` |
| Supply Chain | `docs/manuals/supply-chain/FMCG-ERP-Supply-Chain-Manual-v2.md` |
| Sales & Distribution | `docs/manuals/sales-distribution/FMCG-ERP-Sales-Distribution-Manual-v2.md` |
| Commercial (CRM/Marketing) | `docs/manuals/commercial/FMCG-ERP-Commercial-CRM-Marketing-Manual-v2.md` |
| Finance & Payroll | `docs/manuals/finance-payroll/FMCG-ERP-Finance-Payroll-Manual-v2.md` |
| HR | `docs/manuals/hr/FMCG-ERP-HR-Manual-v2.md` |
| Logistics | `docs/manuals/logistics/FMCG-ERP-Logistics-Manual-v2.md` |
| Maintenance & Utilities | `docs/manuals/maintenance/FMCG-ERP-Maintenance-Utilities-Manual-v2.md` |
| Documents & Communication | `docs/manuals/documents/FMCG-ERP-Documents-Communication-Manual-v2.md` |
| Administration | `docs/manuals/admin/FMCG-ERP-Administration-Manual-v2.md` |
| Intelligence & Analytics | `docs/manuals/intelligence/FMCG-ERP-Intelligence-Analytics-AI-Manual-v2.md` |
| Kenya Go-Live Training | `docs/manuals/kenya-go-live/Kenya-Go-Live-ERP-Training-Manual-v2.md` |
| Full Reference (this document) | `docs/manuals/full-reference/FMCG-ERP-Full-Reference-Manual-v2.md` |
