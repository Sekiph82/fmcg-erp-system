# Deliveries & Goods Receipt

**Route:** `/dashboard/procurement?tab=deliveries`  
**Tab key:** `deliveries`  
**Permission required:** `procurement.view`

---

## What It Does

The Deliveries tab manages Goods Receipt Notes (GRNs) — the documents that record the physical arrival of materials from suppliers. Posting a GRN credits inventory and updates PO receipt quantities. It also triggers QC inspection requests for incoming materials when configured.

---

## GRN Status Values

| Status | Meaning |
|--------|---------|
| `DRAFT` | GRN being filled in; inventory not yet updated |
| `POSTED` | GRN confirmed; inventory credited; PO updated |
| `CANCELLED` | GRN voided; no inventory impact |

---

## Creating a GRN

A GRN is typically created from the PO detail page by clicking **Receive Delivery**. It can also be created from the Deliveries tab.

### GRN Header Fields

| Field | Required | Notes |
|-------|----------|-------|
| GRN No | Yes | User-assigned; e.g. `GRN-2026-001` |
| PO Reference | Yes | Links to the Purchase Order |
| Supplier | Yes | Auto-populated from PO |
| Delivery Date | Yes | Actual date goods arrived |
| Warehouse | Yes | Where goods are being received |
| Notes | No | Free text; delivery note or driver name |

### GRN Line Fields

Each GRN line corresponds to a PO line:

| Field | Required | Notes |
|-------|----------|-------|
| PO Line | Yes | Links to specific PO line |
| Material / Product | — | Auto-populated from PO line |
| Ordered Qty | — | Read-only from PO line |
| Received Qty | Yes | Actual quantity received; can be less than ordered (partial delivery) |
| Lot Number | No | Supplier lot for traceability |
| Expiry Date | No | Expiry date on the received lot |
| Unit Cost | No | Override if different from PO price |

---

## Partial Deliveries

Suppliers may deliver in multiple shipments. Each delivery is a separate GRN against the same PO:
- `received_quantity` on the PO line accumulates across all GRNs
- PO status shows `PARTIALLY_RECEIVED` until all lines are fully received
- The `pending_quantity` on each PO line = `ordered_quantity - received_quantity`

---

## Posting a GRN

Posting the GRN:
1. Validates that received quantities are within allowed tolerance
2. Creates an **inventory ENTRY movement** — credits `quantity_on_hand` in the warehouse
3. Assigns the lot number and expiry date to the stock record
4. Updates PO line `received_quantity`
5. Updates PO status to PARTIALLY_RECEIVED or FULLY_RECEIVED
6. Creates a **QC inspection request** (if incoming QC is configured for this material)
7. Optionally generates a **purchase invoice** for accounts payable

Once posted, a GRN cannot be edited. To correct a posting, a stock adjustment must be raised.

---

## Import Shipment Integration

For international imports, the GRN links to the Logistics module's shipment and container records. When goods arrive from the import shipment:
1. The logistics team records the arrival in **Logistics → Arrivals**
2. Customs clearance status is updated
3. The warehouse team then creates GRNs to receive the goods into inventory
4. Landed costs are allocated to the GRN lines

Import Shipment Status values:

| Status | Meaning |
|--------|---------|
| `PLANNED` | Shipment being organised |
| `BOOKED` | Vessel / cargo space confirmed |
| `CARGO_LOADED` | Container loaded at origin port |
| `IN_TRANSIT` | On the vessel at sea |
| `ARRIVED_PORT` | Arrived at Mombasa port |
| `CUSTOMS_HOLD` | Held by KRA for inspection |
| `CUSTOMS_CLEARED` | KRA clearance obtained |
| `OUT_FOR_DELIVERY` | In transit from port to warehouse |
| `DELIVERED` | Received at warehouse |
| `CANCELLED` | Shipment cancelled |
