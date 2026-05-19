# Sales & Distribution Module — Overview

**Primary route:** `/dashboard/sales`  
**Permission required:** `sales.view`

---

## What This Module Covers

Sales & Distribution manages the complete order-to-cash cycle: sales order creation, customer management, pricing, shipment, invoicing, collections, and returns. It also includes field sales tools, distributor management, van sales operations, and secondary sales tracking.

| Tab | Key | Purpose |
|---|---|---|
| Overview | `overview` | KPI dashboard and recent orders |
| Orders | `orders` | Sales order creation and lifecycle |
| Invoices | `invoices` | Invoice issuance and payment tracking |
| Customers | `customers` | Customer master data |
| Quotes | `quotes` | Quotations before order conversion |
| Shipments | `shipments` | Pick, pack, and dispatch board |
| Delivery | `delivery` | Delivery scheduling and route management |
| Collections | `collections` | Cash and mobile money collection records |
| Returns | `returns` | Sales return and credit note processing |
| Pricing | `pricing` | Pricing rules and promotions |
| Price Lists | `price-lists` | Customer group price lists |
| Dynamic Pricing | `dynamic-pricing` | Rule-based automatic price adjustments |
| Contracts | `contracts` | Commercial agreements |
| Recurring | `recurring` | Scheduled repeat order templates |
| Commissions | `commissions` | Sales rep commission management |
| Secondary Sales | `secondary` | Distributor sell-through tracking |
| Van Sales | `van-sales` | Mobile route sales |
| Distributors | `distributors` | Distributor network |
| Field Sales | `field-sales` | Territory and visit management |
| Margin | `margin` | Product and customer profitability |
| Customer Portal | `portal` | Self-service portal configuration |
| Reports | `reports` | Sales analytics and performance |

---

## Order-to-Cash Flow

```
Quotation (optional)
    → Sales Order created (DRAFT)
    → Order confirmed (CONFIRMED)
    → Stock allocated (ALLOCATED)
    → Pick list generated (PICKING)
    → Shipment packed and dispatched (SHIPPED)
    → Sales Invoice issued (INVOICED)
    → Payment collected → Invoice marked PAID
    → Optional: Sales Return → Credit Note
```
