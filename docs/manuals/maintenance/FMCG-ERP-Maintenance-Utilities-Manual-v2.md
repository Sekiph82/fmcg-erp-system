# FMCG ERP — Maintenance & Utilities Manual v2

**Version:** 2.0 (post-recovery)  
**Date:** 2026-05-24  
**Audience:** Maintenance Managers, Engineers, Utility Managers, Factory Managers  
**Modules Covered:** Maintenance · Assets · Breakdowns · Planned Maintenance · Predictive Maintenance · Spare Parts · Utilities (Electricity, Water)

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Maintenance Overview Dashboard](#2-maintenance-overview-dashboard)
3. [Asset Register](#3-asset-register)
4. [Breakdown Management](#4-breakdown-management)
5. [Planned Maintenance](#5-planned-maintenance)
6. [Maintenance Work Orders](#6-maintenance-work-orders)
7. [Predictive Maintenance](#7-predictive-maintenance)
8. [Spare Parts Management](#8-spare-parts-management)
9. [Maintenance Reports](#9-maintenance-reports)
10. [Utility Management — Electricity](#10-utility-management--electricity)
11. [Utility Management — Water](#11-utility-management--water)
12. [Common Mistakes & Troubleshooting](#12-common-mistakes--troubleshooting)
13. [Related Modules](#13-related-modules)

---

## 1. Module Overview

**What it does:** Manages equipment and facility maintenance — asset register, breakdown logging, preventive maintenance scheduling, predictive maintenance alerts, spare parts inventory, and utility consumption tracking.

**Who uses it:**
- Maintenance Manager — schedules preventive maintenance, monitors asset health
- Maintenance Engineer — logs breakdowns, executes work orders
- Utility Manager — tracks electricity and water consumption
- Production Manager — coordinates planned downtime for maintenance

**When to use it:**
- When a machine breaks down and needs urgent repair
- When scheduling preventive maintenance (PM) activities
- When tracking spare parts usage and stock
- When monitoring electricity and water consumption
- When reviewing equipment uptime and MTBF

**Modules at a glance:**

| Feature | Route | Purpose |
|---------|-------|---------|
| Maintenance | `/dashboard/maintenance` | Full maintenance workspace |
| Utility Management | `/dashboard/utility-management` | Electricity and water tracking |

![Maintenance Overview](../../user-manual/screenshots/captured/119_maintenance.png)
*Maintenance module overview.*

---

## 2. Maintenance Overview Dashboard

**Tab:** Overview

![Maintenance Dashboard](../../user-manual/screenshots/captured/module-ui/maintenance/overview/overview-tab.png)
*Maintenance dashboard — assets count, open breakdowns, pending PM tasks, MTBF, MTTR.*

KPI cards:
- Total Assets (active)
- Open Breakdowns
- Planned PM Tasks Due This Week
- Average MTBF (Mean Time Between Failures)
- Average MTTR (Mean Time To Repair)
- Spare Parts Low Stock Alerts

Charts: Breakdown frequency by machine, PM compliance rate, maintenance cost trend.

---

## 3. Asset Register

**Tab:** Assets

### What it does
Maintains the master register of all equipment and facilities — machines, vehicles, utilities, and infrastructure.

![Assets Tab](../../user-manual/screenshots/captured/module-ui/maintenance/assets/assets-tab.png)
*Asset register — all assets with ID, name, location, status, and last maintenance date.*

### Creating a New Asset

Click **+ New Asset**:

![New Asset Modal](../../user-manual/screenshots/captured/module-ui/maintenance/assets/new-asset-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Asset Name | Yes | e.g. "Packaging Line 3 Filler" |
| Asset Code | Yes | Unique identifier e.g. "PL3-FILL-001" |
| Category | Yes | Machine / Vehicle / Infrastructure / IT |
| Location | Yes | Factory area / line |
| Manufacturer | No | Equipment manufacturer |
| Model | No | Model number |
| Serial Number | No | Manufacturer serial number |
| Purchase Date | No | Date acquired |
| Purchase Cost | No | Acquisition cost |
| Warranty Expiry | No | Warranty end date |
| Useful Life (years) | No | Expected operational life |
| PM Frequency | No | Days between preventive maintenance |
| Criticality | Yes | Critical / Essential / Standard |
| Status | Yes | Active / Under Maintenance / Decommissioned |

### Asset Criticality

| Level | Meaning | PM Priority |
|-------|---------|-------------|
| Critical | Loss stops production entirely | Highest; no deferral |
| Essential | Loss significantly impacts output | High; 24-hour response |
| Standard | Limited production impact | Normal scheduling |

---

## 4. Breakdown Management

**Tab:** Breakdowns

### What it does
Log unplanned equipment failures — capture breakdown time, root cause, repair actions, parts used, and downtime duration.

![Breakdowns Tab](../../user-manual/screenshots/captured/module-ui/maintenance/breakdowns/breakdowns-tab.png)
*Breakdown log — all breakdown events with machine, start time, resolution time, and root cause.*

### Logging a Breakdown

Click **+ Log Breakdown**:

![Log Breakdown Modal](../../user-manual/screenshots/captured/module-ui/maintenance/breakdowns/log-breakdown-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Asset | Yes | Machine that failed |
| Breakdown Start Time | Yes | Date and time failure occurred |
| Failure Description | Yes | What happened |
| Failure Category | Yes | Mechanical / Electrical / Pneumatic / Hydraulic / Operator / Other |
| Severity | Yes | Minor / Major / Critical |
| Reported By | Yes | Person logging the breakdown |
| Assigned Technician | No | Who will repair |
| Estimated Repair Time | No | Expected duration in hours |

### Breakdown Workflow

1. **Log breakdown** → status: OPEN
2. Technician assigned → status: IN_PROGRESS
3. **Log repair actions** — describe what was done
4. **Record parts used** — deduct from spare parts inventory
5. **Record actual repair time**
6. **Close breakdown** — enter root cause, corrective action, and preventive measure
7. Status: CLOSED → downtime minutes auto-calculated
8. Downtime fed to Production → OEE (if linked to machine)

### Breakdown Downtime to OEE
Closed breakdowns linked to a production machine automatically update OEE downtime records. Ensure Asset is linked to the correct Work Center in Manufacturing.

---

## 5. Planned Maintenance

**Tab:** Plans

### What it does
Schedule preventive maintenance tasks — periodic inspections, lubrication, calibration, and overhauls.

![Plans Tab](../../user-manual/screenshots/captured/module-ui/maintenance/plans/plans-tab.png)
*Planned maintenance list — upcoming PM tasks by asset and due date.*

### Creating a Maintenance Plan

Click **+ New PM Plan**:

![New Plan Modal](../../user-manual/screenshots/captured/module-ui/maintenance/plans/new-plan-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Asset | Yes | Target equipment |
| Task Name | Yes | e.g. "Monthly Lubrication Check" |
| Task Type | Yes | Inspection / Lubrication / Calibration / Overhaul / Cleaning |
| Frequency | Yes | Daily / Weekly / Monthly / Quarterly / Annual / Hours-based |
| Interval | Yes | Number (e.g. 30 for every 30 days or 500 for every 500 hours) |
| Estimated Duration (hrs) | Yes | Time to complete |
| Assigned To | No | Default technician |
| Checklist | No | Step-by-step task checklist |
| Next Due Date | Yes | First or next scheduled date |
| Required Parts | No | Pre-stage spare parts |

### PM Schedule View
System auto-calculates next due dates. Upcoming tasks shown in calendar view. Overdue tasks flagged in red.

---

## 6. Maintenance Work Orders

**Tab:** Work Orders

### What it does
Formal work orders for both planned and breakdown maintenance activities.

![Work Orders Tab](../../user-manual/screenshots/captured/module-ui/maintenance/plans/work-orders-tab.png)
*Maintenance work orders — all active and completed work orders.*

**Work Order Status Flow:** `OPEN → ASSIGNED → IN_PROGRESS → PARTS_AWAITING → COMPLETED → CLOSED`

**Work Order fields:**
| Field | Purpose |
|-------|---------|
| Asset | Equipment being maintained |
| Type | Breakdown / Preventive / Predictive / Project |
| Priority | Emergency / High / Normal / Low |
| Assigned Technician | Person doing the work |
| Scheduled Date | When to perform |
| Actual Start / End | For MTTR calculation |
| Parts Used | Spare parts consumed |
| Labor Hours | Time spent |
| Root Cause | For breakdown WOs |
| Work Performed | Description of actions taken |

---

## 7. Predictive Maintenance

**Tab:** Predictive

### What it does
Monitors equipment condition data (vibration, temperature, oil analysis) to predict failures before they occur.

![Predictive Tab](../../user-manual/screenshots/captured/module-ui/maintenance/predictive/predictive-tab.png)
*Predictive maintenance — sensor readings, trend analysis, and risk alerts.*

**Condition monitoring parameters:**
- Vibration (mm/s or g)
- Temperature (°C)
- Current draw (A)
- Oil viscosity/contamination
- Noise level (dB)

**Alerts:** System generates alert when reading exceeds threshold → creates predictive maintenance work order automatically.

---

## 8. Spare Parts Management

**Tab:** Spares

### What it does
Manage spare parts inventory — stock levels, reorder points, part-to-asset linkage.

![Spares Tab](../../user-manual/screenshots/captured/module-ui/maintenance/spares/spares-tab.png)
*Spare parts register — part name, compatible assets, stock on hand, and reorder level.*

### Adding a Spare Part

Click **+ Add Part**:

![Add Part Modal](../../user-manual/screenshots/captured/module-ui/maintenance/spares/add-part-modal.png)

| Field | Required | Notes |
|-------|----------|-------|
| Part Name | Yes | Descriptive name |
| Part Number | Yes | Manufacturer part number |
| Compatible Assets | No | Assets this part is used on |
| Supplier | No | Preferred supplier |
| Unit of Measure | Yes | Each / Kg / Litre |
| Current Stock | Yes | Quantity on hand |
| Reorder Point | Yes | Trigger level for reorder |
| Reorder Quantity | Yes | Standard order quantity |
| Unit Cost | Yes | For valuation |
| Storage Location | No | Warehouse bin location |

### Parts Usage
When a breakdown work order is closed with parts used, spare parts stock is automatically reduced. Low-stock alerts generated when stock falls below reorder point.

---

## 9. Maintenance Reports

**Tab:** Reports

![Reports Tab](../../user-manual/screenshots/captured/module-ui/maintenance/reports/reports-tab.png)
*Maintenance reports — MTBF/MTTR trends, breakdown frequency, PM compliance, cost analysis.*

**Standard reports:**
- MTBF by asset (Mean Time Between Failures)
- MTTR by asset (Mean Time To Repair)
- Breakdown frequency Pareto (which machines break most)
- PM compliance rate (% of planned maintenance completed on time)
- Maintenance cost by asset and category
- Spare parts consumption trend

---

## 10. Utility Management — Electricity

**Route:** `/dashboard/utility-management`  
**Tab:** Electricity

### What it does
Track electricity consumption by meter, area, and machine. Monitor against targets and benchmarks.

![Utility Management Overview](../../user-manual/screenshots/captured/122_utility-management.png)
*Utility management overview.*

![Electricity Tab](../../user-manual/screenshots/captured/123_utility-electricity.png)
*Electricity consumption dashboard — kWh by area, peak demand, and cost.*

**Electricity tracking:**
- Meter readings entered daily/weekly
- System calculates consumption between readings
- Alerts on consumption exceeding threshold
- Cost calculated using configured tariff rates
- Reports: consumption by area, by shift, by machine, cost per unit produced

### Recording a Meter Reading
1. Utility → Electricity → **+ New Reading**
2. Select meter
3. Enter reading and date/time
4. System calculates kWh consumed since last reading

---

## 11. Utility Management — Water

**Tab:** Water

![Water Tab](../../user-manual/screenshots/captured/124_utility-water.png)
*Water consumption dashboard — m³ by process area and cost.*

Same workflow as electricity — meter readings, consumption calculation, and cost analysis.

**Water-specific tracking:**
- Borehole extraction vs. municipal supply
- Process water vs. cleaning water separation
- Effluent discharge monitoring
- Water intensity (litres per unit produced)

---

## 12. Common Mistakes & Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Breakdown not affecting OEE | Asset not linked to work center | Link asset to work center in Asset master |
| PM task not showing as overdue | Frequency set incorrectly | Check PM plan interval and next due date |
| Spare parts stock not reducing | Work order closed without entering parts used | Edit closed work order → add parts used → repost |
| Predictive alert not triggering | Threshold not configured | Set alert thresholds in Predictive → Settings for each sensor |
| Utility cost not calculating | Tariff rate not set | Configure electricity/water tariff in Utility → Settings |
| Breakdown root cause missing | Work order closed without root cause | Root cause is required for CLOSED status — reopen and complete |

---

## 13. Related Modules

| This Action | Connects To |
|-------------|-------------|
| Breakdown logged | Production → OEE (downtime record) |
| PM work order | Spare Parts (consumption) + HR (technician time) |
| Predictive alert | Maintenance → Work Order (auto-created) |
| Spare parts reorder | Procurement → Purchase Requisition |
| Asset capitalized | Finance → Fixed Assets |
| Utility cost | Finance → Budgeting (utility expense) |

---

*End of Maintenance & Utilities Manual v2*
