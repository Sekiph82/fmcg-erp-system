# Sales History & Sessions

---

## Sales History

**Route:** `/dashboard/pos?tab=sales`  
**Permission required:** `sales.view`

### What It Does

The Sales tab lists all completed POS transactions with line items, payment details, cashier, customer (if assigned), and sale status. Authorized users can void a sale.

![POS Sales tab](../../../screenshots/captured/module-ui/pos/pos/sales-tab.png)
*Sales tab showing sale list with sale number, date, cashier, items, payment method, and total.*

### Sale Fields

| Field | Description |
|---|---|
| `sale_no` | Auto-generated sale reference |
| `session_id` | Register session this sale belongs to |
| `cashier_name` | Cashier who processed the sale |
| `customer_name` | Assigned customer (optional) |
| `payment_method` | CASH · MPESA · CARD · SPLIT |
| `status` | COMPLETED or VOIDED |
| `subtotal` | Pre-discount, pre-tax total |
| `discount_total` | Total discount applied |
| `tax_total` | Total VAT collected |
| `sale_total` | Net amount charged |
| `amount_paid` | Amount tendered |
| `change_given` | Change returned (CASH only) |
| `mpesa_ref` | M-Pesa transaction reference |

### Sale Line Fields

| Field | Description |
|---|---|
| `product_name` | Product sold |
| `product_sku` | Product SKU |
| `qty` | Quantity |
| `unit_price` | Price per unit |
| `discount_pct` | Discount % applied |
| `tax_rate` | VAT rate % |
| `line_total` | Calculated line total |

### Voiding a Sale

Authorized users can void a completed sale. Voiding:
- Sets `status` to `VOIDED`
- Does not delete the record
- Reverses inventory deduction (if inventory integration is active)

API: `POST /api/v1/pos/sales/{id}/void`

---

## Register Sessions

**Route:** `/dashboard/pos?tab=sessions`  
**Permission required:** `sales.view`

### What It Does

The Sessions tab shows the register session log. Each session records opening float, all sales within the session, expected cash, actual closing cash, and any over/short difference.

![POS Sessions tab](../../../screenshots/captured/module-ui/pos/pos/sessions-tab.png)
*Sessions tab showing session list with register ID, cashier, open/close times, float, sales total, and cash difference.*

### Session Fields

| Field | Description |
|---|---|
| `session_no` | Auto-generated session reference |
| `register_id` | Register this session belongs to |
| `cashier_name` | Cashier who opened the session |
| `status` | OPEN or CLOSED |
| `opened_at` | Session open timestamp |
| `closed_at` | Session close timestamp |
| `opening_float` | Cash float at open |
| `closing_cash` | Actual cash counted at close |
| `expected_cash` | Calculated: float + cash sales |
| `cash_difference` | `closing_cash − expected_cash` |
| `total_sales` | Total revenue in this session |
| `total_transactions` | Number of sale transactions |

### Session Status

| Status | Meaning |
|---|---|
| `OPEN` | Register is active and selling |
| `CLOSED` | Session reconciled and closed |

### POS Dashboard KPIs (Terminal Top Bar)

| KPI | Description |
|---|---|
| Today Sales Count | Number of sales today |
| Today Sales Total | Revenue total today |
| Today Cash Total | Cash payment total today |
| Today M-Pesa Total | M-Pesa payment total today |
| Today Card Total | Card payment total today |
| Open Sessions | Currently open register sessions |
| Avg Basket Value | Average sale total today |
