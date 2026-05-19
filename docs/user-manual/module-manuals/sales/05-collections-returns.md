# Collections & Returns

---

## Collections

**Route:** `/dashboard/sales?tab=collections`  
**Permission required:** `sales.view`

### What It Does

Collections records cash, mobile money, and cheque receipts from customers. Collection records are reconciled against outstanding invoices to update invoice payment status.

![Collections tab](../../../screenshots/captured/module-ui/sales/sales/collections-tab.png)
*Collections tab showing collection records with payment method, amount, and reconciliation status.*

### Collection Workflow

```
Customer pays (cash / M-Pesa / cheque / bank transfer)
    → Collection record created
    → Allocated to one or more invoices
    → Invoice outstanding balance reduced
    → Invoice marked PARTIALLY_PAID or PAID
```

### Collection Fields

| Field | Description |
|---|---|
| Collection No | Unique reference |
| Customer | Paying customer |
| Collection Date | Date payment was received |
| Method | CASH / MPESA / CHEQUE / BANK_TRANSFER |
| Amount | Amount received |
| Reference | Cheque number or M-Pesa code |
| Allocated | Amount applied to invoices |
| Unallocated | Amount not yet applied |
| Status | PENDING / RECONCILED / PARTIAL |

---

## Returns

**Route:** `/dashboard/sales?tab=returns`  
**Permission required:** `sales.view`

### What It Does

Returns manages sales return transactions: when a customer sends goods back, a return record is created and a credit note is issued. Returns reduce inventory via a return receipt and reduce the customer outstanding balance via the credit note.

![Returns tab](../../../screenshots/captured/module-ui/sales/sales/returns-tab.png)
*Returns tab showing sales return records with reason codes, quantities, and credit note status.*

### Return Workflow

```
Customer initiates return
    → Sales Return created (linked to original SO/invoice)
    → Reason code assigned
    → Goods received at warehouse → inventory receipt posted
    → Credit Note issued → customer outstanding balance reduced
```

### Return Reason Codes

Common return reasons tracked:

| Code | Description |
|---|---|
| `DAMAGED` | Goods received damaged |
| `WRONG_ITEM` | Incorrect product shipped |
| `QUALITY` | Quality does not meet spec |
| `OVERSTOCK` | Customer returned excess stock |
| `EXPIRED` | Products past shelf life |

### Return Fields

| Field | Description |
|---|---|
| Return No | Unique reference |
| Original SO | Source sales order |
| Invoice No | Source invoice |
| Customer | Returning customer |
| Return Date | Date goods were returned |
| Reason | Return reason code |
| Lines | Returned products and quantities |
| Credit Note No | Issued credit note reference |
| Status | PENDING / RECEIVED / CREDITED |
