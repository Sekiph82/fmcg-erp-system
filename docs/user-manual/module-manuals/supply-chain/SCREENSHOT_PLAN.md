# Supply Chain Module — Screenshot Plan

Screenshots are gitignored (`docs/user-manual/screenshots/captured/`). Capture manually and reference in chapters.

## Priority Screenshots

| Chapter | Screen | Route | Description |
|---------|--------|-------|-------------|
| 01-purchase-requisitions | PR list | `/dashboard/procurement?tab=purchase-requests` | PRs with mixed statuses |
| 01-purchase-requisitions | PR create form | `/dashboard/procurement?tab=purchase-requests` | Open create form |
| 02-purchase-orders | PO list | `/dashboard/procurement?tab=purchase-orders` | POs with statuses |
| 02-purchase-orders | PO detail | `/dashboard/procurement/po/[id]` | Full PO with lines |
| 03-rfq | RFQ list | `/dashboard/procurement?tab=rfq` | RFQ with supplier responses |
| 04-deliveries | GRN list | `/dashboard/procurement?tab=deliveries` | GRNs with statuses |
| 05-suppliers | Supplier list | `/dashboard/procurement?tab=suppliers` | Supplier registry |
| 07-inventory-stock | Stock ledger | `/dashboard/inventory?tab=stock` | Stock positions with reorder alert |
| 07-inventory-stock | Stock entry form | `/dashboard/inventory?tab=entry` | Receive stock form |
| 08-movements | Movement ledger | `/dashboard/movements` | Movement list with types |
| 08-movements | Cycle count | `/dashboard/cycle-count` | Count sheet |
| 09-warehouses | Warehouse list | `/dashboard/warehouses` | Warehouse list with types |
| 10-wms | WMS zones | `/dashboard/wms?tab=zones` | Zone list |
| 10-wms | Quarantine form | `/dashboard/wms?tab=quarantine` | Quarantine action form |
| 11-logistics | Logistics overview | `/dashboard/logistics` | KPI tiles + ETA alerts |
| 11-logistics | Shipment list | `/dashboard/logistics?tab=shipments` | Shipments with status badges |

## Capture Notes

- Log in as a user with full `procurement.view` + `inventory.view` permissions
- Use a company with realistic test data (multiple warehouses, POs, GRNs)
- Capture at 1280×800 minimum
- Save to `docs/user-manual/screenshots/captured/supply-chain/`
- Name: `[chapter-no]-[description].png` e.g. `07-stock-ledger.png`
