# Supply Chain Module — Overview

**Manual:** FMCG ERP Supply Chain Module Manual  
**Audience:** Procurement Officers, Warehouse Managers, Logistics Coordinators, Inventory Controllers  
**Scope:** All supply chain screens, workflows, and import formats

---

## What This Module Covers

| Subsystem | Route | Purpose |
|-----------|-------|---------|
| Procurement | `/dashboard/procurement` | Purchase requisitions, orders, RFQ, suppliers, subcontracting |
| Inventory | `/dashboard/inventory` | Stock ledger, entries, issues, transfers, adjustments |
| Warehouses | `/dashboard/warehouses` | Warehouse master data, WMS zones and locations |
| WMS | `/dashboard/wms` (embedded in Warehouses) | Zones, locations, handling units, pick waves, quarantine |
| Logistics | `/dashboard/logistics` | International shipments, containers, customs clearance, fleet |

---

## Navigation

All Supply Chain modules are accessible from the left sidebar. Tab-level access is controlled by permissions.

Quick paths:
- New PR: **Sidebar → Procurement → Purchase Requests tab → New PR**
- Receive stock: **Sidebar → Inventory → Stock Entry (IN) tab**
- New warehouse: **Sidebar → Warehouses → Add Warehouse**
- Quarantine lot: **Sidebar → Warehouses → WMS/Putaway tab → Quarantine tab → Quarantine Stock**
- Track shipment: **Sidebar → Logistics → Overview tab**

---

## Permission Map

| Permission | Grants Access To |
|------------|-----------------|
| `procurement.view` | All procurement tabs (PRs, POs, RFQ, deliveries, etc.) |
| `inventory.view` | Stock ledger, movements, cycle count, shelf life, traceability |
| `inventory.adjust` | Adjust stock quantity for warehouses in scope |
| `inventory.adjust_all` | Adjust stock across all warehouses |
| `inventory.receive_all` | Receive stock into any warehouse |
| `inventory.dispatch_all` | Issue stock from any warehouse |
| `inventory.transfer_all` | Transfer stock between any warehouses |
| `inventory.delete` | Delete zero-quantity stock records in scope |
| `inventory.delete_all` | Delete zero-quantity stock records across all warehouses |
| `logistics.view` | All logistics tabs |

Warehouse-scoped permissions use `canPerformInScope("warehouse", warehouse_id, action)` — a user with `inventory.adjust` (without `_all`) can only adjust stock in warehouses they are scoped to.

---

## Chapters in This Manual

1. [Purchase Requisitions](./01-purchase-requisitions.md) — PR creation, line items, status workflow
2. [Purchase Orders](./02-purchase-orders.md) — PO fields, PR conversion, status, GRN
3. [RFQ & Supplier Quotations](./03-rfq.md) — Request for quotation, responses, comparison
4. [Deliveries & Goods Receipt](./04-deliveries.md) — GRN creation, receipt against PO
5. [Suppliers](./05-suppliers.md) — Supplier master data, portal
6. [Blanket Agreements & Reorder](./06-blanket-reorder.md) — Blanket PAs, reorder policies, suggestions
7. [Inventory Stock Ledger](./07-inventory-stock.md) — Stock summary, entry, issue, transfer, adjust
8. [Inventory Movements & Traceability](./08-movements.md) — Movement ledger, traceability, serials, valuation
9. [Warehouses](./09-warehouses.md) — Warehouse types, create, manage
10. [WMS — Zones, Locations & Operations](./10-wms.md) — Zones, bins, handling units, pick waves, quarantine
11. [Logistics & International Shipments](./11-logistics.md) — Shipments, containers, customs, arrivals, fleet
