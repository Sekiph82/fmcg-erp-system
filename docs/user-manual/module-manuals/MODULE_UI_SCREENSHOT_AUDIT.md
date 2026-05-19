# Module UI Screenshot Audit

**Date:** 2026-05-19  
**Status:** Pre-fix audit

---

## Summary

| Module | Chapters | Markdown Image Refs | Real ERP UI Screenshots Referenced | Action/Modal Screenshots | Status |
|--------|----------|--------------------|------------------------------------|--------------------------|--------|
| Manufacturing | 13 | 0 | 0 | 0 | NOT COMPLETE |
| Supply Chain | 12 | 0 | 0 | 0 | NOT COMPLETE |

**Root cause:** All 40+ real ERP UI screenshots exist in `docs/user-manual/screenshots/captured/` but none are referenced in any chapter markdown file. The PDF generators embed chapter markdown as-is, so PDFs contain zero images.

**Action/modal screenshots** (New Recipe modal, Import BOM modal, etc.) do not yet exist and require Playwright capture with the app running.

---

## Manufacturing Module

### Chapter Files
| File | Markdown Image Refs | Notes |
|------|--------------------|-|
| 00-overview.md | 0 | |
| 01-recipes.md | 0 | Missing: recipes overview, new recipe modal, import BOM modal |
| 02-recipes-import.md | 0 | |
| 03-bom-formula.md | 0 | Missing: bom overview |
| 04-production-plans.md | 0 | Missing: production overview, orders tab |
| 05-work-orders.md | 0 | Missing: execution tab, material flow tab |
| 06-batch-lots.md | 0 | |
| 07-quality-control.md | 0 | Missing: quality overview, inspections |
| 08-shop-floor.md | 0 | Missing: shop floor overview, terminal |
| 09-planning-scheduling.md | 0 | Missing: planning overview, mrp, mps, capacity |
| 10-npd.md | 0 | Missing: npd overview |
| 11-oee-reporting.md | 0 | |
| 12-compliance.md | 0 | Missing: compliance overview |

### Available Real ERP Screenshots (already captured)
| Screenshot File | ID |
|-----------------|----|
| captured/057_recipes.png | recipes |
| captured/053_bom.png | bom |
| captured/054_bom-list.png | bom-list |
| captured/038_production.png | production |
| captured/039_production-orders.png | production-orders |
| captured/040_production-execution.png | production-execution |
| captured/041_production-material-flow.png | production-material-flow |
| captured/042_production-costing.png | production-costing |
| captured/050_shop-floor.png | shop-floor |
| captured/051_shop-floor-terminal.png | shop-floor-terminal |
| captured/052_shop-floor-supervisor.png | shop-floor-supervisor |
| captured/058_planning.png | planning |
| captured/059_planning-mrp.png | planning-mrp |
| captured/060_planning-mps.png | planning-mps |
| captured/061_planning-capacity.png | planning-capacity |
| captured/062_quality.png | quality |
| captured/063_quality-inspections.png | quality-inspections |
| captured/064_quality-qms.png | quality-qms |
| captured/065_quality-allergen.png | quality-allergen |
| captured/066_quality-certificates.png | quality-certificates |
| captured/069_compliance.png | compliance |
| captured/070_compliance-gs1.png | compliance-gs1 |
| captured/118_npd.png | npd |

### Action/Modal Screenshots — Status
| Screenshot | Status |
|------------|--------|
| recipes-new-recipe-modal.png | MISSING — needs capture |
| recipes-import-bom-modal.png | MISSING — needs capture |
| quality-new-inspection-modal.png | MISSING — needs capture |

### PDF Validation
- Manufacturing PDF exists: Yes (`pdf-output/FMCG-ERP-Manufacturing-Manual.pdf`, 0.5 MB)
- Screenshots referenced in PDF: 0
- Status: **NOT COMPLETE** — no images in PDF

---

## Supply Chain Module

### Chapter Files
| File | Markdown Image Refs | Notes |
|------|--------------------|-|
| 00-overview.md | 0 | |
| 01-purchase-requisitions.md | 0 | Missing: procurement-requests overview |
| 02-purchase-orders.md | 0 | Missing: procurement-orders overview |
| 03-rfq.md | 0 | Missing: procurement-rfq overview |
| 04-deliveries.md | 0 | Missing: procurement-deliveries |
| 05-suppliers.md | 0 | Missing: suppliers overview |
| 06-blanket-reorder.md | 0 | Reference stub only |
| 07-inventory-stock.md | 0 | Missing: inventory, inventory-stock |
| 08-movements.md | 0 | Missing: inventory-movements |
| 09-warehouses.md | 0 | Missing: warehouses overview |
| 10-wms.md | 0 | Missing: wms, wms-zones, wms-quarantine |
| 11-logistics.md | 0 | Missing: logistics, logistics-shipments |

### Available Real ERP Screenshots (already captured)
| Screenshot File | ID |
|-----------------|----|
| captured/029_procurement.png | procurement |
| captured/030_procurement-requests.png | procurement-requests |
| captured/031_procurement-orders.png | procurement-orders |
| captured/032_procurement-rfq.png | procurement-rfq |
| captured/033_procurement-deliveries.png | procurement-deliveries |
| captured/034_procurement-suppliers.png | procurement-suppliers |
| captured/014_suppliers.png | suppliers |
| captured/017_inventory.png | inventory |
| captured/018_inventory-stock.png | inventory-stock |
| captured/019_inventory-movements.png | inventory-movements |
| captured/020_inventory-shelf-life.png | inventory-shelf-life |
| captured/021_inventory-cycle-count.png | inventory-cycle-count |
| captured/025_wms.png | wms |
| captured/026_wms-zones.png | wms-zones |
| captured/027_wms-locations.png | wms-locations |
| captured/028_wms-quarantine.png | wms-quarantine |
| captured/083_logistics.png | logistics |
| captured/084_logistics-shipments.png | logistics-shipments |
| captured/015_warehouses.png | warehouses |

### Action/Modal Screenshots — Status
| Screenshot | Status |
|------------|--------|
| procurement-new-request-modal.png | MISSING — needs capture |
| inventory-stock-entry-form.png | MISSING — needs capture |

### PDF Validation
- Supply Chain PDF exists: Yes (`pdf-output/FMCG-ERP-Supply-Chain-Manual.pdf`, 0.5 MB)
- Screenshots referenced in PDF: 0
- Status: **NOT COMPLETE** — no images in PDF

---

## Fix Plan

1. Create `module-action-routes.json` — define action/modal screenshot requirements
2. Create Playwright spec `manual-action-screenshots.spec.ts` — capture modal screenshots
3. Capture action screenshots with app running (confirmed: app is live on localhost:3000)
4. Add all existing screenshot refs + new action screenshots to chapter markdown
5. Regenerate both PDFs
6. Verify PDF image counts

**Expected result after fix:**
- Manufacturing PDF: ~25+ images embedded
- Supply Chain PDF: ~20+ images embedded
- Missing screenshots: 0
