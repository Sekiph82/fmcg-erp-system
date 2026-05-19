# Purchase Requisitions

**Route:** `/dashboard/procurement` (default tab: Purchase Requests)  
**Permission required:** `procurement.view`  
**Tab key:** `purchase-requests`

---

## What It Does

A Purchase Requisition (PR) is an internal request to procure materials or products. PRs are raised by any department and go through an approval workflow before being converted into Purchase Orders. The system enforces scope-based access — users may be restricted to PRs within their company, branch, cost centre, or department.

![Procurement — Purchase Requests tab](../../../screenshots/captured/030_procurement-requests.png)
*Purchase Requests tab showing PR list with status badges and approval controls.*

![New Purchase Requisition modal](../../../screenshots/captured/actions/procurement-new-pr-modal.png)
*New PR form with line items, department, required date, and preferred supplier fields.*

---

## PR List

### Filter

Status dropdown filters the list:

| Filter Option | Value |
|--------------|-------|
| All | _(no filter)_ |
| Draft | `DRAFT` |
| Pending Approval | `PENDING_APPROVAL` |
| Approved | `APPROVED` |
| Converted to PO | `CONVERTED` |
| Rejected | `REJECTED` |
| Cancelled | `CANCELLED` |

### Table Columns

| Column | Field | Notes |
|--------|-------|-------|
| **PR No** | `pr_no` | Monospace; clickable link to PR detail at `/dashboard/procurement/{id}` |
| **Requester** | `requester_name` | Auto-populated from logged-in user |
| **Department** | `department` | Free text department name |
| **Required By** | `required_date` | Locale date format |
| **Lines** | `line_count` | Number of material lines on the PR |
| **Status** | `status` | Badge (APPROVED/CONVERTED = green; PENDING_APPROVAL = blue; REJECTED/CANCELLED = red; DRAFT = blue) |
| **Access** | `access.view_only` | "Actionable" (green) or "View only" (grey) badge based on scope permissions |

---

## Creating a Purchase Requisition

**Button:** `+ New PR` (`data-testid="procurement-create-pr-button"`)

### PR Header Fields

| Field | Label | Required | Backend field | Notes |
|-------|-------|----------|---------------|-------|
| `pr_no` | PR No | Yes | `pr_no` | User-assigned; e.g. `PR-2026-001` |
| `department` | Department | No | `department` | Free text; e.g. "Production", "R&D" |
| `required_date` | Required Date | Yes | `required_date` | Date picker; the date materials are needed by |
| `notes` | Notes | No | `notes` | Free text; visible on PO conversion |

**Submit** disabled until `pr_no` and `required_date` are filled.

### PR Line Fields

Each PR can have one or more lines. Lines are added with the **+ Add Line** button. Minimum one line required (lines without `material_id` and `quantity` are excluded from submission).

| Field | Label | Required | Backend field | Notes |
|-------|-------|----------|---------------|-------|
| `material_id` | Material | Yes* | `material_id` | Select from materials master (`code — name` format) |
| `quantity` | Qty | Yes* | `quantity` | Decimal; step 0.001 |
| `unit` | Unit | Yes | `unit` | Default `KG`; options: KG / G / L / ML / PCS / BOX / CARTON / PALLET |
| `estimated_unit_cost` | Est. cost | No | `estimated_unit_cost` | Decimal; step 0.01 |
| `preferred_supplier_id` | Supplier | No | `preferred_supplier_id` | Optional preferred supplier for this line |
| `notes` | _(no label)_ | No | `notes` | Per-line notes |

*Lines without `material_id` + `quantity` are silently excluded from the submitted payload.

The backend also accepts `product_id` and `description` per line (from `PRLineCreate` schema), but these are not exposed in the current frontend create form.

---

## PR Status Values

| Status | Meaning | Badge Colour |
|--------|---------|-------------|
| `DRAFT` | Created; not submitted for approval | Blue |
| `PENDING_APPROVAL` | Submitted; awaiting approver action | Blue |
| `APPROVED` | Approved by authorised approver | Green |
| `CONVERTED` | PR lines converted to a Purchase Order | Green |
| `REJECTED` | Rejected by approver; `rejection_reason` populated | Red |
| `CANCELLED` | Cancelled by requester or admin | Red |

---

## PR Approval Workflow

```
DRAFT → PENDING_APPROVAL → APPROVED → CONVERTED
                        ↘ REJECTED
```

Actions available from the PR detail page (`/dashboard/procurement/{id}`):
- **Submit for Approval** (DRAFT → PENDING_APPROVAL)
- **Approve** (PENDING_APPROVAL → APPROVED) — records `approved_by_id` and `approved_at`
- **Reject** (PENDING_APPROVAL → REJECTED) — requires `rejection_reason`
- **Convert to PO** (APPROVED → CONVERTED) — opens the Convert to PO flow

### Convert PR to PO

Converting a PR to a Purchase Order requires:

| Field | Backend field | Required | Notes |
|-------|---------------|----------|-------|
| PO No | `po_no` | Yes | User-assigned PO reference |
| Supplier | `supplier_id` | Yes | Must select a supplier for all lines |
| Order Date | `order_date` | Yes | Date of the PO |
| Expected Delivery | `expected_delivery_date` | Yes | Date supplier is expected to deliver |
| Payment Terms | `payment_terms` | No | Free text; e.g. "Net 30" |
| Currency | `currency` | No | Default `USD` |
| Exchange Rate | `exchange_rate` | No | Default `1.0` |
| Notes | `notes` | No | Free text |
| Line Prices | `line_prices` | No | Override unit price per PR line: `{pr_line_id: unit_price}` |

---

## Scope-Based Access

PRs support multi-company, branch, and cost-centre scoping via `ProcurementScopeFields`:

| Field | Purpose |
|-------|---------|
| `company_id` | Restricts PR to a specific legal entity |
| `branch_id` | Restricts PR to a branch/site |
| `cost_center_id` | Links PR to a cost centre for budget control |
| `department` | Free text department label |

Users with limited scope see the "View only" badge on PRs outside their scope — they can read the record but cannot approve, edit, or convert it.

---

## API Endpoints (Reference)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/procurement/purchase-requests/` | List PRs (filter: `status`) |
| POST | `/api/v1/procurement/purchase-requests/` | Create PR with lines |
| GET | `/api/v1/procurement/purchase-requests/{id}` | PR detail with lines |
| PATCH | `/api/v1/procurement/purchase-requests/{id}` | Update PR header (DRAFT only) |
| POST | `/api/v1/procurement/purchase-requests/{id}/approve` | Approve or reject |
| POST | `/api/v1/procurement/purchase-requests/{id}/convert-to-po` | Convert to PO |
