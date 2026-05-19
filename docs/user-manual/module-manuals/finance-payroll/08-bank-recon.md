# Bank Reconciliation & Bank API

---

## Bank Reconciliation

**Route:** `/dashboard/finance?tab=bank-recon`  
**Permission required:** `finance.view`

### What It Does

Bank Reconciliation matches ERP cashbook entries to bank statement lines. It identifies cleared items, unmatched transactions, and timing differences between the bank statement and the internal ledger.

![Bank Recon tab](../../../screenshots/captured/module-ui/finance-payroll/finance/bank-recon-tab.png)
*Bank Reconciliation tab within the Finance workspace.*

![Bank Reconciliation dashboard](../../../screenshots/captured/module-ui/finance-payroll/bank-reconciliation/bank-recon-dashboard.png)
*Bank Reconciliation standalone dashboard showing statement import, matching, and open items.*

### Reconciliation Workflow

```
Import bank statement (CSV/OFX)
    → ERP auto-matches statement lines to cashbook entries
    → Finance reviews unmatched items
    → Manual match or mark as exception
    → Period balance confirmed
    → Reconciliation locked/closed
```

### Bank Recon Sub-pages

| Page | Route | Purpose |
|---|---|---|
| Statements | `/dashboard/bank-reconciliation/statements` | Uploaded bank statements |
| Import | `/dashboard/bank-reconciliation/import` | Upload new bank statement file |
| Accounts | `/dashboard/bank-reconciliation/accounts` | Accounts linked for reconciliation |
| Balance | `/dashboard/bank-reconciliation/balance` | Closing balance confirmation |
| Open Items | `/dashboard/bank-reconciliation/open-items` | Unreconciled statement lines |
| Rules | `/dashboard/bank-reconciliation/rules` | Auto-match rules configuration |
| Reports | `/dashboard/bank-reconciliation/reports` | Reconciliation summary reports |
| AI Assist | `/dashboard/bank-reconciliation/ai` | AI-suggested matches for review |
| M-Pesa | `/dashboard/bank-reconciliation/mpesa` | M-Pesa statement reconciliation |

---

## Bank API

**Route:** `/dashboard/finance?tab=bank-api`  
**Permission required:** `finance.view`

### What It Does

Bank API manages direct bank feed connections. Connected accounts automatically sync transaction data from the bank into the ERP, eliminating manual statement imports for supported banks.

![Bank API tab](../../../screenshots/captured/module-ui/finance-payroll/finance/bank-api-tab.png)
*Bank API tab within the Finance workspace.*

![Bank API page](../../../screenshots/captured/module-ui/finance-payroll/bank-api/bank-api-page.png)
*Bank API connections dashboard showing active connections, sync status, and KPI tiles.*

![Bank API dropdowns](../../../screenshots/captured/module-ui/finance-payroll/bank-api/bank-api-dropdowns.png)
*New Bank Connection form showing Currency and API Type dropdowns expanded.*

### New Bank Connection Form

Always visible on the page (not a modal).

| Field | Label | Required | Notes |
|---|---|---|---|
| `bank_name` | Bank Name | Yes | e.g. KCB Bank Kenya |
| `account_name` | Account Name | Yes | Internal account label |
| `account_number` | Account Number | Yes | Bank account number |
| `bank_code` | Bank Code | No | Short bank identifier |
| `currency` | Currency | No | KES / USD / EUR / GBP (select) |
| `api_type` | API Type | Yes | MOCK / DIRECT (select) |
| `credentials_ref` | Credentials Ref | No | Vault key or credentials reference |

### API Type Options

| Type | Description |
|---|---|
| `MOCK` | Simulated sync for testing and demo environments |
| `DIRECT` | Live connection to bank adapter (requires credentials) |

### Currency Options

KES · USD · EUR · GBP

### Connection Actions

| Action | Description |
|---|---|
| Sync | Fetch latest transactions from the bank for this connection |
| Deactivate | Disable a connection without deleting history |

### Bank Transaction Fields

| Field | Description |
|---|---|
| Date | Transaction timestamp |
| Description | Bank-provided narrative |
| Amount | Transaction amount |
| Direction | CREDIT (green) / DEBIT (red) |
| Classification | Category assigned by auto-classify rules |
| Status | Sync status |
