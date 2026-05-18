# Warehouse & Inventory User Manual

**Audience:** Storekeepers, Receiving Clerks, WMS Operators  
**URLs:** `/dashboard/inventory`, `/dashboard/warehouses`, `/dashboard/wms`  
**Permission required:** `inventory.view`, `inventory.create`

---

## Your Role

You receive and dispatch goods, maintain accurate stock records, count stock, and manage warehouse locations. Accurate inventory is critical for production planning and sales order fulfilment.

---

## Pages You Use

| Page | URL | What you do there |
|---|---|---|
| Inventory workspace | /dashboard/inventory | Stock levels and movements |
| Warehouses & WMS | /dashboard/warehouses | Warehouse setup, bin locations |
| WMS workspace | /dashboard/wms | Picking, putaway, quarantine |
| Materials | /dashboard/materials | Raw material master |
| Products | /dashboard/products | Finished goods master |

---

## Screenshot

> Screenshot pending: Inventory workspace — stock tab

---

## Daily Warehouse Workflow

```
Receiving (morning):
1. Check purchase deliveries expected today  →  Procurement → Deliveries tab
2. Receive goods against the PO              →  Procurement → Deliveries → Receive
3. Put away to correct bin location          →  WMS → Locations

During the day:
4. Issue materials to production             →  Production will request via Material Flow
5. Dispatch finished goods for sales         →  Sales → Shipments tab

End of day:
6. Review stock movements                    →  Inventory → Movements tab
7. Check items expiring soon                 →  Inventory → Shelf Life tab
8. Update cycle count if scheduled           →  Inventory → Cycle Count tab
```

---

## Check Current Stock Levels

1. Go to `/dashboard/inventory?tab=stock`
2. View stock by product/material and warehouse location
3. Use search/filter to find specific items
4. Columns: SKU, Description, On Hand, Reserved, Available, Location, Unit

> Screenshot pending: Inventory — Stock tab

**Available = On Hand minus Reserved**

Stock is reserved when a production order or sales order has been released.

---

## Receive Goods (Goods Receipt Note)

When a delivery arrives:

1. Go to `/dashboard/procurement?tab=deliveries`
2. Find the relevant purchase order
3. Click **Receive Delivery**
4. Enter:
   - Actual quantity received (may differ from PO)
   - Lot/batch number (from supplier label)
   - Expiry date (for perishables)
   - Condition: OK / Damaged / Rejected
5. Click **Confirm Receipt**
6. Stock is automatically added to inventory

If goods are rejected or quarantined:
- Select condition **Quarantine**
- Goods go to WMS → Quarantine tab
- Notify QC to inspect

> Screenshot pending: Procurement — Deliveries tab with receive form

---

## Put Away to Bin Location (WMS)

After receiving:
1. Go to `/dashboard/wms?tab=locations`
2. Find the received material
3. Click **Put Away**
4. Scan or select the bin location
5. Confirm

> Screenshot pending: WMS — Locations tab

---

## Issue Stock to Production

Production will request materials automatically via the production order.  
If manual issuance needed:
1. Go to `/dashboard/inventory?tab=movements`
2. Click **+ Manual Issue**
3. Select: Material, Quantity, Destination (Work Center / Production Order)
4. Click **Post**

---

## Record a Stock Movement (Transfer)

Move stock between locations or warehouses:
1. Inventory → Movements tab
2. Click **+ Transfer**
3. From: source location
4. To: destination location
5. Quantity and unit
6. Click **Post Transfer**

---

## Shelf Life and FEFO (First Expired, First Out)

1. Go to `/dashboard/inventory?tab=shelf-life`
2. Items are sorted by nearest expiry date
3. Items expiring within 30 days are highlighted in orange
4. Items expired are highlighted in red
5. Always pick the earliest expiry batch first (FEFO)

> Screenshot pending: Inventory — Shelf Life tab

**Important for Kenya food production:** Expiry tracking is required for regulatory compliance. Never issue an expired batch to production.

---

## Cycle Count (Physical Stock Count)

1. Go to `/dashboard/inventory?tab=cycle-count`
2. Click **+ New Count**
3. Select warehouse and item range
4. Print the count sheet (or use mobile/tablet)
5. Count physically and enter the actual quantities
6. Click **Post Count**
7. System calculates variance (actual vs system quantity)
8. Supervisor approves the count; inventory is adjusted

> Screenshot pending: Inventory — Cycle Count tab

---

## Traceability

Track a batch forward (where did it go?) or backward (where did it come from?):
1. Inventory → Traceability tab
2. Enter batch/lot number or product
3. View full genealogy: supplier batch → production → finished goods → sales order

---

## Quarantine Management

Items placed in quarantine (damaged delivery, failed QC):
1. WMS → Quarantine tab
2. View all quarantined items
3. After QC inspection:
   - **Release**: moves stock back to normal
   - **Reject/Dispose**: writes off the stock (requires manager approval)

---

## Common Mistakes

| Mistake | How to Avoid |
|---|---|
| Receiving without checking PO | Always find the PO before clicking Receive |
| Not entering expiry date | Required for all perishable materials — check supplier label |
| Wrong bin location | Confirm with WMS map before putting away |
| Issuing stock without production order | Never issue manually unless production supervisor has approved |

---

## Troubleshooting

**Problem:** Stock shows negative  
**Solution:** A movement was posted against insufficient stock. Check Movements tab for the erroneous entry. Contact admin to reverse if needed.

**Problem:** Cannot find a PO in Deliveries tab  
**Solution:** Confirm with procurement that PO has been released/approved. Only released POs appear in Deliveries.

**Problem:** Batch not found in system  
**Solution:** Goods may not have been received yet. Check with procurement.

---

## Training Checklist

- [ ] Can view stock levels and available stock
- [ ] Can receive goods against a purchase order
- [ ] Can put away to the correct bin location
- [ ] Can post a stock transfer between locations
- [ ] Can run and post a cycle count
- [ ] Understands FEFO and can pick the earliest expiry batch
- [ ] Can view and manage quarantined items
- [ ] Can trace a batch number forward and backward
