# Production User Manual

**Audience:** Production Supervisors, Production Operators, Shift Leaders  
**URLs:** `/dashboard/production`, `/dashboard/shop-floor`, `/dashboard/bom`  
**Permission required:** `production.view`, `production.create`

---

## Your Role

You plan and execute manufacturing. You create production orders, record output, report material usage, log downtime, and track batch numbers.

---

## Pages You Use

| Page | URL | What you do there |
|---|---|---|
| Production workspace | /dashboard/production | All production activities |
| Shop Floor terminal | /dashboard/shop-floor | Operator job card confirm/reject |
| BOM & Formula | /dashboard/bom | View/maintain bill of materials |
| Recipes | /dashboard/recipes | Product formulas |
| Planning | /dashboard/planning | MRP and production schedule |
| Maintenance | /dashboard/maintenance | Machine breakdown logging |

---

## Screenshot

![Production Workspace](../screenshots/captured/038_production.png)

---

## Daily Production Workflow

```
Morning:
1. Check production plans for today  →  Production → Plans tab
2. Confirm material availability      →  Check with warehouse
3. Release production orders          →  Production → Orders tab → Release

During production:
4. Operators confirm on Shop Floor terminal
5. Record any downtime events         →  Production → Downtime tab
6. Record waste and yield             →  Production → Waste & Yield tab

End of shift:
7. Confirm production output          →  Production → Execution tab → Confirm
8. Record materials consumed          →  Production → Material Flow tab
9. Assign batch/lot numbers           →  Production → Batch & Lots tab
10. Submit QC check results           →  Production → Quality Control tab
```

---

## Create a Production Order

1. Go to `/dashboard/production?tab=orders`
2. Click **+ New Order**
3. Fill in:
   - **Product**: select the finished good
   - **Quantity**: planned output quantity
   - **Unit**: KG, Litres, Units, etc.
   - **Planned Date**: when production should happen
   - **BOM Version**: select the correct recipe/formula version
   - **Work Center**: machine or production line
4. Click **Save as Draft**
5. Review the material requirements (auto-calculated from BOM)
6. Click **Release** when ready to start

![Production — Orders Tab](../screenshots/captured/039_production-orders.png)

**Status flow:** Draft → Released → In Progress → Completed

---

## Confirm Production Output (Execution)

1. Go to `/dashboard/production?tab=execution`
2. Find the active production order
3. Enter:
   - Actual quantity produced
   - Actual time taken
   - Any quality notes
4. Click **Confirm Output**

Or use the Shop Floor terminal (tablet/touchscreen):
1. Go to `/dashboard/shop-floor?tab=terminal`
2. Select your job card
3. Click **Start** when beginning
4. Click **Complete** when done
5. Enter actual quantity

![Shop Floor — Terminal](../screenshots/captured/051_shop-floor-terminal.png)

---

## Record Material Consumption

1. Go to `/dashboard/production?tab=material-flow`
2. Select the production order
3. Each BOM component shows planned vs actual quantity
4. Enter actual quantities used
5. Click **Post Materials**

If a material substitution was needed, enter the alternate material and quantity.

![Production — Material Flow Tab](../screenshots/captured/041_production-material-flow.png)

---

## Record Downtime

1. Go to `/dashboard/production?tab=downtime`
2. Click **+ Log Downtime**
3. Fill in:
   - Machine / Work Center
   - Start time / End time
   - Downtime reason (select from list or enter free text)
4. Click **Save**

Common downtime reasons: breakdown, changeover, cleaning, waiting for materials, utility failure.

---

## Assign Batch / Lot Numbers

1. Go to `/dashboard/production?tab=batch-lots`
2. Select the completed production order
3. Click **Assign Batch Number**
4. System generates a batch number (or enter manually)
5. Enter: manufacture date, best-before date
6. Click **Confirm**

Batch numbers link production to quality inspections and traceability.

---

## View BOM (Bill of Materials)

1. Go to `/dashboard/bom`
2. Search for the product
3. Select the active BOM version
4. View all components, quantities per batch, units

To check if a substitute is allowed:
- BOM → Substitutes tab → find the component

![BOM Workspace](../screenshots/captured/053_bom.png)

---

## Production Planning (MRP)

1. Go to `/dashboard/planning?tab=mrp`
2. Click **Run MRP**
3. Review suggested production orders
4. Accept or reject each suggestion
5. Accepted suggestions become draft production orders

---

## OEE Dashboard (Supervisors)

1. Go to `/dashboard/production?tab=oee`
2. View Overall Equipment Effectiveness for each line
3. Target: OEE > 85%
4. Drilldown: Availability, Performance, Quality breakdown

---

## Common Mistakes

| Mistake | How to Avoid |
|---|---|
| Creating order without checking stock | Always check materials tab before releasing |
| Forgetting to post materials | Set a end-of-shift reminder; materials tab shows "unposted" warning |
| Wrong BOM version | Always check BOM version date matches today's recipe |
| Not logging downtime | Log within 15 minutes; reasons are needed for OEE accuracy |

---

## Troubleshooting

**Problem:** Cannot release production order — "Insufficient stock"  
**Solution:** Check inventory for the material → raise purchase request or production order for intermediate

**Problem:** BOM shows wrong components  
**Solution:** Check BOM version effective date → contact admin or NPD team to update

**Problem:** Shop Floor terminal says "No active orders"  
**Solution:** Supervisor must release the production order first from the Production → Orders tab

---

## Training Checklist

- [ ] Can create a production order from BOM
- [ ] Can release a production order
- [ ] Can confirm output in Execution tab
- [ ] Can post material consumption in Material Flow tab
- [ ] Can log a downtime event with reason code
- [ ] Can assign a batch number to finished goods
- [ ] Can view OEE for their production line
- [ ] Can use the Shop Floor terminal to confirm a job card
