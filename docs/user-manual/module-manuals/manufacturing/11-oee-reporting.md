# OEE, Downtime & Yield Reporting

**Routes:** `/dashboard/production?tab=oee`, `?tab=downtime`, `?tab=waste-yield`, `?tab=reports`, `?tab=variance`  
**Permission required:** `production.view`

---

## Overall Equipment Effectiveness (OEE)

**Tab key:** `oee`  
**Route:** `/dashboard/production/oee/page`

OEE is the primary manufacturing performance metric. It measures how effectively production equipment is being used compared to its full potential.

### OEE Formula

```
OEE = Availability × Performance × Quality

Availability = (Planned time - Downtime) / Planned time
Performance  = (Actual output / Maximum possible output) × 100
Quality      = (Good output / Total output) × 100
```

### OEE Benchmark Targets

| OEE | World-Class | Good | Acceptable | Poor |
|-----|-------------|------|------------|------|
| % | ≥ 85% | 70–85% | 60–70% | < 60% |

### OEE Dashboard Metrics

| Metric | Description |
|--------|-------------|
| OEE % | Composite OEE score per work center or line |
| Availability % | Time equipment was available vs. scheduled |
| Performance % | Speed efficiency vs. rated speed |
| Quality % | Good output vs. total output |
| Planned vs. Actual | Comparison of planned production vs. actual completed |

### OEE by Work Center

The OEE tab shows OEE broken down per work center for the selected period. Work centers below the target OEE threshold are highlighted.

### OEE Trend Chart

Historical OEE trend for the selected work center and date range. Used to detect systematic decline (equipment wear, process drift) or improvement after maintenance interventions.

---

## Downtime Analysis

**Tab key:** `downtime`  
**Route:** `/dashboard/production/downtime/page`

### Downtime Impact on OEE

All downtime events recorded in the Shop Floor module feed directly into OEE Availability calculations. Planned downtime (maintenance windows) is excluded from availability calculations; unplanned downtime reduces availability.

### Downtime Report Metrics

| Metric | Description |
|--------|-------------|
| Total downtime minutes | Sum of all downtime durations in the period |
| Downtime by category | Pareto chart — which categories cause most lost time |
| Mean Time Between Failures (MTBF) | Average operating time between breakdowns |
| Mean Time To Repair (MTTR) | Average repair duration |
| Top 3 machines by downtime | Identifies most problematic equipment |

### Pareto Analysis

The downtime tab provides a Pareto chart of downtime by category. The 80/20 rule applies: typically 20% of root causes drive 80% of lost time. Focus corrective actions on the top causes.

---

## Waste & Yield

**Tab key:** `waste-yield`  
**Route:** `/dashboard/production/waste-yield/page`

### Key Metrics

| Metric | Formula | Notes |
|--------|---------|-------|
| Yield % | `Good Qty / (Good Qty + Scrap Qty) × 100` | Per work order or per period |
| Waste Qty | Sum of scrap quantities | In production UOM (KG, L, etc.) |
| Waste Cost | `Waste Qty × Material Cost` | Material value of waste |
| Loss % | `100 - Yield %` | Inverse of yield |

### Waste by Category

Waste is categorised at the work order level. Common waste categories:
- **Startup waste** — lost during line startup before process stabilises
- **Shutdown waste** — product remaining in lines at shutdown
- **Quality reject** — off-spec product removed at QC checks
- **Overflow / spill** — process losses from equipment

### Yield vs. Recipe Standard

Each work order has a **standard yield** from the recipe's `loss_percentage` settings. The Waste & Yield tab compares:
- Actual yield vs. standard yield
- Yield variance (favourable if actual > standard; adverse if actual < standard)

---

## Production Reports Tab

**Tab key:** `reports`  
**Route:** `/dashboard/production/reports/page`

Standard reports available:

| Report | Description |
|--------|-------------|
| Production Summary | Orders completed, quantities produced, by period and work center |
| Work Order Status | All open and closed work orders with progress |
| Material Consumption | Materials issued vs. BOM standard |
| Labour Efficiency | Actual hours vs. standard routing hours |
| OEE Report | OEE, Availability, Performance, Quality by work center |
| Waste & Yield Summary | Yield rates and waste costs by product and period |

Reports can be filtered by date range, work center, product, and production plan. Export to CSV is available on all reports.

---

## Variance Analysis

**Tab key:** `variance`  
**Route:** `/dashboard/production/variance/page`

### Variance Types

| Variance | Favourable (F) | Adverse (A) |
|----------|----------------|-------------|
| **Material Usage** | Used less material than standard | Used more than standard |
| **Material Price** | Materials cost less than standard | Materials cost more than standard |
| **Labour Efficiency** | Fewer hours than standard | More hours than standard |
| **Labour Rate** | Labour rates lower than standard | Labour rates higher than standard |
| **Overhead Absorption** | More overhead absorbed than expected | Under-absorbed (low production volume) |

### Variance Report

For each work order or production period, the variance report shows:
- Standard cost per unit (from BOM + Routing)
- Actual cost per unit (from materials issued + hours logged)
- Total variance (KES)
- Variance percentage
- Variance type breakdown

Variances above the configured threshold (e.g. ±5%) are flagged for management review and root cause documentation.
