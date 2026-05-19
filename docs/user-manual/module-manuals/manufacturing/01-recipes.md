# Recipes

**Route:** `/dashboard/recipes`  
**Permission required:** `recipe.view`  
**Tabs:** Single-page (no workspace tabs — standalone module)

---

## What It Does

The Recipes module manages product formulations: the exact materials (BOM items) and manufacturing process parameters (temperature, pH, mixing time, etc.) for each product version. A recipe must be **Approved** before it can be used in production work orders.

![Recipes page overview](../../../screenshots/captured/tabs/recipes-list.png)
*Recipes page showing recipe list with Search, Status filter, Import Recipes / BOM, and + New Recipe buttons.*

---

## Recipe List Page

### Search

The search bar filters across four fields simultaneously:
- Recipe name
- Product SKU
- Product name
- Version number

Typing in the search box performs a live client-side filter. There is no server-side pagination on the default list (fetches up to the API default limit).

### Table Columns

| Column | Description |
|--------|-------------|
| **Name** | Recipe name as a clickable link to the detail page |
| **Version** | Version string, displayed in monospace font |
| **Product** | Product SKU + product name |
| **Status** | Status badge (see Status Values below) |
| **Active** | Active/Inactive badge driven by `is_active` |
| **Valid From** | Start of validity window (date, blank if not set) |
| **Valid To** | End of validity window (date, blank if not set) |
| **Actions** | Delete button (DRAFT only, requires `recipe.delete`) |

### Status Values

| Value | Meaning |
|-------|---------|
| `DRAFT` | Recipe under development; can be edited and deleted |
| `APPROVED` | Approved for production use; edits and deletes blocked |
| `OBSOLETE` | Retired; no longer in active use |

Status transitions are managed from the recipe detail page. New recipes always start as `DRAFT`.

---

## Creating a Recipe

**Button:** `+ New Recipe` (requires `recipe.create`)

![New Recipe modal](../../../screenshots/captured/actions/recipes-new-recipe-modal.png)
*New Recipe / Formulation modal opened from the + New Recipe button.*

### New Recipe Modal Fields

| Field | Label | Required | Default | Notes |
|-------|-------|----------|---------|-------|
| `product_id` | Product | Yes | — | Select dropdown from products list |
| `name` | Recipe Name | Yes | — | Free text |
| `version` | Version | Yes | `"1.0"` | e.g. "1.0", "2.0", "1.1" |
| `description` | Description | No | — | Free text; not shown in list |
| `valid_from` | Valid From | No | — | Date picker |
| `valid_to` | Valid To | No | — | Date picker |

**Submit button** is disabled until both `product_id` and `name` and `version` are filled.

The recipe is always created with status `DRAFT`. The `is_active` flag defaults to `true` in the backend even though it is not exposed in the creation form.

---

## Recipe Detail Page

**Route:** `/dashboard/recipes/{recipe_id}`

The detail page shows the full recipe with two sub-sections beyond the header:

### BOM Items (Ingredients)

Each BOM item row maps to a `RecipeItem` record:

| Backend field | Label / Column | Type | Notes |
|---------------|----------------|------|-------|
| `material_id` | Material | UUID | Links to materials master |
| `line_no` | Line No | int | Ordering sequence; must be unique per recipe |
| `quantity` | Quantity | Decimal | Amount of material per batch |
| `unit` | Unit | str | e.g. "KG", "L", "G", "ML" |
| `loss_percentage` | Loss % | Decimal | Default `0`; represents expected process loss |
| `is_optional` | Optional | bool | Default `false`; marks non-mandatory ingredients |
| `alternative_group` | Alt Group | str or null | Groups substitutable items; null = no substitution |
| `notes` | Notes | str or null | Free text per line |

**DRAFT-only constraint:** Adding, editing, or deleting BOM items is only allowed while the recipe status is `DRAFT`. The API returns HTTP 422 if attempted on APPROVED or OBSOLETE recipes.

### Process Parameters (Steps)

Each step row maps to a `ProcessParameter` record:

| Backend field | Label / Column | Type | Notes |
|---------------|----------------|------|-------|
| `step_no` | Step No | int | Sequence; must be unique per recipe |
| `step_name` | Step Name | str | e.g. "Blending", "Pasteurisation" |
| `target_temperature` | Temp (°C) | Decimal or null | Target process temperature |
| `target_ph` | pH | Decimal or null | Target pH value |
| `target_viscosity` | Viscosity (cP) | Decimal or null | Target viscosity in centipoise |
| `mixing_time_minutes` | Mix Time (min) | int or null | Mixing duration |
| `rpm` | RPM | int or null | Mixer/agitator speed |
| `notes` | Notes | str or null | Free text per step |

**DRAFT-only constraint:** Same as BOM items — process parameters can only be modified on DRAFT recipes.

---

## Deleting a Recipe

- Delete button appears in the list table **only** if `recipe.status == "DRAFT"` AND the user has `recipe.delete` permission.
- Approved and Obsolete recipes cannot be deleted.
- Deleting a recipe also removes all its BOM items and process parameters.

---

## Status Workflow

```
DRAFT → APPROVED → OBSOLETE
```

- `DRAFT → APPROVED`: Approve action on the detail page (requires appropriate permission).
- `APPROVED → OBSOLETE`: Obsolete action on the detail page.
- There is no reverse transition from APPROVED back to DRAFT.

---

## Permissions Summary

| Action | Permission Required |
|--------|---------------------|
| View recipe list | `recipe.view` |
| View recipe detail | `recipe.view` |
| Create recipe | `recipe.create` |
| Edit recipe header (DRAFT) | `recipe.create` |
| Add / edit BOM items (DRAFT) | `recipe.create` |
| Add / edit process parameters (DRAFT) | `recipe.create` |
| Delete recipe (DRAFT) | `recipe.delete` |
| Approve / Obsolete | `recipe.create` (or higher — check role config) |

---

## API Endpoints (Reference)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/recipes/` | List recipes (filters: `product_id`, `status`) |
| POST | `/api/v1/recipes/` | Create recipe (always creates as DRAFT) |
| GET | `/api/v1/recipes/{recipe_id}` | Get recipe detail with items and process params |
| PATCH | `/api/v1/recipes/{recipe_id}` | Update recipe header (DRAFT only) |
| DELETE | `/api/v1/recipes/{recipe_id}` | Delete recipe (DRAFT only) |

The backend enforces DRAFT-only edits via an `_assert_draft()` guard that raises HTTP 422 with an error message if the recipe is not in DRAFT status.
