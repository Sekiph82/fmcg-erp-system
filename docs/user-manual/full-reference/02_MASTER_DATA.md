# Master Data

**URLs:** `/dashboard/products`, `/dashboard/materials`, `/dashboard/suppliers`, `/dashboard/recipes`, `/dashboard/bom`  
**Module:** Master Data  
**Permission:** `products.view`, `procurement.view`, `recipe.view`, `bom.view`

---

## Overview

Master data is the foundation of the ERP. Products, materials, suppliers, recipes, and BOMs must be set up before any operational transactions can begin.

---

## Products Workspace

**URL:** `/dashboard/products`  
Tab: `products`

![Products Workspace](../screenshots/captured/012_products.png)

Finished goods catalogue. Each product has:
- SKU code, description, category
- Unit of measure (KG, Litre, Unit, Carton)
- Packaging specification
- Allergen flags
- Active BOM version link
- Costing group
- Price list assignment

---

## Materials Workspace

**URL:** `/dashboard/materials`  
Tab: `materials`

![Materials Workspace](../screenshots/captured/013_materials.png)

Raw material master. Each material has:
- Material code and description
- Category (raw material, packaging, indirect)
- Unit of measure
- Supplier links
- Reorder point and reorder quantity
- Lead time (days)
- Storage conditions
- Allergen content

---

## Suppliers Workspace

**URL:** `/dashboard/suppliers`  
Tab: `suppliers`

![Suppliers Workspace](../screenshots/captured/014_suppliers.png)

Supplier master used by Procurement. See Chapter 03 (Procurement) for full details.

---

## Recipes Workspace

**URL:** `/dashboard/recipes`  
Tab: `recipes`

![Recipes Workspace](../screenshots/captured/057_recipes.png)

Product formulas. Recipes define ingredients, quantities per batch, and processing steps. A recipe becomes a BOM when linked to a product.

---

## BOM & Formula Workspace

**URL:** `/dashboard/bom`  
Tabs: `list`, `substitutes`, `compare`, `conversion`

![BOM Workspace](../screenshots/captured/053_bom.png)

### BOM Tabs

| Tab | Purpose |
|---|---|
| list | All BOM versions with effective dates |
| substitutes | Allowed material substitutions |
| compare | Side-by-side BOM version comparison |
| conversion | Batch size conversion profiles |

### BOM Version Control

Each BOM has:
- Version number
- Effective from / effective to date
- Status: Draft, Active, Archived

Only one BOM version should be Active for each product at any time.

### Substitutes

When a material is unavailable:
1. BOM → Substitutes tab
2. Find the material
3. See allowed substitutes and quantity equivalence
4. Production supervisor selects substitute when creating the production order

---

## Setup Sequence

For a new product:
1. Create material records for all ingredients
2. Create the product in Products workspace
3. Create a recipe in Recipes workspace
4. Create a BOM in BOM workspace linking product to recipe
5. Set BOM status to Active with today as effective date
6. Test by creating a production order — verify material requirements
