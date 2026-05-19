# Quotes & Shipments

---

## Quotes

**Route:** `/dashboard/sales?tab=quotes`  
**Permission required:** `sales.view`

### What It Does

Quotes allows the sales team to send formal price proposals to customers before converting to a confirmed sales order. Each quote has an expiry date and can be accepted (converted to SO) or rejected.

![Quotes tab](../../../screenshots/captured/module-ui/sales/sales/quotes-tab.png)
*Quotes tab showing quote list with validity dates, conversion status, and customer details.*

### Quote Lifecycle

```
Quote created → Sent to customer → Accepted → Converted to Sales Order
                                → Rejected / Expired → Closed
```

---

## Shipments

**Route:** `/dashboard/sales?tab=shipments`  
**Permission required:** `sales.view`

### What It Does

Shipments is the dispatch board for the warehouse team. It tracks each shipment from pick list creation through packing and dispatching to the customer.

![Shipments tab](../../../screenshots/captured/module-ui/sales/sales/shipments-tab.png)
*Shipments tab showing shipment list with pick progress, status badges, and carrier information.*

### Shipment List Columns

| Column | Description |
|---|---|
| Shipment No | Unique reference; clickable → shipment detail |
| Sales Order | Linked SO number |
| Customer | Customer name |
| Warehouse | Dispatch warehouse |
| Scheduled | Scheduled dispatch date |
| Dispatched | Actual dispatch date |
| Picked | `{picked_lines}/{total_lines}` pick progress |
| Status | Status badge |
| Carrier | Freight carrier name |

### Shipment Status Values

| Status | Badge Colour |
|---|---|
| `PENDING` | Blue |
| `PICKING` | Yellow |
| `PACKED` | Blue |
| `DISPATCHED` | Green |
| `DELIVERED` | Green |
| `CANCELLED` | Red |

### Dispatch Board Stats

KPI counts shown above the table:
- **Pending**: Awaiting pick start
- **In Progress**: Picking or packing
- **Dispatched**: Out for delivery

### Shipment Detail Page

Route: `/dashboard/sales/shipments/{id}`. Shows full line-by-line pick status, carrier tracking, and proof of delivery (POD) upload.

---

## Delivery

**Route:** `/dashboard/sales?tab=delivery`  
**Permission required:** `sales.view`

### What It Does

Delivery manages delivery scheduling and route optimisation for outbound shipments. It groups shipments by zone and date to create efficient delivery runs.

![Delivery tab](../../../screenshots/captured/module-ui/sales/sales/delivery-tab.png)
*Delivery tab showing delivery schedule with route grouping and vehicle assignment.*
