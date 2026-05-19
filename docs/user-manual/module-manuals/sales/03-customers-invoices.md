# Customers & Invoices

---

## Customers

**Route:** `/dashboard/sales?tab=customers`  
**Permission required:** `sales.view`

### What It Does

Customers maintains the customer master record including contact details, sales channel classification, payment terms, credit limit, and currency. Every sales order and invoice is linked to a customer.

![Customers tab](../../../screenshots/captured/module-ui/sales/sales/customers-tab.png)
*Customers tab showing customer list with channel badges, contact details, payment terms, and credit limits.*

### Customer List Columns

| Column | Description |
|---|---|
| Code | Unique customer code |
| Name | Customer display name |
| Channel | RETAIL (green) / WHOLESALE / DISTRIBUTOR / DIRECT / EXPORT (blue) / ONLINE (yellow) badge |
| Contact | Contact person name |
| Email | Primary email address |
| Payment Terms | Net 7 / Net 14 / Net 30 / Net 45 / Net 60 / Net 90 |
| Credit Limit | Maximum outstanding balance; shown as `{currency} {amount}` |
| Status | Active (green) / Inactive (red) badge |
| Edit | Opens edit form for that customer |

### New Customer Modal

Button: **+ Add Customer** (top-right)

![New Customer modal](../../../screenshots/captured/module-ui/sales/customers/new-customer-modal.png)
*New Customer modal showing Customer Code, Name, Channel, Payment Terms, Currency, and Credit Limit fields.*

![Customer dropdowns expanded](../../../screenshots/captured/module-ui/sales/customers/customer-dropdowns.png)
*New Customer modal with Channel dropdown expanded showing RETAIL, WHOLESALE, DISTRIBUTOR, DIRECT, EXPORT, ONLINE; and Payment Terms and Currency dropdowns.*

### Customer Create/Edit Fields

| Field | Label | Required | Notes |
|---|---|---|---|
| `code` | Customer Code | Yes | Unique identifier |
| `name` | Name | Yes | Display name |
| `contact_person` | Contact Person | No | Primary contact |
| `email` | Email | No | — |
| `phone` | Phone | No | — |
| `address` | Address | No | Billing address |
| `city` | City | No | — |
| `country` | Country | No | — |
| `delivery_address` | Delivery Address | No | Ships-to address |
| `delivery_city` | Delivery City | No | — |
| `delivery_country` | Delivery Country | No | — |
| `channel` | Channel | Yes | RETAIL / WHOLESALE / DISTRIBUTOR / DIRECT / EXPORT / ONLINE |
| `payment_terms_days` | Payment Terms | Yes | Net 7 / 14 / 30 / 45 / 60 / 90 |
| `credit_limit` | Credit Limit | No | Maximum allowed outstanding |
| `tax_id` | Tax ID | No | VAT or PIN number |
| `currency` | Currency | Yes | USD / EUR / GBP / JPY / CNY / SGD |
| `notes` | Notes | No | — |

---

## Invoices

**Route:** `/dashboard/sales?tab=invoices`  
**Permission required:** `sales.view`

### What It Does

Invoices lists all sales invoices with payment tracking. Invoices are generated from confirmed and shipped sales orders. The page also shows outstanding balance summaries and supports overdue status sync.

![Invoices tab](../../../screenshots/captured/module-ui/sales/sales/invoices-tab.png)
*Invoices tab showing invoice list with payment status badges, due dates, and outstanding amounts.*

### Invoice List Columns

| Column | Description |
|---|---|
| Invoice No | Unique reference; clickable → invoice detail page |
| Customer | Customer name |
| Sales Order | Linked SO number |
| Invoice Date | Date invoice was issued |
| Due Date | Payment due date; red if overdue |
| Total | Invoice total in invoice currency |
| Paid | Amount received |
| Outstanding | Balance remaining |
| Status | Status badge |

### Invoice Status Values

| Status | Badge Colour |
|---|---|
| `DRAFT` | Gray |
| `ISSUED` | Blue |
| `PARTIALLY_PAID` | Yellow |
| `PAID` | Green |
| `OVERDUE` | Red |
| `CANCELLED` | Red |

### Sync Overdue

Button: **Sync Overdue** — scans all `ISSUED` invoices and marks as `OVERDUE` any that are past their due date. Shows count of updated invoices.
