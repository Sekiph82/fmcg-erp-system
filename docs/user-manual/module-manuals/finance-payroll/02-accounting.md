# Accounting

**Route:** `/dashboard/finance?tab=accounting`  
**Permission required:** `finance.view`  
**Sub-pages:** Customers Ledger, Suppliers Ledger, Sales Invoices, Purchase Invoices, Payments, Accounting Controls

---

## What It Does

The Accounting tab provides the double-entry accounting layer: invoice tracking, ledger balances, and payment records. It is the source of truth for revenue, costs, receivables, and payables.

![Accounting tab](../../../screenshots/captured/module-ui/finance-payroll/finance/accounting-tab.png)
*Accounting dashboard showing five KPI tiles and quick links to ledgers, invoices, and payments.*

---

## Accounting Dashboard KPIs

| KPI | Description |
|---|---|
| Total Revenue | All issued sales invoices |
| Receivables | Outstanding sales invoice value; sub-label shows overdue count; orange if > 0 |
| Total Cost | All purchase invoices |
| Payables | Outstanding purchase invoice value; red if > 0 |
| Net Cash Flow | Receivables minus Payables; green if ≥ 0, red if negative |

---

## Sub-page Quick Links

| Link | Route | Description |
|---|---|---|
| Customers Ledger | `/dashboard/finance/accounting/customers-ledger` | Customer balance history |
| Suppliers Ledger | `/dashboard/finance/accounting/suppliers-ledger` | Supplier balance history |
| Sales Invoices | `/dashboard/finance/accounting/sales-invoices` | Issued customer invoices |
| Purchase Invoices | `/dashboard/finance/accounting/purchase-invoices` | Received supplier invoices |
| Payments | `/dashboard/finance/accounting/payments` | Customer receipts and supplier payments |
| Accounting Controls | `/dashboard/finance/accounting/controls` | Period closing, chart of accounts, trial balance (`finance.configure` required) |

---

## Invoice Status Values

| Status | Badge Colour | Meaning |
|---|---|---|
| `DRAFT` | Gray | Not yet issued |
| `ISSUED` / `RECEIVED` | Blue | Sent to customer / received from supplier |
| `PAID` | Green | Fully settled |
| `PARTIALLY_PAID` | Yellow | Part payment received |
| `OVERDUE` | Red | Past due date, unpaid |
| `CANCELLED` | Gray (strikethrough) | Voided |

---

## Accounting Controls Sub-pages

| Page | Purpose |
|---|---|
| Chart of Accounts | Manage GL accounts and categories |
| General Ledger | All posted debit/credit entries |
| Trial Balance | Period trial balance report |
| Balance Sheet | Assets, liabilities, equity view |
| Profit & Loss | Revenue vs cost for a period |
| Period Closing | Lock prior periods to prevent back-posting |
| Journal | Manual double-entry journal entries |
