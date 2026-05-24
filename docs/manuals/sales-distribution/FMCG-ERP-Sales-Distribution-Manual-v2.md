# FMCG ERP — Sales & Distribution Manual v2

**Version:** 2.0 (post-recovery)  
**Date:** 2026-05-24  
**Audience:** Sales Managers, Sales Reps, Accounts Receivable, Distribution Managers, Van Sales Teams  
**Modules Covered:** Sales · Orders · Invoicing · Pricing · Contracts · Van Sales · Secondary Sales · Distributors · POS

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Sales Overview Dashboard](#2-sales-overview-dashboard)
3. [Sales Orders](#3-sales-orders)
4. [Customer Quotations](#4-customer-quotations)
5. [Invoicing](#5-invoicing)
6. [Delivery & Shipments](#6-delivery--shipments)
7. [Collections & Receivables](#7-collections--receivables)
8. [Returns](#8-returns)
9. [Pricing & Price Lists](#9-pricing--price-lists)
10. [Sales Contracts & Recurring Orders](#10-sales-contracts--recurring-orders)
11. [Van Sales](#11-van-sales)
12. [Secondary Sales & Distributors](#12-secondary-sales--distributors)
13. [Point of Sale (POS)](#13-point-of-sale-pos)
14. [Sales Reports](#14-sales-reports)
15. [Common Mistakes & Troubleshooting](#15-common-mistakes--troubleshooting)
16. [Related Modules](#16-related-modules)

---

## 1. Module Overview

**What it does:** Manages the complete order-to-cash cycle — from customer quotation through delivery, invoicing, and payment collection. Includes pricing management, van sales, distributor management, and POS.

**Who uses it:**
- Sales Manager — monitors KPIs, manages pricing and targets
- Sales Rep — creates quotations and orders for customers
- Accounts Receivable — manages invoices, collections, and reconciliation
- Distribution Manager — tracks deliveries and van sales
- Van Sales Agent — loads stock and captures orders on-the-go

**When to use it:**
- When creating a sales order for a customer
- When issuing a customer invoice
- When tracking outstanding receivables
- When setting prices or promotional pricing
- When processing a return or credit note

**Modules at a glance:**

| Feature | Route | Purpose |
|---------|-------|---------|
| Sales Hub | `/dashboard/sales` | Full sales workspace |
| POS | `/dashboard/pos` | Point of sale terminal |

![Sales Overview](../../user-manual/screenshots/captured/module-ui/sales/sales/overview-tab.png)
*Sales module overview showing KPIs: revenue, orders, collections, and outstanding.*

---

## 2. Sales Overview Dashboard

**Tab:** Overview

KPI cards at top:
- Total Revenue (period)
- Orders Raised
- Outstanding Receivables
- Average Order Value
- Orders by Status (chart)
- Top Products (chart)
- Top Customers (chart)

Use the date range picker to change the reporting period.

---

## 3. Sales Orders

**Tab:** Orders  
**Required permission:** `sales.orders.view`

### What it does
Create, track, and manage customer sales orders from entry through dispatch confirmation.

![Orders Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/orders-tab.png)
*Sales orders list with customer, order date, value, status, and delivery date.*

### Creating a Sales Order

Click **+ New Order**:

![New Order Modal](../../user-manual/screenshots/captured/module-ui/sales/orders/new-order-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Customer | Yes | Select from customer master |
| Order Date | Yes | Default today |
| Required Delivery Date | Yes | Customer's requested date |
| Delivery Address | Yes | Ship-to address (can differ from billing) |
| Payment Terms | Yes | Net terms from customer master (editable) |
| Price List | No | Override default price list |
| Currency | Yes | Transaction currency |
| Sales Rep | Yes | Assigned sales representative |
| Reference | No | Customer PO number |

After filling header, add line items:

| Line Field | Required | Notes |
|------------|----------|-------|
| Product | Yes | Finished good SKU |
| Quantity | Yes | Ordered quantity |
| Unit | Yes | Sales UOM |
| Unit Price | Yes | Auto-filled from price list; editable |
| Discount % | No | Line-level discount |
| VAT Code | Yes | Tax rate for this line |

**Order Status Flow:** `DRAFT → CONFIRMED → PICKING → DISPATCHED → DELIVERED → INVOICED → CLOSED`

**Dropdowns on order:**

![Order Dropdowns](../../user-manual/screenshots/captured/module-ui/sales/orders/order-dropdowns.png)
*Payment terms, currency, price list, and sales rep dropdowns.*

### Required Data Before Creating Orders
- Customer exists in Customers master with billing and delivery address
- Products exist with active price list entry or unit price configured
- Payment terms configured

---

## 4. Customer Quotations

**Tab:** Quotes

### What it does
Create price quotations for customers. Quote can be converted to a sales order upon customer acceptance.

![Quotes Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/quotes-tab.png)
*Quotations list with customer, expiry date, value, and status.*

**Quote Status Flow:** `DRAFT → SENT → ACCEPTED → CONVERTED_TO_ORDER` or `EXPIRED` or `REJECTED`

**Converting a quote:** Open quote → click **Convert to Order** → all lines transferred; quote status set to CONVERTED.

### Quote Validity
Set **Expiry Date** on the quote — after this date, quote status automatically moves to EXPIRED. Customer cannot accept an expired quote; rep must create a new quote.

---

## 5. Invoicing

**Tab:** Invoices

### What it does
Customer invoices — generated from sales orders upon delivery confirmation, or created manually.

![Invoices Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/invoices-tab.png)
*Invoices list with customer, invoice date, due date, amount, and payment status.*

**Invoice Status:** `DRAFT → POSTED → PARTIALLY_PAID → PAID → VOID`

### Creating an Invoice
From a sales order: click **Create Invoice** button on the order detail page. Invoice pre-filled with order lines.

Manual invoice: **+ New Invoice** on Invoices tab.

### Invoice Fields

| Field | Required | Notes |
|-------|----------|-------|
| Customer | Yes | Billing customer |
| Invoice Date | Yes | Accounting date |
| Due Date | Yes | Payment deadline (auto from payment terms) |
| Sales Order | No | Reference order |
| Lines | Yes | Products, qty, price, VAT |

### eTIMS Integration
For Kenyan tax compliance, posted invoices are submitted to KRA eTIMS. Status shown on invoice: `eTIMS: PENDING / SUBMITTED / ACCEPTED / REJECTED`. See Finance → eTIMS tab for submission log.

---

## 6. Delivery & Shipments

**Tabs:** Shipments · Delivery

### What it does
Track outbound delivery status from warehouse dispatch to customer receipt.

![Shipments Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/shipments-tab.png)
*Shipments — all outbound dispatch records with carrier, tracking, and status.*

![Delivery Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/delivery-tab.png)
*Delivery confirmation — mark deliveries as confirmed and record proof of delivery.*

**Delivery confirmation workflow:**
1. Dispatch creates shipment record
2. Driver delivers and obtains customer signature
3. Office updates delivery status to DELIVERED
4. System triggers invoice creation (if not already created)

---

## 7. Collections & Receivables

**Tab:** Collections

### What it does
Record customer payments against invoices. Track outstanding balances. Manage credit limits.

![Collections Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/collections-tab.png)
*Collections register — payments received, allocation to invoices, outstanding balances.*

**Payment allocation workflow:**
1. Customer makes payment (bank transfer, cheque, M-Pesa)
2. Open Collections → **+ New Collection**
3. Select customer and enter amount received
4. Allocate to specific invoices
5. Save — invoice status updates to PARTIALLY_PAID or PAID

**M-Pesa payments:** Reconcile via Finance → M-Pesa tab (automatic matching for payments above KES 1,000 if reference matches).

---

## 8. Returns

**Tab:** Returns

### What it does
Process customer returns — create return authorization, record returned goods, issue credit note.

![Returns Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/returns-tab.png)
*Returns register — return requests, reason codes, and credit note status.*

**Return workflow:**
1. Click **+ New Return**
2. Reference original sales order
3. Select products being returned and quantities
4. Assign reason code (Damaged / Wrong Product / Expired / Customer Changed Mind)
5. Submit → Warehouse receives returned goods
6. QC inspects returns
7. Credit note issued → applied against customer balance

---

## 9. Pricing & Price Lists

**Tabs:** Pricing · Price Lists · Dynamic Pricing

### What it does
Manage product pricing: standard price lists, promotional pricing, volume discounts, and dynamic pricing rules.

![Pricing Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/pricing-tab.png)
*Pricing overview — active price lists and rules summary.*

![Price Lists Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/price-lists-tab.png)
*Price lists — customer segment-specific or channel-specific price books.*

**Creating a Pricing Rule:**

![New Pricing Rule Modal](../../user-manual/screenshots/captured/module-ui/sales/pricing/new-pricing-rule-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Rule Name | Yes | Descriptive name |
| Price List | Yes | Applicable price list |
| Product | No | Leave blank for all products |
| Product Category | No | Category-level rule |
| Customer | No | Customer-specific price |
| Customer Group | No | Segment-level price |
| Min Quantity | No | Volume break trigger |
| Discount % | No | Percentage discount |
| Fixed Price | No | Override price (alternative to discount) |
| Valid From | Yes | Start date |
| Valid To | No | End date (blank = no expiry) |

![Dynamic Pricing Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/dynamic-pricing-tab.png)
*Dynamic pricing — time-based, season, or event-driven pricing adjustments.*

### Price List Priority
When multiple price lists apply: Customer-specific → Customer Group → Promotional → Standard. Most specific wins.

---

## 10. Sales Contracts & Recurring Orders

**Tabs:** Contracts · Recurring

### What it does
Manage long-term customer supply agreements and auto-generate recurring orders on schedule.

![Contracts Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/contracts-tab.png)
*Contracts — framework agreements with committed volumes and pricing.*

![Recurring Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/recurring-tab.png)
*Recurring orders — auto-schedule orders for subscriptions and regular customers.*

**Recurring order setup:**
1. Create recurring order template
2. Set frequency: Daily / Weekly / Monthly / Quarterly
3. Set start date and end date (or open-ended)
4. System auto-creates orders on schedule
5. Orders require confirmation before dispatch

---

## 11. Van Sales

**Tab:** Van Sales

### What it does
Manage pre-sell and cash van sales operations — van loading, route management, order capture, and end-of-day settlement.

![Van Sales Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/van-sales-tab.png)
*Van sales management — active vans, load sheets, and route status.*

**Van Sales workflow:**

1. **Van Loading** (`/dashboard/van-sales/vans/{id}`)
   - Open van record
   - Create load sheet — select products and quantities
   - Approve load → triggers warehouse pick
   - Van departs with physical stock

2. **Order Capture** (mobile or web)
   - Sales rep visits customer
   - Creates order against van stock
   - Cash or credit (within credit limit)

3. **End-of-Day Settlement**
   - Return unloaded stock
   - Reconcile cash collected
   - Upload invoices
   - System closes van route

---

## 12. Secondary Sales & Distributors

**Tabs:** Secondary · Distributors · Field Sales

### What it does
Track secondary sell-through from distributors to retailers. Manage distributor performance and targets.

![Secondary Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/secondary-tab.png)
*Secondary sales — distributor sell-through reporting and target vs. actual.*

![Distributors Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/distributors-tab.png)
*Distributor register — territory, credit limit, and performance metrics.*

![Field Sales Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/field-sales-tab.png)
*Field sales management — rep territory assignments and visit tracking.*

---

## 13. Point of Sale (POS)

**Route:** `/dashboard/pos`  
**Required permission:** `pos.view`

### What it does
Direct retail selling terminal — scan or search products, apply promotions, process cash/card/M-Pesa payments, print receipts.

![POS Overview](../../user-manual/screenshots/captured/138_pos.png)
*POS terminal with product search, basket, payment, and receipt.*

**POS workflow:**
1. Open POS session (assigns cash drawer)
2. Scan or search product → adds to basket
3. Apply discount or promotion if applicable
4. Select payment method: Cash / Card / M-Pesa / Credit
5. Process payment
6. Print or email receipt
7. Close session at end of day → settlement report

**POS requires:**
- Product price configured in active price list
- POS session open by cashier
- M-Pesa integration configured (Finance → Integrations) for M-Pesa payments

---

## 14. Sales Reports

**Tab:** Reports · Margin

### What it does
Sales performance analytics — revenue by product, customer, region, and period. Margin analysis.

![Reports Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/reports-tab.png)
*Sales reports — revenue trends, customer rankings, product performance.*

![Margin Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/margin-tab.png)
*Margin analysis — gross margin by product, customer, and order.*

**Commissions Tab:**

![Commissions Tab](../../user-manual/screenshots/captured/module-ui/sales/sales/commissions-tab.png)
*Sales commissions — calculated per rep based on sales achieved vs. target.*

---

## 15. Common Mistakes & Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Order won't confirm | Customer credit limit exceeded | Increase credit limit or require prepayment |
| Price not auto-filling | No active price list for this product/customer | Add product to price list or create customer-specific rule |
| Invoice not submitting to eTIMS | Missing customer KRA PIN | Add customer PIN in Customers master → Tax details |
| Delivery status stuck | Carrier not linked to shipment | Assign carrier and tracking number on shipment record |
| Return won't create credit note | Original invoice not POSTED | Invoice must be posted before return can generate credit note |
| M-Pesa payment not matching | Reference number mismatch | Manually match in Finance → M-Pesa → Unmatched tab |
| Van sales won't settle | Unconfirmed orders remain | Confirm or cancel all open orders before EOD settlement |

---

## 16. Related Modules

| This Action | Connects To |
|-------------|-------------|
| Sales order confirmed | Inventory → Pick Wave (WMS) |
| Invoice posted | Finance → Accounts Receivable |
| Payment collected | Finance → Bank Reconciliation |
| Return received | Inventory → Stock (increase) + Quality → Inspection |
| Van loading | Inventory → Stock Issue (van load) |
| eTIMS submission | Finance → Tax / eTIMS tab |
| Distributor order | CRM → Customer Account |

---

*End of Sales & Distribution Manual v2*
