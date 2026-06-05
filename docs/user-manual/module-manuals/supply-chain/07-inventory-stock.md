# Inventory Stock Ledger

**Route:** `/dashboard/inventory` (default tab: Stock Ledger)  
**Permission required:** `inventory.view`  
**Workspace tabs:** Stock Ledger, Movements, Cycle Count, Shelf Life, Traceability, Serials, Valuation

> Hover over the ? icon in the page header for quick field, status, and workflow guidance.

---

## What It Does

The Inventory module manages finished goods stock positions across all warehouses. Each stock record (position) represents a unique combination of product + warehouse + lot number. The inventory page provides four operational sub-tabs: stock summary, stock entry (receive), stock issue (dispatch), and inter-warehouse transfer.

![Inventory — Stock Ledger tab](../../../screenshots/captured/module-ui/supply-chain/inventory/stock-tab.png)
*Stock Ledger showing on-hand, available, and reserved quantities with reorder alerts.*

---

## Stock Summary (Current Stock Tab)

**Tab:** `stock` — `data-testid="inventory-stock-table"`

Shows all stock positions with real-time quantities.

### Table Columns

| Column | Field | Notes |
|--------|-------|-------|
| **SKU** | `product_sku` | Monospace |
| **Product** | `product_name` | Product description |
| **Warehouse** | `warehouse_code — warehouse_name` | Composite display |
| **Lot** | `lot_number` | "no lot" shown in grey if null |
| **Expiry** | `expiry_date` | Blank if no expiry |
| **On Hand** | `quantity_on_hand` | Bold red + ⚠ low if `is_below_reorder = true` |
| **Available** | `quantity_available` | Emerald text; = On Hand minus Reserved |
| **Reserved** | `quantity_reserved` | Quantity committed to open sales orders |
| **Actions** | — | Adjust / Delete (permission-gated) |

### Quantity Relationships

```
quantity_on_hand = quantity_available + quantity_reserved
```

- `quantity_available` — what can be picked for new orders
- `quantity_reserved` — held for open but not yet dispatched sales orders
- `is_below_reorder` — true when `quantity_on_hand < reorder_point` (from Reorder Policies)

### Reorder Alert

Stock positions below their reorder point show a bold red quantity and a `⚠ low` suffix. This signals procurement to raise a PR.

---

## Stock Entry (IN) — Receiving Stock

**Tab:** `entry` (green label)

Used to receive finished goods into a warehouse. Typically triggered after a production batch is completed or a direct purchase receipt outside the procurement module.

![Stock Entry (IN) form](../../../screenshots/captured/module-ui/supply-chain/inventory/entry-tab.png)
*Stock Entry form for receiving goods: product, warehouse, quantity, lot number, expiry date, and reference.*

### Stock Entry Fields

| Field | Label | Required | Backend field | Notes |
|-------|-------|----------|---------------|-------|
| `product_id` | Product | Yes | `product_id` | Select from products master (SKU — Name) |
| `warehouse_id` | Warehouse | Yes | `warehouse_id` | Select from warehouses (Code — Name) |
| `quantity` | Quantity | Yes | `quantity` | Decimal; step 0.001; must be > 0 |
| `unit_cost` | Unit Cost (Rp) | No | `unit_cost` | Cost per unit for inventory valuation |
| `lot_number` | Lot Number | No | `lot_number` | e.g. `LOT-2026-001` |
| `expiry_date` | Expiry Date | No | `expiry_date` | Date picker |
| `reference` | Reference # | Yes | `reference` | Default pre-filled as `GR-YYYY-MM-DD`; identifies the source document |
| `notes` | Notes | No | `notes` | Free text |

**Permission check:** Button disabled if user lacks `inventory.receive_all` and is out of scope for the selected warehouse. Error message: "You can view this warehouse but cannot receive stock in this scope."

On success: `quantity_on_hand` increases; a RECEIPT movement is created in the ledger; returns to Stock tab.

---

## Stock Issue (OUT) — Dispatching Stock

**Tab:** `issue` (red label)

Used to issue finished goods from a warehouse. Typically used for sales order fulfilment or production material issue outside the main work order flow.

![Stock Issue (OUT) form](../../../screenshots/captured/module-ui/supply-chain/inventory/issue-tab.png)
*Stock Issue form for dispatching goods: product, warehouse, quantity, lot number, and reference.*

### Stock Issue Fields

| Field | Label | Required | Backend field | Notes |
|-------|-------|----------|---------------|-------|
| `product_id` | Product | Yes | `product_id` | Select from products master |
| `warehouse_id` | Warehouse | Yes | `warehouse_id` | Select from warehouses |
| `quantity` | Quantity | Yes | `quantity` | Decimal; step 0.001; must be > 0 |
| `lot_number` | Lot Number (optional) | No | `lot_number` | Specify lot for FEFO picking |
| `reference` | Reference # | Yes | `reference` | Default `SO-YYYY-MM-DD` |
| `notes` | Notes | No | `notes` | Free text |

**Insufficient stock guard:** The API returns an error if `quantity > quantity_available`. The UI shows a toast: "Insufficient Stock" with the API's message. An amber warning box in the form states: "The system will reject this if available stock is insufficient."

**Permission check:** Button disabled if user lacks `inventory.dispatch_all` and is out of scope for the selected warehouse.

On success: `quantity_on_hand` decreases; an ISSUE movement is created; returns to Stock tab.

---

## Transfer — Moving Stock Between Warehouses

**Tab:** `transfer` (blue label)

Transfers stock between two warehouses of the same company.

![Stock Transfer form](../../../screenshots/captured/module-ui/supply-chain/inventory/transfer-tab.png)
*Transfer form: select product, source warehouse, destination warehouse, quantity, and reference.*

### Transfer Fields

| Field | Label | Required | Backend field | Notes |
|-------|-------|----------|---------------|-------|
| `product_id` | Product | Yes | `product_id` | Select from products master |
| `from_warehouse_id` | From Warehouse | Yes | `from_warehouse_id` | Source warehouse |
| `to_warehouse_id` | To Warehouse | Yes | `to_warehouse_id` | Destination warehouse |
| `quantity` | Quantity | Yes | `quantity` | Decimal; step 0.001; must be > 0 |
| `lot_number` | Lot Number (optional) | No | `lot_number` | Specify lot to maintain FEFO tracking |
| `reference` | Reference # | Yes | `reference` | Default `TRF-YYYY-MM-DD` |
| `notes` | Notes | No | `notes` | Free text |

**Permission check:** Requires `inventory.transfer_all` OR `canPerformInScope` on both the source and destination warehouses. Button disabled with tooltip if insufficient permissions.

On success: source warehouse `quantity_on_hand` decreases; destination increases; two TRANSFER movements created (OUT from source, IN to destination); returns to Stock tab.

---

## Adjusting Stock

From the Stock Summary tab, users with `inventory.adjust` (in scope) or `inventory.adjust_all` see an **Adjust** button per row.

### Adjustment Modal

| Field | Required | Notes |
|-------|----------|-------|
| New Quantity | Yes | The corrected on-hand quantity (not the delta) |
| Reason | Yes | e.g. "Physical count correction", "Damaged goods write-off" |

The adjustment creates an ADJUSTMENT movement. The delta (new − old) is shown in green (positive) or red (negative) before submission.

---

## Deleting a Stock Record

From the Stock Summary tab, users with `inventory.delete` (in scope) or `inventory.delete_all` see a **Delete** button.

**Constraint:** A stock record can only be deleted when `quantity_on_hand = 0`. If the quantity is non-zero, the delete modal shows a warning: "You must adjust the quantity to zero before deleting this record."

**Blocked error (HTTP 409):** If the stock record is referenced by other data (e.g. open sales order reservations), deletion is blocked with a structured error listing the blocking references.

---

## CSV Import

The `ImportModal` (module: `inventory_stock`) allows bulk stock positions to be imported via CSV. Use this for initial data load or period-end corrections.

CSV columns (inspect ImportModal configuration for exact headers — the module key is `inventory_stock`).

---

## Inventory Workspace Tabs

| Tab Key | Label | Content |
|---------|-------|---------|
| `stock` | Stock Ledger | Stock summary, entry, issue, transfer |
| `movements` | Movements | Full movement ledger |
| `cycle-count` | Cycle Count | Physical count sheets and reconciliation |
| `shelf-life` | Shelf Life | Expiry management and FEFO alerts |
| `traceability` | Traceability | Forward and backward lot trace |
| `serials` | Serials | Serial number tracking |
| `valuation` | Valuation | Inventory value reports |

All tabs require `inventory.view`.

---

## Demo Data — Inventory Seed (I1–I7)

The system ships with FMCG inventory seed data populated across all inventory tabs. This data represents a realistic starting state for demonstration, training, and testing.

![Inventory — Stock Ledger](../../../screenshots/captured/017_inventory.png)
*Inventory workspace showing seeded stock positions across PROD-WH and FG-WH warehouses.*

![Inventory — Stock tab](../../../screenshots/captured/018_inventory-stock.png)
*Stock Ledger tab with seeded stock levels, lot numbers, and reorder alerts.*

### Seed Warehouses

| Code | Name | Purpose |
|---|---|---|
| `PROD-WH` | Production Warehouse | Raw materials and in-process stock |
| `FG-WH` | Finished Goods Warehouse | Completed product stock |

### Seeded Products (5) and Materials (7)

Products and materials are sourced from the production master data seed (TASK-015). Each inventory record links to these items via SKU/material code.

### I1 — Lots and Stock Positions

Opening lot records and stock balances seeded for all 5 products and 7 materials across both warehouses. Each lot has a `lot_number`, `expiry_date`, and opening quantity.

### I2 — WMS Zones and Storage Locations

WMS zones (PROD-WH and FG-WH) and bin locations seeded. See the WMS manual for zone/location details.

### I3 — Trace Events for Lot Genealogy

Trace events seeded to support forward and backward lot traceability. Each lot has receipt, issue, and production consumption events recorded.

![Inventory — Traceability](../../../screenshots/captured/022_inventory-traceability.png)
*Traceability tab showing lot genealogy chain from raw material receipt through production consumption.*

### I4 — Cycle Count Plans

Cycle count plans seeded for both warehouses with planned count dates and item assignments.

![Inventory — Cycle Count](../../../screenshots/captured/021_inventory-cycle-count.png)
*Cycle Count tab showing seeded count plans with status and item coverage.*

### I5 — Shelf Life Profiles and Alerts

Lot shelf life profiles seeded with `expiry_date`, `best_before_date`, and `days_remaining` calculations. Shelf life alerts generated for lots approaching expiry thresholds.

![Inventory — Shelf Life](../../../screenshots/captured/020_inventory-shelf-life.png)
*Shelf Life tab showing seeded lots with expiry alerts and FEFO ranking.*

### I6 — Demand Forecasts

Demand forecasts seeded using `ForecastModelType.PROPHET` (implemented as local statsmodels Holt-Winters). See the AI & Automation manual for details on the forecasting engine.

Forecast records include:
- Forecast model type: `PROPHET` (maps to local Holt-Winters — no external API required)
- Forecast status: `COMPLETED`
- Period type: `MONTHLY`
- Forecast lines per product with predicted demand quantities

### I7 — MRP Run, Results, Suggestions, and Exceptions

An MRP run (`MRP-SEED-001`) is seeded with a 90-day planning horizon:

| Data type | Count |
|---|---|
| MRP run | 1 (`MRP-SEED-001`, status `COMPLETED`) |
| MRP results | 5 (one per product) |
| MRP suggestions | Multiple per product |
| MRP exceptions | Includes shortage flag for `POVU-HS` |

![Planning — MRP](../../../screenshots/captured/059_planning-mrp.png)
*MRP page showing seeded MRP run with demand forecasts, results, and shortage alerts.*

**Shortage flag:** Product `POVU-HS` has `shortage_flag = true` in the MRP result, indicating projected stock-out within the planning horizon.

---

## Shelf Life Management

**Tab:** `shelf-life`

The Shelf Life tab manages lot expiry, FEFO picking order, and near-expiry alerts.

### Shelf Life Alert Types

| Alert type | Trigger |
|---|---|
| Near expiry | Lot within the configured warning threshold days of expiry |
| Expired | Lot past expiry date |
| Best before breach | Lot past best-before date (quality advisory; not a hard block) |

### FEFO Picking

Lots are ranked by expiry date. The oldest-expiry lot is issued first (First Expired, First Out). This ranking is enforced by `shelf_life_service.py` which reads all lots — FEFO must see the complete lot list to rank correctly.

---

## Traceability

**Tab:** `traceability`

Forward and backward lot tracing across the supply chain:

| Direction | Coverage |
|---|---|
| Backward (upstream) | From finished lot → production batch → raw material receipt |
| Forward (downstream) | From raw material lot → which work orders consumed it → which finished batches |

Trace events record: receipt, issue, production consumption, inter-warehouse transfer, and adjustment.

---

## Cycle Count

**Tab:** `cycle-count`

Cycle count plans schedule periodic physical counts of stock locations. Each plan defines:
- Count date
- Warehouses in scope
- Items or item categories to count
- Assigned counter

After counting, actual quantities are entered and variance reports are generated. Discrepancies trigger stock adjustments.

---

## Valuation

**Tab:** `valuation`

Inventory valuation uses FIFO cost layers. Each receipt creates a cost layer. Issues are costed using the oldest available cost layer first.

| Metric | Description |
|---|---|
| Total inventory value (KES) | Sum of all on-hand stock at FIFO cost |
| Value by warehouse | Per-warehouse inventory value |
| Value by product | Per-product inventory value |
| Cost layer details | Unit cost and quantity per open FIFO layer |
