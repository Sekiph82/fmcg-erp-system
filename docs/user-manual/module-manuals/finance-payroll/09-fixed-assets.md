# Fixed Assets & Dimensions

---

## Fixed Assets

**Route:** `/dashboard/finance?tab=fixed-assets`  
**Permission required:** `finance.view`

### What It Does

Fixed Assets manages the full financial lifecycle of long-lived assets: acquisition, depreciation scheduling, disposal, and asset transfers between cost centres or locations.

![Fixed Assets tab](../../../screenshots/captured/module-ui/finance-payroll/finance/fixed-assets-tab.png)
*Fixed Assets tab within the Finance workspace.*

![Fixed Assets dashboard](../../../screenshots/captured/module-ui/finance-payroll/fixed-assets/fixed-assets-dashboard.png)
*Fixed Assets standalone dashboard showing seven KPI tiles and module navigation quick links.*

### Dashboard KPIs

| KPI | Description |
|---|---|
| Total Assets | Count of all asset records |
| Active Assets | Count of assets not disposed or written off |
| Total Cost (KES) | Sum of acquisition costs of all assets |
| Accumulated Depreciation | Total cumulative depreciation charged |
| Net Book Value | Total Cost minus Accumulated Depreciation |
| Pending Depreciation Lines | Scheduled depreciation lines not yet posted |
| AI Recommendations | Open AI agent recommendations awaiting review |

### Fixed Assets Sub-pages

| Page | Route | Purpose |
|---|---|---|
| Asset Register | `/dashboard/fixed-assets/assets` | Full list of all assets |
| New Asset | `/dashboard/fixed-assets/assets/new` | Create asset record |
| Asset Categories | `/dashboard/fixed-assets/categories` | Depreciation method and useful life by category |
| Depreciation Schedules | `/dashboard/fixed-assets/depreciation` | Per-asset depreciation lines |
| Posting Run | `/dashboard/fixed-assets/posting` | Post pending depreciation to the GL |
| Disposals | `/dashboard/fixed-assets/disposal` | Record asset sales or write-offs |
| Transfers | `/dashboard/fixed-assets/transfer` | Move asset between cost centres |
| Legacy Import | `/dashboard/fixed-assets/import` | Bulk import existing asset register |
| AI Agents | `/dashboard/fixed-assets/ai` | AI-suggested actions (revaluation, disposal, maintenance) |

### Asset Depreciation Methods

Configured per asset category:

| Method | Description |
|---|---|
| Straight Line | Equal annual charge: (Cost − Residual) ÷ Useful Life |
| Reducing Balance | Fixed percentage applied to net book value each period |

### Asset Lifecycle Flow

```
New Asset created (acquisition date, cost, category)
    → Depreciation schedule auto-generated
    → Monthly Posting Run charges depreciation to GL
    → Asset reaches zero NBV or disposal decision
    → Disposal record created (sale proceeds or write-off)
    → GL disposal entry posted
```

---

## Dimensions

**Route:** `/dashboard/finance?tab=dimensions`  
**Permission required:** `finance.view`

### What It Does

Dimensions allow financial transactions to be tagged with additional analysis codes (cost centre, project, product line, region). Dimension tags flow through to the general ledger and are used for management reporting.

![Dimensions tab](../../../screenshots/captured/module-ui/finance-payroll/finance/dimensions-tab.png)
*Dimensions tab showing dimension types and their configured values.*

### Common Dimension Types

| Dimension | Examples |
|---|---|
| Cost Centre | Production, Sales, HR, IT |
| Project | specific capital or opex project codes |
| Product Line | FMCG category groupings |
| Region | Kenya Central, Nairobi, Mombasa |
