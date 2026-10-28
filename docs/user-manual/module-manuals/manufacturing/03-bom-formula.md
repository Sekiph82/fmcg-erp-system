# BOM & Formula Management

**Route:** `/dashboard/bom`  
**Permission required:** `bom.view`  
**Workspace tabs:** BOM / Formula, Substitutes, Compare, Conversion

---

## What It Does

The BOM & Formula module manages the Bill of Materials for all manufactured products. A BOM defines the components, quantities, and structure for producing a finished good. BOMs support multiple types (formula, packaging, intermediate, etc.) and a full lifecycle from DRAFT to RELEASED.

The BOM module is separate from the Recipes module. Recipes focus on process parameters and formulation trials; BOMs focus on costing, production release, and structural explosion.

![BOM & Formula workspace](../../../screenshots/captured/module-ui/manufacturing/bom/bom-list-tab.png)
*BOM workspace overview showing the formula list with lifecycle status badges.*

---

## BOM Types

| Type | Use Case |
|------|----------|
| `FORMULA` | Primary product formulation — ingredients for a finished good |
| `INTERMEDIATE` | Semi-finished goods used in another BOM |
| `PACKAGING` | Packaging materials — labels, bottles, cartons |
| `MULTILEVEL` | Complex multi-level assemblies |
| `PHANTOM` | Virtual grouping — not physically produced; explodes to its children |
| `REWORK` | Re-processing of off-spec product |
| `COPRODUCT` | One process with a main product and separately identified co-product/by-product outputs |

### Co-Product and By-Product Outputs

BOM lines marked `CO_PRODUCT` or `BY_PRODUCT` are reported as separate expected output quantities in the BOM costing view, using each line's declared quantity and unit for the BOM base batch. These quantities remain separate by output type and unit. They are not treated as material consumption, cost credits, or cost allocations; BOM cost totals are calculated from cost-bearing components and remain unchanged by secondary outputs.

---

## BOM Lifecycle States

| State | Meaning |
|-------|---------|
| `DRAFT` | Under development; editable |
| `UNDER_REVIEW` | Submitted for approval review |
| `APPROVED` | Approved; ready for release to production |
| `RELEASED` | Released to production; work orders can reference this BOM |
| `SUPERSEDED` | Replaced by a newer version; kept for traceability |
| `ARCHIVED` | No longer in use; read-only |

---

## BOM List Tab

### Dashboard KPIs

| KPI | Description |
|-----|-------------|
| `total_boms` | Count of all BOMs |
| `released_boms` | Count in RELEASED state |
| `draft_boms` | Count in DRAFT state |
| `pending_review` | Count in UNDER_REVIEW state |
| `boms_with_allergens` | Count with allergen declarations |
| `pending_ai_recs` | Count with pending AI optimisation recommendations |

### Filters

| Filter | Options |
|--------|---------|
| Type | All Types / FORMULA / INTERMEDIATE / PACKAGING / MULTILEVEL / PHANTOM / REWORK / COPRODUCT |
| Status | All Statuses / DRAFT / UNDER_REVIEW / APPROVED / RELEASED / SUPERSEDED / ARCHIVED |

### Table Columns

| Column | Field | Notes |
|--------|-------|-------|
| **Code** | `bom_code` | Auto-generated code; monospace font |
| **Name** | `bom_name` | Clickable link to BOM detail page; shows "default" badge if `is_default=true` |
| **Type** | `bom_type` | Coloured badge per type |
| **Product** | `product_name` | Associated finished goods product |
| **Base Qty** | `base_qty` + `base_uom` | e.g. "1,000 KG" — the batch size this BOM is written for |
| **Version** | `version_no` | Prefixed with "v", e.g. "v1.0" |
| **Status** | `lifecycle` | Lifecycle state badge |
| **Std Cost** | `standard_batch_cost` | Standard batch cost in KES; "—" if not costed |
| **Actions** | — | View / Formula quick links |

### `is_default` Flag

A product can have multiple BOM versions. The one marked `is_default=true` is used by production work orders when no specific BOM version is specified.

---

## Creating a BOM

**Button:** `+ New BOM` (requires `bom.create`)

![New BOM modal](../../../screenshots/captured/module-ui/manufacturing/bom/new-bom-modal.png)
*New BOM modal — BOM Name, Type, Base Qty, Unit, and Version fields.*

### Create Form Fields

| Field | Label | Required | Default | Allowed Values |
|-------|-------|----------|---------|----------------|
| `bom_name` | BOM Name | Yes | — | Free text |
| `bom_type` | Type | Yes | `FORMULA` | FORMULA / INTERMEDIATE / PACKAGING / MULTILEVEL / PHANTOM / REWORK / COPRODUCT |
| `base_qty` | Base Qty | Yes | `1000` | Number |
| `base_uom` | Unit | Yes | `KG` | KG / L / UNIT / MT / G / ML |
| `version_no` | Version | Yes | `1.0` | e.g. "1.0", "2.0" |

Submit is disabled until `bom_name` is filled. The new BOM is created in `DRAFT` lifecycle state.

---

## BOM Detail Page

**Route:** `/dashboard/bom/{bom_id}`

The BOM detail page provides tabs for formula editing, costing, compliance, and cost explosion. Key actions from the Actions column:

- **View** — navigates to `/dashboard/bom/{id}` (main detail)
- **Formula** — navigates to `/dashboard/bom/{id}?tab=formula` (direct tab link)

---

## Substitutes Tab

**Route:** `/dashboard/bom?tab=substitutes`

![BOM — Substitutes tab](../../../screenshots/captured/module-ui/manufacturing/bom/substitutes-tab.png)
*Substitutes tab listing approved substitute groups and alternative materials.*

**Button:** `+ New Substitute Group`

![New Substitute Group modal](../../../screenshots/captured/module-ui/manufacturing/bom/new-substitute-group-modal.png)
*New Substitute Group modal — group code and primary material fields.*

Manages substitute groups and batch-specific substitution requests. Adding a substitute only registers a candidate; it does not authorize its use. A request records the BOM line, exact BOM target quantity, substitute quantity, production/order reference, reason, and the policy that was in force when submitted. Requests stay unavailable to BOM explosion until the required approvals are complete. An approved request can only be applied to the same target quantity and exact production/order reference it names.

### Approval and emergency rule

- `NO_SUB`: substitution requests are not allowed.
- `PLANNER_APPROVAL`: a user with `bom.approve` must approve.
- `QA_APPROVAL`: a user with `quality.approve` must approve.
- `BOTH_REQUIRED`: both permissions must be exercised by two different users.
- `SHORTAGE_ONLY`: the request must include a traceable shortage-evidence reference and a planner (`bom.approve`) approval.
- `EMERGENCY_ONLY`: use only when the primary material cannot meet the required quantity/date and routine procurement cannot meet the schedule. The requester must provide a detailed emergency reason and a traceable shortage-evidence reference. Separate users with `bom.approve` and `quality.approve` must approve. Rejection ends the request; a new request is needed after any change.

The emergency rule is a process gate, not an automatic stock calculation: approvers must verify that the primary material cannot meet the scheduled quantity/date and that routine procurement cannot meet the schedule. Shortage evidence is referenced and reviewed by the approvers; the system does not independently verify the external stock/shortage record. The production/order context is also a trace reference supplied by the requester, not a foreign key to a verified order. Each request is tied to its directly owning BOM, line and target quantity. The substitute quantity is calculated server-side from the BOM line basis, loss factors and substitute ratio; the requester cannot choose a different quantity. Approval decisions and reasons are recorded in the audit log. A pending, rejected, missing-decision, differently sized, differently referenced, policy-mismatched, repeated-occurrence, inactive, or wrong-UOM request cannot be applied to an explosion. Substitute materials/products must resolve to an active master item with the same item type and UOM as the BOM line; implicit UOM conversion is rejected. Line policy and group policy must match exactly.

---

## Compare Tab

**Route:** `/dashboard/bom?tab=compare`

![BOM — Compare tab](../../../screenshots/captured/module-ui/manufacturing/bom/compare-tab.png)
*Compare tab — side-by-side view of two BOM versions showing ingredient and cost differences.*

Side-by-side comparison of two BOM versions for the same product. Used during reformulation reviews to see cost and ingredient differences.

---

## Conversion Tab

**Route:** `/dashboard/bom?tab=conversion`

![BOM — Conversion tab](../../../screenshots/captured/module-ui/manufacturing/bom/conversion-tab.png)
*Conversion tab showing UoM conversion factors for bulk-to-packaged unit equivalents.*

Manages unit of measure conversions specific to this BOM's product line (e.g. converting bulk KG quantities to packaged unit equivalents).

Conversion profiles can be imported from CSV with the standard template → validate → import flow. The template lists the profile fields; product and linked packaging BOM references use their UUIDs. A blank profile code is generated automatically. Imports create new profile versions; an existing profile-code/version pair is reported as a duplicate and is not overwritten. Export CSV downloads the active profiles available in the list; text that could be interpreted as a spreadsheet formula is escaped in the export.

---

## BOM vs Recipe

| Aspect | Recipe | BOM |
|--------|--------|-----|
| Purpose | Formulation R&D; process parameters | Production release; cost explosion |
| Status cycle | DRAFT → APPROVED → OBSOLETE | DRAFT → UNDER_REVIEW → APPROVED → RELEASED → SUPERSEDED → ARCHIVED |
| Process steps | Yes (temperature, pH, RPM) | No |
| Cost fields | No | Yes (`standard_batch_cost`) |
| Used by work orders | No | Yes (RELEASED BOMs only) |
| `is_default` flag | No | Yes |
