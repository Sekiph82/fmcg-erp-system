# Procurement User Manual

**Audience:** Purchasing Officers, Procurement Manager  
**URL:** `/dashboard/procurement`  
**Permission required:** `procurement.view`, `procurement.create`

---

## Your Role

You source materials, raise purchase orders, manage suppliers, and oversee goods receipt. You ensure production never runs out of raw materials.

---

## Pages You Use

| Page | URL | What you do there |
|---|---|---|
| Procurement workspace | /dashboard/procurement | All procurement activities |
| Suppliers workspace | /dashboard/suppliers | Supplier master data |

---

## Screenshot

> Screenshot pending: Procurement workspace overview

---

## Procurement Workflow

```
1. Receive purchase request from production/warehouse
2. Identify supplier and get price
3. Raise Request for Quotation (RFQ) if needed
4. Create Purchase Order
5. Send PO to supplier
6. Receive goods confirmation from warehouse
7. Match invoice to GRN
8. Approve payment
```

---

## Create a Purchase Request

When production or warehouse needs materials:

1. Go to `/dashboard/procurement?tab=purchase-requests`
2. Click **+ New Request**
3. Fill in:
   - Material/Product
   - Quantity required
   - Required by date
   - Justification
4. Click **Submit for Approval**

Or production/warehouse staff can submit requests themselves — they appear in your queue.

> Screenshot pending: Procurement — Purchase Requests tab

---

## Create a Purchase Order

1. Go to `/dashboard/procurement?tab=orders`
2. Click **+ New PO**
3. Fill in:
   - Supplier (select from list)
   - Delivery warehouse
   - Expected delivery date
4. Add line items:
   - Material/product
   - Quantity
   - Unit price (KES)
   - VAT type
5. Click **Save**
6. Click **Send to Supplier** (or print and email manually)

**Status flow:** Draft → Confirmed → Sent → Partially Received → Fully Received → Invoiced

> Screenshot pending: Procurement — Orders tab with PO list

---

## Supplier Management

1. Go to `/dashboard/suppliers`
2. **Create supplier:**
   - Click **+ New Supplier**
   - Name, KRA PIN, payment terms, delivery lead time
   - Contact person, phone, email
   - Bank account for payment
3. **Rate supplier:** after each delivery, rate quality, timeliness, documentation

> Screenshot pending: Suppliers workspace

---

## Request for Quotation (RFQ)

For large purchases or new items:
1. Procurement → RFQ tab
2. Click **+ New RFQ**
3. Add materials and quantities
4. Add suppliers to send RFQ to
5. Click **Send RFQ**
6. Suppliers respond; compare quotes in system
7. Select winning supplier → **Convert to PO**

---

## Goods Receipt Confirmation

When warehouse receives goods against your PO:
1. Procurement → Deliveries tab
2. Open the delivery note
3. Review: actual quantity vs ordered quantity
4. Click **Approve Receipt** if correct
5. System posts stock to inventory

If short delivery: partial receipt is posted; remaining balance shows as open.  
If damaged goods: warehouse will mark as quarantine; QC inspects.

> Screenshot pending: Procurement — Deliveries tab

---

## AI Procurement Suggestions

The system suggests what to order based on stock levels and production plans:
1. Procurement → AI Suggestions tab
2. Review suggested items, quantities, and recommended suppliers
3. Click **Accept** to create a draft PO
4. Review and confirm the PO

---

## Landed Cost (Import Orders)

For imported materials (add duties, freight, insurance to unit cost):
1. Procurement → Landed Cost tab
2. Select the PO
3. Add costs: freight, insurance, customs duty, port charges
4. Allocate to lines by weight, quantity, or value
5. System recalculates unit cost and posts to inventory valuation

---

## Common Mistakes

| Mistake | How to Avoid |
|---|---|
| Ordering from wrong supplier | Check preferred supplier in supplier master |
| Wrong unit (KG vs litres) | Verify unit with materials master before PO |
| Not matching invoice to GRN | Always match before approving payment |
| PO not sent to supplier | Check status = "Sent" before assuming supplier has it |

---

## Troubleshooting

**Problem:** Supplier not in system  
**Solution:** Create supplier first in Suppliers workspace → then link to PO

**Problem:** PO approval required but approver not responding  
**Solution:** Escalate to manager; check approval workflow in Admin → Approvals

**Problem:** Goods received but stock not updated  
**Solution:** Warehouse must confirm delivery in Deliveries tab

---

## Training Checklist

- [ ] Can create a purchase request
- [ ] Can create a purchase order with correct pricing
- [ ] Can send PO to supplier
- [ ] Can confirm goods receipt
- [ ] Can create and send an RFQ
- [ ] Can compare RFQ responses and convert to PO
- [ ] Can view AI procurement suggestions
- [ ] Can add landed cost to imported goods
- [ ] Knows supplier rating workflow
