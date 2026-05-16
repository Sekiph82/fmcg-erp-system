# FMCG ERP System — Documentation Audit
**Audit Date:** 2026-05-16  
**Auditor:** Claude Code (static code inspection)  
**Method:** Repository scan — no live execution, no screenshots  
**Repository Root:** `fmcg-erp-system-main/`

---

## 1. Executive Summary

| Metric | Count |
|---|---|
| Frontend pages (page.tsx files) | 755 |
| Frontend navigation sections (sidebar) | ~50 sections across 14 clusters |
| Backend endpoint router groups | 133 (28 ModuleDefinitions + 105 EndpointRouteDefinitions) |
| ORM model files | 110 |
| ORM model classes | 134+ |
| Pydantic schema files | 109 |
| Pydantic schema classes | 1,658+ |
| Service files | 113 |
| Enum/Status classes | 690+ |
| Defined roles | 37 |
| Mock/Stub/Placeholder patterns found | 60+ |
| Pages with TODO/mock/placeholder keywords | 371 of 755 |

**Key Risks Found:**
- AI module runs in mock mode by default (no API key configured) — responses are labeled but could mislead users
- M-Pesa integration uses fake checkout/merchant IDs in placeholder service — **Critical production risk**
- WhatsApp: `is_demo_mode=True` by default in model — messages are simulated, not sent
- IoT/MQTT: explicitly a stub, no live streaming
- Forecast module: Prophet/AI forecasting is stubbed
- Bank API sync: mock Kenyan bank sync
- OTP dispatch in auth flow: TODO, not implemented
- eTIMS (KRA e-invoice): placeholder for live KRA call

---

## 2. Frontend Inventory

> Navigation source: `frontend/src/components/nav-config.tsx`  
> Pages discovered from: `frontend/src/app/**/*.tsx` (755 page.tsx files)

### 2.1 Cluster: Master Data

| Module | Page/Screen | Route/Path | UI File Path | Visible Buttons/Actions | Forms/Tables Found | Notes |
|---|---|---|---|---|---|---|
| Master Data | Products | /dashboard/products | frontend/src/app/dashboard/products/page.tsx | Not clearly discoverable from current code | Table expected | Backend: /products endpoint exists |
| Master Data | Materials | /dashboard/materials | frontend/src/app/dashboard/materials/page.tsx | Not clearly discoverable from current code | Table expected | Backend: /materials endpoint exists |
| Master Data | Suppliers | /dashboard/suppliers | frontend/src/app/dashboard/suppliers/page.tsx | Not clearly discoverable from current code | Table expected | Backend: /suppliers endpoint exists |
| Master Data | Warehouses | /dashboard/warehouses | frontend/src/app/dashboard/warehouses/page.tsx | Not clearly discoverable from current code | Table expected | Backend: /warehouses endpoint exists |
| Master Data | Customers | /dashboard/sales/customers | frontend/src/app/dashboard/sales/customers/page.tsx | Not clearly discoverable from current code | Table expected | Backend: /sales customers endpoint exists |
| Master Data | Recipes / BOM | /dashboard/recipes | frontend/src/app/dashboard/recipes/page.tsx | Not clearly discoverable from current code | Table expected | Permission: recipe.view |

### 2.2 Cluster: Planning

| Module | Page/Screen | Route/Path | UI File Path | Visible Buttons/Actions | Forms/Tables Found | Notes |
|---|---|---|---|---|---|---|
| NPD | NPD Projects | /dashboard/npd | frontend/src/app/dashboard/npd/page.tsx | Not clearly discoverable | Table + detail expected | Permission: npd.view; Backend: /npd-workflow |
| NPD | NPD Detail | /dashboard/npd/[id] | frontend/src/app/dashboard/npd/[id]/page.tsx | Not clearly discoverable | Detail form | Dynamic route |
| MRP | MRP Dashboard | /dashboard/mrp | frontend/src/app/dashboard/mrp/page.tsx | Run MRP, View Suggestions | Dashboard widgets | Backend: /mrp |
| MRP | Planner Workbench | /dashboard/mrp/workbench | frontend/src/app/dashboard/mrp/workbench/page.tsx | Not clearly discoverable | Table/grid expected | |
| MRP | MRP Runs | /dashboard/mrp/run | frontend/src/app/dashboard/mrp/run/page.tsx | Not clearly discoverable | Run log table | |
| MRP | Suggestions | /dashboard/mrp/suggestions | frontend/src/app/dashboard/mrp/suggestions/page.tsx | Convert to PO | Table | |
| MRP | Demand Forecasting | /dashboard/mrp/forecast | frontend/src/app/dashboard/mrp/forecast/page.tsx | Not clearly discoverable | Chart + table | Forecast service uses Prophet stub |
| MRP | Forecast Accuracy | /dashboard/mrp/forecast/accuracy | frontend/src/app/dashboard/mrp/forecast/accuracy/page.tsx | Not clearly discoverable | Chart | |
| MRP | Cross-SKU Correlation | /dashboard/mrp/forecast/correlation | frontend/src/app/dashboard/mrp/forecast/correlation/page.tsx | Not clearly discoverable | Chart | |
| MPS | MPS Dashboard | /dashboard/mps | frontend/src/app/dashboard/mps/page.tsx | Not clearly discoverable | Dashboard | Backend: /mps |
| MPS | Planning Board | /dashboard/mps/planning-board | frontend/src/app/dashboard/mps/planning-board/page.tsx | Not clearly discoverable | Gantt/grid | |
| MPS | Capacity Heatmap | /dashboard/mps/capacity | frontend/src/app/dashboard/mps/capacity/page.tsx | Not clearly discoverable | Heatmap | |
| MPS | Campaign View | /dashboard/mps/campaigns | frontend/src/app/dashboard/mps/campaigns/page.tsx | Not clearly discoverable | Table | |
| MPS | What-If Simulator | /dashboard/mps/whatif | frontend/src/app/dashboard/mps/whatif/page.tsx | Not clearly discoverable | Simulator form | |
| Planning | Planning Dashboard | /dashboard/planning | frontend/src/app/dashboard/planning/page.tsx | Not clearly discoverable | Dashboard | Permission: planning.view; Backend: /planning |
| Planning | Schedule Board | /dashboard/planning/schedule | frontend/src/app/dashboard/planning/schedule/page.tsx | Not clearly discoverable | Board | |
| Planning | Capacity Board | /dashboard/planning/capacity | frontend/src/app/dashboard/planning/capacity/page.tsx | Not clearly discoverable | Board | |
| Planning | Bottleneck Explorer | /dashboard/planning/bottlenecks | frontend/src/app/dashboard/planning/bottlenecks/page.tsx | Not clearly discoverable | Chart | |
| Planning | Simulation Sandbox | /dashboard/planning/simulation | frontend/src/app/dashboard/planning/simulation/page.tsx | Not clearly discoverable | Simulator | |
| Planning | Changeover Matrix | /dashboard/planning/changeover | frontend/src/app/dashboard/planning/changeover/page.tsx | Not clearly discoverable | Matrix | |
| Proc. Suggestion | PS Dashboard | /dashboard/procurement-suggestion | frontend/src/app/dashboard/procurement-suggestion/page.tsx | Not clearly discoverable | Dashboard | Backend: /procurement/suggestions |
| Proc. Suggestion | Suggestions | /dashboard/procurement-suggestion/suggestions | frontend/src/app/dashboard/procurement-suggestion/suggestions/page.tsx | Convert, Approve | Table | |
| Proc. Suggestion | AI Agents | /dashboard/procurement-suggestion/ai | frontend/src/app/dashboard/procurement-suggestion/ai/page.tsx | Not clearly discoverable | AI output | |
| Projects | All Projects | /dashboard/projects | frontend/src/app/dashboard/projects/page.tsx | New Project | Table | Backend: /projects |
| Projects | Dashboard | /dashboard/projects/dashboard | frontend/src/app/dashboard/projects/dashboard/page.tsx | Not clearly discoverable | KPI dashboard | |
| Projects | Project Detail | /dashboard/projects/[id] | frontend/src/app/dashboard/projects/[id]/page.tsx | Edit, Delete | Detail view | |

### 2.3 Cluster: Production / MES

| Module | Page/Screen | Route/Path | UI File Path | Visible Buttons/Actions | Forms/Tables Found | Notes |
|---|---|---|---|---|---|---|
| Production | Production Plans | /dashboard/production | frontend/src/app/dashboard/production/page.tsx | New Plan, Release | Table | Permission: production.view; Backend: /production |
| Production | Production Orders | /dashboard/production/orders | frontend/src/app/dashboard/production/orders/page.tsx | New Order, Release, Complete | Table | Status workflow: DRAFT→RELEASED→IN_PROGRESS→COMPLETED |
| Production | Order Detail | /dashboard/production/orders/[id] | frontend/src/app/dashboard/production/orders/[id]/page.tsx | Release, Cancel, Complete | Detail + lines | |
| Production | Work Centers | /dashboard/production/work-centers | frontend/src/app/dashboard/production/work-centers/page.tsx | Add, Edit | Table | |
| Production | Scheduling | /dashboard/production/scheduling | frontend/src/app/dashboard/production/scheduling/page.tsx | Schedule, Reschedule | Gantt/board | |
| Production | OEE Records | /dashboard/production/oee | frontend/src/app/dashboard/production/oee/page.tsx | Not clearly discoverable | Chart + table | |
| Production | Waste & Yield | /dashboard/production/waste-yield | frontend/src/app/dashboard/production/waste-yield/page.tsx | Not clearly discoverable | Table | |
| Production | Batch/Lots | /dashboard/production/batch-lots | frontend/src/app/dashboard/production/batch-lots/page.tsx | Not clearly discoverable | Table | |
| Production | Costing | /dashboard/production/costing | frontend/src/app/dashboard/production/costing/page.tsx | Not clearly discoverable | Table | |
| Production | WIP Valuation | /dashboard/production/wip | frontend/src/app/dashboard/production/wip/page.tsx | Not clearly discoverable | Table | |
| Production | Variance Analysis | /dashboard/production/variance | frontend/src/app/dashboard/production/variance/page.tsx | Not clearly discoverable | Chart | |
| Production | AI Intelligence | /dashboard/production/ai | frontend/src/app/dashboard/production/ai/page.tsx | Not clearly discoverable | AI output | Backend: /production-ai |
| Production | MES Reports | /dashboard/production/reports | frontend/src/app/dashboard/production/reports/page.tsx | Export | Report list | |
| Prod. Execution | Order Dashboard | /dashboard/production-execution | frontend/src/app/dashboard/production-execution/page.tsx | Start, Pause, Complete | Dashboard | Backend: /production-execution |
| Prod. Execution | Work Order Queue | /dashboard/production-execution/work-orders | frontend/src/app/dashboard/production-execution/work-orders/page.tsx | Start WO, Complete WO | Queue table | |
| Prod. Execution | Order Detail | /dashboard/production-execution/[id] | frontend/src/app/dashboard/production-execution/[id]/page.tsx | Record Output, Scrap | Detail + materials | |
| Prod. Execution | Genealogy | /dashboard/production-execution/[id]/genealogy | frontend/src/app/dashboard/production-execution/[id]/genealogy/page.tsx | Not clearly discoverable | Genealogy graph | |
| BOM & Formula | BOM Master | /dashboard/bom | frontend/src/app/dashboard/bom/page.tsx | New BOM, Approve, Release | Table | Permission: bom.view; Backend: /bom |
| BOM & Formula | BOM Detail | /dashboard/bom/[id] | frontend/src/app/dashboard/bom/[id]/page.tsx | Approve, Release, Archive | Detail + lines | |
| BOM & Formula | Compliance | /dashboard/bom/[id]/compliance | frontend/src/app/dashboard/bom/[id]/compliance/page.tsx | Not clearly discoverable | Compliance check | |
| BOM & Formula | Costing | /dashboard/bom/[id]/costing | frontend/src/app/dashboard/bom/[id]/costing/page.tsx | Run Costing | Cost breakdown | |
| BOM & Formula | Explode | /dashboard/bom/[id]/explode | frontend/src/app/dashboard/bom/[id]/explode/page.tsx | Explode | Tree/table | |
| BOM & Formula | Conversion Profiles | /dashboard/bom/conversion | frontend/src/app/dashboard/bom/conversion/page.tsx | Not clearly discoverable | Table | |
| BOM & Formula | Substitute Manager | /dashboard/bom/substitutes | frontend/src/app/dashboard/bom/substitutes/page.tsx | Not clearly discoverable | Table | |
| BOM & Formula | Version Compare | /dashboard/bom/compare | frontend/src/app/dashboard/bom/compare/page.tsx | Not clearly discoverable | Compare view | |
| Shop Floor | SF Dashboard | /dashboard/shop-floor | frontend/src/app/dashboard/shop-floor/page.tsx | Not clearly discoverable | Dashboard | Backend: /shop-floor |
| Shop Floor | Operator Terminal | /dashboard/shop-floor/terminal | frontend/src/app/dashboard/shop-floor/terminal/page.tsx | Start, Complete, Scrap | Terminal UI | High-risk: production execution |
| Shop Floor | Supervisor Console | /dashboard/shop-floor/supervisor | frontend/src/app/dashboard/shop-floor/supervisor/page.tsx | Not clearly discoverable | Console | |
| Shop Floor | Queue Board | /dashboard/shop-floor/queue | frontend/src/app/dashboard/shop-floor/queue/page.tsx | Not clearly discoverable | Queue | |
| Shop Floor | Downtime Board | /dashboard/shop-floor/downtime | frontend/src/app/dashboard/shop-floor/downtime/page.tsx | Log Downtime | Board | |
| Shop Floor | Shift Handover | /dashboard/shop-floor/handover | frontend/src/app/dashboard/shop-floor/handover/page.tsx | Submit Handover | Form | |
| Machine Ops | MO Dashboard | /dashboard/machine-ops | frontend/src/app/dashboard/machine-ops/page.tsx | Not clearly discoverable | Dashboard | Backend: /machine-ops |
| Machine Ops | Machine Master | /dashboard/machine-ops/machines | frontend/src/app/dashboard/machine-ops/machines/page.tsx | Add Machine | Table | |
| Machine Ops | Operators | /dashboard/machine-ops/operators | frontend/src/app/dashboard/machine-ops/operators/page.tsx | Assign, Cert | Table | |
| Machine Ops | Teams | /dashboard/machine-ops/teams | frontend/src/app/dashboard/machine-ops/teams/page.tsx | Not clearly discoverable | Table | |
| Machine Ops | Runtime Logs | /dashboard/machine-ops/runtime | frontend/src/app/dashboard/machine-ops/runtime/page.tsx | Not clearly discoverable | Table | |
| Machine Ops | OEE/Performance | /dashboard/machine-ops/performance | frontend/src/app/dashboard/machine-ops/performance/page.tsx | Not clearly discoverable | Chart | |
| Machine Ops | Downtime Board | /dashboard/machine-ops/downtime | frontend/src/app/dashboard/machine-ops/downtime/page.tsx | Log Downtime | Board | |
| Machine Ops | Cost Contribution | /dashboard/machine-ops/costing | frontend/src/app/dashboard/machine-ops/costing/page.tsx | Not clearly discoverable | Table | |
| Machine Ops | Cert Monitor | /dashboard/machine-ops/certs | frontend/src/app/dashboard/machine-ops/certs/page.tsx | Not clearly discoverable | Table | |
| Machine Ops | Assignment Board | /dashboard/machine-ops/assignment | frontend/src/app/dashboard/machine-ops/assignment/page.tsx | Assign | Board | |
| Material Flow | MF Dashboard | /dashboard/material-flow | frontend/src/app/dashboard/material-flow/page.tsx | Not clearly discoverable | Dashboard | Backend: /material-flow |
| Material Flow | Issue to Production | /dashboard/material-flow/issue | frontend/src/app/dashboard/material-flow/issue/page.tsx | Issue | Form | High-risk: stock movement |
| Material Flow | Reservations | /dashboard/material-flow/reservations | frontend/src/app/dashboard/material-flow/reservations/page.tsx | Reserve, Cancel | Table | |
| Material Flow | WIP/Stage Transfer | /dashboard/material-flow/wip-transfer | frontend/src/app/dashboard/material-flow/wip-transfer/page.tsx | Transfer | Form | |
| Material Flow | Bulk Transfer | /dashboard/material-flow/bulk-transfer | frontend/src/app/dashboard/material-flow/bulk-transfer/page.tsx | Transfer | Form | High-risk: bulk stock move |
| Material Flow | Packaging Issue | /dashboard/material-flow/packaging | frontend/src/app/dashboard/material-flow/packaging/page.tsx | Issue | Form | |
| Material Flow | FG Receipt | /dashboard/material-flow/fg-receipt | frontend/src/app/dashboard/material-flow/fg-receipt/page.tsx | Receive | Form | High-risk: inventory increase |
| Material Flow | Returns & Reversals | /dashboard/material-flow/returns | frontend/src/app/dashboard/material-flow/returns/page.tsx | Return, Reverse | Form | |
| Material Flow | Tank Occupancy | /dashboard/material-flow/tanks | frontend/src/app/dashboard/material-flow/tanks/page.tsx | Not clearly discoverable | Chart | |
| Material Flow | Flow History | /dashboard/material-flow/history | frontend/src/app/dashboard/material-flow/history/page.tsx | Export | Table | |
| Material Flow | Reconciliation | /dashboard/material-flow/reconciliation | frontend/src/app/dashboard/material-flow/reconciliation/page.tsx | Reconcile | Form | High-risk |
| Material Flow | Stage Config | /dashboard/material-flow/stages | frontend/src/app/dashboard/material-flow/stages/page.tsx | Add Stage | Table | |

### 2.4 Cluster: Inventory & Warehouse

| Module | Page/Screen | Route/Path | UI File Path | Visible Buttons/Actions | Forms/Tables Found | Notes |
|---|---|---|---|---|---|---|
| Warehouse/Inventory | Inventory | /dashboard/inventory | frontend/src/app/dashboard/inventory/page.tsx | Adjust Stock, Export | Table | Permission: inventory.view |
| Warehouse/Inventory | Stock Movements | /dashboard/movements | frontend/src/app/dashboard/movements/page.tsx | Export | Table | |
| Warehouse/Inventory | Serial Numbers | /dashboard/inventory/serials | frontend/src/app/dashboard/inventory/serials/page.tsx | Not clearly discoverable | Table | Backend: /inventory/serials |
| Warehouse/Inventory | Valuation | /dashboard/inventory/valuation | frontend/src/app/dashboard/inventory/valuation/page.tsx | Not clearly discoverable | Report | |
| WMS | WMS/Zones | /dashboard/wms | frontend/src/app/dashboard/wms/page.tsx | Not clearly discoverable | Dashboard | Permission: wms.view; Backend: /wms |
| WMS | Stock Counts | /dashboard/wms/counts | frontend/src/app/dashboard/wms/counts/page.tsx | Start Count, Close | Table | High-risk: stock adjustment |
| WMS | Count Detail | /dashboard/wms/counts/[id] | frontend/src/app/dashboard/wms/counts/[id]/page.tsx | Close Count, Adjust | Detail | |
| WMS | Picking Ops | /dashboard/wms/picking | frontend/src/app/dashboard/wms/picking/page.tsx | Pick, Complete | Queue | |
| WMS | Bin Replenishment | /dashboard/wms/replenishment | frontend/src/app/dashboard/wms/replenishment/page.tsx | Replenish | Queue | |
| WMS | WMS Reports | /dashboard/wms/reports | frontend/src/app/dashboard/wms/reports/page.tsx | Export | Report list | |
| WMS | Putaway Tasks | /dashboard/putaway | frontend/src/app/dashboard/putaway/page.tsx | Execute, Complete | Table | |
| WMS | Putaway Rules | /dashboard/putaway/rules | frontend/src/app/dashboard/putaway/rules/page.tsx | Add Rule | Table | |
| Shelf Life/FEFO | SL Dashboard | /dashboard/shelf-life | frontend/src/app/dashboard/shelf-life/page.tsx | Not clearly discoverable | Dashboard | Permission: shelf_life.view |
| Shelf Life/FEFO | FEFO Config | /dashboard/shelf-life/fefo-config | frontend/src/app/dashboard/shelf-life/fefo-config/page.tsx | Configure | Config form | |
| Shelf Life/FEFO | Lot Aging Explorer | /dashboard/shelf-life/lot-aging | frontend/src/app/dashboard/shelf-life/lot-aging/page.tsx | Not clearly discoverable | Table/chart | |
| Shelf Life/FEFO | Near-Expiry Board | /dashboard/shelf-life/near-expiry | frontend/src/app/dashboard/shelf-life/near-expiry/page.tsx | Hold, Release | Board | Medium-risk |
| Shelf Life/FEFO | Expired Stock Board | /dashboard/shelf-life/expired | frontend/src/app/dashboard/shelf-life/expired/page.tsx | Dispose, Hold | Board | High-risk: disposal |
| Shelf Life/FEFO | Retest Queue | /dashboard/shelf-life/retest-queue | frontend/src/app/dashboard/shelf-life/retest-queue/page.tsx | Approve Retest, Reject | Queue | Permission: shelf_life.approve |
| Shelf Life/FEFO | Shipment Validation | /dashboard/shelf-life/shipment-validation | frontend/src/app/dashboard/shelf-life/shipment-validation/page.tsx | Approve, Block | Form | |
| Shelf Life/FEFO | Production Validation | /dashboard/shelf-life/production-validation | frontend/src/app/dashboard/shelf-life/production-validation/page.tsx | Validate, Block | Form | |
| Shelf Life/FEFO | FEFO Compliance Audit | /dashboard/shelf-life/compliance | frontend/src/app/dashboard/shelf-life/compliance/page.tsx | Export | Report | Permission: shelf_life.report |
| Shelf Life/FEFO | Disposition Console | /dashboard/shelf-life/disposition | frontend/src/app/dashboard/shelf-life/disposition/page.tsx | Dispose, Donate, Rework | Console | Permission: shelf_life.dispose; Critical-risk |
| Shelf Life/FEFO | Customer SL Rules | /dashboard/shelf-life/customer-rules | frontend/src/app/dashboard/shelf-life/customer-rules/page.tsx | Add Rule, Edit | Table | Permission: shelf_life.edit |
| Shelf Life/FEFO | Bulk Hold Monitor | /dashboard/shelf-life/bulk-hold-monitor | frontend/src/app/dashboard/shelf-life/bulk-hold-monitor/page.tsx | Hold, Release | Table | Permission: shelf_life.hold; High-risk |
| Traceability | Trace Dashboard | /dashboard/traceability | frontend/src/app/dashboard/traceability/page.tsx | Not clearly discoverable | Dashboard | |
| Traceability | Trace Search | /dashboard/traceability/search | frontend/src/app/dashboard/traceability/search/page.tsx | Search | Search form | |
| Traceability | Backward Trace | /dashboard/traceability/backward | frontend/src/app/dashboard/traceability/backward/page.tsx | Trace | Form + tree | |
| Traceability | Forward Trace | /dashboard/traceability/forward | frontend/src/app/dashboard/traceability/forward/page.tsx | Trace | Form + tree | |
| Traceability | Genealogy Graph | /dashboard/traceability/genealogy | frontend/src/app/dashboard/traceability/genealogy/page.tsx | Not clearly discoverable | Graph | |
| Traceability | Recall List | /dashboard/traceability/recalls | frontend/src/app/dashboard/traceability/recalls/page.tsx | Initiate Recall, Close | Table | Critical-risk |
| Traceability | Recall Detail | /dashboard/traceability/recalls/[id] | frontend/src/app/dashboard/traceability/recalls/[id]/page.tsx | Execute Recall, Notify | Detail | Critical-risk |
| Traceability | Mock Recall Drill | /dashboard/traceability/mock-recall | frontend/src/app/dashboard/traceability/mock-recall/page.tsx | Run Drill | Drill UI | Medium-risk; labeled mock |
| Traceability | Comm. Templates | /dashboard/traceability/templates | frontend/src/app/dashboard/traceability/templates/page.tsx | Add Template | Table | |
| Traceability | Regulatory Reports | /dashboard/traceability/regulatory | frontend/src/app/dashboard/traceability/regulatory/page.tsx | Export | Report | |
| Cycle Count | Dashboard | /dashboard/cycle-count | frontend/src/app/dashboard/cycle-count/page.tsx | New Plan | Dashboard | Permission: inventory.view |
| Cycle Count | Count Plans | /dashboard/cycle-count/plans | frontend/src/app/dashboard/cycle-count/plans/page.tsx | Create Plan, Activate | Table | |
| Cycle Count | Count Tasks | /dashboard/cycle-count/tasks | frontend/src/app/dashboard/cycle-count/tasks/page.tsx | Assign, Start | Table | |
| Cycle Count | Count Entries | /dashboard/cycle-count/entries | frontend/src/app/dashboard/cycle-count/entries/page.tsx | Enter Count | Form | |
| Cycle Count | Variance Review | /dashboard/cycle-count/variances | frontend/src/app/dashboard/cycle-count/variances/page.tsx | Approve, Reject | Table | High-risk: stock adjustment |
| Cycle Count | Reports & AI | /dashboard/cycle-count/reports | frontend/src/app/dashboard/cycle-count/reports/page.tsx | Export | Report | |
| Containers | Container Management | /dashboard/containers | frontend/src/app/dashboard/containers/page.tsx | Not clearly discoverable | Table | Backend: /containers |
| Containers | Outstanding | /dashboard/containers/outstanding | frontend/src/app/dashboard/containers/outstanding/page.tsx | Not clearly discoverable | Table | |

### 2.5 Cluster: Quality & Compliance

| Module | Page/Screen | Route/Path | UI File Path | Visible Buttons/Actions | Forms/Tables Found | Notes |
|---|---|---|---|---|---|---|
| Quality Control | QC Inspections | /dashboard/quality | frontend/src/app/dashboard/quality/page.tsx | Pass, Fail, Hold | Table + form | Permission: quality.view |
| Quality Control | QC Parameters | /dashboard/quality/parameters | frontend/src/app/dashboard/quality/parameters/page.tsx | Add Parameter | Table | |
| Quality Control | Consumer Complaints | /dashboard/quality/consumer-complaints | frontend/src/app/dashboard/quality/consumer-complaints/page.tsx | Create, Escalate, Close | Table | Permission: consumer_complaints.view |
| Quality Control | Reg. Certificates | /dashboard/quality/certificates | frontend/src/app/dashboard/quality/certificates/page.tsx | Upload, Expire | Table | Backend: /regulatory-certs |
| Quality Control | Brand Assets/DAM | /dashboard/brand-assets | frontend/src/app/dashboard/brand-assets/page.tsx | Upload, Archive | Grid/table | Backend: /brand-assets |
| Quality Control | QC Reports | /dashboard/quality/reports | frontend/src/app/dashboard/quality/reports/page.tsx | Export | Report | |
| QMS & HACCP | QMS Dashboard | /dashboard/qms | frontend/src/app/dashboard/qms/page.tsx | Not clearly discoverable | Dashboard | Permission: quality.view; Backend: /qms |
| QMS & HACCP | QC Inspections | /dashboard/qms/inspections | frontend/src/app/dashboard/qms/inspections/page.tsx | Pass, Fail, Hold | Table | |
| QMS & HACCP | QC Templates | /dashboard/qms/templates | frontend/src/app/dashboard/qms/templates/page.tsx | Add Template | Table | |
| QMS & HACCP | HACCP Analysis | /dashboard/qms/haccp | frontend/src/app/dashboard/qms/haccp/page.tsx | Add Hazard | Table | |
| QMS & HACCP | CCP Monitoring | /dashboard/qms/ccp | frontend/src/app/dashboard/qms/ccp/page.tsx | Record Reading, Alert | Table | High-risk: food safety |
| QMS & HACCP | Deviations | /dashboard/qms/deviations | frontend/src/app/dashboard/qms/deviations/page.tsx | Create Deviation, Close | Table | |
| QMS & HACCP | Corrective Actions | /dashboard/qms/corrective-actions | frontend/src/app/dashboard/qms/corrective-actions/page.tsx | Assign, Close | Table | |
| QMS & HACCP | Quarantine/Hold | /dashboard/qms/quarantine | frontend/src/app/dashboard/qms/quarantine/page.tsx | Hold, Release | Table | High-risk: stock hold |
| QMS & HACCP | Allergen Validation | /dashboard/qms/allergen | frontend/src/app/dashboard/qms/allergen/page.tsx | Validate | Form | |
| QMS & HACCP | Instrument Calibration | /dashboard/qms/calibration | frontend/src/app/dashboard/qms/calibration/page.tsx | Record Calibration | Table | |
| QMS & HACCP | AQL Sampling Plans | /dashboard/qms/aql | frontend/src/app/dashboard/qms/aql/page.tsx | Create Plan | Table | |
| QMS & HACCP | Certificate of Analysis | /dashboard/qms/coa | frontend/src/app/dashboard/qms/coa/page.tsx | Generate, Approve | Table | |
| QMS & HACCP | Audit Checklists | /dashboard/qms/audit-checklists | frontend/src/app/dashboard/qms/audit-checklists/page.tsx | Create, Run | Table | Audit types: INTERNAL, MOCK, THIRD_PARTY, REGULATORY |
| QMS & HACCP | Supplier Food Safety | /dashboard/qms/supplier-safety | frontend/src/app/dashboard/qms/supplier-safety/page.tsx | Not clearly discoverable | Table | |
| QMS & HACCP | QMS Reports | /dashboard/qms/reports | frontend/src/app/dashboard/qms/reports/page.tsx | Export | Report | |
| QMS & HACCP | AI Quality Agents | /dashboard/qms/ai | frontend/src/app/dashboard/qms/ai/page.tsx | Not clearly discoverable | AI output | |
| Allergen & Nutrition | AN Dashboard | /dashboard/allergen | frontend/src/app/dashboard/allergen/page.tsx | Not clearly discoverable | Dashboard | Permission: quality.view; Backend: /allergen |
| Allergen & Nutrition | Allergen Master | /dashboard/allergen/allergens | frontend/src/app/dashboard/allergen/allergens/page.tsx | Add Allergen | Table | |
| Allergen & Nutrition | Material Profiles | /dashboard/allergen/material-profiles | frontend/src/app/dashboard/allergen/material-profiles/page.tsx | Not clearly discoverable | Table | Frontend placeholder or partial implementation |
| Allergen & Nutrition | Nutrition Profiles | /dashboard/allergen/nutrition | frontend/src/app/dashboard/allergen/nutrition/page.tsx | Not clearly discoverable | Table | Frontend placeholder or partial implementation |
| Allergen & Nutrition | Product Allergens | /dashboard/allergen/product-allergens | frontend/src/app/dashboard/allergen/product-allergens/page.tsx | Not clearly discoverable | Table | Frontend placeholder or partial implementation |
| Allergen & Nutrition | Product Nutrition | /dashboard/allergen/product-nutrition | frontend/src/app/dashboard/allergen/product-nutrition/page.tsx | Not clearly discoverable | Table | |
| Allergen & Nutrition | Roll-Up Viewer | /dashboard/allergen/rollup | frontend/src/app/dashboard/allergen/rollup/page.tsx | Not clearly discoverable | Tree view | Frontend placeholder or partial implementation |
| Allergen & Nutrition | Label Readiness | /dashboard/allergen/label-readiness | frontend/src/app/dashboard/allergen/label-readiness/page.tsx | Not clearly discoverable | Table | Frontend placeholder or partial implementation |
| Allergen & Nutrition | Cleaning Validation | /dashboard/allergen/cleaning | frontend/src/app/dashboard/allergen/cleaning/page.tsx | Not clearly discoverable | Form | Frontend placeholder or partial implementation |
| Allergen & Nutrition | Change Logs | /dashboard/allergen/change-logs | frontend/src/app/dashboard/allergen/change-logs/page.tsx | Not clearly discoverable | Table | |
| Allergen & Nutrition | Reports | /dashboard/allergen/reports | frontend/src/app/dashboard/allergen/reports/page.tsx | Export | Report | |
| GS1 & Labels | GS1 Dashboard | /dashboard/gs1 | frontend/src/app/dashboard/gs1/page.tsx | Not clearly discoverable | Dashboard | Permission: gs1.view; Backend: /gs1 |
| GS1 & Labels | GS1 Configuration | /dashboard/gs1/config | frontend/src/app/dashboard/gs1/config/page.tsx | Save Config | Config form | |
| GS1 & Labels | Barcode Generator | /dashboard/gs1/barcodes | frontend/src/app/dashboard/gs1/barcodes/page.tsx | Generate | Form | |
| GS1 & Labels | Label Templates | /dashboard/gs1/labels | frontend/src/app/dashboard/gs1/labels/page.tsx | Add Template | Table | |
| GS1 & Labels | Print Queue | /dashboard/gs1/print-queue | frontend/src/app/dashboard/gs1/print-queue/page.tsx | Print | Queue | Permission: gs1.print; Backend: barcode_service placeholder |
| GS1 & Labels | SSCC Pallets | /dashboard/gs1/sscc | frontend/src/app/dashboard/gs1/sscc/page.tsx | Generate SSCC | Table | |
| GS1 & Labels | Scan Debug | /dashboard/gs1/scan | frontend/src/app/dashboard/gs1/scan/page.tsx | Scan | Form | |
| GS1 & Labels | GS1 Reports | /dashboard/gs1/reports | frontend/src/app/dashboard/gs1/reports/page.tsx | Export | Report | |
| GS1 & Labels | AI Agents | /dashboard/gs1/ai | frontend/src/app/dashboard/gs1/ai/page.tsx | Not clearly discoverable | AI output | Permission: gs1.admin |
| Helpdesk | Dashboard | /dashboard/helpdesk | frontend/src/app/dashboard/helpdesk/page.tsx | Not clearly discoverable | Dashboard | Backend: /helpdesk |
| Helpdesk | All Tickets | /dashboard/helpdesk/tickets | frontend/src/app/dashboard/helpdesk/tickets/page.tsx | Create, Assign, Close | Table | |
| Helpdesk | Open | /dashboard/helpdesk/open | frontend/src/app/dashboard/helpdesk/open/page.tsx | Assign, Escalate | Filtered table | |
| Helpdesk | Escalated | /dashboard/helpdesk/escalated | frontend/src/app/dashboard/helpdesk/escalated/page.tsx | Resolve, Escalate | Filtered table | |
| Helpdesk | SLA Breaches | /dashboard/helpdesk/sla | frontend/src/app/dashboard/helpdesk/sla/page.tsx | Not clearly discoverable | Table | |

### 2.6 Cluster: Procurement & Suppliers

| Module | Page/Screen | Route/Path | UI File Path | Visible Buttons/Actions | Forms/Tables Found | Notes |
|---|---|---|---|---|---|---|
| Procurement | Purchase Requests | /dashboard/procurement | frontend/src/app/dashboard/procurement/page.tsx | New PR, Approve, Convert to PO | Table | Permission: procurement.view; Backend: /procurement |
| Procurement | Purchase Orders | /dashboard/procurement/orders | frontend/src/app/dashboard/procurement/orders/page.tsx | Create PO, Receive, Cancel | Table | High-risk |
| Procurement | PO Detail | /dashboard/procurement/orders/[id] | frontend/src/app/dashboard/procurement/orders/[id]/page.tsx | Approve, Receive, Cancel | Detail + lines | |
| Procurement | RFQ | /dashboard/procurement/rfq | frontend/src/app/dashboard/procurement/rfq/page.tsx | Create RFQ, Award | Table | |
| Procurement | Blanket Agreements | /dashboard/procurement/blanket-agreements | frontend/src/app/dashboard/procurement/blanket-agreements/page.tsx | Create, Amend | Table | |
| Procurement | Reorder Policies | /dashboard/procurement/reorder-policies | frontend/src/app/dashboard/procurement/reorder-policies/page.tsx | Add Policy | Table | |
| Procurement | Delivery Planning | /dashboard/procurement/deliveries | frontend/src/app/dashboard/procurement/deliveries/page.tsx | Schedule | Table | |
| Procurement | Supplier Scorecard | /dashboard/procurement/suppliers | frontend/src/app/dashboard/procurement/suppliers/page.tsx | Rate, Export | Table | |
| Procurement | PR Detail | /dashboard/procurement/[id] | frontend/src/app/dashboard/procurement/[id]/page.tsx | Approve, Reject, Convert | Detail | |
| Subcontracting | SC Dashboard | /dashboard/subcontracting | frontend/src/app/dashboard/subcontracting/page.tsx | Not clearly discoverable | Dashboard | Backend: /subcontracting |
| Subcontracting | Orders | /dashboard/subcontracting/orders | frontend/src/app/dashboard/subcontracting/orders/page.tsx | Create, Complete | Table | |
| Landed Cost | LC Dashboard | /dashboard/landed-cost | frontend/src/app/dashboard/landed-cost/page.tsx | Not clearly discoverable | Dashboard | Backend: /landed-cost |
| Landed Cost | Documents | /dashboard/landed-cost/documents | frontend/src/app/dashboard/landed-cost/documents/page.tsx | Allocate | Table | |
| Landed Cost | LC Detail | /dashboard/landed-cost/[id] | frontend/src/app/dashboard/landed-cost/[id]/page.tsx | Post, Reverse | Detail | High-risk: finance posting |
| Supplier Portal | Portal Admin | /dashboard/supplier-portal | frontend/src/app/dashboard/supplier-portal/page.tsx | Invite Supplier | Dashboard | Backend: /supplier-portal |
| Supplier Portal | PO List | /dashboard/supplier-portal/accounts | frontend/src/app/dashboard/supplier-portal/accounts/page.tsx | Not clearly discoverable | Table | |
| Supplier Portal | Supplier Account | /dashboard/supplier-portal/accounts/[id] | frontend/src/app/dashboard/supplier-portal/accounts/[id]/page.tsx | Not clearly discoverable | Detail | |
| Supplier Portal | Portal Token | Not clearly discoverable from current code | — | — | — | portal_service.py uses "placeholder JWT-like token" |

### 2.7 Cluster: Sales & Distribution

| Module | Page/Screen | Route/Path | UI File Path | Visible Buttons/Actions | Forms/Tables Found | Notes |
|---|---|---|---|---|---|---|
| POS | POS Terminal | /dashboard/pos | frontend/src/app/dashboard/pos/page.tsx | Checkout, Void | POS UI | Permission: sales.view; Backend: /pos |
| POS | Sessions | /dashboard/pos/sessions | frontend/src/app/dashboard/pos/sessions/page.tsx | Open/Close Session | Table | High-risk: cash handling |
| POS | Today's Sales | /dashboard/pos/sales | frontend/src/app/dashboard/pos/sales/page.tsx | Not clearly discoverable | Table | |
| Sales | Quotations | /dashboard/sales/quotes | frontend/src/app/dashboard/sales/quotes/page.tsx | New Quote, Convert to SO | Table | Backend: /quotes |
| Sales | Sales Orders | /dashboard/sales/orders | frontend/src/app/dashboard/sales/orders/page.tsx | New SO, Confirm, Cancel | Table | Backend: /sales |
| Sales | SO Detail | /dashboard/sales/orders/[id] | frontend/src/app/dashboard/sales/orders/[id]/page.tsx | Confirm, Cancel, Deliver | Detail + lines | |
| Sales | Field Sales | /dashboard/sales/field-sales | frontend/src/app/dashboard/sales/field-sales/page.tsx | Not clearly discoverable | Table | Backend: /field-sales |
| Sales | Distributors | /dashboard/sales/distributors | frontend/src/app/dashboard/sales/distributors/page.tsx | Not clearly discoverable | Table | Backend: /distributors |
| Sales | Secondary Sales | /dashboard/secondary-sales | frontend/src/app/dashboard/secondary-sales/page.tsx | Upload | Dashboard | Backend: /secondary-sales |
| Sales | Secondary Upload | /dashboard/secondary-sales/upload | frontend/src/app/dashboard/secondary-sales/upload/page.tsx | Upload CSV | Form | |
| Sales | Delivery | /dashboard/sales/delivery | frontend/src/app/dashboard/sales/delivery/page.tsx | Dispatch, Confirm POD | Table | Backend: /delivery |
| Sales | Shipments | /dashboard/sales/shipments | frontend/src/app/dashboard/sales/shipments/page.tsx | Create Shipment | Table | |
| Sales | Shipment Detail | /dashboard/sales/shipments/[id] | frontend/src/app/dashboard/sales/shipments/[id]/page.tsx | Confirm, Deliver | Detail | |
| Sales | POD | /dashboard/sales/pod | frontend/src/app/dashboard/sales/pod/page.tsx | Confirm POD | Table | |
| Sales | Collections | /dashboard/sales/collections | frontend/src/app/dashboard/sales/collections/page.tsx | Record Payment | Table | High-risk: payment |
| Sales | Returns | /dashboard/sales/returns | frontend/src/app/dashboard/sales/returns/page.tsx | Process Return | Table | Backend: /returns |
| Sales | Invoices | /dashboard/sales/invoices | frontend/src/app/dashboard/sales/invoices/page.tsx | Create Invoice, Post | Table | High-risk: finance posting |
| Sales | Invoice Detail | /dashboard/sales/invoices/[id] | frontend/src/app/dashboard/sales/invoices/[id]/page.tsx | Post, Cancel, Credit Note | Detail | |
| Sales | Customer Statement | /dashboard/sales/customer-statement | frontend/src/app/dashboard/sales/customer-statement/page.tsx | Export, Send | Report | |
| Sales | Margin Analysis | /dashboard/sales/margin | frontend/src/app/dashboard/sales/margin/page.tsx | Not clearly discoverable | Chart + table | |
| Sales | Reports | /dashboard/sales/reports | frontend/src/app/dashboard/sales/reports/page.tsx | Export | Report list | |
| Price Lists | Dashboard | /dashboard/price-lists | frontend/src/app/dashboard/price-lists/page.tsx | Not clearly discoverable | Dashboard | Backend: /price-lists |
| Price Lists | Approval Queue | /dashboard/price-lists/approval-queue | frontend/src/app/dashboard/price-lists/approval-queue/page.tsx | Approve, Reject | Queue | |
| Price Lists | Bulk Import | /dashboard/price-lists/import | frontend/src/app/dashboard/price-lists/import/page.tsx | Upload CSV | Import form | |
| Contracts | All Contracts | /dashboard/contracts/list | frontend/src/app/dashboard/contracts/list/page.tsx | New Contract, Renew | Table | Backend: /contracts |
| Contracts | Contract Detail | /dashboard/contracts/list/[id] | frontend/src/app/dashboard/contracts/list/[id]/page.tsx | Amend, Terminate | Detail | |
| Recurring Orders | Dashboard | /dashboard/recurring-orders | frontend/src/app/dashboard/recurring-orders/page.tsx | Not clearly discoverable | Dashboard | Backend: /recurring-orders |
| Commissions | Dashboard | /dashboard/commissions | frontend/src/app/dashboard/commissions/page.tsx | Not clearly discoverable | Dashboard | Backend: /commissions |
| Commissions | Payouts | /dashboard/commissions/payouts | frontend/src/app/dashboard/commissions/payouts/page.tsx | Pay, Approve | Table | High-risk: payment |
| Customer Portal | Portal Admin | /dashboard/portal | frontend/src/app/dashboard/portal/page.tsx | Invite Customer | Dashboard | Backend: /portal; JWT placeholder |
| Customer Portal | Portal Accounts | /dashboard/portal/accounts | frontend/src/app/dashboard/portal/accounts/page.tsx | Not clearly discoverable | Table | |
| Van Sales | Dashboard | /dashboard/van-sales | frontend/src/app/dashboard/van-sales/page.tsx | Not clearly discoverable | Dashboard | Backend: /van-sales |
| Van Sales | Mobile POS | /dashboard/van-sales/pos | frontend/src/app/dashboard/van-sales/pos/page.tsx | Checkout | POS UI | High-risk: cash |
| Van Sales | Reconciliation | /dashboard/van-sales/reconciliation | frontend/src/app/dashboard/van-sales/reconciliation/page.tsx | Reconcile, Submit | Form | High-risk |
| Van Sales | M-Pesa Payments | /dashboard/van-sales/mpesa | frontend/src/app/dashboard/van-sales/mpesa/page.tsx | Initiate Payment | Form | M-Pesa is placeholder service |

### 2.8 Cluster: Marketing & CRM

| Module | Page/Screen | Route/Path | UI File Path | Notes |
|---|---|---|---|---|
| CRM Pipeline | All CRM pages (12 subpages) | /dashboard/crm/... | frontend/src/app/dashboard/crm/... | Permission: sales.view; Backend: /crm; crm_service.py is "scalable placeholder" |
| Marketing | Dashboard + 20 subpages | /dashboard/marketing/... | frontend/src/app/dashboard/marketing/... | Permission: marketing.view; Backend: /marketing; ecommerce_service simulates orders |
| TPM | 9 subpages | /dashboard/tpm/... | frontend/src/app/dashboard/tpm/... | Permission: promotions.view; Backend: /tpm |
| Promotions | 7 subpages | /dashboard/promotions/... | frontend/src/app/dashboard/promotions/... | Permission: promotions.view; Backend: /promotions |

### 2.9 Cluster: Finance & Accounting

| Module | Page/Screen | Route/Path | UI File Path | Notes |
|---|---|---|---|---|
| Finance | Overview + 7 subpages | /dashboard/finance/... | frontend/src/app/dashboard/finance/... | Permission: finance.view; M-Pesa page uses placeholder service |
| Accounting | 14 subpages | /dashboard/finance/accounting/... | frontend/src/app/dashboard/finance/accounting/... | Permission: finance.view; journal posting is high-risk |
| Invoice Matching | 8 subpages | /dashboard/invoice-match/... | frontend/src/app/dashboard/invoice-match/... | Permission: finance.view |
| Bank Reconciliation | 10 subpages | /dashboard/bank-reconciliation/... | frontend/src/app/dashboard/bank-reconciliation/... | Bank import statement functionality exists |
| Open Banking | Connections | /dashboard/bank-api | frontend/src/app/dashboard/bank-api/page.tsx | bank_api_service.py is "mock Kenyan bank sync" |
| Fixed Assets | 10 subpages | /dashboard/fixed-assets/... | frontend/src/app/dashboard/fixed-assets/... | Permission: finance.view |
| Dimensions | 11 subpages | /dashboard/dimensions/... | frontend/src/app/dashboard/dimensions/... | Permission: finance.view |
| Dunning | 9 subpages | /dashboard/dunning/... | frontend/src/app/dashboard/dunning/... | Permission: finance.view |
| Tax | 7 subpages | /dashboard/tax/... | frontend/src/app/dashboard/tax/... | Permission: tax.view; eTIMS is "placeholder for live KRA call" |

### 2.10 Cluster: HR & Payroll

| Module | Page/Screen | Route/Path | UI File Path | Notes |
|---|---|---|---|---|
| HR | Overview + 7 subpages | /dashboard/hr/... | frontend/src/app/dashboard/hr/... | Permission: hr.view |
| Kenya Payroll | Dashboard + profile + reports + run | /dashboard/payroll/... | frontend/src/app/dashboard/payroll/... | Permission: payroll_ke.view; hardcoded 2024 PAYE bands fallback; High-risk |
| Payroll Run | Run Detail | /dashboard/payroll/runs/[id] | frontend/src/app/dashboard/payroll/runs/[id]/page.tsx | Approve, Finalize | Detail | Critical-risk: payroll payment |
| Recruitment | 9 subpages | /dashboard/recruitment/... | frontend/src/app/dashboard/recruitment/... | Permission: hr.view |
| ESS | 9 subpages | /dashboard/ess/... | frontend/src/app/dashboard/ess/... | Permission: hr.view |
| Appraisals | 11 subpages | /dashboard/appraisals/... | frontend/src/app/dashboard/appraisals/... | Permission: hr.view |
| Training | 9 subpages | /dashboard/training/... | frontend/src/app/dashboard/training/... | Permission: hr.view |
| Timesheets | 7 subpages | /dashboard/timesheets/... | frontend/src/app/dashboard/timesheets/... | Permission: hr.view |
| Expenses | 11 subpages | /dashboard/expenses/... | frontend/src/app/dashboard/expenses/... | Permission: hr.view; Receipt OCR backend exists |

### 2.11 Cluster: Logistics & Field Operations

| Module | Page/Screen | Route/Path | UI File Path | Notes |
|---|---|---|---|---|
| Logistics | Overview + 4 subpages | /dashboard/logistics/... | frontend/src/app/dashboard/logistics/... | Permission: logistics.view |
| Fleet | 8 subpages | /dashboard/fleet/... | frontend/src/app/dashboard/fleet/... | Permission: logistics.view; Backend: /fleet |
| Van Sales | 13 subpages | /dashboard/van-sales/... | frontend/src/app/dashboard/van-sales/... | M-Pesa is placeholder |
| Maintenance | 7 subpages | /dashboard/maintenance/... | frontend/src/app/dashboard/maintenance/... | Permission: maintenance.view; predictive maintenance: ML stub |

### 2.12 Cluster: Utilities & Sustainability

| Module | Page/Screen | Route/Path | UI File Path | Notes |
|---|---|---|---|---|
| Utility Management | 17 subpages | /dashboard/utility-management/... | frontend/src/app/dashboard/utility-management/... | Permission: utility_management.view; IoT is stub |
| ESG | 7 subpages | /dashboard/esg/... | frontend/src/app/dashboard/esg/... | Permission: esg.view |
| IoT | IoT Dashboard | /dashboard/iot | frontend/src/app/dashboard/iot/page.tsx | Not clearly discoverable | Backend: /iot; iot_service.py is "MQTT/streaming bridge placeholder" |

### 2.13 Cluster: System, AI & Platform

| Module | Page/Screen | Route/Path | UI File Path | Notes |
|---|---|---|---|---|
| AI & Intelligence | 10 subpages | /dashboard/ai/... | frontend/src/app/dashboard/ai/... | Permission: ai.view; Mock mode active without API key |
| Analytics/BI | 9 subpages | /dashboard/analytics/... | frontend/src/app/dashboard/analytics/... | Permission: analytics.view |
| Custom Report Builder | 10 subpages | /dashboard/report-builder/... | frontend/src/app/dashboard/report-builder/... | Permission: reports.view |
| Kanban | 6 subpages | /dashboard/kanban/... | frontend/src/app/dashboard/kanban/... | Permission: hr.view |
| Notification Center | 7 subpages | /dashboard/notification-center/... | frontend/src/app/dashboard/notification-center/... | Permission: notifications.view |
| Calendar | 10 subpages | /dashboard/calendar/... | frontend/src/app/dashboard/calendar/... | Permission: hr.view |
| Chatter | 7 subpages | /dashboard/chatter/... | frontend/src/app/dashboard/chatter/... | Permission: hr.view |
| Custom Fields | 8 subpages | /dashboard/custom-fields/... | frontend/src/app/dashboard/custom-fields/... | Permission: hr.view |
| Webhooks | 6 subpages | /dashboard/webhooks/... | frontend/src/app/dashboard/webhooks/... | Permission: integrations.view |
| Companies | Companies | /dashboard/companies | frontend/src/app/dashboard/companies/page.tsx | Create Company, Edit | Table | Permission: company.view; RequirePermission guard present |
| Users | Users | /dashboard/users | frontend/src/app/dashboard/users/page.tsx | Create User, Edit, Delete | Table | Permission: users.view |
| Roles | Roles | /dashboard/roles | frontend/src/app/dashboard/roles/page.tsx | Create Role, Edit | Table | Permission: roles.view |
| Permissions | Permissions | /dashboard/permissions | frontend/src/app/dashboard/permissions/page.tsx | Not clearly discoverable | Table | |
| Developer | Developer Portal | /dashboard/developer | frontend/src/app/dashboard/developer/page.tsx | Generate Key | Dashboard | Backend: /developer; GraphQL is stub |
| Security | Security Monitor | /dashboard/security | frontend/src/app/dashboard/security/page.tsx | Not clearly discoverable | Dashboard | Backend: /security |
| Integration Hub | Integrations | /dashboard/integrations | frontend/src/app/dashboard/integrations/page.tsx | Sync, Configure | Dashboard | Several integrations are placeholders |

### 2.14 Auth Routes

| Module | Page/Screen | Route/Path | UI File Path | Notes |
|---|---|---|---|---|
| Auth | Login | /login | frontend/src/app/login/page.tsx | Login | Form | |
| Auth | 2FA | /auth/2fa | frontend/src/app/auth/2fa/page.tsx | Submit OTP | Form | OTP dispatch is TODO in backend |
| Auth | Change Password | /auth/change-password | frontend/src/app/auth/change-password/page.tsx | Change Password | Form | |

### 2.15 Pages with no clear sidebar navigation

The following pages exist as files but are **not clearly visible in sidebar navigation** (may be accessible via deep link or programmatic navigation):
- `/dashboard/approvals` — global approval queue
- `/dashboard/movements` — stock movements
- `/dashboard/putaway` — putaway tasks
- `/dashboard/messages` — messaging
- `/dashboard/mobile` — mobile device management
- `/dashboard/mobile/approvals`, `/dashboard/mobile/devices`
- `/dashboard/logs`, `/dashboard/logs/compliance`, `/dashboard/logs/retention`
- `/dashboard/import-history`
- `/dashboard/reports/*` — reports hub
- All subpages under `/dashboard/analytics/`, `/dashboard/reports/`
- `/dashboard/bank-api`

---

## 3. Backend Inventory

> Source: `backend/app/api/v1/endpoints/` (120+ files), `backend/app/api/v1/router.py`  
> Router uses dynamic registration via `module_registry.py`

### 3.1 Core Auth & System

| Module | Method | Endpoint | Router File | Permission/Auth | Frontend Connection | Notes |
|---|---|---|---|---|---|---|
| Auth | POST | /auth/login | auth.py | None (public) | /login | JWT token issue |
| Auth | POST | /auth/logout | auth.py | Bearer token | Any | |
| Auth | GET | /auth/me | auth.py | Bearer token | Any | Returns permissions, modules |
| Auth | POST | /auth/refresh | auth.py | Refresh token | Any | |
| Auth | POST | /auth/change-password | auth.py | Bearer token | /auth/change-password | |
| Auth | POST | /auth/2fa/setup | two_factor.py | Bearer token | /auth/2fa | |
| Auth | POST | /auth/2fa/verify | two_factor.py | Bearer token | /auth/2fa | OTP dispatch TODO |
| Users | GET/POST | /users/ | users.py | users.view / users.create | /dashboard/users | |
| Users | GET/PATCH | /users/{id} | users.py | users.view / users.edit | /dashboard/users/[id] | |
| Roles | GET/POST | /roles/ | roles.py | roles.view / roles.create | /dashboard/roles | |
| Modules | GET | /modules/manifest | modules.py | Bearer token | Any | Returns module registry |
| Security | GET | /security/events | security_monitor.py | Bearer token | /dashboard/security | |
| Audit | GET | /audit/logs | audit.py | Bearer token | /dashboard/logs | |
| Search | GET | /search | search.py | Bearer token | Not clearly discoverable | Global search |
| Health | GET | /health | health.py | None (public) | None | Health check |

### 3.2 Inventory & Warehouse

| Module | Method | Endpoint | Router File | Permission/Auth | Frontend Connection | Notes |
|---|---|---|---|---|---|---|
| Inventory | GET | /inventory/ | inventory.py | inventory.view | /dashboard/inventory | |
| Inventory | POST | /inventory/adjust | inventory.py | inventory.edit | /dashboard/inventory | High-risk: stock adjustment |
| Inventory | GET | /inventory/serials | serial_tracking.py | inventory.view | /dashboard/inventory/serials | |
| Warehouses | GET/POST | /warehouses/ | warehouses.py | warehouses.view / create | /dashboard/warehouses | |
| WMS | GET | /wms/zones | wms.py | wms.view | /dashboard/wms | |
| WMS | GET/POST | /wms/picks | wms.py | wms.view | /dashboard/wms/picking | |
| WMS | GET/POST | /wms/counts | wms.py | wms.view | /dashboard/wms/counts | |
| Cycle Count | GET/POST | /cycle-count/ | cycle_count.py | inventory.view | /dashboard/cycle-count | |
| Shelf Life | GET | /shelf-life/ | shelf_life.py | shelf_life.view | /dashboard/shelf-life | |
| Shelf Life | POST | /shelf-life/hold | shelf_life.py | shelf_life.hold | /dashboard/shelf-life/bulk-hold-monitor | High-risk |
| Shelf Life | POST | /shelf-life/dispose | shelf_life.py | shelf_life.dispose | /dashboard/shelf-life/disposition | Critical-risk |
| Traceability | GET | /traceability/search | traceability.py | production.view | /dashboard/traceability/search | |
| Traceability | POST | /traceability/recalls | traceability.py | production.view | /dashboard/traceability/recalls | Critical-risk |
| Containers | GET/POST | /containers/ | containers.py | inventory.view | /dashboard/containers | |

### 3.3 Production & Manufacturing

| Module | Method | Endpoint | Router File | Permission/Auth | Frontend Connection | Notes |
|---|---|---|---|---|---|---|
| Production | GET/POST | /production/ | production.py | production.view/create | /dashboard/production | |
| Production | POST | /production/{id}/release | production.py | production.approve | /dashboard/production/orders/[id] | High-risk |
| Production | POST | /production/{id}/complete | production.py | production.approve | /dashboard/production/orders/[id] | High-risk |
| Prod. Execution | GET | /production-execution/ | production_execution.py | production.view | /dashboard/production-execution | |
| Prod. Execution | POST | /production-execution/{id}/start | production_execution.py | production.view | /dashboard/production-execution/[id] | |
| Prod. AI | POST | /production-ai/analyze | production_ai.py | production.view | /dashboard/production/ai | AI-dependent |
| Shop Floor | GET | /shop-floor/queue | shop_floor.py | production.view | /dashboard/shop-floor/queue | |
| Shop Floor | POST | /shop-floor/handover | shop_floor.py | production.view | /dashboard/shop-floor/handover | |
| Material Flow | POST | /material-flow/issue | material_flow.py | production.view | /dashboard/material-flow/issue | High-risk |
| Material Flow | POST | /material-flow/fg-receipt | material_flow.py | production.view | /dashboard/material-flow/fg-receipt | High-risk |
| MRP | POST | /mrp/run | mrp.py | production.view | /dashboard/mrp/run | |
| MRP | GET | /mrp/suggestions | mrp.py | production.view | /dashboard/mrp/suggestions | |
| MPS | GET | /mps/ | mps.py | production.view | /dashboard/mps | |
| Planning | GET | /planning/ | planning.py | planning.view | /dashboard/planning | |
| BOM | GET/POST | /bom/ | bom.py | bom.view/create | /dashboard/bom | |
| BOM | POST | /bom/{id}/approve | bom.py | bom.approve | /dashboard/bom/[id] | |
| BOM | POST | /bom/{id}/release | bom.py | bom.release | /dashboard/bom/[id] | High-risk |
| NPD | GET | /npd-workflow/ | npd_workflow.py | npd.view | /dashboard/npd | |
| NPD | POST | /npd-workflow/{id}/advance | npd_workflow.py | npd.advance | /dashboard/npd/[id] | |
| Recipes | GET/POST | /recipes/ | recipes.py | recipe.view/create | /dashboard/recipes | |
| Machine Ops | GET | /machine-ops/ | machine_operator.py | production.view | /dashboard/machine-ops | |

### 3.4 Procurement

| Module | Method | Endpoint | Router File | Permission/Auth | Frontend Connection | Notes |
|---|---|---|---|---|---|---|
| Procurement | GET/POST | /procurement/ | procurement.py | procurement.view/create | /dashboard/procurement | |
| Procurement | POST | /procurement/{id}/approve | procurement.py | procurement.approve | /dashboard/procurement/[id] | High-risk |
| Procurement | POST | /procurement/orders/{id}/receive | procurement.py | procurement.receive | /dashboard/procurement/orders/[id] | |
| Procurement | POST | /procurement/orders/{id}/post | procurement.py | procurement.post | /dashboard/procurement/orders/[id] | High-risk: finance |
| Suppliers | GET/POST | /suppliers/ | suppliers.py | procurement.view | /dashboard/suppliers | |
| Subcontracting | GET/POST | /subcontracting/ | subcontracting.py | procurement.view | /dashboard/subcontracting | |
| Landed Cost | POST | /landed-cost/{id}/post | landed_cost.py | procurement.view | /dashboard/landed-cost/[id] | High-risk: finance |
| Supplier Portal | GET | /supplier-portal/ | supplier_portal.py | procurement.view | /dashboard/supplier-portal | |
| Proc. Suggestion | GET | /procurement/suggestions/ | procurement_suggestion.py | procurement.view | /dashboard/procurement-suggestion | |

### 3.5 Sales & CRM

| Module | Method | Endpoint | Router File | Permission/Auth | Frontend Connection | Notes |
|---|---|---|---|---|---|---|
| Sales | GET/POST | /sales/ | sales.py | sales.view/create | /dashboard/sales/orders | |
| Sales | POST | /sales/{id}/confirm | sales.py | sales.approve | /dashboard/sales/orders/[id] | |
| Sales | POST | /sales/{id}/cancel | sales.py | sales.cancel | /dashboard/sales/orders/[id] | |
| Sales | POST | /sales/{id}/invoice | sales.py | sales.approve | /dashboard/sales/invoices | High-risk: finance |
| Quotation | GET/POST | /quotes/ | quotation.py | sales.view | /dashboard/sales/quotes | |
| Delivery | GET/POST | /delivery/ | delivery.py | sales.view | /dashboard/sales/delivery | |
| Returns | GET/POST | /returns/ | returns_mgmt.py | sales.view | /dashboard/sales/returns | |
| CRM | GET/POST | /crm/ | crm_pipeline.py | sales.view | /dashboard/crm | crm_service is "scalable placeholder" |
| Distributors | GET/POST | /distributors/ | distributors.py | sales.view | /dashboard/sales/distributors | |
| POS | GET/POST | /pos/ | pos.py | sales.view | /dashboard/pos | |
| Van Sales | GET/POST | /van-sales/ | van_sales.py | sales.view | /dashboard/van-sales | |
| Commissions | GET/POST | /commissions/ | commissions.py | sales.view | /dashboard/commissions | |
| Price Lists | GET/POST | /price-lists/ | price_list.py | sales.view | /dashboard/price-lists | |
| Promotions | GET/POST | /promotions/ | promotions.py | promotions.view | /dashboard/promotions | |
| Contracts | GET/POST | /contracts/ | contracts.py | sales.view | /dashboard/contracts | |
| Recurring Orders | GET/POST | /recurring-orders/ | subscription.py | sales.view | /dashboard/recurring-orders | |
| Portal | GET | /portal/ | portal.py | sales.view | /dashboard/portal | JWT is placeholder |

### 3.6 Finance

| Module | Method | Endpoint | Router File | Permission/Auth | Frontend Connection | Notes |
|---|---|---|---|---|---|---|
| Finance | GET/POST | /finance/ | finance.py | finance.view/create | /dashboard/finance | |
| Finance | POST | /finance/journals/{id}/post | finance.py | finance.approve | /dashboard/finance/accounting/journal | Critical-risk |
| Finance | POST | /finance/periods/{id}/close | finance.py | finance.approve | /dashboard/finance/accounting/period-closing | Critical-risk |
| Bank Recon | GET/POST | /bank-reconciliation/ | bank_reconciliation.py | finance.view | /dashboard/bank-reconciliation | |
| Invoice Match | GET/POST | /invoice-match/ | invoice_match.py | finance.view | /dashboard/invoice-match | |
| Fixed Assets | GET/POST | /fixed-assets/ | fixed_assets.py | finance.view | /dashboard/fixed-assets | |
| Fixed Assets | POST | /fixed-assets/{id}/dispose | fixed_assets.py | finance.view | /dashboard/fixed-assets/disposal | High-risk |
| Dimensions | GET/POST | /dimensions/ | dimensions.py | finance.view | /dashboard/dimensions | |
| Dunning | GET/POST | /dunning/ | dunning.py | finance.view | /dashboard/dunning | |
| Tax | GET/POST | /tax/ | tax_regulatory.py | tax.view | /dashboard/tax | |
| Tax | POST | /tax/etims/submit | tax_regulatory.py | tax.view | /dashboard/finance/etims | Placeholder for live KRA call |
| Landed Cost | GET/POST | /landed-cost/ | landed_cost.py | procurement.view | /dashboard/landed-cost | |
| Bank API | GET | /bank-api/ | bank_api.py | finance.view | /dashboard/bank-api | Mock Kenyan bank sync |

### 3.7 HR & Payroll

| Module | Method | Endpoint | Router File | Permission/Auth | Frontend Connection | Notes |
|---|---|---|---|---|---|---|
| HR | GET/POST | /hr/ | hr.py | hr.view/create | /dashboard/hr | |
| Payroll KE | GET/POST | /payroll-ke/ | payroll_ke.py | payroll_ke.view/create | /dashboard/payroll | Hardcoded 2024 PAYE fallback |
| Payroll KE | POST | /payroll-ke/runs/{id}/approve | payroll_ke.py | payroll_ke.approve | /dashboard/payroll/runs/[id] | Critical-risk |
| Recruitment | GET/POST | /recruitment/ | recruitment.py | hr.view | /dashboard/recruitment | |
| ESS | GET | /ess/ | ess.py | hr.view | /dashboard/ess | |
| Timesheets | GET/POST | /timesheets/ | timesheets.py | hr.view | /dashboard/timesheets | |
| Appraisals | GET/POST | /appraisals/ | appraisals.py | hr.view | /dashboard/appraisals | |
| Training | GET/POST | /training/ | training.py | hr.view | /dashboard/training | |
| Expenses | GET/POST | /expenses/ | expenses.py | hr.view | /dashboard/expenses | |

### 3.8 Quality & Compliance

| Module | Method | Endpoint | Router File | Permission/Auth | Frontend Connection | Notes |
|---|---|---|---|---|---|---|
| Quality | GET/POST | /quality/ | quality.py | quality.view/create | /dashboard/quality | |
| Quality | POST | /quality/{id}/approve | quality.py | quality.approve | /dashboard/quality/[id] | High-risk: QC release |
| Consumer Complaints | GET/POST | /consumer-complaints/ | consumer_complaints.py | consumer_complaints.view | /dashboard/quality/consumer-complaints | |
| Consumer Complaints | POST | /consumer-complaints/{id}/close | consumer_complaints.py | consumer_complaints.close | — | |
| Consumer Complaints | POST | /consumer-complaints/{id}/link-recall | consumer_complaints.py | consumer_complaints.link_recall | — | Critical-risk |
| QMS | GET/POST | /qms/ | qms.py | quality.view | /dashboard/qms | |
| Allergen | GET/POST | /allergen/ | allergen.py | quality.view | /dashboard/allergen | |
| GS1 | GET/POST | /gs1/ | gs1.py | gs1.view | /dashboard/gs1 | |
| Shelf Life | GET/POST | /shelf-life/ | shelf_life.py | shelf_life.view | /dashboard/shelf-life | |
| Traceability | GET/POST | /traceability/ | traceability.py | production.view | /dashboard/traceability | |
| Regulatory Certs | GET/POST | /regulatory-certs/ | regulatory_certs.py | quality.view | /dashboard/quality/certificates | |
| Helpdesk | GET/POST | /helpdesk/ | helpdesk.py | quality.view | /dashboard/helpdesk | |

### 3.9 AI & Intelligence

| Module | Method | Endpoint | Router File | Permission/Auth | Frontend Connection | Notes |
|---|---|---|---|---|---|---|
| AI | GET | /ai/status | ai.py | ai.view | /dashboard/ai | Returns mock status when provider=mock |
| AI | POST | /ai/chat | ai.py | ai.create | /dashboard/ai/chat | Mock mode: returns [MOCK/DEV MODE] responses |
| AI | POST | /ai/nl-command | ai.py | ai.create | /dashboard/ai/nl-command | Disabled in mock mode |
| AI | GET/POST | /ai/predictions | ai.py | ai.view | /dashboard/ai/predictions | Mock mode active without API key |
| AI | GET/POST | /ai/recommendations | ai.py | ai.view | /dashboard/ai/recommendations | Mock mode |
| AI | POST | /ai/scenarios | ai.py | ai.create | /dashboard/ai/scenarios | Mock mode |
| AI | POST | /ai/formulations | ai.py | ai.create | /dashboard/ai/formulations | Mock mode |
| AI | GET | /ai/logs | ai.py | ai.view | /dashboard/ai/logs | |
| AI | GET/POST | /ai/prompts | ai.py | ai.configure | /dashboard/ai/governance | Prompt registry |
| AI | POST | /ai/forecast-baseline | ai.py | ai.view | /dashboard/mrp/forecast | |

### 3.10 Utilities & Integration

| Module | Method | Endpoint | Router File | Permission/Auth | Frontend Connection | Notes |
|---|---|---|---|---|---|---|
| Utility Mgmt | GET/POST | /utility-management/ | utility_management.py | utility_management.view | /dashboard/utility-management | |
| IoT | GET/POST | /iot/ | iot.py | iot.view | /dashboard/iot | iot_service is MQTT stub |
| Electricity | GET/POST | /electricity/ | electricity.py | utility_management.view | /dashboard/utility-management/electricity | |
| Water | GET/POST | /water/ | water.py | utility_management.view | /dashboard/utility-management/water | |
| Integrations | GET/POST | /integrations/ | integrations.py | Various | /dashboard/integrations | Several placeholders |
| Webhooks | GET/POST | /webhooks/ | webhooks.py | integrations.view | /dashboard/webhooks | |
| WhatsApp | GET/POST | /whatsapp/ | whatsapp.py | Bearer token | /dashboard/whatsapp | is_demo_mode=True by default |
| WhatsApp | POST | /whatsapp/simulate-inbound | whatsapp.py | Bearer token | — | Demo: creates fake inbound message |
| Notifications | GET/POST | /notifications/ | notifications.py | notifications.view | /dashboard/notification-center | |
| Documents | GET/POST | /documents/ | documents.py | documents.view | /dashboard/documents | |
| ESG | GET/POST | /esg/ | esg.py | esg.view | /dashboard/esg | |
| Marketing | GET/POST | /marketing/ | marketing.py | marketing.view | /dashboard/marketing | |
| Reports | GET/POST | /reports-builder/ | report_builder.py | reports.view | /dashboard/report-builder | |
| Analytics | GET | /analytics/ | analytics.py | Various | /dashboard/analytics | "Nothing hardcoded; all from real ERP data" |
| Developer | GET | /developer/ | api_portal.py | Bearer token | /dashboard/developer | GraphQL is stub |

---

## 4. Module Completeness Matrix

| Module | Frontend Exists | Backend Exists | DB Models Exist | Services Exist | Permissions Exist | Workflow/Statuses Exist | Manual Priority | Notes/Gaps |
|---|---|---|---|---|---|---|---|---|
| Dashboard | Yes | Yes | Partial | Yes | Partial | No | Critical | KPI widgets; permissions not enforced on all widgets |
| Auth / Login | Yes | Yes | Yes | Yes | Yes | Partial | Critical | OTP dispatch is TODO |
| Products / Master Data | Yes | Yes | Yes | Yes | Partial | No | Critical | Permission enforcement needs review on some endpoints |
| Inventory | Yes | Yes | Yes | Yes | Yes | Yes | Critical | Stock adjustment is high-risk; need permission audit |
| Warehouses / WMS | Yes | Yes | Yes | Yes | Yes | Yes | Critical | |
| Production / MES | Yes | Yes | Yes | Yes | Yes | Yes | Critical | Release/Complete are high-risk ops |
| Production Execution | Yes | Yes | Yes | Yes | Yes | Yes | Critical | |
| BOM & Formula | Yes | Yes | Yes | Yes | Yes | Yes | Critical | |
| Recipes | Yes | Yes | Yes | Yes | Yes | Yes | Critical | |
| Procurement / PO | Yes | Yes | Yes | Yes | Yes | Yes | Critical | Approve/Receive/Post are high-risk |
| Sales / Orders | Yes | Yes | Yes | Yes | Yes | Yes | Critical | |
| Finance / Accounting | Yes | Yes | Yes | Yes | Yes | Yes | Critical | Journal post/period close are Critical-risk |
| Bank Reconciliation | Yes | Yes | Yes | Yes | Yes | Yes | High | |
| Invoice Matching | Yes | Yes | Yes | Yes | Yes | Partial | High | |
| Fixed Assets | Yes | Yes | Yes | Yes | Yes | Yes | High | Disposal is high-risk |
| Tax / eTIMS | Yes | Yes | Yes | Yes | Partial | Partial | High | eTIMS is placeholder; VAT3 needs review |
| HR / Employees | Yes | Yes | Yes | Yes | Yes | Yes | High | |
| Kenya Payroll | Yes | Yes | Yes | Yes | Yes | Yes | Critical | Hardcoded PAYE fallback; approve/finalize is Critical-risk |
| Recruitment / ATS | Yes | Yes | Yes | Yes | Yes | Yes | High | |
| ESS | Yes | Yes | Yes | Yes | Yes | Yes | High | |
| Appraisals | Yes | Yes | Yes | Yes | Yes | Yes | Medium | |
| Training | Yes | Yes | Yes | Yes | Yes | Yes | Medium | |
| Timesheets | Yes | Yes | Yes | Yes | Yes | Yes | Medium | |
| Expenses | Yes | Yes | Yes | Yes | Yes | Yes | Medium | |
| Quality Control | Yes | Yes | Yes | Yes | Yes | Yes | Critical | QC release is high-risk (food safety) |
| QMS & HACCP | Yes | Yes | Yes | Yes | Yes | Yes | Critical | CCP monitoring is Critical-risk |
| Allergen & Nutrition | Yes | Yes | Yes | Yes | Partial | Partial | High | Several pages are Frontend placeholder or partial implementation |
| GS1 & Label Printing | Yes | Yes | Yes | Yes | Yes | Partial | High | Print is barcode_service placeholder |
| Shelf Life / FEFO | Yes | Yes | Yes | Yes | Yes | Yes | Critical | Disposition is Critical-risk |
| Traceability & Recall | Yes | Yes | Yes | Yes | Partial | Yes | Critical | Recall initiation is Critical-risk |
| Consumer Complaints | Yes | Yes | Yes | Yes | Yes | Yes | High | link_recall is Critical-risk |
| NPD | Yes | Yes | Yes | Yes | Yes | Yes | Medium | |
| MRP & Forecasting | Yes | Yes | Yes | Yes | Partial | Yes | High | Prophet/AI forecast is stub |
| MPS | Yes | Yes | Yes | Yes | Partial | Yes | Medium | |
| Advanced Planning | Yes | Yes | Yes | Yes | Partial | Partial | Medium | |
| CRM Pipeline | Yes | Yes | Yes | Partial | Yes | Yes | High | crm_service is "scalable placeholder" |
| Marketing | Yes | Yes | Yes | Partial | Partial | Partial | Medium | e-commerce simulates orders |
| TPM | Yes | Yes | Yes | Yes | Yes | Partial | Medium | |
| Promotions | Yes | Yes | Yes | Yes | Yes | Partial | Medium | |
| Price Lists | Yes | Yes | Yes | Yes | Yes | Partial | Medium | |
| Contracts | Yes | Yes | Yes | Yes | Yes | Partial | Medium | |
| Recurring Orders | Yes | Yes | Yes | Yes | Partial | Partial | Medium | |
| Commissions | Yes | Yes | Yes | Yes | Partial | Partial | Medium | |
| Customer/Dist. Portal | Yes | Yes | Yes | Yes | Partial | Partial | Medium | JWT is placeholder |
| Supplier Portal | Yes | Yes | Yes | Yes | Yes | Partial | Medium | |
| Dunning & Collections | Yes | Yes | Yes | Yes | Yes | Yes | High | |
| Accounting Dimensions | Yes | Yes | Yes | Yes | Yes | Partial | High | |
| Logistics | Yes | Yes | Yes | Yes | Yes | Partial | Medium | |
| Fleet | Yes | Yes | Yes | Yes | Partial | Yes | Medium | |
| Van Sales | Yes | Yes | Yes | Yes | Partial | Yes | High | M-Pesa is placeholder |
| Maintenance | Yes | Yes | Yes | Yes | Yes | Partial | Medium | Predictive ML is stub |
| Utility Management | Yes | Yes | Yes | Yes | Yes | Partial | Medium | |
| IoT / Machine Streaming | Yes | Yes | Yes | Yes | Yes | Partial | Medium | MQTT bridge is placeholder |
| ESG | Yes | Yes | Yes | Yes | Yes | Partial | Low | |
| AI & Intelligence | Yes | Yes | Yes | Yes | Yes | No | High | Mock mode active without API key |
| Analytics / BI | Yes | Yes | Partial | Yes | Partial | No | High | Permission enforcement needs review |
| Report Builder | Yes | Yes | Yes | Yes | Yes | Yes | High | |
| Notification Center | Yes | Yes | Yes | Yes | Yes | Yes | Medium | |
| Kanban | Yes | Yes | Yes | Yes | Partial | Yes | Low | |
| Calendar | Yes | Yes | Yes | Yes | Partial | Yes | Low | |
| Chatter | Yes | Yes | Yes | Yes | Partial | Yes | Low | |
| Custom Fields | Yes | Yes | Yes | Yes | Partial | Partial | Low | |
| Webhooks | Yes | Yes | Yes | Yes | Yes | Yes | Admin/Technical only | |
| Companies | Yes | Yes | Yes | Partial | Yes | Partial | Admin/Technical only | Multi-company support added GAP-025 |
| Users & Roles | Yes | Yes | Yes | Yes | Yes | No | Admin/Technical only | |
| Developer Portal | Yes | Yes | Yes | Yes | Partial | No | Admin/Technical only | GraphQL is stub |
| Security Monitor | Yes | Yes | Yes | Partial | Yes | Partial | Admin/Technical only | |
| M-Pesa (Finance) | Yes | Yes | Yes | Yes | Yes | Partial | High | mpesa_service is placeholder with fake IDs |
| M-Pesa (Van Sales) | Yes | Yes | Yes | Yes | Partial | Partial | High | Same placeholder service |
| Bank API (Open Banking) | Yes | Yes | Yes | Yes | Yes | No | High | Mock Kenyan bank sync |
| WhatsApp | Yes | Yes | Yes | Yes | Partial | Partial | High | is_demo_mode=True by default |
| Email Integration | Yes | Yes | Yes | Yes | Partial | Partial | Medium | |
| POS | Yes | Yes | Yes | Yes | Partial | Yes | High | |
| Subcontracting | Yes | Yes | Yes | Yes | Partial | Partial | Medium | |
| Co-Packing | Yes | Yes | Yes | Yes | Partial | Partial | Low | |
| Secondary Sales | Yes | Yes | Yes | Yes | Partial | Partial | Medium | |
| Field Sales | Yes | Yes | Yes | Yes | Partial | Partial | Medium | |
| Landed Cost | Yes | Yes | Yes | Yes | Partial | Partial | Medium | Finance post is High-risk |
| Market Intelligence | Yes | Yes | Yes | Yes | Partial | Partial | Medium | |
| Shop Floor | Yes | Yes | Yes | Yes | Yes | Yes | High | Operator terminal is High-risk |
| Machine Ops | Yes | Yes | Yes | Yes | Partial | Yes | Medium | |
| Material Flow | Yes | Yes | Yes | Yes | Partial | Yes | High | Issue/receive are High-risk |

---

## 5. Button and Action Inventory

> Only high-risk and notable actions documented. Full action inventory requires browser review.

| Module | Page | Button/Action Label | UI File Path | Expected Behavior | API Endpoint If Found | Permission If Found | Risk Level | Notes |
|---|---|---|---|---|---|---|---|---|
| Production | Production Orders | Release | /dashboard/production/orders/[id] | Changes status to RELEASED; enables WO creation | POST /production/{id}/release | production.approve | High | Initiates manufacturing |
| Production | Production Orders | Complete | /dashboard/production/orders/[id] | Changes status to COMPLETED; triggers stock update | POST /production/{id}/complete | production.approve | High | Updates inventory |
| Production | Production Orders | Cancel | /dashboard/production/orders/[id] | Cancels order; reverses reservations | POST /production/{id}/cancel | production.approve | Medium | |
| Shop Floor | Operator Terminal | Complete WO | /dashboard/shop-floor/terminal | Records output, scrap, and completes work order | POST /production-execution/{id}/complete | production.view | High | Executes production |
| Material Flow | Issue to Production | Issue | /dashboard/material-flow/issue | Deducts stock from warehouse to production | POST /material-flow/issue | production.view | High | Stock deduction |
| Material Flow | FG Receipt | Receive FG | /dashboard/material-flow/fg-receipt | Adds finished goods to warehouse stock | POST /material-flow/fg-receipt | production.view | High | Stock addition |
| Material Flow | Bulk Transfer | Transfer | /dashboard/material-flow/bulk-transfer | Bulk moves stock between locations | POST /material-flow/bulk-transfer | production.view | High | Bulk stock move |
| Inventory | Inventory | Adjust Stock | /dashboard/inventory | Directly adjusts stock levels | POST /inventory/adjust | inventory.edit | High | Stock adjustment |
| WMS | Stock Counts | Close Count | /dashboard/wms/counts/[id] | Closes count; triggers variance calculation | POST /wms/counts/{id}/close | wms.view | High | May trigger stock adjustment |
| Cycle Count | Variance Review | Approve Variance | /dashboard/cycle-count/variances | Posts stock adjustment to reconcile variance | Not clearly discoverable | inventory.view | High | Stock adjustment |
| Shelf Life | Disposition Console | Dispose | /dashboard/shelf-life/disposition | Permanently removes stock from system | POST /shelf-life/dispose | shelf_life.dispose | Critical | Irreversible stock write-off |
| Shelf Life | Disposition Console | Rework | /dashboard/shelf-life/disposition | Transfers to rework; triggers production order | Not clearly discoverable | shelf_life.dispose | High | |
| Shelf Life | Bulk Hold Monitor | Hold (Bulk) | /dashboard/shelf-life/bulk-hold-monitor | Places lots on bulk quality hold | POST /shelf-life/hold | shelf_life.hold | High | |
| Traceability | Recall List | Initiate Recall | /dashboard/traceability/recalls | Creates formal recall event | POST /traceability/recalls | production.view | Critical | Customer/regulatory notification |
| Traceability | Recall Detail | Execute Recall | /dashboard/traceability/recalls/[id] | Triggers customer notification and regulatory report | Not clearly discoverable | production.view | Critical | External communication |
| Consumer Complaints | Complaint Detail | Link Recall | — | Links complaint to traceability recall | POST /consumer-complaints/{id}/link-recall | consumer_complaints.link_recall | Critical | |
| QMS | CCP Monitoring | Alert CCP Breach | /dashboard/qms/ccp | Triggers critical food safety alert | Not clearly discoverable | quality.view | Critical | Food safety |
| QMS | Quarantine | Release from Hold | /dashboard/qms/quarantine | Releases stock from quality hold | Not clearly discoverable | quality.view | High | |
| Finance | Journal Entries | Post | /dashboard/finance/accounting/journal | Posts journal to general ledger | POST /finance/journals/{id}/post | finance.approve | Critical | Irreversible accounting entry |
| Finance | Period Closing | Close Period | /dashboard/finance/accounting/period-closing | Closes accounting period; blocks further posting | POST /finance/periods/{id}/close | finance.approve | Critical | Blocks future posting to period |
| Finance | Payments | Pay | /dashboard/finance/accounting/payments | Executes payment to supplier/from customer | Not clearly discoverable | finance.approve | Critical | Cash disbursement |
| Landed Cost | LC Detail | Post | /dashboard/landed-cost/[id] | Posts landed cost allocation to GL | POST /landed-cost/{id}/post | procurement.view | High | Finance posting |
| Fixed Assets | Disposals | Dispose Asset | /dashboard/fixed-assets/disposal | Retires asset; posts disposal to GL | POST /fixed-assets/{id}/dispose | finance.view | High | Finance posting |
| BOM | BOM Detail | Release | /dashboard/bom/[id] | Releases BOM for production use | POST /bom/{id}/release | bom.release | High | Enables production usage |
| Payroll | Payroll Run | Approve Run | /dashboard/payroll/runs/[id] | Approves payroll; triggers payment processing | POST /payroll-ke/runs/{id}/approve | payroll_ke.approve | Critical | Mass payment |
| Payroll | Payroll Run | Finalize Run | /dashboard/payroll/runs/[id] | Finalizes payroll; records in finance | Not clearly discoverable | payroll_ke.approve | Critical | Finance integration |
| Sales | Invoice Detail | Post Invoice | /dashboard/sales/invoices/[id] | Posts sales invoice to AR/GL | Not clearly discoverable | sales.approve | High | Finance posting |
| Procurement | PO Detail | Receive | /dashboard/procurement/orders/[id] | Records goods receipt; updates stock | POST /procurement/orders/{id}/receive | procurement.receive | High | Stock addition |
| Procurement | PO Detail | Post GR | /dashboard/procurement/orders/[id] | Posts goods receipt to GL | POST /procurement/orders/{id}/post | procurement.post | High | Finance posting |
| Procurement | PR | Approve PR | /dashboard/procurement/[id] | Approves purchase request | POST /procurement/{id}/approve | procurement.approve | Medium | |
| Tax | eTIMS | Submit to KRA | /dashboard/finance/etims | Sends e-invoice to Kenya Revenue Authority | POST /tax/etims/submit | tax.view | High | External regulatory submission; currently placeholder |
| AI | NL ERP Control | Execute Command | /dashboard/ai/nl-command | AI interprets and executes ERP action | POST /ai/nl-command | ai.create | Critical | AI executes arbitrary ERP actions; mock mode blocks this |
| WhatsApp | Simulate Inbound | Simulate | /dashboard/whatsapp | Creates fake inbound message | POST /whatsapp/simulate-inbound | Bearer token | Medium | Demo only endpoint |
| M-Pesa | M-Pesa Payments | Initiate STK Push | /dashboard/van-sales/mpesa | Sends M-Pesa STK push request | Not clearly discoverable | Not clearly discoverable | Critical | Using placeholder service with fake IDs |
| Companies | Companies | Create Company | /dashboard/companies | Creates new company entity | POST /companies/ | company.create | High | Multi-company |
| Users | Users | Delete User | /dashboard/users/[id] | Permanently deletes user account | DELETE /users/{id} | users.delete | High | Irreversible |
| BOM | BOM Detail | Archive | /dashboard/bom/[id] | Archives BOM; prevents future production use | POST /bom/{id}/archive | bom.archive | Medium | |
| Price Lists | Approval Queue | Approve Price | /dashboard/price-lists/approval-queue | Approves new price list version | Not clearly discoverable | sales.view | High | Affects all customer pricing |
| Reports | Report Builder | Run Report | /dashboard/report-builder/viewer | Executes report query against live DB | POST /reports-builder/{id}/run | reports.run | Medium | Could be slow on large datasets |
| Import | Bulk Import | Import | /dashboard/import-history | Bulk imports data from CSV | POST /bulk-import/ | Not clearly discoverable | High | Mass data change |
| GS1 | Print Queue | Print Labels | /dashboard/gs1/print-queue | Sends labels to printer | POST /gs1/print | gs1.print | Medium | barcode_service is placeholder |

---

## 6. Workflow and Status Inventory

| Module | Status/Workflow | Values Found | Where Found | Transition Logic Found? | Notes |
|---|---|---|---|---|---|
| Production Orders | ProductionStatus | DRAFT, PLANNED, RELEASED, IN_PROGRESS, COMPLETED, CANCELLED | backend/app/models/production.py | Yes (service layer) | Release/Complete are gated by permission |
| Production Execution | ProdExecStatus | PENDING, IN_PROGRESS, PAUSED, COMPLETED, CANCELLED | backend/app/models/production_execution.py | Yes | |
| Work Order Execution | WOExecStatus | PENDING, STARTED, PAUSED, COMPLETED, CANCELLED | backend/app/models/production_execution.py | Yes | |
| Sales Orders | SOStatus | DRAFT, CONFIRMED, ALLOCATED, PICKING, SHIPPED, DELIVERED, CANCELLED | backend/app/models/sales.py | Yes | |
| Purchase Orders | POStatus | PENDING, APPROVED, PARTIAL, RECEIVED, CANCELLED | backend/app/models/procurement.py | Yes | |
| Purchase Requests | PRStatus | DRAFT, SUBMITTED, APPROVED, REJECTED, CONVERTED | backend/app/models/procurement.py | Yes | |
| Payroll Run | PayrollStatus | DRAFT, RUNNING, APPROVED, FINALIZED, PAID | backend/app/models/payroll_ke.py | Yes | Critical workflow |
| BOM Lifecycle | BOMLifecycle | DRAFT, IN_REVIEW, APPROVED, RELEASED, ARCHIVED, OBSOLETE | backend/app/models/bom.py | Yes | |
| Finance Journals | JournalStatus | DRAFT, POSTED, REVERSED | backend/app/models/finance.py | Yes | |
| Fiscal Period | PeriodStatus | OPEN, CLOSING, CLOSED | backend/app/models/finance.py | Yes | |
| Quality Inspections | InspectionStatus | PENDING, IN_PROGRESS, PASSED, FAILED, ON_HOLD | backend/app/models/quality.py | Yes | |
| Consumer Complaints | ComplaintStatus | OPEN, INVESTIGATING, RESOLVED, CLOSED | backend/app/models/consumer_complaints.py | Yes | |
| Recall Events | RecallStatus | INITIATED, IN_PROGRESS, CONTAINED, CLOSED | backend/app/models/traceability.py | Status values found, but transition rules not clearly discoverable from current code | |
| NPD Projects | NPDStatus | CONCEPT, DEVELOPMENT, PILOT, APPROVED, LAUNCHED, CANCELLED | backend/app/models/npd.py | Yes | |
| Appraisal | AppraisalStatus | DRAFT, SELF_REVIEW, MANAGER_REVIEW, HR_REVIEW, CALIBRATION, FINAL, CLOSED | backend/app/models/appraisals.py | Yes | |
| Recruitment | RequisitionStatus | OPEN, APPROVED, ON_HOLD, CLOSED, CANCELLED | backend/app/models/recruitment.py | Status values found, but transition rules not clearly discoverable from current code | |
| Recruitment | CandidateStatus | APPLIED, SCREENING, INTERVIEW, OFFER, HIRED, REJECTED | backend/app/models/recruitment.py | Yes | |
| Offers | OfferStatus | DRAFT, SENT, ACCEPTED, REJECTED, WITHDRAWN | backend/app/models/recruitment.py | Status values found, but transition rules not clearly discoverable from current code | |
| ESS Leave | LeaveStatus | PENDING, APPROVED, REJECTED, CANCELLED | backend/app/models/ess.py | Yes | |
| Expense Claims | ExpenseStatus | DRAFT, SUBMITTED, APPROVED, REJECTED, PAID | backend/app/models/expenses.py | Yes | |
| Fleet/Trips | TripStatus | PLANNED, IN_TRANSIT, COMPLETED, CANCELLED | backend/app/models/fleet.py | Status values found, but transition rules not clearly discoverable from current code | |
| Van Sales | VanSaleStatus | OPEN, RECONCILED, CLOSED | backend/app/models/van_sales.py | Status values found, but transition rules not clearly discoverable from current code | |
| Dunning Cases | DunningStatus | OPEN, IN_PROGRESS, RESOLVED, WRITTEN_OFF | backend/app/models/dunning.py | Status values found, but transition rules not clearly discoverable from current code | |
| Fixed Assets | AssetStatus | ACTIVE, UNDER_MAINTENANCE, DISPOSED, RETIRED | backend/app/models/fixed_assets.py | Status values found, but transition rules not clearly discoverable from current code | |
| IoT Devices | IoTDeviceStatus | ACTIVE, INACTIVE, MAINTENANCE, ERROR | backend/app/models/iot.py | Status values found, but transition rules not clearly discoverable from current code | |
| IoT Alerts | AlertStatus | OPEN, ACKNOWLEDGED, RESOLVED | backend/app/models/iot.py | Yes | |
| AI Requests | AIProviderEnum | mock, anthropic, openai, gemini | backend/app/models/ai.py | N/A (config-based) | mock is default without API key |
| MRP Forecast | ForecastMethod | MOVING_AVG, EXP_SMOOTHING, PROPHET | backend/app/models/mrp.py | N/A (algorithm selection) | PROPHET is stub |
| MPS Campaign | MPS status values | Not clearly discoverable from current code | backend/app/models/mps.py | Not clearly discoverable | |
| Maintenance | MaintenanceStatus | PENDING, IN_PROGRESS, COMPLETED | backend/app/models/maintenance.py | Status values found, but transition rules not clearly discoverable from current code | |
| WhatsApp Demo | is_demo_mode | True/False | backend/app/models/whatsapp.py | Not transition (config flag) | True by default; False required for live production |

---

## 7. Role and Permission Inventory

### 7.1 Defined Roles (37 total)

| Role Key | Description | Dangerous Permissions |
|---|---|---|
| owner | Full system access | All permissions including delete, approve, payroll |
| admin | User & role mgmt + destructive ops | users.delete, roles.delete, company.manage |
| ceo | Read-only executive access | None (view/export only) |
| coo | Read-only operations | None (view/export only) |
| cfo | Finance authority | finance.approve, payroll_ke.approve |
| cto | Technical oversight | ai.configure |
| cmo | Marketing authority | marketing permissions |
| company_admin | Company-level admin | company.manage |
| finance_manager | Finance operations | finance.approve, finance.create |
| sales_manager | Sales operations | sales.approve, sales.cancel |
| procurement_officer | Procurement operations | procurement.approve, procurement.receive, procurement.post |
| warehouse_operator | Warehouse operations | inventory.edit (stock adjustment risk) |
| production_supervisor | Production operations | production.approve (release/complete orders) |
| quality_officer | QC operations | quality.approve (QC release — food safety risk) |
| logistics_officer | Logistics | logistics permissions |
| maintenance_technician | Maintenance | maintenance permissions |
| hr_manager | HR operations | hr.approve, payroll_ke.approve |
| factory_manager | Factory-wide | production.approve, quality.approve |
| warehouse_manager | Warehouse mgmt | wms.view, inventory.edit |
| production_manager | Production mgmt | production.approve |
| quality_manager | QMS + HACCP | quality.approve, consumer_complaints.close, consumer_complaints.link_recall |
| procurement_manager | Procurement mgmt | procurement.approve, procurement.post |
| regional_sales_manager | Regional sales | sales.approve |
| scoped_finance_manager | Scoped finance | finance.approve (scoped) |
| scoped_hr_manager | Scoped HR | hr.approve (scoped) |
| read_only_auditor | View/export only | None |
| shop_floor_operator | Shop floor execution | production.view (limited) |
| marketing_manager | Marketing | marketing.create, campaigns.create |
| field_marketing_agent | Field marketing | field permissions |
| brand_manager | Brand | brand permissions |
| trade_marketing_manager | Trade promotions | promotions.create |
| digital_marketing_manager | Digital channels | digital marketing |
| ecommerce_manager | E-commerce | ecommerce permissions |
| crm_manager | CRM | crm permissions |
| data_manager | Bulk import + analytics | bulk_import permissions |

### 7.2 Permission Enforcement Gaps

| Module | Area | Issue |
|---|---|---|
| Traceability | Recall initiation | Uses production.view — all production staff can initiate recalls |
| AI NL Command | Execute command | ai.create permission — but command scope not restricted; could execute dangerous actions |
| Analytics | All analytics pages | Permission enforcement needs review — some use generic analytics.view |
| WhatsApp | simulate-inbound | Only requires Bearer token — no role check |
| IoT | Ingestion | Only iot.ingest — no granular per-device control |
| M-Pesa | Van Sales M-Pesa | sales.view — same permission as read-only; payment initiation needs separate permission |
| Inventory | Stock Adjust | inventory.edit — bulk adjustments not separated from single-unit edits |
| Bulk Import | Any | Not clearly discoverable what role has access |

### 7.3 Backend Permission Pattern Verification

- Permission dependency: `require_permission(module, action)` from `app.core.deps`
- Pattern: `Depends(require_permission("module", "action"))`
- Verified in: company.py (all 12 endpoints), users.py, roles.py, ai.py, shelf_life.py
- Some older endpoints may use bare `Depends(get_current_user)` — requires review

---

## 8. Mock / Stub / Dev-Only Inventory

| Module | Feature | File Path | Mock/Stub Description | Production Risk | Recommendation |
|---|---|---|---|---|---|
| AI | AI Provider | backend/app/services/ai_provider.py | MockProvider returns deterministic "[MOCK/DEV MODE]" responses. Active when AI_PROVIDER=mock or no API key | High | Configure ANTHROPIC_API_KEY or OPENAI_API_KEY in production. Mock responses clearly labeled. |
| AI | AI Mode Label | backend/app/api/v1/endpoints/ai.py | Returns "Mock / Dev Mode" label when no API key; some AI actions disabled in mock mode | High | Same — configure live API key |
| AI | NL Command | backend/app/api/v1/endpoints/ai.py | Explicitly disabled in mock mode: "disabled in AI mock mode" | Medium | NL command executes arbitrary ERP actions — requires live AI + human review workflow |
| M-Pesa | STK Push / Payment | backend/app/services/mpesa_service.py | "placeholder implementation that simulates STK Push flow"; uses fake_request_id, fake_checkout, fake_merchant | Critical | Replace with real Safaricom Daraja API credentials before production |
| M-Pesa | Daraja | backend/app/services/mpesa_daraja_service.py | fake checkout/merchant IDs; `"_simulated": True` on all responses | Critical | Same as above — must configure real Daraja credentials |
| WhatsApp | Demo Mode | backend/app/models/whatsapp.py | `is_demo_mode = Column(Boolean, default=True)` — all messages are simulated | High | Set is_demo_mode=False and configure real WhatsApp Business API credentials |
| WhatsApp | Simulate Inbound | backend/app/api/v1/endpoints/whatsapp.py | POST /simulate-inbound creates fake inbound messages | Medium | Remove or restrict to dev environment in production |
| Bank API | Open Banking | backend/app/services/bank_api_service.py | "mock Kenyan bank sync" | High | Integrate real bank API (Equity, KCB, etc.) before enabling Open Banking feature |
| IoT | MQTT Streaming | backend/app/services/iot_service.py | "placeholder; MQTT/streaming bridge stub" | High | Connect real MQTT broker (Mosquitto/AWS IoT) before IoT monitoring is usable |
| Forecast | Prophet AI | backend/app/services/forecast_service.py | "Prophet-style AI forecasting is stubbed for future integration"; falls back to exponential smoothing | Medium | Forecasts work via ES fallback; Prophet stub means AI-powered accuracy not available |
| CRM | CRM Service | backend/app/services/crm_service.py | "scalable placeholder" | Medium | CRM endpoints exist but service logic may return placeholder results |
| E-commerce | Ecommerce Integration | backend/app/services/ecommerce_service.py | `simulated_orders` (max 3); "scalable placeholder; simulated orders" | High | Connect real e-commerce platform API (Shopify, WooCommerce) |
| Tax | eTIMS / KRA | backend/app/api/v1/endpoints/tax_regulatory.py | "Real integration — placeholder for live KRA call" | Critical | Must connect to real KRA eTIMS API before going live for tax compliance |
| Barcode | Label Printer | backend/app/services/barcode_service.py | "placeholder — integrate with label printer SDK" | Medium | Print queue UI works but no actual printer integration |
| Portal | Auth Token | backend/app/services/portal_service.py | "placeholder JWT-like token; use real JWT in production" | High | Supplier/Customer portal tokens must use proper JWT or OAuth |
| Auth | OTP Dispatch | backend/app/api/v1/endpoints/auth.py:109 | `# TODO: dispatch OTP via notification service` | High | 2FA shows UI but OTP is not dispatched; 2FA does not work in production |
| Marketing | Marketing Sync | backend/app/api/v1/endpoints/integrations.py | "MARKETING SYNC HOOKS (placeholders — swap body for real API calls in v2)" | Medium | Marketing integration (Facebook Ads, Google Ads, etc.) not connected |
| Developer | GraphQL | backend/app/api/v1/endpoints/api_portal.py | "GraphQL layer — stub" | Low | API portal exists but GraphQL queries not implemented |
| Payroll KE | PAYE Bands | backend/app/services/payroll_ke_service.py | "Fallback PAYE using hardcoded 2024 Kenya bands" — only a fallback | Medium | Primary calculation uses DB-stored bands; verify bands are seeded correctly |
| Seed | Demo Users | backend/app/db/seed.py | DEMO_USERS created in seed — includes demo_user with demo_role | Low | Ensure demo users are removed or password-changed before production |
| Seed | Utility Demo Data | backend/app/db/seed_utilities.py | "Insert all demo utility data" with reset option | Medium | Do not run seed_utilities with demo data in production |
| Traceability | Mock Recall Drill | frontend/src/app/dashboard/traceability/mock-recall/page.tsx | "Mock Recall Drill" — simulation, not real recall | Low | Clearly labeled; production recall requires real /recalls endpoint |
| QMS | Audit Types | frontend/src/app/dashboard/qms/audit-checklists/page.tsx | AUDIT_TYPES includes "MOCK" as a valid type | Low | Mock audit type is for drill purposes; clearly labeled |

---

## 9. Frontend/Backend Connection Gaps

| Module | Frontend Route | Backend Endpoint | Gap Description |
|---|---|---|---|
| Allergen | /dashboard/allergen/material-profiles | /allergen/material-profiles | Frontend placeholder or partial implementation |
| Allergen | /dashboard/allergen/label-readiness | /allergen/ | Frontend placeholder or partial implementation |
| Allergen | /dashboard/allergen/rollup | /allergen/ | Frontend placeholder or partial implementation |
| Market Intelligence | /dashboard/market-intelligence | /market-intel/ | Backend/API available, frontend screen not clearly found |
| Email Integration | /dashboard/email | /email/ | Frontend exists but limited UI — partial implementation |
| Reports (General) | /dashboard/reports/* | /analytics/ | Frontend/backend connection not clearly discoverable from current code |
| Approvals | /dashboard/approvals | /approvals/ | Global approval queue — backend exists, frontend connection unclear |
| Import History | /dashboard/import-history | /bulk-import/ | Frontend connection not clearly discoverable from current code |
| Moto Sales | Not clearly found | /moto-sales/ | Backend exists but frontend route not found in nav-config or pages |
| Calls/VoIP | /dashboard/calls | /calls/ | Frontend page exists; backend voip.py exists; connection not clearly discoverable |
| ESS AI | /dashboard/ess/ai | /ess/ | AI subpage — Backend/API available, frontend screen not clearly found |
| Loyalty | /dashboard/loyalty | /loyalty/ | Frontend exists; backend exists; connection not clearly discoverable from current code |
| NPS | /dashboard/nps | /nps/ | Frontend exists; backend exists; connection not clearly discoverable |
| Meetings | /dashboard/meetings | /meetings/ | Frontend exists; backend exists; connection not clearly discoverable |

---

## 10. Limitations of This Audit

1. **Static analysis only** — No live server running. Actual UI behavior, form validation, API responses, and user experience not observed.
2. **Page internals not fully inspected** — 755 pages × average 200-400 lines = too large for full inspection. Button/action inventory based on pattern matching and partial inspection.
3. **Permission audit is partial** — Only verified pattern-level (`require_permission`) usage. Full endpoint-by-endpoint permission audit requires running the API and checking each route.
4. **Mock mode behavior** — Many features appear functional in UI but return mock/placeholder data. Cannot distinguish from static analysis alone which features return real vs. simulated data.
5. **Database state unknown** — All migrations are in Alembic files but live DB not verified. Some features may depend on seed data being correctly populated.
6. **AI features require live API key** — All AI pages exist and have UI, but without API key configured, responses are mock.
7. **Integration features require external credentials** — M-Pesa, WhatsApp, Bank API, eTIMS, IoT, email, and e-commerce integrations require separate external credentials.
8. **Multi-company data isolation** — Company/branch filtering at application layer only; row-level DB security not confirmed.

---

## 11. Files Inspected

- `frontend/src/components/nav-config.tsx` — complete (755-item navigation)
- `frontend/src/lib/modules.ts` — module manifest API client
- `frontend/src/app/**/*.tsx` — 755 page files (names and routes; not all content)
- `backend/app/api/v1/router.py` — router registration
- `backend/app/core/module_registry.py` — 28 ModuleDefinitions, 105 EndpointRouteDefinitions
- `backend/app/db/seed.py` — 37 roles, 200+ permission tuples
- `backend/app/api/v1/endpoints/*.py` — 120 endpoint files (grep for patterns)
- `backend/app/models/*.py` — 110 model files (class names, enums)
- `backend/app/schemas/*.py` — 109 schema files (class counts)
- `backend/app/services/*.py` — 113 service files (stub/placeholder patterns)
- `backend/app/core/config.py` — AI mode, mock mode config
- `backend/app/core/integration_capabilities.py` — integration capability notes
