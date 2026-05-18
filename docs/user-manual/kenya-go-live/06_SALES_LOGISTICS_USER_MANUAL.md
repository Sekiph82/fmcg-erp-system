# Sales & Logistics User Manual

**Audience:** Sales Representatives, Invoicing Clerks, Van Sales Drivers, Logistics Coordinator  
**URLs:** `/dashboard/sales`, `/dashboard/logistics`  
**Permission required:** `sales.view`, `sales.create`

---

## Your Role

You manage customer orders, raise invoices, coordinate deliveries, and settle van sales. Revenue and collections depend on your accuracy.

---

## Pages You Use

| Page | URL | What you do there |
|---|---|---|
| Sales workspace | /dashboard/sales | All sales activities |
| Logistics workspace | /dashboard/logistics | Fleet, shipments, containers |
| CRM workspace | /dashboard/crm | Customer relationships |

---

## Screenshot

> Screenshot pending: Sales workspace — Orders tab

---

## Sales Order Workflow

```
1. Receive customer order (phone, portal, field rep)
2. Create sales order in system
3. Check credit limit and pricing
4. Confirm order (triggers warehouse pick)
5. Dispatch → delivery note generated
6. Invoice raised
7. Customer pays (M-Pesa, bank, cash)
8. Payment reconciled → order closed
```

---

## Create a Sales Order

1. Go to `/dashboard/sales?tab=orders`
2. Click **+ New Order**
3. Fill in:
   - Customer (select from list or search by name/code)
   - Delivery address
   - Order date
   - Required delivery date
4. Add line items:
   - Product
   - Quantity
   - Price (auto-fills from price list; edit if special)
   - Discount % (if authorised — may require approval)
5. Check total and VAT
6. Click **Confirm Order**

> Screenshot pending: Sales — Orders tab with order list

---

## Customer Master

Add a new customer:
1. Sales → Customers tab
2. Click **+ New Customer**
3. Fill in:
   - Name
   - KRA PIN (required for eTIMS invoice)
   - Contact name, phone, email
   - Delivery address
   - Credit limit (KES)
   - Payment terms (e.g., Net 30)
   - Price list (assign appropriate tier)
4. Save

> Screenshot pending: Sales — Customers tab

---

## Raise an Invoice

After goods are dispatched:
1. Sales → Invoices tab
2. Find the sales order
3. Click **Generate Invoice**
4. Check: items, prices, VAT, customer KRA PIN
5. Click **Post Invoice**
6. Download PDF or send by email
7. System sends to eTIMS (KRA) for e-invoicing compliance

> Screenshot pending: Sales — Invoices tab

---

## Van Sales Workflow

Pre-selling (morning):
1. Sales → Van Sales tab
2. Create a **Van Load**:
   - Select vehicle/driver
   - Add products and quantities to load
3. Print the loading order
4. Warehouse loads the van

Selling route:
5. Driver visits customers
6. On return: Sales → Van Sales → Settlement
7. Enter: products sold by customer, cash collected, returns
8. System creates invoices and updates stock

> Screenshot pending: Sales — Van Sales tab

---

## Price Lists

1. Sales → Price Lists tab
2. View existing price lists (Retail, Wholesale, Distributor, etc.)
3. To update: select price list → edit prices → effective date
4. Changes apply to all customers on that price list

**Never change a price list during active van sales — wait until settlement is done.**

---

## Track Shipments

1. Go to `/dashboard/logistics?tab=shipments`
2. View all outbound shipments with status
3. Click shipment to see:
   - Products, quantities, driver, vehicle
   - Delivery confirmation status
4. Mark as **Delivered** when customer confirms receipt

---

## Collections (Payments)

Record customer payment:
1. Sales → Collections tab
2. Find the open invoice
3. Click **Record Payment**
4. Select method: M-Pesa, bank transfer, cheque, cash
5. Enter amount and reference
6. Click **Post**

M-Pesa payments can be reconciled automatically (requires integration to be configured).

---

## Returns Management

Customer returns a product:
1. Sales → Returns tab
2. Click **+ New Return**
3. Reference original invoice
4. Enter returned products and quantities
5. Reason: expired, damaged, wrong product, etc.
6. Credit note is generated automatically
7. Goods go back to inventory as quarantine (pending QC check)

---

## Common Mistakes

| Mistake | How to Avoid |
|---|---|
| Wrong price on invoice | Check price list assignment for the customer before invoicing |
| Invoice without KRA PIN | Customer KRA PIN is mandatory for eTIMS — add it to customer master |
| Van load quantity wrong | Confirm with warehouse at loading time |
| Payment recorded twice | Check invoice status before recording — "Paid" invoices are closed |

---

## Troubleshooting

**Problem:** Cannot confirm sales order — "Credit limit exceeded"  
**Solution:** Contact credit controller to increase customer credit limit or get advance payment

**Problem:** Invoice shows wrong tax  
**Solution:** Check customer VAT status and product VAT group; update if incorrect

**Problem:** Van Sales settlement shows mismatch  
**Solution:** Recount physical returns and cash; check for unentered damages

---

## Training Checklist

- [ ] Can create a sales order from customer request
- [ ] Can check customer credit limit
- [ ] Can generate and post an invoice
- [ ] Can create a van load and record settlement
- [ ] Can record a customer payment
- [ ] Can process a customer return
- [ ] Can view shipment status
- [ ] Can view and update price lists
- [ ] Knows eTIMS requirement (KRA PIN on every invoice)
