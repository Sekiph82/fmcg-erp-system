# Distribution — Van Sales, Field Sales, Distributors & Secondary Sales

---

## Van Sales

**Route:** `/dashboard/sales?tab=van-sales`  
**Permission required:** `sales.view`

### What It Does

Van Sales supports route-based mobile selling where sales reps load vans with stock and sell directly to customers on a route. The van acts as a mobile warehouse — stock is pre-loaded at departure and reconciled at route close.

![Van Sales tab](../../../screenshots/captured/module-ui/sales/sales/van-sales-tab.png)
*Van Sales tab showing van routes with loaded inventory, sales recorded on route, and end-of-day reconciliation.*

### Van Sales Workflow

```
Route planned and van loaded (stock issued from warehouse)
    → Rep drives route, records sales against customers
    → Sales recorded as sales orders (status: INVOICED immediately)
    → Unsold stock returned at route close
    → Cash/M-Pesa collections submitted
    → End-of-day reconciliation confirms stock and cash
```

---

## Field Sales

**Route:** `/dashboard/sales?tab=field-sales`  
**Permission required:** `sales.view`

### What It Does

Field Sales manages sales rep territories, customer visit scheduling, and outlet coverage. Reps use the field sales module to log customer visits, capture orders, and track distribution targets.

![Field Sales tab](../../../screenshots/captured/module-ui/sales/sales/field-sales-tab.png)
*Field Sales tab showing rep territories, visit schedules, and outlet coverage metrics.*

### Field Sales Concepts

| Concept | Description |
|---|---|
| Territory | Geographic area assigned to a rep |
| Route | Ordered sequence of outlets to visit |
| Outlet | Retail or wholesale customer on a route |
| Visit | Logged customer call with activity recorded |
| Distribution target | % of outlets expected to carry each SKU |

---

## Distributors

**Route:** `/dashboard/sales?tab=distributors`  
**Permission required:** `sales.view`

### What It Does

Distributors manages the network of third-party distributors who purchase in bulk and sell into sub-channels (retail, hotels, etc.). Each distributor has an assigned territory, product range, and performance targets.

![Distributors tab](../../../screenshots/captured/module-ui/sales/sales/distributors-tab.png)
*Distributors tab showing distributor list with territory assignment, credit terms, and performance metrics.*

---

## Secondary Sales

**Route:** `/dashboard/sales?tab=secondary`  
**Permission required:** `sales.view`

### What It Does

Secondary Sales tracks sell-through data from distributors to their end customers. This gives the manufacturer visibility into actual market demand versus primary (manufacturer-to-distributor) sales.

![Secondary Sales tab](../../../screenshots/captured/module-ui/sales/sales/secondary-tab.png)
*Secondary Sales tab showing distributor sell-through reports with product, volume, and outlet breakdown.*

### Primary vs Secondary Sales

| Type | Description |
|---|---|
| Primary Sales | Manufacturer → Distributor |
| Secondary Sales | Distributor → Retail / Wholesale / Consumer |

Secondary data is collected via distributor reports, van sales uploads, or field rep market surveys.
