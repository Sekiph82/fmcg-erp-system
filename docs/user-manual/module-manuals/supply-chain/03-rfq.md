# RFQ & Supplier Quotations

**Route:** `/dashboard/procurement?tab=rfq`  
**Tab key:** `rfq`  
**Permission required:** `procurement.view`

---

## What It Does

A Request for Quotation (RFQ) is sent to one or more suppliers to obtain pricing before committing to a Purchase Order. Suppliers respond with their quoted prices; the procurement team compares responses and awards the business to the preferred supplier, which then creates a PO.

---

## RFQ Workflow

```
Create RFQ → Send to Suppliers → Receive Responses → Compare → Award → PO Created
```

---

## RFQ Status Values

| Status | Meaning |
|--------|---------|
| `DRAFT` | RFQ being prepared |
| `SENT` | RFQ dispatched to suppliers |
| `RESPONSES_RECEIVED` | At least one supplier has responded |
| `AWARDED` | Business awarded to a supplier; PO being created |
| `CANCELLED` | RFQ cancelled |
| `CLOSED` | RFQ closed without awarding |

---

## RFQ Response Status Values

| Status | Meaning |
|--------|---------|
| `PENDING` | Supplier has not yet responded |
| `RECEIVED` | Response submitted |
| `ACCEPTED` | This response was awarded |
| `REJECTED` | Supplier not selected |

---

## Creating an RFQ

An RFQ is typically created from a PR or independently. Fields include:
- RFQ number (user-assigned; e.g. `RFQ-2026-001`)
- Closing date (deadline for supplier responses)
- Materials/items with quantities and target units
- Selected suppliers (one RFQ can go to multiple suppliers)

Each selected supplier receives an individual response slot. Their quoted unit prices, lead times, and notes are recorded against each supplier response.

---

## Comparing Responses

The RFQ comparison view shows all supplier responses side by side:
- Quoted unit price per line
- Total value
- Lead time quoted
- Terms and conditions
- Previous performance rating (if configured)

The procurement officer selects the winning supplier and clicks **Award**. This creates a PO pre-filled with the winning supplier's prices.

---

## Blanket Purchase Agreements

**Tab key:** `blanket-agreements`

Blanket Purchase Agreements (BPAs) pre-negotiate pricing with a supplier for a defined period and volume, without committing to specific delivery dates. Call-off orders are raised against the BPA.

BPA status values: DRAFT, ACTIVE, EXPIRED, CANCELLED.

Key fields:
- Agreement number
- Supplier
- Validity period (start date → end date)
- Material/product lines with agreed unit prices
- Cumulative call-off quantity limit

When a PO is raised against a BPA, the agreed price is applied automatically and the cumulative call-off quantity is tracked against the BPA limit.

---

## Reorder Policies

**Tab key:** `reorder-policies`

Reorder policies define automatic replenishment triggers for materials:

| Field | Description |
|-------|-------------|
| Material | The material this policy governs |
| Warehouse | The warehouse where the reorder point applies |
| Reorder Point | Minimum on-hand quantity that triggers a reorder alert |
| Reorder Quantity | How much to order each time |
| Lead Time (days) | Days from PO creation to delivery |
| Preferred Supplier | Supplier pre-selected on auto-generated PRs |

When `quantity_on_hand` drops below the Reorder Point, the stock summary shows a `⚠ low` warning and the Procurement Suggestions tab generates a suggested PR.

---

## Procurement Suggestions

**Tab key:** `suggestions`

The Suggestions tab aggregates:
- Materials below reorder point (from Reorder Policies)
- MRP-generated material requirements (from Planning module)
- AI-generated suggestions based on consumption trends

Each suggestion shows the material, shortfall quantity, suggested reorder quantity, and recommended supplier. Approving a suggestion creates a PR automatically.

---

## Subcontracting

**Tab key:** `subcontracting`

Subcontracting orders are used when manufacturing is outsourced to a third-party processor. The subcontract order:
- Specifies the product to be made and the quantity
- Lists the raw materials to send to the subcontractor
- Records the finished goods received back

Subcontracting integrates with production (work orders) and inventory (material issue + goods receipt).

---

## Landed Cost

**Tab key:** `landed-cost`

Landed cost allocation apportions import costs (freight, insurance, customs duty, handling) across the material lines of a PO. This ensures the true cost of imported materials is captured in inventory valuation.

Allocation methods:
- **By Value** — proportional to line value
- **By Quantity** — proportional to quantity
- **By Weight** — proportional to material weight
- **Manual** — user specifies amounts per line

After posting landed costs, the material's average cost in inventory is updated to include the allocated import costs.
