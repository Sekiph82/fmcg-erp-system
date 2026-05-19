# Warehouse Management System (WMS)

**Route:** `/dashboard/wms`  
**Permission required:** `inventory.view`  
**Workspace tabs:** Zones, Locations, Handling Units, Pick Waves, Quarantine

---

## What It Does

WMS provides sub-warehouse organisation: zones within a warehouse, bin locations within zones, handling unit tracking, wave picking, and quarantine management. It sits on top of the inventory ledger — WMS locations track where within a warehouse stock physically resides.

---

## Zones Tab

**Tab key:** `zones`

Zones are areas within a warehouse with a specific function (raw material, staging, quarantine, etc.).

### Zone Type Values

| Type | Description |
|------|-------------|
| `RAW_MATERIAL` | Input material storage |
| `SEMI_FINISHED` | WIP / intermediate goods |
| `FINISHED_GOODS` | Completed product storage |
| `QUARANTINE` | Blocked / suspect stock |
| `RETURNS` | Customer returns holding |
| `STAGING` | Pick, pack, and dispatch staging |

### Zone Create Form

| Field | Label | Required | Notes |
|-------|-------|----------|-------|
| `warehouse_id` | Warehouse | Yes | Select from warehouses list |
| `code` | Zone Code | Yes | Short identifier; e.g. `FG-A` |
| `name` | Zone Name | Yes | Descriptive name |
| `zone_type` | Zone Type | Yes | See type values above |
| `is_active` | Active | No | Default `true` |

---

## Locations Tab

**Tab key:** `locations`

Bin locations are the leaf-level storage positions within a zone (rack, shelf, bin address).

### Location Create Form

| Field | Label | Required | Notes |
|-------|-------|----------|-------|
| `zone_id` | Zone | Yes | Select from zones list |
| `code` | Location Code | Yes | e.g. `A-01-03` (aisle-rack-level) |
| `name` | Location Name | Yes | Descriptive label |
| `barcode` | Barcode | No | Scannable barcode for the location |
| `is_active` | Active | No | Default `true` |
| `is_blocked` | Blocked | No | Prevents picks/puts when blocked |

---

## Handling Units Tab

**Tab key:** `handlingUnits`

Handling units (HUs) group individual stock items under a single licence plate for tracking pallets, totes, or cartons.

### Handling Unit List Columns

| Column | Description |
|--------|-------------|
| License Plate | Unique HU identifier (scannable) |
| Type | HU type (PALLET, TOTE, CARTON, etc.) |
| Warehouse | Warehouse where HU is located |
| Location | Bin location within the warehouse |
| Items | Count of stock lines in the HU |
| Status | Current HU status |
| Access | Link to HU detail |

### HU Status Badge Colours

| Status | Colour |
|--------|--------|
| `OPEN`, `DRAFT`, `PENDING`, `IN_PROGRESS`, `RELEASED` | Blue |
| `CLOSED`, `COMPLETED`, `PICKED`, `PACKED`, `SHIPPED` | Green |
| `ON_HOLD`, `CANCELLED`, `VOID`, `CONSUMED` | Red |

---

## Pick Waves Tab

**Tab key:** `pickWaves`

Wave picking batches multiple pick tasks across multiple orders into a single wave for efficient picking routes.

### Pick Wave List Columns

| Column | Description |
|--------|-------------|
| Wave | `wave_no` — wave reference number |
| Warehouse | Warehouse the wave belongs to |
| Priority | Pick priority (higher = more urgent) |
| Tasks | `task_count` — number of individual pick tasks |
| Status | Current wave status |
| Access | Link to wave detail |

Wave status uses the same badge colour scheme as handling units.

---

## Quarantine Tab

**Tab key:** `quarantine`

Quarantine blocks specific stock from being picked or issued. It applies at the lot level within a warehouse.

### Quarantine Action Form

| Field | Label | Required | Notes |
|-------|-------|----------|-------|
| `warehouse_id` | Warehouse | Yes | Warehouse containing the stock |
| `lot_number` | Lot Number | No | Leave blank to quarantine all lots in the warehouse |
| `reason` | Reason | Yes | Why the stock is being quarantined |
| `notes` | Notes | No | Additional detail |

**Effect:** Sets `quantity_available = 0` for the affected stock positions. Creates an audit movement of type `QUARANTINE`.

### Quarantine Release Form

| Field | Label | Required | Notes |
|-------|-------|----------|-------|
| `warehouse_id` | Warehouse | Yes | Warehouse with quarantined stock |
| `lot_number` | Lot Number | Yes | Lot number to release |
| `notes` | Notes | No | Release justification |

**Effect:** Restores `quantity_available` to prior level. Creates a `QUARANTINE_RELEASE` movement in the inventory ledger.

---

## WMS and Inventory Relationship

WMS locations are informational overlays on the inventory ledger. The authoritative stock quantity is always in the inventory ledger (`quantity_on_hand`). WMS provides the physical location data. Discrepancies between WMS and the ledger are resolved via cycle count.
