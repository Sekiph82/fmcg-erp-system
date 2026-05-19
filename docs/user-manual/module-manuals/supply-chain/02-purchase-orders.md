# Purchase Orders

**Route:** `/dashboard/procurement?tab=orders`  
**Tab key:** `orders`  
**Permission required:** `procurement.view`

---

## What It Does

Purchase Orders (POs) are the formal external documents sent to suppliers to procure materials or products. POs can be created by converting an approved PR, or created directly. Each PO tracks receipt progress through Goods Receipt Notes (GRNs).

![Procurement — Orders tab](../../../screenshots/captured/module-ui/supply-chain/procurement/orders-tab.png)
*Purchase Orders tab showing PO list with status, supplier, and receipt progress.*

![New Purchase Order modal](../../../screenshots/captured/module-ui/supply-chain/procurement/new-po-modal.png)
*New Purchase Order modal — PO No, Supplier, Order Date, Delivery Date, and line items.*

---

## PO Header Fields

From the `POCreate` schema:

| Field | Label | Required | Default | Notes |
|-------|-------|----------|---------|-------|
| `po_no` | PO No | Yes | — | User-assigned; e.g. `PO-2026-001` |
| `supplier_id` | Supplier | Yes | — | Select from suppliers master |
| `order_date` | Order Date | Yes | — | Date PO is issued |
| `expected_delivery_date` | Expected Delivery | Yes | — | Date supplier should deliver |
| `payment_terms` | Payment Terms | No | — | Free text; e.g. "Net 30", "50% advance" |
| `currency` | Currency | No | `USD` | ISO currency code |
| `exchange_rate` | Exchange Rate | No | `1.0` | To KES; used for landed cost |
| `notes` | Notes | No | — | Internal notes |
| `lines` | Lines | No | `[]` | See PO Line Fields below |

### PO Line Fields

From `POLineCreate`:

| Field | Backend field | Required | Default | Notes |
|-------|---------------|----------|---------|-------|
| `line_no` | Line No | Yes | — | Sequence |
| `material_id` | Material | No | — | Either `material_id` or `product_id` |
| `product_id` | Product | No | — | Either `material_id` or `product_id` |
| `pr_line_id` | PR Line | No | — | Links back to originating PR line |
| `description` | Description | No | — | Free text override |
| `ordered_quantity` | Ordered Qty | Yes | — | Decimal |
| `unit` | Unit | Yes | `KG` | UOM |
| `unit_price` | Unit Price | Yes | `0` | Decimal |
| `tax_rate` | Tax Rate | Yes | `0` | Decimal; e.g. `0.16` for 16% VAT |

**Computed fields** on `POLineRead`:
- `line_total = ordered_quantity × unit_price × (1 + tax_rate)`
- `pending_quantity = max(ordered_quantity - received_quantity, 0)` — quantity not yet received via GRN

---

## PO Status Values

| Status | Meaning |
|--------|---------|
| `DRAFT` | PO created; not yet sent to supplier |
| `SENT` | PO dispatched to supplier |
| `ACKNOWLEDGED` | Supplier confirmed receipt of PO |
| `PARTIALLY_RECEIVED` | Some lines received via GRN; some pending |
| `FULLY_RECEIVED` | All lines fully received |
| `CANCELLED` | PO cancelled |
| `CLOSED` | PO administratively closed |

---

## PO Payment Status Values

| Status | Meaning |
|--------|---------|
| `UNPAID` | Invoice received but payment not made |
| `PARTIALLY_PAID` | Part payment made |
| `PAID` | Fully paid |
| `OVERPAID` | Payment exceeds PO value |

---

## PO Detail Page

**Route:** `/dashboard/procurement/orders/{id}` (or via procurement workspace)

From the detail page:
- View all PO lines with ordered, received, and pending quantities
- See linked GRNs (goods receipt notes)
- Mark PO as sent/acknowledged
- Cancel PO (if no goods received)
- Link to supplier portal view

---

## Goods Receipt Note (GRN)

When materials arrive, a GRN records the actual received quantities against the PO. GRN status values:

| Status | Meaning |
|--------|---------|
| `DRAFT` | GRN being filled in |
| `POSTED` | GRN confirmed; inventory updated |
| `CANCELLED` | GRN voided |

On posting a GRN:
1. Stock is credited to the selected warehouse
2. `received_quantity` on each PO line is updated
3. PO status moves to PARTIALLY_RECEIVED or FULLY_RECEIVED
4. A purchase invoice can be generated from the GRN for payment processing

---

## Procurement Workspace Tabs (Full List)

| Tab Key | Label | Content |
|---------|-------|---------|
| `purchase-requests` | Purchase Requests | PR list and creation |
| `orders` | Purchase Orders | PO list and management |
| `rfq` | RFQ | Request for quotation management |
| `deliveries` | Deliveries | Goods receipt notes |
| `suppliers` | Suppliers | Supplier master data |
| `blanket-agreements` | Blanket Agreements | Blanket purchase agreements |
| `reorder-policies` | Reorder Policies | Auto-reorder configuration |
| `suggestions` | Suggestions | AI-generated procurement suggestions |
| `subcontracting` | Subcontracting | Outsourced manufacturing orders |
| `landed-cost` | Landed Cost | Import duty, freight, insurance allocation |
| `supplier-portal` | Supplier Portal | Self-service portal for suppliers |

All tabs require `procurement.view`.
