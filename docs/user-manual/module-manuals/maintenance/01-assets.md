# Asset Register

**Route:** `/dashboard/maintenance?tab=assets`  
**Permission required:** `maintenance.view`

## What It Does

Maintains the plant's master equipment register: production machines, utilities, vehicles, and infrastructure. Each asset tracks its type, production line assignment, manufacturer details, warranty, and operational status.

![Assets Tab](../../../screenshots/captured/module-ui/maintenance/assets/assets-tab.png)
*Asset register — full list with asset numbers, types, line assignments, and status badges.*

## Asset Status

| Status | Meaning |
|--------|---------|
| ACTIVE | Fully operational |
| IDLE | Operational but not in use |
| UNDER_MAINTENANCE | Currently being serviced |
| DECOMMISSIONED | Retired from service |

## Asset Table Columns

| Column | Description |
|--------|-------------|
| Asset No | System-generated unique identifier |
| Name | Descriptive asset name |
| Type | Category (e.g., Filling Machine, Conveyor, Boiler) |
| Line | Production line assignment |
| Serial No | Manufacturer serial number |
| Install Date | Date placed in service |
| Location | Physical location on plant |
| Status | Current operational status badge |

## Add Asset Form

![New Asset Modal](../../../screenshots/captured/module-ui/maintenance/assets/new-asset-modal.png)
*Add Asset modal — all registration fields.*

| Field | Description |
|-------|-------------|
| Asset No | Unique reference code (e.g., AST-001) |
| Name | Full descriptive name |
| Asset Type | Free-text category |
| Line | Production line (optional) |
| Serial No | Manufacturer serial number |
| Manufacturer | Brand or OEM name |
| Model | Model designation |
| Install Date | Date of installation |
| Warranty Expiry | Warranty end date |
| Location | Zone/bay on the plant floor |
| Status | ACTIVE · IDLE · UNDER_MAINTENANCE · DECOMMISSIONED |
| Notes | Free text |

API: `POST /api/v1/maintenance/assets`, `PUT /api/v1/maintenance/assets/{id}`
