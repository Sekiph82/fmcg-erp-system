# Finance Overview

**Route:** `/dashboard/finance?tab=overview`  
**Permission required:** `finance.view`

---

## What It Does

The Finance Overview tab is the financial command centre. It displays four live KPI tiles, a cash position table, and quick links to key finance sub-modules.

![Finance Overview tab](../../../screenshots/captured/module-ui/finance-payroll/finance/overview-tab.png)
*Finance Overview showing KPI tiles (Total Cash & Bank, Outstanding Receivables, M-Pesa This Month, Recon Exceptions) and the cash position table.*

---

## KPI Tiles

| Tile | Calculation | Colour |
|---|---|---|
| Total Cash & Bank | Sum of all cash account balances | Green |
| Outstanding Receivables | Sum of all unpaid invoice outstanding amounts | Red if overdue count > 0, else orange |
| M-Pesa This Month | Total received via M-Pesa in current calendar month | Indigo |
| Recon Exceptions | Count of reconciliation records with status `EXCEPTION` | Red if > 0, else gray |

Each tile is clickable and navigates to the relevant sub-module.

---

## Cash Position Table

Displays all configured cash/bank/M-Pesa accounts with:

| Column | Description |
|---|---|
| Account | Account name |
| Type | `CASH` (gray) / `BANK` (green) / `MPESA` (blue) badge |
| Balance | Current running balance |
| Pending In | Uncleared receipts |
| Pending Out | Uncleared payments |
| Cleared | Cleared balance only |

Clicking "Manage accounts" navigates to Cashbook.

---

## Quick Links

| Link | Destination |
|---|---|
| Cashbook & Bank Entries | `/dashboard/finance/cashbook` |
| M-Pesa Reconciliation | `/dashboard/finance/mpesa` |
| Product Costing | `/dashboard/finance/costing` |
| Receivables | `/dashboard/finance/receivables` |
| Budget Management | `/dashboard/finance/budget` |
| Journal Entries | `/dashboard/finance/cashbook?tab=journal` |
