# POS Terminal

**Route:** `/dashboard/pos?tab=pos`  
**Permission required:** `sales.view`

## What It Does

The POS Terminal is a split-screen interface: product grid on the left, cart on the right. The cashier searches for products by name or SKU, adds them to the cart, adjusts quantities, and processes payment. A register session must be open before selling.

![POS Terminal tab](../../../screenshots/captured/module-ui/pos/pos/terminal-tab.png)
*POS Terminal showing product grid (left) and cart panel (right) with totals and payment button.*

## Terminal Layout

### Left Panel — Product Grid

- Search bar: filters by product name or SKU (live filter, shows up to 40 results)
- Product cards showing: SKU, name, selling price
- Click card to add to cart (disabled when no session open)
- Today's stats banner: sale count and total revenue

### Right Panel — Cart

- Cart items list with quantity controls (+ / −) and remove button
- Line total per item
- Subtotal, discount, and tax (VAT) breakdown
- **Total** (bold, large)
- `Pay Now` button — opens Payment modal
- `Clear Cart` button — empties the cart

## Register Session

A session must be open to sell. Session status shown in the top bar:
- Green badge: `{REGISTER-ID} — OPEN`
- Red badge: `NO OPEN SESSION`

### Opening a Session

Click `Open Register`:

![Open Register modal](../../../screenshots/captured/module-ui/pos/terminal/open-session-modal.png)
*Open Register modal.*

| Field | Description |
|---|---|
| Register ID | Register identifier (e.g. REGISTER-1) |
| Opening Float (KES) | Cash float counted into the drawer |

API: `POST /api/v1/pos/sessions` with `{ register_id, opening_float }`

### Closing a Session

Click `Close Register` (visible only when a session is open):

| Field | Description |
|---|---|
| Actual Cash in Drawer (KES) | Physical cash counted at close |
| Notes | Any reconciliation notes |

API: `POST /api/v1/pos/sessions/{id}/close` with `{ closing_cash, notes }`

The system calculates:
- **Expected Cash** = opening float + cash sales
- **Cash Difference** = actual − expected (positive = over, negative = short)

## Cart Line Calculation

For each cart line:

| Field | Default | Description |
|---|---|---|
| `qty` | 1 | Quantity |
| `unit_price` | `product.selling_price` | Price per unit |
| `discount_pct` | 0 | Discount percentage |
| `tax_rate` | 16 | VAT rate (%) |
| `line_total` | `qty × unit_price × (1 − disc/100) × (1 + tax/100)` | Calculated total |

Cart totals:
- **Subtotal** = sum of `qty × unit_price` (pre-discount, pre-tax)
- **Discount** = sum of `qty × unit_price × discount_pct / 100`
- **Tax (VAT)** = calculated on discounted amount
- **Total** = subtotal − discount + tax

## Payment

Click `Pay Now` to open the Payment modal. Fields:

| Field | Description |
|---|---|
| Payment Method | CASH · MPESA · CARD |
| Amount Received | Cashier enters amount given by customer |
| M-Pesa Reference | Required for MPESA method |
| Change | Auto-calculated for CASH (amount received − total) |

Click `Complete Sale` to post the transaction.

API: `POST /api/v1/pos/sales` with cart lines and payment details.

### Payment Methods

| Value | Description |
|---|---|
| `CASH` | Physical cash — change calculated |
| `MPESA` | M-Pesa mobile money — reference required |
| `CARD` | Card payment |
| `SPLIT` | Split payment across methods |

## Sale Receipt

After successful payment, a receipt banner appears in the cart panel showing:
- Sale number (`sale_no`)
- Total amount
- Change given (for CASH)
