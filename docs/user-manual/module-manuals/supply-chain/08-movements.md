# Inventory Movements & Traceability

**Route:** `/dashboard/inventory` (various tabs)  
**Permission required:** `inventory.view`

---

## Movements Tab

**Tab key:** `movements`  
**Route:** `/dashboard/movements/page`

![Inventory — Movements tab](../../../screenshots/captured/019_inventory-movements.png)
*Movements ledger showing all stock changes with movement type, quantity, reference, and timestamp.*

Every change to inventory — receipt, issue, transfer, adjustment, quarantine — creates an immutable movement record in the ledger. Movements are the audit trail of all stock changes.

### Movement Types

| Type | Direction | Created By |
|------|-----------|-----------|
| `RECEIPT` | IN | Stock Entry form, GRN posting |
| `ISSUE` | OUT | Stock Issue form, sales order dispatch |
| `TRANSFER_IN` | IN | Transfer (destination side) |
| `TRANSFER_OUT` | OUT | Transfer (source side) |
| `ADJUSTMENT` | IN or OUT | Stock Adjustment modal |
| `PRODUCTION_ISSUE` | OUT | Work order material issuance |
| `PRODUCTION_RECEIPT` | IN | Work order finished goods receipt |
| `QUARANTINE` | OUT (blocked) | WMS quarantine action |
| `QUARANTINE_RELEASE` | IN (unblocked) | WMS quarantine release |

### Movement Record Fields

| Field | Description |
|-------|-------------|
| `movement_no` | System-generated reference |
| `movement_type` | Type from list above |
| `product_sku` + `product_name` | Product affected |
| `warehouse_name` | Warehouse affected |
| `quantity` | Signed quantity (positive = IN, negative = OUT) |
| `lot_number` | Lot affected (if applicable) |
| `reference` | Source document reference (PO no, SO no, etc.) |
| `notes` | Free text notes |
| `created_at` | Timestamp of the movement |
| `created_by` | User who created it |

### Filtering Movements

The Movements tab supports filtering by:
- Date range
- Movement type
- Product
- Warehouse

---

## Cycle Count Tab

**Tab key:** `cycle-count`  
**Route:** `/dashboard/cycle-count/page`

![Inventory — Cycle Count tab](../../../screenshots/captured/021_inventory-cycle-count.png)
*Cycle Count tab showing count sheets with status (DRAFT, IN_PROGRESS, POSTED, CANCELLED).*

Cycle counting is the process of periodically counting a subset of inventory items to verify the accuracy of the stock ledger without doing a full warehouse shutdown.

### Cycle Count Process

1. **Create Count Sheet** — select products and/or locations to count
2. **Print / Export** — generate count sheets for warehouse staff
3. **Enter Counts** — staff record physical counts on the sheet
4. **Reconcile** — system compares physical counts to book quantities
5. **Post Adjustments** — approve and post variances as ADJUSTMENT movements

### Count Status Values

| Status | Meaning |
|--------|---------|
| `DRAFT` | Count sheet created |
| `IN_PROGRESS` | Counting underway |
| `POSTED` | Adjustments applied; ledger updated |
| `CANCELLED` | Count voided |

---

## Shelf Life Tab

**Tab key:** `shelf-life`  
**Route:** `/dashboard/shelf-life/page`

![Inventory — Shelf Life tab](../../../screenshots/captured/020_inventory-shelf-life.png)
*Shelf Life tab showing expiring stock positions grouped by urgency with FEFO ranking.*

Manages expiry dates across all stock positions.

### Key Views

| View | Description |
|------|-------------|
| Expiring within 30 days | Stock positions approaching expiry |
| Expiring within 90 days | Medium-term expiry planning |
| Already expired | Expired stock requiring write-off |
| FEFO ranking | First-Expiry-First-Out picking priority order |

### FEFO Enforcement

When issuing stock, the system prioritises lot numbers with the earliest expiry date. If `lot_number` is not specified on the issue, the system automatically selects the FEFO lot.

---

## Traceability Tab

**Tab key:** `traceability`  
**Route:** `/dashboard/traceability/page`

Provides full forward and backward traceability for any product or lot number. See the [Batch & Lots chapter](../manufacturing/06-batch-lots.md) for the traceability model.

### Forward Trace

From a production batch number or supplier lot: which customers received it?

### Backward Trace

From a sales order or customer: which supplier lots contributed to the product?

---

## Serials Tab

**Tab key:** `serials`  
**Route:** `/dashboard/inventory/serials/page`

Serial number tracking for high-value products that require individual unit identification (e.g. equipment, appliances). Each serial number:
- Is linked to a specific product and lot
- Has a status: IN_STOCK / SOLD / RETURNED / SCRAPPED
- Has a full movement history

---

## Valuation Tab

**Tab key:** `valuation`  
**Route:** `/dashboard/inventory/valuation/page`

Inventory valuation reports the financial value of stock on hand. Valuation methods:

| Method | Description |
|--------|-------------|
| **FIFO** | First In, First Out — uses the cost of the oldest stock |
| **Weighted Average Cost (WAC)** | Average of all receipts for the product |
| **Standard Cost** | Uses a pre-defined standard cost per unit |

The valuation report shows:
- Stock value per product
- Stock value per warehouse
- Total inventory value at the company level
- Comparison to prior period

This feeds directly into the Finance module's balance sheet for inventory asset reporting.
