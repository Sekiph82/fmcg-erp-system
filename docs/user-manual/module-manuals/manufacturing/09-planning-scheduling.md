# Advanced Planning & MRP

**Route:** `/dashboard/planning`  
**Permission required:** `planning.view`  
**Workspace tabs:** Dashboard, Schedule, Capacity, Simulation, Bottlenecks, Changeover, MRP, MPS, Kanban

---

## What It Does

The Advanced Planning module provides finite and infinite capacity scheduling, material requirements planning (MRP), master production scheduling (MPS), bottleneck detection, and AI-driven optimisation. It is built for production planners who need to schedule across multiple work centers, manage capacity constraints, and align production with demand.

![Planning workspace](../../../screenshots/captured/058_planning.png)
*Advanced Planning workspace showing the dashboard with scenario KPIs, scenario list, and navigation tabs.*

---

## Planning Dashboard Tab

**Tab key:** `advanced`

### Dashboard KPIs

| KPI | Field | Description |
|-----|-------|-------------|
| Active Scenarios | `active_scenarios` | Planning scenarios currently in use |
| Total Ops Today | `total_ops_today` | Total scheduled operations for today |
| Scheduled % | `scheduled_pct` | Percentage of operations scheduled vs. total required |
| Avg Utilisation | `avg_utilization_pct` | Average capacity utilisation across all work centers |
| Critical Bottlenecks | `critical_bottlenecks` | Count of work centers at critical overload |
| Pending AI Recs | `pending_ai_recs` | AI recommendations awaiting review |

### Scenario List

Each scenario row shows:
- `scenario_no` — system reference number
- `scenario_name` — user-assigned name (clickable link to Schedule Board)
- `status` — scenario state (coloured badge)
- `mode` — FINITE or INFINITE capacity mode
- `horizon_start` → `horizon_end` — planning horizon date range
- `scheduled_ops / total_ops` — progress fraction
- `bottleneck_count` — count of detected bottlenecks
- `calculated_at` — date of last calculation

**Status badge colours** depend on the scenario status (DRAFT, ACTIVE, ARCHIVED, etc.).

### Top Bottlenecks Panel

Shows the most constrained work centers with:
- `work_center_name` — name of the bottleneck work center
- `severity` — bottleneck severity badge
- `peak_utilization_pct` — highest utilisation percentage in the horizon
- `overloaded_days` — count of days with utilisation > 100%

### AI Recommendations Panel

Pending AI recommendations from the planning agents:
- `agent_type` — which AI agent generated it (coloured badge)
- `title` — recommendation summary

### Quick Navigation

| Action | Route |
|--------|-------|
| Schedule Board | `/dashboard/planning/schedule` |
| Capacity Board | `/dashboard/planning/capacity` |
| Bottleneck Explorer | `/dashboard/planning/bottlenecks` |
| Simulation Sandbox | `/dashboard/planning/simulation` |
| Changeover Matrix | `/dashboard/planning/changeover` |

---

## Creating a Planning Scenario

**Button:** `+ New Scenario`

### New Planning Scenario Fields

| Field | Label | Required | Default | Notes |
|-------|-------|----------|---------|-------|
| `scenario_name` | Scenario name | Yes | — | Descriptive name; e.g. "Q2 2026 Baseline" |
| `mode` | Capacity mode | Yes | `FINITE` | `FINITE` (respects work center limits) / `INFINITE` (no capacity constraints) |
| `description` | Description | No | — | Optional notes |

Submit disabled until `scenario_name` is filled.

### Capacity Modes

| Mode | When to Use |
|------|-------------|
| `FINITE` | Standard scheduling — work orders queue when capacity is full; bottlenecks are identified |
| `INFINITE` | "What-if" analysis — schedule without capacity limits; shows theoretical throughput |

Start with a FINITE scenario for operational planning. Use INFINITE for demand-side what-if analysis.

---

## Schedule Tab

**Tab key:** `schedule`  
**Route:** `/dashboard/planning/schedule/page`

Interactive Gantt board showing scheduled operations per work center per day/shift. Drag-and-drop to reschedule. Conflicts highlighted in red.

Navigate to a specific scenario via URL: `/dashboard/planning/schedule?scenario={id}`

---

## Capacity Tab

**Tab key:** `capacity`  
**Route:** `/dashboard/planning/capacity/page`

![Planning — Capacity tab](../../../screenshots/captured/061_planning-capacity.png)
*Capacity tab showing work center load vs. available capacity for the planning horizon.*

Visual capacity loading chart per work center for the planning horizon. Shows available capacity, scheduled load, and overloaded periods. Used to identify where to offload or reschedule.

---

## Simulation Tab

**Tab key:** `simulation`  
**Route:** `/dashboard/planning/simulation/page`

Sandbox environment to test alternative schedules without affecting operational plans. Create a simulation scenario, apply changes (shift priorities, add/remove work orders, change capacity), and compare results with the baseline.

---

## Bottlenecks Tab

**Tab key:** `bottlenecks`  
**Route:** `/dashboard/planning/bottlenecks/page`

Detailed bottleneck analysis explorer. Shows each constrained work center with:
- Overload severity
- Number of overloaded days in the horizon
- Peak utilisation date
- Work orders contributing to overload
- AI recommendations for resolution

---

## Changeover Tab

**Tab key:** `changeover`  
**Route:** `/dashboard/planning/changeover/page`

Changeover matrix management. Defines the setup time required when switching between products on a given work center (e.g. from product A to product B on Line 1 = 45 minutes). The scheduler uses these times when sequencing work orders to minimise total changeover duration.

---

## MRP Tab

**Tab key:** `mrp`  
**Route:** `/dashboard/mrp/page`

![Planning — MRP tab](../../../screenshots/captured/059_planning-mrp.png)
*MRP tab showing material requirements plan output with planned orders and suggested actions.*

Material Requirements Planning calculates what materials need to be ordered or produced, by when, to fulfil the demand plan.

MRP run inputs:
- Demand (from MPS or sales orders)
- Current stock on hand
- Open purchase orders
- BOM explosions
- Planned production orders

MRP run outputs:
- Planned purchase orders (with suggested due dates)
- Planned production orders
- Action messages (expedite, defer, cancel)

---

## MPS Tab

**Tab key:** `mps`  
**Route:** `/dashboard/mps/page`

![Planning — MPS tab](../../../screenshots/captured/060_planning-mps.png)
*Master Production Schedule tab showing the time-phased production schedule by product.*

Master Production Schedule defines the production plan at the finished goods level across the planning horizon. MPS drives MRP. Planners manage MPS quantities by product and week/day.

---

## Kanban Tab

**Tab key:** `kanban`  
**Route:** `/dashboard/kanban/page`

Kanban-based replenishment for high-velocity materials or work centers that operate on pull scheduling rather than MRP push scheduling. Manages Kanban card quantities, bin sizes, and replenishment triggers.
