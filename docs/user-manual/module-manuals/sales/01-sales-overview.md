# Sales Overview

**Route:** `/dashboard/sales?tab=overview`  
**Permission required:** `sales.view`

---

## What It Does

The Sales Overview tab is the order-to-cash command centre. It displays six KPI tiles, an overdue invoice alert panel, and a list of recent orders.

![Sales Overview tab](../../../screenshots/captured/module-ui/sales/sales/overview-tab.png)
*Sales Overview showing KPI tiles, overdue alert banner, quick links, and recent orders list.*

---

## KPI Tiles

| Tile | Description | Colour |
|---|---|---|
| Total Orders | All sales orders created | Gray |
| Order Value | Total value of confirmed orders | Blue |
| Total Invoiced | Sum of all invoice totals | Gray |
| Collected | Payments received to date | Green |
| Outstanding | Order Value minus Collected | Orange |
| Overdue Invoices | Count of invoices past due date | Red if > 0 |

All tiles are clickable and navigate to the relevant sub-page.

---

## Overdue Alert Panel

Appears when overdue invoices exist. Shows up to 5 overdue invoices with: invoice number, customer, days overdue, and outstanding amount. Colour: red-50 background.

---

## Quick Links

| Link | Destination |
|---|---|
| Manage Orders | `/dashboard/sales/orders` |
| Customers | `/dashboard/sales/customers` |
| Dispatch Board | `/dashboard/sales/shipments` |
| Invoice & AR | `/dashboard/sales/invoices` |

---

## Recent Orders

Lists the 8 most recent sales orders with: order number (clickable → detail), customer name, delivery date, value, and status badge.

### Sales Order Status Values

| Status | Badge Colour |
|---|---|
| `DRAFT` | Blue |
| `CONFIRMED` | Blue |
| `ALLOCATED` | Blue |
| `PICKING` | Yellow |
| `SHIPPED` | Green |
| `INVOICED` | Green |
| `CANCELLED` | Red |
