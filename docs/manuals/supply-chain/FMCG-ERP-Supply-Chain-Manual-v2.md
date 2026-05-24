# FMCG ERP — Supply Chain Manual v2

**Version:** 2.0 (post-recovery)  
**Date:** 2026-05-24  
**Audience:** Procurement Officers, Warehouse Managers, Inventory Controllers, Logistics Coordinators  
**Modules Covered:** Procurement · Suppliers · Inventory · Warehouses · WMS · Logistics

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Procurement](#2-procurement)
3. [Suppliers](#3-suppliers)
4. [Inventory Management](#4-inventory-management)
5. [Inventory Movements](#5-inventory-movements)
6. [Cycle Count](#6-cycle-count)
7. [Shelf Life Management](#7-shelf-life-management)
8. [Warehouses](#8-warehouses)
9. [WMS (Warehouse Management System)](#9-wms-warehouse-management-system)
10. [Logistics](#10-logistics)
11. [Common Mistakes & Troubleshooting](#11-common-mistakes--troubleshooting)
12. [Related Modules](#12-related-modules)

---

## 1. Module Overview

**What it does:** Manages the full inbound supply chain — from purchase requisitions through supplier management, goods receipt, inventory control, warehouse operations, and outbound logistics.

**Who uses it:**
- Procurement Officer — raises purchase requisitions and purchase orders, manages RFQs
- Warehouse Manager — controls warehouse zones, locations, and stock movements
- Inventory Controller — monitors stock levels, cycle counts, shelf life
- Logistics Coordinator — tracks shipments, fleet, and delivery schedules

**When to use it:**
- When reordering raw materials or packaging
- When receiving goods from suppliers
- When performing a physical stock count
- When managing warehouse locations and pick waves
- When tracking inbound/outbound shipments

**Modules at a glance:**

| Module | Route | Purpose |
|--------|-------|---------|
| Procurement | `/dashboard/procurement` | PRs, POs, RFQs, deliveries |
| Suppliers | `/dashboard/suppliers` | Supplier master and performance |
| Inventory | `/dashboard/inventory` | Stock levels and movements |
| Warehouses | `/dashboard/warehouses` | Warehouse configuration |
| WMS | `/dashboard/wms` | Zones, locations, pick waves |
| Logistics | `/dashboard/logistics` | Shipments and fleet |

![Supply Chain Overview](../../user-manual/screenshots/captured/029_procurement.png)
*Procurement module overview.*

---

## 2. Procurement

**Route:** `/dashboard/procurement`  
**Required permission:** `procurement.view`

### What it does
Full procurement lifecycle: purchase requisitions → purchase orders → goods receipt → supplier invoicing. Includes RFQs, blanket agreements, auto-reorder suggestions, subcontracting, and landed cost.

### Tabs

| Tab | Purpose |
|-----|---------|
| Purchase Requests | Internal purchase requisitions |
| Orders | Purchase orders sent to suppliers |
| RFQ | Request for Quotation |
| Deliveries | Goods receipt and delivery tracking |
| Suppliers | Quick supplier lookup |
| Blanket Agreements | Framework contracts with volume commitments |
| Reorder Policies | Min/max reorder rules per item |
| Suggestions | AI/rule-based reorder suggestions |
| Subcontracting | Outsourced production orders |
| Landed Cost | Import duty and freight allocation |
| Supplier Portal | External portal access management |

![Purchase Requests Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/purchase-requests-tab.png)
*Purchase Requests tab showing all PRs with status, requester, and priority.*

### Creating a Purchase Requisition

Click **+ New Request**:

![New PR Modal](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/new-pr-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Item | Yes | Product or material to purchase |
| Quantity | Yes | Required quantity |
| Unit | Yes | UOM |
| Required By Date | Yes | Needed-by date |
| Priority | Yes | Low / Medium / High / Critical |
| Department | Yes | Requesting department |
| Notes | No | Free text justification |

**PR Status Flow:** `DRAFT → SUBMITTED → APPROVED → PO_CREATED → CLOSED`

After approval, PR can be converted to a Purchase Order (click **Create PO** on the PR detail).

### Purchase Orders Tab

![Orders Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/orders-tab.png)
*Purchase Orders tab — all POs with supplier, value, and delivery status.*

**Creating a Purchase Order:**

![New PO Modal](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/new-po-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Supplier | Yes | Select from approved suppliers |
| Order Date | Yes | Date of order |
| Required Delivery Date | Yes | Expected delivery |
| Payment Terms | Yes | e.g. NET30, COD |
| Currency | Yes | KES, USD, EUR, etc. |
| Delivery Location | Yes | Destination warehouse |
| Line Items | Yes | Product, qty, unit price per line |

**PO Status Flow:** `DRAFT → SENT → ACKNOWLEDGED → PARTIAL_DELIVERY → DELIVERED → INVOICED → CLOSED`

### RFQ Tab

![RFQ Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/rfq-tab.png)
*Request for Quotation — send RFQ to multiple suppliers and compare responses.*

**Creating an RFQ:**

![New RFQ Modal](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/new-rfq-modal.png)

1. Create RFQ with item list
2. Select suppliers to invite (multi-select)
3. Set response deadline
4. System sends email invitations
5. Suppliers respond via portal or manual entry
6. Compare quotes side-by-side → award to winning supplier → auto-creates PO

### Deliveries Tab

![Deliveries Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/deliveries-tab.png)
*Deliveries — expected and received goods, GRN creation, discrepancy reporting.*

**Goods Receipt workflow:**
1. Select pending delivery from list
2. Enter received quantities per line (can be partial)
3. Record batch/lot numbers if applicable
4. Confirm receipt → creates Goods Receipt Note (GRN)
5. GRN triggers inventory increase and supplier invoice matching

### Blanket Agreements Tab

![Blanket Agreements Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/blanket-agreements-tab.png)
*Blanket agreements — framework contracts with committed volumes and pricing.*

![New Blanket Modal](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/new-blanket-modal.png)

### Reorder Policies Tab

![Reorder Policies Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/reorder-policies-tab.png)
*Reorder policies — set min/max stock levels and reorder quantities per item-location.*

![New Reorder Policy Modal](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/new-reorder-policy-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Item | Yes | Material or product |
| Location | Yes | Warehouse/location |
| Min Stock | Yes | Reorder trigger level |
| Max Stock | Yes | Order-up-to level |
| Reorder Qty | Yes | Fixed quantity per order |
| Supplier | No | Preferred supplier |
| Lead Time (days) | No | Supplier lead time |

### Suggestions Tab

![Suggestions Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/suggestions-tab.png)
*Auto-generated reorder suggestions based on policies, MRP, and demand forecast.*

Click **Generate Suggestions** to refresh. Review and approve to convert to PRs.

### Subcontracting Tab

![Subcontracting Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/subcontracting-tab.png)
*Subcontracting orders — send components to external processor, receive finished goods.*

### Landed Cost Tab

![Landed Cost Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/landed-cost-tab.png)
*Landed cost allocation — distribute import duty, freight, and insurance across PO lines.*

**Allocation methods:** By Value / By Weight / By Volume / By Qty / Equal

### Supplier Portal Tab

![Supplier Portal Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/procurement/supplier-portal-tab.png)
*Manage external supplier portal access credentials and permissions.*

---

## 3. Suppliers

**Route:** `/dashboard/suppliers`  
**Required permission:** `suppliers.view`

### What it does
Supplier master data management — contact details, payment terms, certification status, and performance tracking.

![Suppliers List](../../user-manual/screenshots/captured/module-ui/supply-chain/suppliers/suppliers-list-tab.png)
*Suppliers list with name, category, rating, and status.*

### Adding a Supplier

Click **+ Add Supplier**:

![Add Supplier Modal](../../user-manual/screenshots/captured/module-ui/supply-chain/suppliers/add-supplier-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Supplier Name | Yes | Legal entity name |
| Category | Yes | Raw Material / Packaging / Service / Utility |
| Contact Person | Yes | Primary contact name |
| Email | Yes | Primary email |
| Phone | No | Primary phone |
| Country | Yes | Country of operation |
| Payment Terms | Yes | Default terms for this supplier |
| Currency | Yes | Transaction currency |
| Tax/VAT Number | No | Registration number |
| Bank Details | No | For payment processing |
| Rating | No | 1–5 star performance rating |
| Notes | No | Free text |

### Required Before First PO
- Supplier must be created and status set to **Active**
- Payment terms and currency must be set
- At least one contact email required (for PO delivery and RFQ invitations)

---

## 4. Inventory Management

**Route:** `/dashboard/inventory`  
**Required permission:** `inventory.view`

### What it does
Real-time stock visibility — current stock levels by product, location, batch, and lot. Entry (receipts), issues (consumption), and transfers.

### Inventory Stock Tab

![Stock Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/inventory/stock-tab.png)
*Current stock tab — item, location, quantity on hand, reserved, available.*

**Columns:**
| Column | Description |
|--------|-------------|
| Item | Product/material name and SKU |
| Location | Warehouse and bin location |
| On Hand | Physical quantity in stock |
| Reserved | Quantity allocated to work orders or sales orders |
| Available | On Hand minus Reserved |
| Unit | UOM |
| Batch/Lot | Batch number if tracked |
| Expiry | Best-before/expiry date if tracked |

### Stock Entry Tab

![Entry Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/inventory/entry-tab.png)
*Stock entry — manual stock receipt not linked to PO (adjustments, opening balances).*

| Field | Required | Notes |
|-------|----------|-------|
| Item | Yes | Product or material |
| Location | Yes | Destination location |
| Quantity | Yes | Quantity to add |
| Unit | Yes | UOM |
| Reference | No | Internal reference or document number |
| Batch/Lot | No | Batch number |
| Expiry Date | No | For shelf-life tracked items |
| Notes | No | Reason for entry |

### Stock Issue Tab

![Issue Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/inventory/issue-tab.png)
*Stock issue — record consumption or removal from stock.*

Use for: material consumption not triggered by production order, samples, damaged stock write-off.

### Stock Transfer Tab

![Transfer Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/inventory/transfer-tab.png)
*Inter-warehouse or inter-location stock transfer.*

| Field | Required |
|-------|----------|
| From Location | Yes |
| To Location | Yes |
| Item | Yes |
| Quantity | Yes |
| Transfer Date | Yes |

---

## 5. Inventory Movements

**Route:** `/dashboard/inventory/movements`

### What it does
Full transaction history of every stock movement — entries, issues, transfers, production consumption, goods receipts.

![Movements List](../../user-manual/screenshots/captured/module-ui/supply-chain/movements/movements-list.png)
*All inventory transactions with date, type, item, quantity, and reference.*

**Filter by:** Date range, Movement Type, Item, Location, Reference

**Movement types:**
| Type | Trigger |
|------|---------|
| RECEIPT | Goods receipt from PO delivery |
| ISSUE | Manual issue or production consumption |
| TRANSFER | Location-to-location move |
| ADJUSTMENT | Manual correction |
| RETURN | Supplier return or customer return |
| WRITE_OFF | Disposal of expired or damaged stock |

---

## 6. Cycle Count

**Route:** `/dashboard/inventory/cycle-count`  
**Required permission:** `inventory.view`

### What it does
Physical stock count management — schedule counts, record actual quantities, generate variance reports, and approve adjustments.

![Cycle Count Dashboard](../../user-manual/screenshots/captured/module-ui/supply-chain/cycle-count/cycle-count-dashboard.png)
*Cycle count dashboard showing count schedule, pending counts, and variance summary.*

### Cycle Count Workflow

1. **Schedule count** — select location(s) and items to count
2. **Print count sheet** — blind sheet (no expected quantities shown to counters)
3. **Record actual counts** — enter physical counts per location/item
4. **Review variance** — system highlights discrepancies > tolerance threshold
5. **Approve adjustments** — manager approves; stock adjusted automatically
6. **Close count** — marks count cycle as complete

### Best Practices
- Schedule ABC analysis — count A-items (high value/fast-moving) monthly, B quarterly, C annually
- Use blind count sheets — do not show expected quantities to counters
- Require two-counter verification for high-value items
- Investigate variances > ±2% before approving adjustment

---

## 7. Shelf Life Management

**Route:** `/dashboard/inventory/shelf-life`

### What it does
Tracks expiry dates for perishable raw materials and finished goods. Flags stock approaching expiry for action.

![Shelf Life Dashboard](../../user-manual/screenshots/captured/module-ui/supply-chain/shelf-life/shelf-life-dashboard.png)
*Shelf life dashboard — items expiring within 30/60/90 days.*

**Alert thresholds:** Configurable per item — default: RED (0–30 days), AMBER (31–60 days), GREEN (>60 days)

**Required:** Items must have `shelf_life_tracked = true` in product master and expiry date entered at receipt.

---

## 8. Warehouses

**Route:** `/dashboard/warehouses`  
**Required permission:** `warehouses.view`

### What it does
Configure physical warehouses — location, type, capacity. Parent container for WMS zones and bin locations.

![Warehouses List](../../user-manual/screenshots/captured/module-ui/supply-chain/warehouses/warehouses-list-tab.png)
*Warehouses list with name, location, type, and capacity.*

### Adding a Warehouse

Click **+ Add Warehouse**:

![Add Warehouse Modal](../../user-manual/screenshots/captured/module-ui/supply-chain/warehouses/add-warehouse-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Name | Yes | e.g. "Main Warehouse Nairobi" |
| Code | Yes | Short code e.g. "NBO-MAIN" |
| Type | Yes | Raw Material / Finished Goods / Bonded / Cold Chain |
| Address | Yes | Physical address |
| Capacity (m²) | No | Floor area |
| Manager | No | Assigned warehouse manager |
| Is Active | Yes | Default true |

---

## 9. WMS (Warehouse Management System)

**Route:** `/dashboard/wms`  
**Required permission:** `wms.view`

### What it does
Fine-grained warehouse management — define zones and bin locations within warehouses, manage pick waves, handle quarantine stock.

### Tabs

| Tab | Purpose |
|-----|---------|
| Zones | Warehouse zones (areas within warehouse) |
| Locations | Individual bin locations within zones |
| Handling Units | Pallets, cases, and containerization |
| Pick Waves | Batch pick operations for outbound |
| Quarantine | Segregated hold area for suspect stock |

### Zones Tab

![Zones Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/wms/zones-tab.png)
*Zones list — named areas within a warehouse (e.g. Receiving, Bulk Storage, Picking Face).*

**Creating a Zone:**

![New Zone Modal](../../user-manual/screenshots/captured/module-ui/supply-chain/wms/new-zone-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Warehouse | Yes | Parent warehouse |
| Zone Name | Yes | e.g. "Bulk Storage A" |
| Zone Code | Yes | e.g. "BULK-A" |
| Zone Type | Yes | Receiving / Storage / Picking / Dispatch / Quarantine |
| Temperature Range | No | For cold chain zones |

### Locations Tab

![Locations Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/wms/locations-tab.png)
*Individual bin locations — row, aisle, level, bin identifiers.*

**Creating a Location:**

![New Location Modal](../../user-manual/screenshots/captured/module-ui/supply-chain/wms/new-location-modal.png)

Location code convention: `[Zone]-[Row][Aisle][Level][Bin]` e.g. "BULK-A-A01-01"

### Handling Units Tab

![Handling Units Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/wms/handling-units-tab.png)
*Pallets and cases — track mixed-SKU handling units through the warehouse.*

### Pick Waves Tab

![Pick Waves Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/wms/pick-waves-tab.png)
*Pick waves — batch multiple pick orders into a single wave for efficiency.*

**Pick wave workflow:**
1. Select pending pick orders (from sales orders or work orders)
2. Click **Create Wave** — system generates optimized pick sequence by location
3. Assign pickers
4. Confirm picks — updates inventory in real-time
5. Complete wave — triggers dispatch or production release

### Quarantine Tab

![Quarantine Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/wms/quarantine-tab.png)
*Quarantine — hold stock pending QC clearance or investigation.*

**Quarantine stock:**

![Quarantine Stock Modal](../../user-manual/screenshots/captured/module-ui/supply-chain/wms/quarantine-stock-modal.png)

Enter item, quantity, reason code, and reference. Stock moves to quarantine location and cannot be allocated until released.

---

## 10. Logistics

**Route:** `/dashboard/logistics`

### What it does
Inbound and outbound shipment tracking, container management, fleet management, and import document control.

### Tabs

| Tab | Purpose |
|-----|---------|
| Overview | Logistics KPI dashboard |
| Shipments | All shipments (inbound and outbound) |
| Containers | Container tracking |
| Arrivals | Expected arrival schedule |
| Documents | Import/export documents |
| Fleet | Company-owned delivery fleet |

![Logistics Overview](../../user-manual/screenshots/captured/module-ui/supply-chain/logistics/overview-tab.png)
*Logistics overview — shipments in transit, arriving today, and pending clearance.*

![Shipments Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/logistics/shipments-tab.png)
*All shipments with origin, destination, carrier, ETA, and status.*

![Containers Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/logistics/containers-tab.png)
*Container tracking — container number, contents, port status, and clearance.*

![Arrivals Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/logistics/arrivals-tab.png)
*Arrival schedule — expected delivery date, supplier, PO reference.*

![Documents Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/logistics/documents-tab.png)
*Import documents — Bill of Lading, Commercial Invoice, Packing List, Certificate of Origin, Customs Declaration.*

![Fleet Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/logistics/fleet-tab.png)
*Fleet management — company vehicles, driver assignments, maintenance schedule.*

---

## 11. Common Mistakes & Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| PR approval stuck | Approver not configured for department | Check Admin → Approvals for department approval chain |
| PO can't be sent | Supplier has no email | Add supplier email in Suppliers module |
| GRN won't post | Item not in inventory master | Ensure item exists in Products or Materials master |
| Stock count variance not clearing | Count not yet approved | Manager must approve variance in Cycle Count module |
| Reorder suggestions not generating | No reorder policy for item | Create reorder policy in Procurement → Reorder Policies |
| Shelf life alerts not showing | Item not set as shelf-life tracked | Enable in product master: `shelf_life_tracked = true` |
| Location not available in transfer | Location is inactive | Activate location in WMS → Locations |

---

## 12. Related Modules

| This Action | Connects To |
|-------------|-------------|
| Goods receipt from PO | Inventory → Stock (increase) + Finance → AP Invoice matching |
| Reorder suggestion | Procurement → Purchase Requisition |
| MRP recommendation | Procurement → Purchase Requisition |
| Production material issue | Inventory → Movements (consumption) |
| Quarantine release | Quality → QC Inspection decision |
| Outbound shipment | Sales → Delivery confirmation |

---

*End of Supply Chain Manual v2*
