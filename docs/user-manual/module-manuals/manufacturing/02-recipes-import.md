# Recipe Bulk CSV Import

**Component:** `RecipeBulkImportModal`  
**Triggered from:** Recipe list page → Import button  
**Modules involved:** `recipes`, `recipe_items`, `recipe_steps`

---

## Overview

The bulk import modal allows you to upload recipe data from CSV files. It has three separate tabs — one per data type — and each tab runs an independent validate-then-import flow. You must import in the correct order:

![Import dialog — Recipe Headers tab](../../../screenshots/captured/module-ui/manufacturing/recipes/import-modal-headers-tab.png)
*Bulk Import — Recipe Headers tab: template download, CSV picker, Validate, and Import buttons.*

![Import dialog — BOM Items tab](../../../screenshots/captured/module-ui/manufacturing/recipes/import-modal-bom-items-tab.png)
*Bulk Import — BOM Items tab for uploading ingredient quantities per recipe.*

![Import dialog — Process Steps tab](../../../screenshots/captured/module-ui/manufacturing/recipes/import-modal-process-steps-tab.png)
*Bulk Import — Process Steps tab for uploading process parameters per recipe.*

1. **Recipe Headers** first
2. **BOM Items** second (recipes must already exist)
3. **Process Steps** third (recipes must already exist)

Existing recipes are identified by `product_sku` + `version`. Existing BOM item `line_no` values and step `step_no` values are updated in-place if they already exist.

---

## Tab 1: Recipe Headers

**Module key:** `recipes`

### CSV Columns

| Column | Required | Type | Notes |
|--------|----------|------|-------|
| `product_sku` | ✅ Yes (`*`) | string | Must match an existing product SKU in master data |
| `version` | ✅ Yes (`*`) | string | e.g. `1.0`, `2.0` |
| `name` | ✅ Yes (`*`) | string | Recipe name |
| `description` | No | string | Optional free text |
| `is_active` | No | `true`/`false` | Defaults to `true` if blank |
| `valid_from` | No | date (YYYY-MM-DD) | Start of validity window |
| `valid_to` | No | date (YYYY-MM-DD) | End of validity window |

`*` = required column; header row must use exactly these column names.

### Sample CSV

```csv
product_sku,version,name,description,is_active,valid_from,valid_to
POVU-ALC-1L,1.0,POVU AllClean Multi-Purpose Cleaner 1 L Standard,,true,2026-01-01,
POVU-ALC-1L,2.0,POVU AllClean Multi-Purpose Cleaner 1 L Reformulated,Lower surfactant formulation,true,2026-06-01,
POVU-CFL-1L,1.0,POVU ColorFresh Liquid Detergent Colors 1 L,,true,,
```

---

## Tab 2: BOM Items

**Module key:** `recipe_items`

### CSV Columns

| Column | Required | Type | Notes |
|--------|----------|------|-------|
| `product_sku` | ✅ Yes (`*`) | string | Must match an existing product SKU |
| `version` | ✅ Yes (`*`) | string | Must match an existing recipe version for this SKU |
| `line_no` | ✅ Yes (`*`) | integer | Sequence number; existing line_no is updated in-place |
| `material_code` | ✅ Yes (`*`) | string | Must match an existing material code in master data |
| `quantity` | ✅ Yes (`*`) | decimal | Amount per batch |
| `unit` | ✅ Yes (`*`) | string | e.g. `KG`, `L`, `G`, `ML` |
| `loss_percent` | No | decimal | Process loss %; defaults to `0` |
| `optional` | No | `true`/`false` | Whether this ingredient is optional; defaults to `false` |
| `alternative_group` | No | string | Substitution group code; blank = not substitutable |
| `notes` | No | string | Free text per line |

**Constraint:** The target recipe must be in `DRAFT` status. Items cannot be imported into APPROVED or OBSOLETE recipes.

### Sample CSV

```csv
product_sku,version,line_no,material_code,quantity,unit,loss_percent,optional,alternative_group,notes
POVU-ALC-1L,1.0,10,RAW-SURF-LAS,90,KG,1.5,false,,LAS surfactant blend
POVU-ALC-1L,1.0,20,RAW-THICK-SALT,15,KG,0,false,,
POVU-ALC-1L,1.0,30,RAW-FRAG-LAV,3,KG,0,true,FRAG-GRP,Can substitute with another fragrance oil
POVU-ALC-1L,1.0,40,MAT-WATER,892,L,0,false,,Process water
```

---

## Tab 3: Process Steps

**Module key:** `recipe_steps`

### CSV Columns

| Column | Required | Type | Notes |
|--------|----------|------|-------|
| `product_sku` | ✅ Yes (`*`) | string | Must match an existing product SKU |
| `version` | ✅ Yes (`*`) | string | Must match an existing recipe version for this SKU |
| `step_no` | ✅ Yes (`*`) | integer | Step sequence; existing step_no is updated in-place |
| `step_name` | ✅ Yes (`*`) | string | e.g. `Blending`, `Pasteurisation`, `Filling` |
| `temperature_c` | No | decimal | Target temperature in Celsius |
| `target_ph` | No | decimal | Target pH |
| `viscosity_cp` | No | decimal | Target viscosity in centipoise |
| `mix_time_min` | No | integer | Mixing time in minutes |
| `rpm` | No | integer | Agitator RPM |
| `notes` | No | string | Free text per step |

**Constraint:** Same as BOM Items — recipe must be in `DRAFT` status.

### Sample CSV

```csv
product_sku,version,step_no,step_name,temperature_c,target_ph,viscosity_cp,mix_time_min,rpm,notes
POVU-ALC-1L,1.0,10,Pre-mixing,,,,10,120,Water and LAS surfactant
POVU-ALC-1L,1.0,20,Blending,25,7.5,,20,200,Add salt thickener slowly
POVU-ALC-1L,1.0,30,Fragrance,25,,800,10,150,Add lavender fragrance oil
POVU-ALC-1L,1.0,40,Quality check,25,7.5,800,,0,pH and viscosity before filling
POVU-ALC-1L,1.0,50,Filling,,,,,0,
```

---

## Import Flow

The same four-step flow applies to all three tabs:

```
1. Download Template  →  Get an empty CSV with correct headers
2. Pick CSV File      →  Browse and select your completed CSV
3. Validate          →  Server validates rows, returns pass/fail counts
4. Import            →  Confirmed import of valid (or all) rows
```

### Validation Response

After validation, the modal shows:
- Total rows found
- Rows that passed validation
- Rows with errors (with error message per row)
- Option to download error rows as CSV for correction

### Import Modes

| Mode | Label | Behaviour |
|------|-------|-----------|
| `import_valid_only` | Import valid rows only | Imports all rows that passed validation; skips errors |
| `strict` | Strict (abort on any error) | Aborts the entire import if any row has an error |

Choose `strict` when data integrity is critical (e.g. costed formulas where a missing line would corrupt cost calculations).

---

## Error Handling

- **Product SKU not found:** Row rejected; error shows the unknown SKU.
- **Material code not found:** Row rejected; error shows the unknown material code.
- **Recipe not found for SKU+version:** BOM/Steps import row rejected; import Recipe Headers first.
- **Recipe not in DRAFT:** BOM/Steps import row rejected with "Recipe is not DRAFT" message.
- **Duplicate line_no/step_no:** Existing record is updated in-place; not treated as an error.
- **Missing required field:** Row rejected with field name in error message.

---

## Import Order Enforcement

Always import in this order:

```
Recipe Headers (Tab 1)  →  BOM Items (Tab 2)  →  Process Steps (Tab 3)
```

BOM Items and Process Steps reference the recipe by `product_sku` + `version`. If the recipe header does not exist, those rows will fail validation with "Recipe not found".
