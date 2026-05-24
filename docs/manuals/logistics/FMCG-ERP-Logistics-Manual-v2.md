# FMCG ERP — Logistics Manual v2

**Version:** 2.0 (post-recovery)  
**Date:** 2026-05-24  
**Audience:** Logistics Coordinators, Import/Export Officers, Fleet Managers, Supply Chain Managers  
**Modules Covered:** Logistics · Shipments · Containers · Arrivals · Import Documents · Fleet Management

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Logistics Overview Dashboard](#2-logistics-overview-dashboard)
3. [Shipments](#3-shipments)
4. [Container Tracking](#4-container-tracking)
5. [Arrival Schedule](#5-arrival-schedule)
6. [Import/Export Documents](#6-importexport-documents)
7. [Fleet Management](#7-fleet-management)
8. [Outbound Logistics (Sales Delivery)](#8-outbound-logistics-sales-delivery)
9. [Common Mistakes & Troubleshooting](#9-common-mistakes--troubleshooting)
10. [Related Modules](#10-related-modules)

---

## 1. Module Overview

**What it does:** Manages inbound and outbound logistics — shipment tracking, container management, customs documentation, and fleet operations. Bridges the gap between supplier POs arriving from overseas and warehouse receipt.

**Who uses it:**
- Logistics Coordinator — tracks shipments, raises customs documentation
- Import Officer — manages container clearance, document filing
- Fleet Manager — manages delivery vehicles and driver assignments
- Supply Chain Manager — monitors supply chain lead times and transit KPIs

**When to use it:**
- When tracking an incoming container from overseas
- When scheduling a delivery run for customer orders
- When managing customs clearance documentation
- When monitoring fleet vehicle maintenance schedules
- When recording actual vs. expected arrival times

**Module route:** `/dashboard/logistics`

![Logistics Overview](../../user-manual/screenshots/captured/module-ui/supply-chain/logistics/overview-tab.png)
*Logistics overview dashboard — shipments in transit, due today, and pending clearance.*

---

## 2. Logistics Overview Dashboard

**Tab:** Overview

### KPI Cards

| KPI | Description |
|-----|-------------|
| Shipments In Transit | Count of active inbound and outbound shipments |
| Arriving Today | Shipments with ETA = today |
| Pending Customs Clearance | Containers at port awaiting clearance |
| Late Shipments | Arrivals past their ETA |
| Fleet Vehicles Active | Number of company vehicles currently deployed |
| Documents Due | Import/export documents due for filing |

### Charts
- Transit time trend (actual vs. planned by supplier/lane)
- Freight cost by carrier and period
- On-time delivery rate (outbound)

---

## 3. Shipments

**Tab:** Shipments

### What it does
Track all inbound shipments (from suppliers) and outbound shipments (to customers). Each shipment links to purchase orders (inbound) or sales orders (outbound).

![Shipments Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/logistics/shipments-tab.png)
*Shipments list — all active and recent shipments with mode, carrier, ETA, and status.*

### Shipment Fields

| Field | Required | Notes |
|-------|----------|-------|
| Shipment Reference | Yes | Auto-generated or manual reference |
| Direction | Yes | Inbound / Outbound |
| Mode | Yes | Sea / Air / Road / Rail |
| Origin | Yes | Country and city of departure |
| Destination | Yes | Country and city of arrival |
| Carrier | Yes | Shipping line, airline, or road haulier |
| Vessel/Flight/Vehicle | No | Vessel name, flight number, or truck plate |
| Bill of Lading / AWB | No | Transport document reference |
| Departure Date | Yes | Actual or estimated departure |
| ETA | Yes | Estimated arrival at destination |
| ATA | No | Actual time of arrival (filled when received) |
| Related POs | No | Link to purchase order(s) |
| Related Sales Orders | No | Link to sales order(s) |
| Incoterm | No | EXW / FOB / CIF / DAP / DDP |
| Carrier Reference | No | Carrier booking number |
| Status | Yes | See status values below |

### Shipment Status Values

| Status | Meaning |
|--------|---------|
| BOOKING_CONFIRMED | Space confirmed with carrier |
| IN_TRANSIT | Cargo departed; en route |
| AT_TRANSSHIPMENT | In transit via intermediate port |
| AT_DESTINATION_PORT | Arrived at destination port |
| CUSTOMS_CLEARANCE | Under customs examination |
| CLEARED | Customs cleared |
| OUT_FOR_DELIVERY | Last-mile delivery in progress |
| DELIVERED | Goods received at warehouse |

### Creating a Shipment

1. Logistics → Shipments → **+ New Shipment**
2. Set direction (Inbound/Outbound)
3. Enter carrier, route, ETA
4. Link to purchase orders (for inbound) or sales orders (for outbound)
5. Attach transport documents
6. Save and track status updates as shipment progresses

---

## 4. Container Tracking

**Tab:** Containers

### What it does
Detailed container-level tracking — container numbers, seal numbers, contents summary, port status, and clearance milestones.

![Containers Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/logistics/containers-tab.png)
*Container tracking — container number, shipping line, port status, and clearance milestone.*

### Container Fields

| Field | Required | Notes |
|-------|----------|-------|
| Container Number | Yes | ISO standard format e.g. MSCU1234567 |
| Container Type | Yes | 20GP / 40GP / 40HC / Reefer |
| Seal Number | Yes | Security seal (from shipping line or customs) |
| Shipment | Yes | Parent shipment reference |
| Loading Port | Yes | Port of origin |
| Discharge Port | Yes | Port of destination |
| Contents Summary | No | Brief description for customs |
| Gross Weight (kg) | No | Total cargo weight |
| Net Weight (kg) | No | Net payload weight |
| Volume (CBM) | No | Cubic meter measurement |
| Container Status | Yes | See container milestones below |

### Container Milestone Tracking

Track each stage:
1. Empty container collected from depot
2. Stuffed (loaded) at origin
3. Gate-in at port
4. Loaded on vessel
5. Departed origin port
6. Arrived transshipment port
7. Departed transshipment port
8. Arrived destination port (discharge)
9. Customs examination / clearance
10. Gate-out from port (release)
11. Transported to warehouse
12. Unstuffed (unloaded) at warehouse
13. Empty returned to shipping line

---

## 5. Arrival Schedule

**Tab:** Arrivals

### What it does
Rolling schedule of expected inbound deliveries — by date, origin, supplier, and PO reference. Used by warehouse to plan receiving resources.

![Arrivals Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/logistics/arrivals-tab.png)
*Arrival schedule — expected delivery date, supplier, PO reference, and quantity.*

**Arrival schedule view shows:**
- Expected arrival date (ETA)
- Supplier name
- PO reference number
- Items and quantities
- Carrier and transport reference
- Status (On Time / Delayed / Arrived)

**Warehouse planning:** Receiving supervisor views arrival schedule daily to pre-allocate receiving bays, staff, and equipment.

---

## 6. Import/Export Documents

**Tab:** Documents

### What it does
Central repository for all import and export trade documents — Bill of Lading, Commercial Invoice, Packing List, Certificate of Origin, Customs Declaration, and Phytosanitary Certificates.

![Documents Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/logistics/documents-tab.png)
*Import documents — document type, shipment reference, status, and file attachment.*

### Required Import Documents for Kenya

| Document | Issued By | Required For |
|----------|----------|-------------|
| Bill of Lading (OBL) | Shipping Line | All sea freight |
| Commercial Invoice | Supplier | Customs valuation |
| Packing List | Supplier | Customs examination |
| Certificate of Origin | Chamber of Commerce | Duty preferential rates |
| Phytosanitary Certificate | Origin Country Dept. | Food/agricultural goods |
| Conformity Certificate (CoC) | PVOC Agency | Regulated goods (KEBS) |
| Food Import Permit | KEPHIS/KRA | Food products |
| Health Certificate | Origin country health authority | Animal products |
| Import Declaration Form (IDF) | KRA iCMS | All imports |

### Document Upload Process

1. Logistics → Documents → **+ Add Document**
2. Set document type, shipment reference, supplier, and date issued
3. Upload file (PDF, scan)
4. Mark as Required: Yes/No
5. Set review status: Received / Pending / Missing

**Customs clearance cannot proceed** until all required documents are marked Received.

### Document Status Tracking

| Status | Meaning |
|--------|---------|
| PENDING | Not yet received |
| RECEIVED | Original or certified copy received |
| QUERIED | Customs or bank raised a query |
| ACCEPTED | Accepted by customs/bank |
| REJECTED | Rejected — resubmission required |

---

## 7. Fleet Management

**Tab:** Fleet

### What it does
Manage company-owned delivery vehicles — vehicle register, driver assignments, maintenance scheduling, fuel tracking, and route assignment.

![Fleet Tab](../../user-manual/screenshots/captured/module-ui/supply-chain/logistics/fleet-tab.png)
*Fleet management — all vehicles with status, assigned driver, and last service date.*

### Vehicle Register Fields

| Field | Required | Notes |
|-------|----------|-------|
| Vehicle Name | Yes | e.g. "KBX 001T — Isuzu NQR" |
| Registration Number | Yes | Kenyan number plate |
| Vehicle Type | Yes | Pickup / 3-Ton / 10-Ton / Refrigerated / Tanker |
| Capacity (kg) | Yes | Max payload |
| Driver | No | Assigned driver (link to HR employee) |
| Year of Manufacture | No | |
| Insurance Expiry | Yes | Alert when expiring |
| Inspection (NTSA) Expiry | Yes | Alert when expiring |
| Status | Yes | Active / Under Maintenance / Disposed |
| Fuel Type | Yes | Diesel / Petrol / Electric |

### Fleet Maintenance Alerts
System alerts for:
- Insurance expiring within 30 days
- NTSA inspection due within 14 days
- Scheduled service due (based on mileage or calendar interval)

### Fuel Tracking
Log fuel fill-ups: date, vehicle, litres, cost per litre, odometer reading.  
Report: fuel efficiency (km per litre) per vehicle.

### Route Assignment
When sales orders are dispatched, assign vehicle and driver to delivery:
1. Sales → Orders → Dispatch → select vehicle from fleet
2. Vehicle appears on delivery schedule for that date

---

## 8. Outbound Logistics (Sales Delivery)

### What it does
Tracks the outbound journey of customer orders from warehouse dispatch to delivery confirmation.

**Outbound workflow:**

1. **Sales order confirmed** → WMS pick wave created
2. **Picking completed** → goods staged at dispatch bay
3. **Load vehicle** → assign vehicle and driver (Fleet)
4. **Dispatch** → Shipment created (type: Outbound), status: OUT_FOR_DELIVERY
5. **Driver delivers** → customer signs delivery note (paper or electronic)
6. **Office confirms delivery** → Shipment status = DELIVERED
7. **System triggers** → Sales order status = DELIVERED → Invoice generation prompt

### Proof of Delivery (POD)
Record POD reference number and received-by name when confirming delivery. Attach scanned copy if available.

### OTIF Tracking
**OTIF = On Time In Full**
- On Time: Delivered on or before promised delivery date
- In Full: Delivered quantity = ordered quantity

Target: >95% OTIF. Monthly OTIF report available in Analytics → Sales.

---

## 9. Common Mistakes & Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Shipment not linked to PO | PO not selected when creating shipment | Edit shipment → add PO reference |
| Container not clearing customs | Required document missing | Upload missing document in Documents tab; mark as Received |
| Arrival date wrong | ETA not updated | Update ETA on shipment when new sailing advice received |
| Fleet vehicle not available | Status = Under Maintenance | Update vehicle status when maintenance complete |
| Delivery not triggering invoice | Sales order not marked DELIVERED | Confirm delivery on the shipment record |
| Customs duty calculation wrong | Commercial invoice value incorrect | Liaise with supplier for correct value; update document |

---

## 10. Related Modules

| This Action | Connects To |
|-------------|-------------|
| Inbound shipment arrives | Procurement → Deliveries (GRN) |
| Container cleared | Procurement → Goods Receipt |
| Outbound dispatch | Sales → Delivery Confirmation |
| Fleet maintenance due | Maintenance → Work Order |
| Import documents | Finance → Landed Cost (duty allocation) |
| OTIF metrics | Analytics → Supply Chain |
| Driver expense (fuel/tolls) | Finance → Expenses |

---

*End of Logistics Manual v2*
