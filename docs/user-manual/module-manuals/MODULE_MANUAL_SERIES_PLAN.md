# Module Manual Series — Production Plan

**Purpose:** Each module manual is a standalone deep-dive document covering every screen, field, workflow, and import format for that manufacturing domain. Together they form the complete FMCG ERP operational library beyond the Kenya Go-Live and Full Reference manuals.

---

## Series Overview

| # | Module | Audience | Priority | Est. Chapters |
|---|--------|----------|----------|---------------|
| 1 | Manufacturing | Production, Quality, Planning roles | HIGH | 13 |
| 2 | Supply Chain | Procurement, Warehouse, Logistics roles | HIGH | ~12 |
| 3 | Finance & Payroll | Finance, HR roles | MEDIUM | ~10 |
| 4 | Sales & Distribution | Sales, POS Operator roles | MEDIUM | ~8 |
| 5 | Admin & Master Data | System Admin, Data Entry roles | MEDIUM | ~8 |
| 6 | Analytics & AI | Manager, Analyst roles | LOW | ~6 |

---

## Manufacturing Module — Chapter Map

| File | Title | Key Content |
|------|-------|-------------|
| `00-overview.md` | Manufacturing Overview | Module map, navigation, permissions |
| `01-recipes.md` | Recipes | Recipe header fields, BOM items, process parameters, status workflow |
| `02-recipes-import.md` | Recipe Bulk CSV Import | 3-tab import, CSV column names, validation, import modes |
| `03-bom-formula.md` | BOM & Formula Management | BOM types, lifecycle, create form, detail tabs |
| `04-production-plans.md` | Production Plans | Plan creation, status workflow, confirmation |
| `05-work-orders.md` | Work Orders & Scheduling | Work order tabs, scheduling, work centers, routing |
| `06-batch-lots.md` | Batch & Lots | Batch tracking, lot numbers, traceability |
| `07-quality-control.md` | QC Inspections | Inspection types, create form, test results, decisions |
| `08-shop-floor.md` | Shop Floor Operations | Terminal, Supervisor, Queue, Downtime, Handover |
| `09-planning-scheduling.md` | Advanced Planning & MRP | Scenarios, capacity, MRP, MPS, Kanban |
| `10-npd.md` | New Product Development | Stage-gate pipeline, project fields, categories |
| `11-oee-reporting.md` | OEE, Downtime & Yield | OEE KPIs, downtime categories, waste & yield |
| `12-compliance.md` | Compliance & Labelling | GS1 labels, barcodes, regulatory certificates |

---

## Quality Benchmark

Chapter `01-recipes.md` serves as the quality benchmark for this series:
- Every field documented with its exact form label, backend field name, type, and constraints
- Every status value listed with transition rules
- Every table column described
- Every import CSV column listed with `*` marking required fields
- DRAFT-only operations explicitly called out

All subsequent chapters in this series and future modules must match this level of field-level accuracy. Do not infer field names from chapter titles — read the source code.

---

## Screenshot Strategy

Screenshots are stored in the shared directory `docs/user-manual/screenshots/captured/` (gitignored). The Manufacturing manual references screenshots using relative paths from within each chapter file:

```markdown
![Recipe List](../../../screenshots/captured/recipes-list.png)
```

Screenshots captured by the existing Playwright suite. If a new page needs a screenshot not in the current `routes.json`, add it there and re-run the capture script.

---

## PDF Strategy

Each module manual has its own PDF generator at:
```
docs/user-manual/module-manuals/{module}/pdf-export/generate-{module}-pdf.mjs
```

PDF outputs go to `docs/user-manual/pdf-output/` which is gitignored. Generate locally before distribution. Pipeline validates: screenshots exist, chapter files exist, no broken image refs.
