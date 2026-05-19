# Cashbook

**Route:** `/dashboard/finance?tab=cashbook`  
**Permission required:** `finance.view`  
**Internal tabs:** Accounts, Transactions, Journal

---

## What It Does

Cashbook manages cash, bank, and M-Pesa accounts. It records incoming receipts and outgoing payments against specific accounts, and maintains a journal of auto-generated and manual double-entry records.

![Cashbook tab](../../../screenshots/captured/module-ui/finance-payroll/finance/cashbook-tab.png)
*Cashbook entry point within the Finance workspace.*

---

## Accounts Tab

**Tab key:** `accounts`

![Cashbook — Accounts tab](../../../screenshots/captured/module-ui/finance-payroll/cashbook/accounts-tab.png)
*Accounts tab showing all cash/bank/M-Pesa accounts with balances, type badges, and bank details.*

Lists all configured cash accounts.

### Account List Columns

| Column | Field | Notes |
|---|---|---|
| Name | `name` | Account display name |
| Type | `account_type` | CASH (gray) / BANK (green) / MPESA (blue) |
| Bank / Number | `bank_name`, `account_number` | Bank name and account number joined with · |
| Opening | `opening_balance` | Balance at account creation |
| Current Balance | `current_balance` | Live running balance |
| Status | `is_active` | Active (green) / Inactive (gray) |
| Transactions | link | Click to open that account's transactions |

### New Account Modal

Button: **New Account** (always visible, top-right)

![New Cash Account modal](../../../screenshots/captured/module-ui/finance-payroll/cashbook/new-account-modal.png)
*New Cash Account modal — Name, Type, Bank Name, Account No., Currency, and Opening Balance fields.*

![Account Type dropdown](../../../screenshots/captured/module-ui/finance-payroll/cashbook/account-type-dropdown.png)
*Account Type dropdown showing all options: Cash, Bank, M-Pesa.*

| Field | Label | Required | Notes |
|---|---|---|---|
| `name` | Name | Yes | Account display name |
| `account_type` | Type | Yes | Cash / Bank / M-Pesa (select) |
| `bank_name` | Bank Name | No | Bank institution name |
| `account_number` | Account No. | No | Bank account number |
| `currency` | Currency | No | Default: KES |
| `opening_balance` | Opening Balance | No | Default: 0 |

---

## Transactions Tab

**Tab key:** `transactions`

![Cashbook — Transactions tab](../../../screenshots/captured/module-ui/finance-payroll/cashbook/transactions-tab.png)
*Transactions tab showing transaction history for a selected account, with direction badges and clear action.*

Available only after selecting an account from the Accounts tab. Tab label changes to "Transactions — {account name}".

### Transaction List Columns

| Column | Field | Notes |
|---|---|---|
| Date | `transaction_date` | Transaction date |
| Description | `description` | Free text description |
| Direction | `direction` | RECEIPT (green) / PAYMENT (red) badge |
| Amount | `amount` | Transaction amount |
| Status | `status` | CLEARED (green) / PENDING (yellow) / FAILED (red) / REVERSED (gray) |
| Reference | `reference` | External reference number |
| Action | — | "Clear" button appears only when status is PENDING |

### Add Transaction Modal

Button: **Add Transaction** — visible only when an account is selected.

| Field | Label | Required | Notes |
|---|---|---|---|
| `transaction_date` | Date | Yes | Date picker, defaults to today |
| `direction` | Direction | Yes | Receipt (in) / Payment (out) |
| `amount` | Amount (KES) | Yes | Numeric |
| `description` | Description | No | Free text |
| `reference` | Reference | No | Cheque or ref number |
| `status` | Status | Yes | Cleared / Pending |
| `mpesa_phone` | M-Pesa Phone | If MPESA | Only shown for MPESA-type accounts |
| `mpesa_receipt` | M-Pesa Receipt | If MPESA | M-Pesa transaction code |

---

## Journal Tab

**Tab key:** `journal`

![Cashbook — Journal tab](../../../screenshots/captured/module-ui/finance-payroll/cashbook/journal-tab.png)
*Journal tab showing double-entry journal entries with entry number, date, source module, debit, credit, and posted status.*

Lists all double-entry journal entries. Entries are generated automatically by ERP transactions (sales invoices, purchase invoices, payroll) and can also be created manually.

### Journal List Columns

| Column | Field | Notes |
|---|---|---|
| Entry No | `entry_no` | Unique sequential reference |
| Date | `entry_date` | Posting date |
| Description | `description` | Journal description |
| Module | `source_module` | ERP module that generated the entry |
| Debit | `total_debit` | Total debit amount |
| Credit | `total_credit` | Total credit amount |
| Posted | `is_posted` | Posted (green) / Draft (yellow) badge |
