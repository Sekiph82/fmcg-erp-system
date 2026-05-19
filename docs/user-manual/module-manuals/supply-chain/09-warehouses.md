# Warehouses

**Route:** `/dashboard/warehouses`  
**Permission required:** `inventory.view`  
**Workspace tabs:** Warehouses, WMS

---

## What It Does

The Warehouses module manages the physical warehouse master data — the locations where stock is held. Warehouse records are referenced by inventory positions, GRNs, transfers, WMS zones, and logistics arrivals.

---

## Warehouse List

Shows all warehouses with:
- Warehouse code (monospace)
- Name
- Type (badge)
- City
- Country
- Capacity (m²)
- Status (Active / Inactive)
- Delete button (permission-gated)

---

## Warehouse Record Fields

### Create / Edit Form

| Field | Label | Required | Notes |
|-------|-------|----------|-------|
| `code` | Warehouse Code | Yes | Short identifier; e.g. `WH-NBI-01` |
| `name` | Warehouse Name | Yes | Full descriptive name |
| `warehouse_type` | Type | Yes | See type values below |
| `is_active` | Active | No | Default `true` |
| `city` | City | No | City where warehouse is located |
| `country` | Country | No | Country |
| `capacity_sqm` | Capacity (m²) | No | Floor area in square metres |

### Warehouse Type Values

| Type | Description |
|------|-------------|
| `FINISHED_GOODS` | Stores finished products ready for dispatch |
| `RAW_MATERIAL` | Stores input materials for production |
| `TRANSIT` | Intermediate holding for goods in transit between locations |
| `RETURNS` | Holds returned goods pending inspection or disposition |

---

## Warehouse Scoping

Warehouse records are scoped to the tenant company. Users with `inventory.view` see only the warehouses within their permitted scope.

Some inventory actions (receive, issue, transfer, adjust) require the user to have permissions scoped to the specific warehouse:
- `inventory.receive_all` — receive into any warehouse
- `inventory.dispatch_all` — issue from any warehouse
- `inventory.transfer_all` — transfer between any warehouses
- `inventory.adjust_all` — adjust stock in any warehouse
- `canPerformInScope("warehouse", warehouse_id, action)` — scope-limited equivalent

---

## WMS Tab

**Tab key:** `wms`

The Warehouses page embeds the WMS module as a second tab. See [10-wms.md](./10-wms.md) for full WMS documentation.

---

## Deleting a Warehouse

Delete is only available to users with the appropriate permission. A warehouse with associated stock positions, WMS zones, or open documents cannot be deleted — a constraint error is returned.
