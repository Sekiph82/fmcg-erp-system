# Inventory Stock Ledger

**Route:** `/dashboard/inventory` (default tab: Stock Ledger)  
**Permission required:** `inventory.view`  
**Workspace tabs:** Stock Ledger, Movements, Cycle Count, Shelf Life, Traceability, Serials, Valuation

---

## What It Does

The Inventory module manages finished goods stock positions across all warehouses. Each stock record (position) represents a unique combination of product + warehouse + lot number. The inventory page provides four operational sub-tabs: stock summary, stock entry (receive), stock issue (dispatch), and inter-warehouse transfer.

![Inventory workspace](../../../screenshots/captured/017_inventory.png)
*Inventory workspace showing real-time stock positions across all warehouses.*

![Inventory — Stock Ledger tab](../../../screenshots/captured/018_inventory-stock.png)
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

![Stock Entry (IN) form](../../../screenshots/captured/actions/inventory-stock-entry-form.png)
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
| `shelf-life` | Shelf Life | Expiry management |
| `traceability` | Traceability | Forward and backward lot trace |
| `serials` | Serials | Serial number tracking |
| `valuation` | Valuation | Inventory value reports |

All tabs require `inventory.view`.
