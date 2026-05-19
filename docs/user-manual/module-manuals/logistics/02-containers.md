# Container Tracking

**Route:** `/dashboard/logistics?tab=containers`  
**Permission required:** `logistics.view`

## What It Does

Tracks each shipping container by number, seal, contents, weight, and customs release. Containers are linked to shipments and progress through their own status lifecycle.

![Containers Tab](../../../screenshots/captured/module-ui/logistics/containers/containers-tab.png)
*Container list with status filter bar.*

## Container Statuses

| Status | Meaning |
|--------|---------|
| EMPTY | Container empty, awaiting loading |
| LOADING | Being stuffed with cargo |
| LOADED | Cargo loaded, sealed |
| IN_TRANSIT | On the vessel at sea |
| AT_PORT | Arrived at Mombasa port |
| CUSTOMS_HOLD | Held by KRA for examination |
| RELEASED | Customs released, ready for delivery |
| RETURNED | Empty container returned to shipping line |

## Container Types

| Type | Description |
|------|-------------|
| 20FT_DRY | Standard 20-foot dry container |
| 40FT_DRY | Standard 40-foot dry container |
| 40FT_HC | 40-foot high-cube (extra height) |
| 20FT_REEFER | 20-foot refrigerated container |
| LCL | Less-than-container load (groupage) |

## Add Container Form

| Field | Description |
|-------|-------------|
| Shipment | Select parent shipment |
| Container No | ISO container number (e.g. MSCU1234567) |
| Seal No | Customs seal number |
| Type | Container type |
| Status | Current status |
| Gross Weight (kg) | Total loaded weight |
| CBM | Volume in cubic metres |
| Customs Release No | KRA release reference |
| Demurrage Free Days | Days before port storage charges apply (default 7) |
| Contents Summary | Brief description of cargo |

API: `POST /api/v1/logistics/containers`

## Container Table Columns

| Column | Description |
|--------|-------------|
| Container No | ISO container number (highlighted) |
| Seal No | Customs seal |
| Type | Container type badge |
| Shipment | Linked shipment number |
| Weight (kg) | Gross weight |
| CBM | Volume |
| Contents | Cargo summary |
| Customs Release | Release reference number |
| Free Days | Demurrage-free days |
| Status | Current status badge |
