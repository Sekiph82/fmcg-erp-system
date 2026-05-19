# Suppliers

**Route:** `/dashboard/procurement?tab=suppliers`  
**Tab key:** `suppliers`  
**Permission required:** `procurement.view`

---

## What It Does

The Suppliers tab manages the supplier master data — the registry of all vendors from whom materials and products are purchased. Supplier records are referenced across procurement (PRs, POs, RFQs), quality (incoming inspections, certificates), and logistics (import shipments).

---

## Supplier List

Shows all suppliers with:
- Supplier name
- Supplier code (monospace)
- Country
- Contact information
- Active/Inactive status
- Link to supplier detail

---

## Supplier Record Fields

| Field | Description |
|-------|-------------|
| `code` | Internal supplier code (e.g. `SUP-001`) |
| `name` | Legal business name |
| `country` | Country of registration |
| `city` | City |
| `address` | Full address |
| `contact_name` | Primary contact person |
| `contact_email` | Email address |
| `contact_phone` | Phone number |
| `payment_terms` | Default payment terms (e.g. "Net 30") |
| `currency` | Default transaction currency |
| `tax_id` | VAT registration or tax ID number |
| `is_active` | Whether supplier is available for new orders |
| `approved_materials` | Materials this supplier is approved to supply |

---

## Supplier Approval Status

Suppliers may be categorised as:
- **Approved** — qualified and on the approved vendor list (AVL)
- **Conditional** — approved with restrictions or pending re-qualification
- **Suspended** — temporarily blocked from new orders
- **Blacklisted** — permanently blocked

Only APPROVED suppliers can be selected on Purchase Orders (CONDITIONAL suppliers require override approval, depending on configuration).

---

## Approved Vendor List (AVL)

Each material can have one or more approved suppliers. The AVL enforces that materials are only purchased from qualified vendors. When raising a PO line, the supplier field filters to show only AVL-approved suppliers for that material.

---

## Supplier Portal

**Tab key:** `supplier-portal`  
**Route:** `/dashboard/supplier-portal/page` (embedded)

The Supplier Portal gives external suppliers (or procurement staff acting on their behalf) a view of:
- Open POs awaiting acknowledgment
- Delivery schedules
- Outstanding GRNs
- Invoice status

Access is controlled per supplier and requires supplier-specific credentials or a guest token.

---

## Supplier Performance

From the supplier detail page, procurement managers can review:
- On-time delivery rate
- Quality pass rate (from QC incoming inspections)
- Price variance vs. quoted prices
- Outstanding invoice amounts

These metrics feed into the RFQ comparison and supplier selection decisions.
