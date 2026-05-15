# GAP-018 GS1 / Label Printing / Packaging Compliance — Schema Design

## Decision: Minimal Additive + Bug Fix

Three fields are missing from `ProductGS1Config` causing runtime bugs. One migration adds them. Module promotion to MODULE_DEFINITIONS requires no schema changes.

---

## Existing Relevant Fields (do NOT re-add)

### `ProductGS1Config` (table: `product_gs1_configs`)

All existing fields: id, product_id, gtin, barcode_type, packaging_level, label_template_id, is_serialized, include_lot, include_expiry, units_per_inner, inners_per_carton, cartons_per_pallet, is_active, notes, timestamps.

Missing (referenced in endpoints but absent from model):

| Field | Endpoint references |
|---|---|
| `product_sku_code` | `GET /gtin/lookup` line ~545, `POST /scan/dispatch-validate` line ~506 |
| `net_weight_g` | `GET /gtin/lookup` line ~547 |
| `net_volume_ml` | `GET /gtin/lookup` line ~548 |

---

## Proposed Additions

### `product_gs1_configs` table

| Column | Type | Nullable | Default | Reason |
|---|---|---|---|---|
| `product_sku_code` | VARCHAR(100) | YES | NULL | SKU code displayed in GTIN lookup response |
| `net_weight_g` | NUMERIC(12, 4) | YES | NULL | Net weight in grams for label compliance |
| `net_volume_ml` | NUMERIC(12, 4) | YES | NULL | Net volume in ml for label compliance |

---

## What Is NOT in Scope for GAP-018C

| Item | Reason |
|---|---|
| Label approval workflow fields | Scope increase — separate effort |
| GLN model | No current regulatory requirement |
| Batch print job schema | Existing schema can handle; no new table needed |

---

## Migration Plan

Single migration file: `20260515_0060_gs1_product_config_fields.py`

```sql
ALTER TABLE product_gs1_configs ADD COLUMN product_sku_code VARCHAR(100);
ALTER TABLE product_gs1_configs ADD COLUMN net_weight_g NUMERIC(12, 4);
ALTER TABLE product_gs1_configs ADD COLUMN net_volume_ml NUMERIC(12, 4);
```

Guards: `_add_column_once()` pattern (same as recent migrations).

---

## Module Promotion Plan (GAP-018I, no schema changes)

GS1 promoted from `ENDPOINT_ROUTE_DEFINITIONS` → `MODULE_DEFINITIONS` with:
- `key="gs1"`
- `permission_actions=("view", "create", "edit", "approve", "print", "report", "admin")`
- `sidebar_group="Compliance"`
- `critical=False`

Seed permissions added: gs1.view, gs1.create, gs1.edit, gs1.approve, gs1.print, gs1.report, gs1.admin

---

## Schema Changes Summary

| Table | Column | Type | Change |
|---|---|---|---|
| `product_gs1_configs` | `product_sku_code` | VARCHAR(100) | ADD |
| `product_gs1_configs` | `net_weight_g` | NUMERIC(12,4) | ADD |
| `product_gs1_configs` | `net_volume_ml` | NUMERIC(12,4) | ADD |

Total: 3 additive nullable columns. Zero breaking changes.
