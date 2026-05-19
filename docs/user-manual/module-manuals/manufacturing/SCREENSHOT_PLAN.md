# Manufacturing Manual — Screenshot Plan

Screenshots are stored in `docs/user-manual/screenshots/captured/` (gitignored). Reference them in chapter files with:

```markdown
![Alt text](../../../screenshots/captured/{filename}.png)
```

---

## Screenshots by Chapter

### Chapter 01 — Recipes

| Screenshot File | Page / State | Priority |
|-----------------|-------------|----------|
| `recipes-list.png` | `/dashboard/recipes` — recipe list with data | HIGH |
| `recipes-new-modal.png` | New Recipe modal — all fields visible | HIGH |
| `recipes-detail-bom.png` | Recipe detail — BOM items tab | HIGH |
| `recipes-detail-process.png` | Recipe detail — Process Parameters tab | MEDIUM |
| `recipes-status-badge.png` | Recipe list — APPROVED and DRAFT badges visible | MEDIUM |

### Chapter 02 — Recipe Import

| Screenshot File | Page / State | Priority |
|-----------------|-------------|----------|
| `recipes-import-tab1.png` | Import modal — Recipe Headers tab | HIGH |
| `recipes-import-tab2.png` | Import modal — BOM Items tab | MEDIUM |
| `recipes-import-tab3.png` | Import modal — Process Steps tab | MEDIUM |
| `recipes-import-validation.png` | Import modal — after validation, showing pass/fail counts | HIGH |

### Chapter 03 — BOM & Formula

| Screenshot File | Page / State | Priority |
|-----------------|-------------|----------|
| `bom-list.png` | `/dashboard/bom` — BOM list with multiple types | HIGH |
| `bom-create-modal.png` | New BOM modal — fields visible | HIGH |
| `bom-detail-formula.png` | BOM detail — formula tab | HIGH |
| `bom-type-badges.png` | BOM list — multiple type badges visible | MEDIUM |

### Chapter 04 — Production Plans

| Screenshot File | Page / State | Priority |
|-----------------|-------------|----------|
| `production-plans-list.png` | `/dashboard/production?tab=plans` — plan list | HIGH |
| `production-plans-new.png` | New Production Plan modal | HIGH |
| `production-plans-confirm.png` | Plan list — Confirm button visible on DRAFT plan | MEDIUM |

### Chapter 07 — QC Inspections

| Screenshot File | Page / State | Priority |
|-----------------|-------------|----------|
| `quality-inspections-list.png` | `/dashboard/quality` — inspection list | HIGH |
| `quality-new-inspection.png` | New QC Inspection modal | HIGH |
| `quality-dashboard-cards.png` | QC dashboard summary cards | MEDIUM |
| `quality-inspection-detail.png` | Inspection detail with test results | HIGH |

### Chapter 08 — Shop Floor

| Screenshot File | Page / State | Priority |
|-----------------|-------------|----------|
| `shopfloor-overview.png` | `/dashboard/shop-floor` — overview KPI grid | HIGH |
| `shopfloor-terminal.png` | Operator terminal page | HIGH |
| `shopfloor-supervisor.png` | Supervisor console | MEDIUM |
| `shopfloor-downtime-board.png` | Downtime board with active events | MEDIUM |
| `shopfloor-handover.png` | Shift handover list | MEDIUM |

### Chapter 09 — Planning

| Screenshot File | Page / State | Priority |
|-----------------|-------------|----------|
| `planning-dashboard.png` | `/dashboard/planning` — scenario list and KPIs | HIGH |
| `planning-new-scenario.png` | New Planning Scenario modal | HIGH |
| `planning-bottlenecks.png` | Bottleneck explorer | MEDIUM |
| `planning-schedule.png` | Schedule Gantt board | MEDIUM |

### Chapter 10 — NPD

| Screenshot File | Page / State | Priority |
|-----------------|-------------|----------|
| `npd-projects-grid.png` | `/dashboard/npd` — project card grid | HIGH |
| `npd-new-project.png` | New Project form | HIGH |
| `npd-stage-pipeline.png` | Stage filter chips visible | MEDIUM |

---

## Capture Notes

- All screenshots from the existing Playwright capture suite in `docs/user-manual/screenshots/`
- To add new routes to the capture suite, add entries to `docs/user-manual/screenshots/routes.json`
- Re-run: `cd frontend && E2E_SKIP_WEBSERVER=1 npm run test:manual-screenshots`
- Existing captured files: 140+ PNGs (see `screenshots-index.json` for full list)

---

## Screenshots Already Captured

Check `docs/user-manual/screenshots/screenshots-index.json` for which routes have been captured. Filter by `module` = `production`, `quality`, `planning` etc. to find existing relevant screenshots. If the filename matches, no new capture is needed.
