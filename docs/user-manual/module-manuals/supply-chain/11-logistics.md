# Logistics & Import Shipments

**Route:** `/dashboard/logistics`  
**Permission required:** `procurement.view`  
**Workspace tabs:** Overview, Shipments, Containers, Arrivals, Documents, Fleet

---

## What It Does

The Logistics module manages international import shipments from origin port to warehouse delivery. It tracks vessels, containers, customs clearance, and arrival milestones. Logistics integrates with Procurement (links to POs) and Inventory (GRN creation on delivery).

![Logistics workspace](../../../screenshots/captured/module-ui/supply-chain/logistics/overview-tab.png)
*Logistics overview showing KPI tiles (Active Shipments, In Transit, At Port/Clearing, Overdue Documents) and ETA alert panel.*

---

## Dashboard KPIs

The overview tab shows four KPI tiles:

| Tile | Description |
|------|-------------|
| Active Shipments | Total shipments not cancelled or delivered |
| In Transit | Shipments with status `IN_TRANSIT` |
| At Port / Clearing | Shipments at `ARRIVED_PORT`, `CUSTOMS_HOLD`, or `CUSTOMS_CLEARED` |
| Overdue Documents | Count of shipments with overdue required documents; shown in **red** if > 0 |

### ETA Alert Panel

Shipments within 14 days of ETA appear in the alert panel. Colour coding:

| Condition | Display |
|-----------|---------|
| `days_to_eta ≤ 3` | **Red bold** — critical; action required |
| `days_to_eta 4–14` | Amber — approaching |

---

## Shipment Status Values

| Status | Colour | Meaning |
|--------|--------|---------|
| `PLANNED` | — | Shipment being organised |
| `BOOKED` | — | Vessel / cargo space confirmed |
| `CARGO_LOADED` | Blue | Container loaded at origin port |
| `IN_TRANSIT` | Blue | On the vessel at sea |
| `ARRIVED_PORT` | Yellow | Arrived at destination port |
| `CUSTOMS_HOLD` | Red | Held by customs for inspection |
| `CUSTOMS_CLEARED` | Green | Customs clearance obtained |
| `OUT_FOR_DELIVERY` | Yellow | In transit from port to warehouse |
| `DELIVERED` | Green | Received at warehouse |
| `CANCELLED` | Gray | Shipment cancelled |

---

## Customs Clearance Status

| Status | Colour |
|--------|--------|
| `CLEARED` | Green |
| `HELD` | Red |
| `DUTY_PAID` | Yellow |

---

## Transport Mode

| Mode | Badge Colour |
|------|-------------|
| `SEA` | Blue |
| `AIR` | Yellow |
| `ROAD` | Gray |

---

## Shipments Tab

**Tab key:** `shipments`

![Logistics — Shipments tab](../../../screenshots/captured/module-ui/supply-chain/logistics/shipments-tab.png)
*Shipments tab showing import shipments with mode badges, ETA, days to ETA (colour-coded), clearance status, and shipment status.*

Lists all import shipments with filterable columns.

### Shipment List Columns

| Column | Field | Notes |
|--------|-------|-------|
| Shipment No | `shipment_no` | Reference number |
| Mode | Mode badge | SEA / AIR / ROAD |
| Vessel / Carrier | `vessel_name` or `carrier` | Shipping line or air carrier |
| B/L Number | `bl_number` | Bill of lading |
| Origin Port | `origin_port` | Port of loading |
| ETA | `eta` | Original estimated time of arrival |
| ETA (Revised) | `eta_revised` | Updated ETA if rescheduled |
| Days to ETA | `days_to_eta` | Colour-coded by urgency |
| Containers | `container_count` | Number of containers on shipment |
| POs | `po_count` | Number of linked Purchase Orders |
| Clearance | `clearance_status` | Customs clearance badge |
| Status | `status` | Shipment status badge |

**Row highlight:** Rows where `has_overdue_docs = true` display with a red-50 background.

---

## Containers Tab

**Tab key:** `containers`

![Logistics — Containers tab](../../../screenshots/captured/module-ui/supply-chain/logistics/containers-tab.png)
*Containers tab showing container numbers, seal numbers, size, weight, and shipment linkage.*

Tracks individual container records linked to shipments. Containers have their own tracking (seal number, container number, size, weight).

---

## Arrivals Tab

**Tab key:** `arrivals`

![Logistics — Arrivals tab](../../../screenshots/captured/module-ui/supply-chain/logistics/arrivals-tab.png)
*Arrivals tab showing port event records, ETA alerts, and customs clearance tracking.*

Records the physical arrival of goods at the warehouse. After an arrival is confirmed:
1. The logistics team marks the shipment as `DELIVERED`
2. The warehouse team creates GRNs (Goods Receipt Notes) in the Procurement module to credit inventory

See [04-deliveries.md](./04-deliveries.md) for the GRN process.

---

## Documents Tab

**Tab key:** `documents`

![Logistics — Documents tab](../../../screenshots/captured/module-ui/supply-chain/logistics/documents-tab.png)
*Documents tab listing shipping documents (bill of lading, commercial invoice, certificates) with due dates and status.*

Manages import documentation: bill of lading, commercial invoice, packing list, certificate of origin, phytosanitary certificate, import declaration. Documents have due dates; overdue documents drive the red KPI tile on the dashboard.

---

## Fleet Tab

**Tab key:** `fleet`

![Logistics — Fleet tab](../../../screenshots/captured/module-ui/supply-chain/logistics/fleet-tab.png)
*Fleet tab showing internal delivery vehicles with registration, driver assignment, and trip status.*

Manages internal delivery fleet vehicles used for last-mile delivery from port to warehouse. Tracks vehicle registration, driver assignment, and trip logs.

---

## Quick Links (Overview Tab)

| Link | Purpose |
|------|---------|
| Shipment Planning | Create and plan new import shipments |
| Container Tracking | Monitor container locations and status |
| Customs Documents | Upload and track clearance documents |
| Arrival & Clearance | Record arrivals and update clearance status |

---

## Logistics → Inventory Flow

```
Shipment BOOKED
    → Cargo loaded (CARGO_LOADED)
    → Vessel at sea (IN_TRANSIT)
    → Port arrival (ARRIVED_PORT)
    → Customs clearance (CUSTOMS_CLEARED)
    → Out for delivery (OUT_FOR_DELIVERY)
    → Delivered to warehouse (DELIVERED)
    → GRN created in Procurement
    → Inventory RECEIPT movement posted
    → Landed costs allocated to GRN lines
```
