# Sales Orders

**Route:** `/dashboard/sales?tab=orders`  
**Permission required:** `sales.view`

---

## What It Does

Sales Orders manages the creation, confirmation, allocation, and fulfilment lifecycle of customer orders. Each order has a header (customer, dates, currency) and one or more order lines (product, quantity, price, discount).

![Sales Orders tab](../../../screenshots/captured/module-ui/sales/sales/orders-tab.png)
*Orders tab showing sales orders list with status badges, delivery dates, and total values.*

---

## Orders List Columns

| Column | Description |
|---|---|
| Order No | Unique reference; clickable → order detail page |
| Customer | Customer name |
| Order Date | Date order was created |
| Delivery Date | Requested delivery date; red if past due |
| Lines | Count of order lines |
| Total Value | Order total in order currency |
| Status | Status badge |

Rows show "View only" label when the user has read-only access to that order.

---

## Create Sales Order Modal

Button: **+ New Order** (top-right)

![Create Sales Order modal](../../../screenshots/captured/module-ui/sales/orders/new-order-modal.png)
*Create Sales Order modal showing header fields: Order No, Customer, dates, Warehouse, Currency, and order lines section.*

![New Order dropdowns expanded](../../../screenshots/captured/module-ui/sales/orders/order-dropdowns.png)
*New Order form with Currency dropdown expanded showing all options: USD, EUR, GBP, JPY, CNY, SGD.*

### Header Fields

| Field | Label | Required | Notes |
|---|---|---|---|
| `order_no` | Order No | Yes | Free text reference |
| `customer_id` | Customer | Yes | Select from customer list |
| `order_date` | Order Date | No | Defaults to today |
| `requested_delivery_date` | Requested Delivery | Yes | Expected delivery date |
| `warehouse_id` | Warehouse | No | Optional dispatch warehouse |
| `currency` | Currency | Yes | USD / EUR / GBP / JPY / CNY / SGD |
| `notes` | Notes | No | Free text |

### Order Line Fields

| Field | Label | Required | Notes |
|---|---|---|---|
| `product_id` | Product | Yes | Select from product catalogue |
| `ordered_quantity` | Quantity | Yes | Numeric |
| `unit` | Unit | Yes | PCS / BOX / CARTON / PALLET / KG / L |
| `unit_price` | Unit Price | No | Price per unit |
| `discount_pct` | Discount % | No | 0–100 |
| `tax_rate` | Tax Rate | No | Applied tax rate percentage |
| `notes` | Notes | No | Line-level note |

Multiple lines can be added with **+ Add Line**. Lines can be removed individually.

---

## Order Status Workflow

```
DRAFT → CONFIRMED → ALLOCATED → PICKING → SHIPPED → INVOICED
                                                   ↓
                                             CANCELLED (from any stage)
```

- **DRAFT**: Created, not yet confirmed
- **CONFIRMED**: Accepted by sales team
- **ALLOCATED**: Stock reserved in warehouse
- **PICKING**: Pick list generated, warehouse fulfilling
- **SHIPPED**: Goods dispatched to customer
- **INVOICED**: Sales invoice raised

---

## Order Detail Page

Accessible by clicking Order No. Route: `/dashboard/sales/orders/{id}`. Shows full order with all lines, status history, and linked shipments/invoices.
