# M-Pesa Reconciliation

**Route:** `/dashboard/finance?tab=mpesa`  
**Permission required:** `finance.view`

---

## What It Does

M-Pesa Reconciliation matches incoming M-Pesa mobile money receipts to customer sales invoices. It supports automatic matching via business rules and manual override for exceptions.

![M-Pesa tab](../../../screenshots/captured/module-ui/finance-payroll/finance/mpesa-tab.png)
*M-Pesa tab showing reconciliation records with status filter tabs, amount, phone, and action buttons.*

---

## Reconciliation Status Values

| Status | Badge | Meaning |
|---|---|---|
| `UNMATCHED` | Yellow | Receipt received; no invoice linked yet |
| `MATCHED` | Green | Automatically matched to an invoice |
| `MANUAL` | Blue | Manually matched by finance team |
| `EXCEPTION` | Red | Could not be matched; flagged for review |

---

## Status Filter Bar

Five filter buttons at the top of the list: **ALL**, **UNMATCHED**, **MATCHED**, **MANUAL**, **EXCEPTION**. Each shows a count of records in that state.

---

## Auto-Match

Button: **Run Auto-Match** (top-right).

The auto-match engine attempts to pair M-Pesa receipts with open sales invoices using:
1. Amount match (exact)
2. Phone number linked to a customer
3. M-Pesa receipt code reference

Result dialog reports: `{N} matched, {N} skipped`.

---

## Manual Match

Available when an `UNMATCHED` record is selected:

| Field | Description |
|---|---|
| Invoice ID | Select the invoice to link this receipt to |
| Notes | Match justification |

Submitting moves the record to `MANUAL` status.

---

## Mark as Exception

Available for any unresolved record. Requires a reason. Moves record to `EXCEPTION` status.

---

## M-Pesa Transaction Fields

| Field | Description |
|---|---|
| M-Pesa Receipt | Safaricom transaction code (e.g. `QHJ1234XY`) |
| Phone | Sender phone number |
| Amount | Received amount in KES |
| Date | Transaction timestamp |
| Status | Current reconciliation status |
| Matched Invoice | Linked invoice number (if matched) |
