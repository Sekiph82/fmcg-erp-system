# Inventory and Warehouse

**URLs:** `/dashboard/inventory`, `/dashboard/warehouses`, `/dashboard/wms`  
**Module:** Inventory / WMS  
**Permission:** `inventory.view`

---

## Screenshot

> Screenshot pending: Inventory workspace — Stock tab

---

## Inventory Workspace Tabs

| Tab | URL | Purpose |
|---|---|---|
| Stock | ?tab=stock | Current stock levels by SKU and location |
| Movements | ?tab=movements | All in/out movements history |
| Cycle Count | ?tab=cycle-count | Physical count scheduling |
| Shelf Life | ?tab=shelf-life | FEFO expiry tracking |
| Traceability | ?tab=traceability | Lot/batch forward/backward trace |
| Serials | ?tab=serials | Serial number tracking |
| Valuation | ?tab=valuation | Stock value by cost method |

---

## Warehouses Workspace Tabs

| Tab | URL | Purpose |
|---|---|---|
| Warehouses | ?tab=warehouses | Warehouse list and configuration |
| WMS | ?tab=wms | WMS layout inside warehouses context |

---

## WMS Workspace Tabs

| Tab | URL | Purpose |
|---|---|---|
| Zones | ?tab=zones | Zone configuration |
| Locations | ?tab=locations | Bin location list and capacity |
| Quarantine | ?tab=quarantine | Quarantined stock |

---

## Key Concepts

**Available stock** = On Hand − Reserved (reserved by released production/sales orders)

**FEFO (First Expired, First Out):** The system suggests picking the batch with the nearest expiry date first. Critical for food production.

**Lot/Batch traceability:** Every stock movement carries the batch number. The traceability tab shows the full genealogy.

**Valuation methods:** FIFO, AVCO (Average Cost), or Standard Cost. Set per product category in Admin.

---

## Quarantine Workflow

1. Incoming goods failing QC → marked Quarantine during receipt
2. WMS Quarantine tab shows all quarantined stock
3. QC technician inspects
4. Release to stock (if pass) or write off (if fail)
5. Write-off requires manager approval

---

## Related Workspaces

- Procurement (`/dashboard/procurement`) — goods receipt
- Production (`/dashboard/production`) — material consumption
- Quality (`/dashboard/quality`) — QC inspections linked to batches

---

## Screenshot

> Screenshot pending: WMS workspace — Locations tab
