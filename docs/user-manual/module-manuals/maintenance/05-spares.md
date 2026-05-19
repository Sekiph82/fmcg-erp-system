# Spare Parts

**Route:** `/dashboard/maintenance?tab=spares`  
**Permission required:** `maintenance.view`

## What It Does

Manages the maintenance spare parts inventory: stock levels, reorder thresholds, unit costs, lead times, and usage records. Rows highlighted in orange when stock is at or below the reorder level.

![Spares Tab](../../../screenshots/captured/module-ui/maintenance/spares/spares-tab.png)
*Spare Parts — inventory table with reorder level, unit cost, and Low Stock badge.*

## Spare Parts Table Columns

| Column | Description |
|--------|-------------|
| Part No | Unique part reference (e.g., SPC-0001) |
| Name | Part name and description |
| Supplier | Preferred supplier name |
| Stock | Current stock quantity with unit |
| Reorder Level | Threshold that triggers low-stock alert |
| Unit Cost | Cost per unit in KES |
| Lead Time | Days to receive from supplier |
| Status | OK (green) or Low Stock (yellow/orange) |

## Low Stock Filter

**Low Stock Only** toggle filters the table to show only parts at or below their reorder level. Count shown on the button.

## Add Spare Part Form

![Add Part Modal](../../../screenshots/captured/module-ui/maintenance/spares/add-part-modal.png)
*Add Spare Part modal — full inventory registration form.*

| Field | Description |
|-------|-------------|
| Part No | Unique reference (locked after creation) |
| Unit | Unit of measure: pcs, litre, kg, etc. |
| Name | Full part name |
| Description | Additional details |
| Current Stock | Initial stock quantity |
| Reorder Level | Trigger level for low-stock alert |
| Unit Cost (KES) | Cost per unit |
| Lead Time (days) | Days to receive from supplier |
| Supplier | Preferred supplier name |

API: `POST /api/v1/maintenance/spare-parts`, `PUT /api/v1/maintenance/spare-parts/{id}`

## Record Spare Part Usage

Records stock consumption for a specific asset maintenance event.

| Field | Description |
|-------|-------------|
| Spare Part | Select from inventory (shows current stock) |
| Asset | Asset the parts were used on |
| Quantity Used | Amount consumed |
| Unit Cost (KES) | Override cost (defaults to part's unit_cost) |
| Notes | Free text |

Stock is decremented automatically on save.

API: `POST /api/v1/maintenance/spare-usage`
