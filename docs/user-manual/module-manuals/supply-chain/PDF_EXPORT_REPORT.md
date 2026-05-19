# Supply Chain Module Manual — PDF Export Report

## Output

| Field | Value |
|-------|-------|
| File | `docs/user-manual/pdf-output/FMCG-ERP-Supply-Chain-Manual.pdf` |
| Size | 0.5 MB |
| Chapters | 12 |
| Images loaded | 0 / 0 (no image refs in chapters yet) |
| Generator | `pdf-export/generate-supply-chain-pdf.mjs` |

## Chapter List

| # | File | Topic |
|---|------|-------|
| 0 | 00-overview.md | Module overview, subsystems, permissions |
| 1 | 01-purchase-requisitions.md | PR creation, approval, convert to PO |
| 2 | 02-purchase-orders.md | PO lifecycle, lines, GRN, payment |
| 3 | 03-rfq.md | RFQ, blanket agreements, reorder, suggestions |
| 4 | 04-deliveries.md | GRN creation, posting, import shipment |
| 5 | 05-suppliers.md | Supplier master, AVL, portal, performance |
| 6 | 06-blanket-reorder.md | Reference stub → 03-rfq.md |
| 7 | 07-inventory-stock.md | Stock ledger, entry, issue, transfer, adjust |
| 8 | 08-movements.md | Movement types, cycle count, shelf life, valuation |
| 9 | 09-warehouses.md | Warehouse master, types, scoping |
| 10 | 10-wms.md | Zones, locations, handling units, pick waves, quarantine |
| 11 | 11-logistics.md | Import shipments, KPIs, status values, tabs |

## Notes

- Screenshots not yet embedded (captured folder present, 140 PNGs; no refs in supply-chain chapters)
- To embed screenshots: add `![alt](../../../screenshots/captured/supply-chain/filename.png)` to chapter files, then re-run generator
- PDF is gitignored — not committed to repo
