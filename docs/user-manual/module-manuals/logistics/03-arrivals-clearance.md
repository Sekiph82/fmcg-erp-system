# Arrivals & Customs Clearance

**Route:** `/dashboard/logistics?tab=arrivals`  
**Permission required:** `logistics.view`

## What It Does

Manages the Kenya-side logistics lifecycle after a shipment leaves Turkey: port arrival events, KRA customs clearance, and local cost recording. Select a shipment from the dropdown to work on its arrival data.

![Arrivals Tab](../../../screenshots/captured/module-ui/logistics/arrivals/arrivals-tab.png)
*Arrivals page — ETA alert table and shipment selector.*

## ETA Alerts Panel

Shows all shipments arriving within the next 21 days. Columns: Shipment No, Vessel, B/L, ETA, Days-to-ETA (red when ≤ 5 days), Status.

## Arrival Events Sub-Tab

Timeline with 5 milestone dates. Each milestone turns green when its date is entered.

| Field | Milestone |
|-------|-----------|
| Revised ETA | Updated expected arrival date |
| Actual Arrival at Port (ATA) | Physical vessel arrival |
| Port Discharge / Released | Container discharged and released by port |
| Customs Cleared | KRA customs clearance completed |
| Delivered to Warehouse | Final delivery confirmed |
| GRN ID | UUID of the Goods Receipt Note created on delivery |

API: `PUT /api/v1/logistics/shipments/{id}/arrival`

## Customs Clearance Sub-Tab (KRA)

### Clearance Statuses

| Status | Meaning |
|--------|---------|
| PENDING | Not yet initiated |
| DOCS_SUBMITTED | Documents submitted to KRA |
| UNDER_REVIEW | KRA reviewing documents |
| EXAM_REQUESTED | Physical examination ordered |
| DUTY_ASSESSED | KRA has issued duty assessment |
| DUTY_PAID | Import duties paid |
| CLEARED | Full clearance granted |
| HELD | Goods detained — compliance issue |

### Clearance Form Fields

| Field | Description |
|-------|-------------|
| IDF / Entry No | Import Declaration Form number |
| Clearing Agent | Customs agent company |
| KRA PIN | Importer's KRA PIN |
| Submission Date | Date docs submitted to KRA |
| Examination Date | Physical exam date (if ordered) |
| Clearance Date | Date clearance granted |
| Status | Current clearance status |
| CIF Value (USD) | Cost + Insurance + Freight value in USD |
| Import Duty (KES) | Custom duty assessed |
| VAT (16%) (KES) | Value Added Tax |
| IDF Fee (KES) | Import Declaration Fee |
| Railway Dev. Levy (KES) | Railway Development Levy |
| Other Charges (KES) | Miscellaneous port charges |
| Total Taxes (KES) | Auto-sum of all duties (editable) |

API: `POST /api/v1/logistics/clearances`, `PUT /api/v1/logistics/clearances/{id}`

## Local Costs & Payments Sub-Tab

Records Kenya-side logistics expenses: transport, clearing fees, port handling. Supports M-Pesa payment confirmation.

### Cost Types

| Type | Description |
|------|-------------|
| TRANSPORT | Mombasa–Nairobi truck or SGR rail |
| CLEARING_FEE | Clearing agent service fee |
| PORT_HANDLING | Port authority handling charges |
| WAREHOUSE_HANDLING | Receiving/unstuffing at warehouse |
| FUMIGATION | Phytosanitary fumigation |
| INSPECTION_FEE | KEBS or other inspection fees |
| OTHER | Any other local cost |

### Payment Methods

| Method | Icon |
|--------|------|
| MPESA | 📱 Mobile money |
| BANK | 🏦 Bank transfer |
| CASH | 💵 Cash |

### Payment Status

`PENDING` → `PAID` (confirmed with M-Pesa receipt + phone) or `DISPUTED`

### Cost Summary

The panel shows: Total KES, Paid KES, Pending KES.

API: `POST /api/v1/logistics/shipments/{id}/local-costs`
