# BOM & Formula Management

**Route:** `/dashboard/bom`  
**Permission required:** `bom.view`  
**Workspace tabs:** BOM / Formula, Substitutes, Compare, Conversion

---

## What It Does

The BOM & Formula module manages the Bill of Materials for all manufactured products. A BOM defines the components, quantities, and structure for producing a finished good. BOMs support multiple types (formula, packaging, intermediate, etc.) and a full lifecycle from DRAFT to RELEASED.

The BOM module is separate from the Recipes module. Recipes focus on process parameters and formulation trials; BOMs focus on costing, production release, and structural explosion.

![BOM & Formula workspace](../../../screenshots/captured/tabs/bom-list.png)
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
| `COPRODUCT` | By-products produced alongside the main product |

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

Manages approved material substitutions. When a BOM item's primary material is unavailable, an approved substitute with the same `alternative_group` can be used.

---

## Compare Tab

**Route:** `/dashboard/bom?tab=compare`

Side-by-side comparison of two BOM versions for the same product. Used during reformulation reviews to see cost and ingredient differences.

---

## Conversion Tab

**Route:** `/dashboard/bom?tab=conversion`

Manages unit of measure conversions specific to this BOM's product line (e.g. converting bulk KG quantities to packaged unit equivalents).

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
