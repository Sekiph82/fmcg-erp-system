# Shipment Planning

**Route:** `/dashboard/logistics?tab=shipments`  
**Permission required:** `logistics.view`

## What It Does

Manages international import shipments from Turkey to Kenya. Each shipment tracks the vessel, B/L number, ETA, containers, and linked purchase orders through the full delivery lifecycle.

![Shipments Tab](../../../screenshots/captured/module-ui/logistics/shipments/shipments-tab.png)
*Shipments list with status filters.*

## Shipment Status Flow

```
DRAFT → BOOKING_CONFIRMED → CARGO_LOADED → IN_TRANSIT →
ARRIVED_PORT → CUSTOMS_HOLD → CUSTOMS_CLEARED → OUT_FOR_DELIVERY → DELIVERED
```

| Status | Meaning |
|--------|---------|
| DRAFT | Shipment planned, not yet booked |
| BOOKING_CONFIRMED | Carrier booking confirmed |
| CARGO_LOADED | Goods stuffed into containers |
| IN_TRANSIT | Vessel at sea |
| ARRIVED_PORT | Reached Port of Mombasa |
| CUSTOMS_HOLD | Held by KRA for inspection |
| CUSTOMS_CLEARED | KRA clearance received |
| OUT_FOR_DELIVERY | Trucking to warehouse |
| DELIVERED | Goods received at warehouse |

## New Shipment Form

Click **New Shipment** to open the form.

![New Shipment Modal](../../../screenshots/captured/module-ui/logistics/shipments/new-shipment-modal.png)
*New Shipment form.*

| Field | Description |
|-------|-------------|
| Shipment No | Unique identifier (e.g. ISH-00001) |
| Mode | SEA · AIR · ROAD · RAIL |
| Origin Country | Default: Turkey |
| Origin City | Default: Istanbul |
| Origin Port | Default: Port of Istanbul |
| Destination City | Default: Mombasa |
| Destination Port | Default: Port of Mombasa |
| Final Destination | Warehouse address after port |
| Carrier | Shipping line (e.g. MSC, Maersk) |
| Vessel Name | Ship name |
| Voyage No | Voyage reference |
| B/L Number | Bill of Lading number |
| Planned Departure | ETD from origin port |
| ETA Mombasa | Estimated arrival at Mombasa |
| Incoterm | EXW · FCA · FOB · CFR · CIF · CPT · CIP · DAP · DDP |
| Currency | USD · EUR · TRY · KES |
| Freight Cost | Ocean/air freight amount |
| Insurance | Insurance premium |
| Total CBM | Volume in cubic metres |
| Weight (kg) | Gross shipment weight |
| Forwarder | Clearing and forwarding agent |
| Status | Current shipment status |
| Notes | Free text |

API: `POST /api/v1/logistics/shipments`

## Shipment Table Columns

| Column | Description |
|--------|-------------|
| Shipment No | Unique reference |
| Mode | Transport mode badge |
| Origin | City + port |
| Carrier / Vessel | Shipping line and ship name |
| B/L | Bill of Lading number |
| Departure | Planned ETD |
| ETA | Estimated arrival (with days counter) |
| Incoterm | Trade terms |
| Ctrs | Container count |
| POs | Linked purchase orders |
| Status | Current status badge |

## ETA Alert Logic

Shipments arriving within 14 days appear in the amber alert panel on the Overview tab. Days counter turns red when ≤ 3 days remain or when `days_to_eta < 0` (overdue).
