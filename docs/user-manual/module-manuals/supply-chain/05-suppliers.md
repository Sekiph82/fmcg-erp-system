# Suppliers

**Route:** `/dashboard/procurement?tab=suppliers`  
**Tab key:** `suppliers`  
**Permission required:** `procurement.view`

---

## What It Does

The Suppliers tab manages the supplier master data — the registry of all vendors from whom materials and products are purchased. Supplier records are referenced across procurement (PRs, POs, RFQs), quality (incoming inspections, certificates), and logistics (import shipments).

![Suppliers workspace](../../../screenshots/captured/module-ui/supply-chain/suppliers/suppliers-list-tab.png)
*Supplier master list showing code, name, country, contact, and active/inactive status.*

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

## Add Supplier Form

Click **+ Add Supplier** to open the create dialog.

![Add Supplier modal](../../../screenshots/captured/module-ui/supply-chain/suppliers/add-supplier-modal.png)
*Add Supplier form: Code, Name, Contact Person, Email, Phone, Country, and Payment Terms.*

Fields shown in the form:

| Field | Required | Default | Notes |
|-------|----------|---------|-------|
| `Code` | Yes | — | Internal supplier code (e.g. `SUP-001`) |
| `Name` | Yes | — | Legal business name |
| `Contact Person` | No | — | Primary contact name |
| `Email` | No | — | Contact email address |
| `Phone` | No | — | Contact phone number |
| `Country` | No | — | Country of registration |
| `Payment Terms (days)` | No | 30 | Default net payment terms in days |

---

## Supplier Record Fields

All fields stored per supplier record (full schema including CSV-importable fields):

| Field | Required | Description |
|-------|----------|-------------|
| `code` | Yes | Internal supplier code (e.g. `SUP-001`) |
| `name` | Yes | Legal business name |
| `contact_person` | No | Primary contact person name |
| `email` | No | Email address |
| `phone` | No | Phone number |
| `address` | No | Full street address |
| `city` | No | City |
| `country` | No | Country of registration |
| `tax_id` | No | VAT / tax registration number |
| `payment_terms_days` | No | Default payment terms in days (default: 30) |
| `is_active` | No | Whether supplier is available for new orders (default: true) |
| `preferred_payment_method` | No | `bank`, `cash`, or `mpesa` |
| `mpesa_phone_number` | No | M-Pesa number (required when method is `mpesa`) |
| `supplier_category` | No | Internal category / segment label |
| `qualification_status` | No | AVL status — see Supplier Approval Status below |
| `risk_level` | No | Procurement risk rating — `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `approved_from` | No | Approval start date (YYYY-MM-DD) |
| `approved_until` | No | Approval expiry date (YYYY-MM-DD) |

---

## Importing Suppliers via CSV

Click **Import** on the Suppliers page to bulk-load supplier records from a CSV file.

**Steps:**
1. Download the CSV template from the Import dialog.
2. Fill in one supplier per row.
3. Upload the file and click **Import**.
4. Review the validation summary — rows with errors are skipped; valid rows are created.

**CSV column reference:**

| Column | Required | Accepted values / format |
|--------|----------|--------------------------|
| `code` | **Yes** | Unique code, e.g. `SUP-001` |
| `name` | **Yes** | Legal business name |
| `contact_person` | No | Contact person name |
| `email` | No | Valid email address |
| `phone` | No | Phone number |
| `address` | No | Full street address |
| `city` | No | City name |
| `country` | No | Country name |
| `tax_id` | No | VAT / tax ID number |
| `payment_terms_days` | No | Integer, e.g. `30` (default: 30) |
| `is_active` | No | `true` or `false` (default: true) |
| `preferred_payment_method` | No | `bank`, `cash`, or `mpesa` |
| `mpesa_phone_number` | No | M-Pesa phone number (required if method is `mpesa`) |
| `supplier_category` | No | Free-text category label |
| `qualification_status` | No | `PENDING`, `APPROVED`, `CONDITIONAL`, `SUSPENDED`, `REJECTED` |
| `risk_level` | No | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `approved_from` | No | Date in `YYYY-MM-DD` format |
| `approved_until` | No | Date in `YYYY-MM-DD` format |

> Columns marked **Yes** are mandatory — rows missing `code` or `name` will be rejected.

---

## Supplier Approval Status

The `qualification_status` field controls whether a supplier can be used on orders:

| Status | Meaning |
|--------|---------|
| `PENDING` | Awaiting qualification review |
| `APPROVED` | Fully qualified; on the Approved Vendor List (AVL) |
| `CONDITIONAL` | Approved with restrictions or pending re-qualification |
| `SUSPENDED` | Temporarily blocked from new orders |
| `REJECTED` | Permanently disqualified |

Only `APPROVED` suppliers can be selected on Purchase Orders. `CONDITIONAL` suppliers may require override approval depending on configuration.

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
