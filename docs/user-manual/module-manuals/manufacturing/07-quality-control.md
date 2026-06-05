# QC Inspections

**Route:** `/dashboard/quality` (default tab: Inspections)  
**Permission required:** `quality.view`  
**Tab key:** `inspections`  
**Workspace tabs:** Inspections, Certificates, Parameters, Consumer Complaints, Reports, QMS, Allergen, Brand Assets

---

## What It Does

The Quality module manages all QC inspections across three inspection contexts: incoming raw materials, in-process production checks, and finished goods release. Each inspection records test results, a pass/fail decision, and optional quarantine actions.

![Production — Quality Control](../../../screenshots/captured/044_production-quality-control.png)
*Quality workspace showing the Inspections tab with seeded QC inspections, dashboard counters, and inspection list.*

---

## Inspection List

### Dashboard Counters

| Counter | Description |
|---------|-------------|
| Pending / Active | Inspections with status PENDING or IN_PROGRESS |
| Passed | Inspections with status PASSED |
| Failed | Inspections with status FAILED |
| Critical Failures | Inspections where `critical_fail = true` |

Critical failures are highlighted in bold red. These indicate a safety or regulatory failure requiring immediate supervisor action.

### Filters

| Filter | Options |
|--------|---------|
| Type | All Types / Incoming QC / In-Process QC / Finished Goods QC |
| Status | All Statuses / Pending / In Progress / Passed / Failed / Conditional Release / Cancelled |

### Table Columns

| Column | Field | Notes |
|--------|-------|-------|
| **Inspection No** | `inspection_no` | Monospace; clickable link to detail at `/dashboard/quality/{id}` |
| **Type** | `qc_type` | Coloured badge: INCOMING (blue), IN_PROCESS (blue), FINISHED_GOODS (green) |
| **Item** | `material_code` + `material_name` or `product_name` | Material code shown in monospace prefix |
| **Supplier** | `supplier_name` | Blank for non-incoming inspections |
| **Lot / Batch** | `lot_number` or `batch_no` | Whichever is present |
| **Date** | `inspection_date` | Locale date format |
| **Tests** | `pass_count` ✓ `fail_count` ✗ | Green pass count, red fail count; "CRIT" badge if `critical_fail` |
| **Status** | `status` + `quarantine_applied` | Status badge; QUARANTINED badge shown separately if quarantine applied |

---

## Creating a QC Inspection

**Button:** `+ New Inspection` (`data-testid="quality-create-inspection-button"`)

![New QC Inspection modal](../../../screenshots/captured/module-ui/manufacturing/quality/new-inspection-modal.png)
*New QC Inspection form. The Supplier and Material fields only appear when qc_type is INCOMING.*

### New QC Inspection Modal Fields

| Field | Label | Required | Type | Notes |
|-------|-------|----------|------|-------|
| `inspection_no` | Inspection No | Yes | string | User-assigned; e.g. `QC-2026-001` |
| `qc_type` | QC Type | Yes | enum | INCOMING / IN_PROCESS / FINISHED_GOODS |
| `inspection_date` | Inspection Date | Yes | date | Date picker |
| `lot_number` | Lot Number | No | string | Supplier lot for incoming |
| `batch_no` | Batch No | No | string | Production batch for in-process or FG |
| `supplier_id` | Supplier | No (shown for INCOMING) | select | Appears only when `qc_type = INCOMING` |
| `material_id` | Material | No (shown for INCOMING) | select | Appears only when `qc_type = INCOMING` |
| `warehouse_id` | Warehouse | No | select | Which warehouse this inspection is associated with |
| `sample_size` | Sample Size | No | decimal | Number (e.g. 2.5) |
| `sample_unit` | Sample Unit | No | string | Default `"KG"`; free text |
| `notes` | Notes | No | string | Free text |

**Conditional display:** The `supplier_id` and `material_id` fields are shown only when `qc_type` is set to `INCOMING`. They are hidden for IN_PROCESS and FINISHED_GOODS types.

**Submit** is disabled until `inspection_no` and `inspection_date` are filled.

After creation, the user is immediately navigated to the inspection detail page at `/dashboard/quality/{id}`.

---

## QC Inspection Types

| Type | When Used | Typical Item |
|------|-----------|--------------|
| `INCOMING` | On receipt of raw materials from supplier | Raw material + lot number |
| `IN_PROCESS` | During active production run | Intermediate product + batch number |
| `FINISHED_GOODS` | On completion of a production batch | Finished product + batch number |

---

## Inspection Status Values

| Status | Meaning |
|--------|---------|
| `PENDING` | Created but no tests recorded yet |
| `IN_PROGRESS` | Tests being entered; not yet decided |
| `PASSED` | All tests passed; item released |
| `FAILED` | One or more tests failed; item rejected or reworked |
| `CONDITIONAL_RELEASE` | Released despite minor non-conformance; conditions noted |
| `CANCELLED` | Inspection voided; no action taken |

---

## QC Decision Values

| Decision | Badge Colour | Meaning |
|----------|-------------|---------|
| `ACCEPT` | Green | Item fully accepted |
| `REJECT` | Red | Item rejected; return to supplier or dispose |
| `REWORK` | Red | Item to be reworked before re-inspection |
| `CONDITIONAL_RELEASE` | Blue | Accepted with conditions and documentation |

---

## Critical Fail Flag

`critical_fail = true` is set when at least one test result breaches a critical specification limit (e.g. microbiological contamination, allergen mislabelling, regulatory parameter breach). Critical failures:
- Are displayed as bold "CRIT" in the test column
- Increment the Critical Failures dashboard counter
- Typically trigger automatic quarantine of the affected batch/lot

---

## Quarantine

`quarantine_applied = true` indicates that the warehouse stock associated with this inspection has been moved to a quarantine location. The QUARANTINED badge is shown alongside the status badge in the list.

To release from quarantine, record the ACCEPT or CONDITIONAL_RELEASE decision on the inspection detail page.

---

## Inspection Detail Page

**Route:** `/dashboard/quality/{inspection_id}`

The detail page provides:
- Full header information
- Test result entry (each parameter with target, actual, and pass/fail)
- Decision recording (ACCEPT / REJECT / REWORK / CONDITIONAL_RELEASE)
- Quarantine management
- Attached certificates (certificates linked from the Certificates tab)
- History log of status changes

---

## Other Quality Tabs

![Quality — Certificates tab](../../../screenshots/captured/module-ui/manufacturing/quality/certificates-tab.png)
*Certificates tab listing regulatory and quality certificates with status and expiry dates.*

![Quality — Parameters tab](../../../screenshots/captured/module-ui/manufacturing/quality/parameters-tab.png)
*Parameters tab with specification limits per product and material.*

![Quality — Consumer Complaints tab](../../../screenshots/captured/module-ui/manufacturing/quality/consumer-complaints-tab.png)
*Consumer Complaints tab tracking customer-reported product issues linked to batches.*

![Quality — Reports tab](../../../screenshots/captured/module-ui/manufacturing/quality/reports-tab.png)
*Quality Reports tab showing KPI trends and generated quality reports.*

![Quality — QMS tab](../../../screenshots/captured/module-ui/manufacturing/quality/qms-tab.png)
*QMS tab for non-conformance reports, CAPA, and SOPs.*

![Quality — Allergen tab](../../../screenshots/captured/module-ui/manufacturing/quality/allergen-tab.png)
*Allergen management tab showing allergen declarations and cross-contamination matrix.*

![Quality — Brand Assets tab](../../../screenshots/captured/module-ui/manufacturing/quality/brand-assets-tab.png)
*Brand Assets tab for brand-related quality standards and packaging specifications.*

| Tab | Content |
|-----|---------|
| **Certificates** | Quality / regulatory certificates linked to suppliers and products |
| **Parameters** | Standard test parameters and specification limits per product/material |
| **Consumer Complaints** | Customer-reported product complaints; linked to batches |
| **Reports** | Quality reports and KPI trends |
| **QMS** | Quality Management System documents and workflows |
| **Allergen** | Allergen declarations per product and BOM; cross-contamination risk matrix |
| **Brand Assets** | Brand-related quality standards and packaging specifications |

---

## Demo Data — QC Inspection Seed (TASK-015.2)

The system ships with seeded QC inspections covering all three inspection types. These use the production master data (work centers, products, materials, batch lots) seeded in TASK-015.

### Seeded Inspection Types

| QC Type | Scope |
|---|---|
| `INCOMING` | Raw material receipt inspections with supplier and material references |
| `IN_PROCESS` | In-process checks linked to production work orders and batch numbers |
| `FINISHED_GOODS` | Final product release inspections |

### Seeded Status Distribution

| Status | Meaning |
|---|---|
| `PASSED` | Inspection completed with all tests within spec |
| `FAILED` | One or more tests outside spec |
| `CONDITIONAL_RELEASE` | Released with documented conditions |
| `PENDING` | Created; awaiting test entry |

### Seeded Test Parameters

Each seeded inspection has test results with `actual_value`, `target_value`, and `pass_fail` recorded per parameter. Critical fail (`critical_fail = true`) is set on inspections where a critical specification breach is simulated.

### Idempotency

The QC seed is idempotent — re-running Docker startup does not duplicate inspections. The `_get_or_create_qc` helper uses `inspection_no` as the unique key.
