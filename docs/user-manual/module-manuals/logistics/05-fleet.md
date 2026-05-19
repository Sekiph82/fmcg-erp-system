# Fleet Management

**Route:** `/dashboard/logistics?tab=fleet`  
**Permission required:** `logistics.view`

## What It Does

Manages the domestic vehicle fleet used for last-mile delivery and inter-branch transport: vehicle register, driver roster, trip planning, fuel log, maintenance scheduling, and incident tracking.

![Fleet Tab](../../../screenshots/captured/module-ui/logistics/fleet/fleet-tab.png)
*Fleet dashboard showing KPI tiles, quick navigation, upcoming maintenance, and recent trips.*

## KPI Tiles

| KPI | Description |
|-----|-------------|
| Total Vehicles | All vehicles in register |
| Active | Currently operational vehicles |
| In Maintenance | Vehicles undergoing service |
| Trips Today | Trips scheduled for today |
| In Progress | Trips currently active |
| Open Incidents | Unresolved accident / damage reports |
| Available Drivers | Drivers not assigned to an active trip |
| Fuel Cost (Mo.) | This month's total fuel spend (KES) |
| Maint. Cost (Mo.) | This month's maintenance spend (KES) |

## Fleet Sub-Pages

| Page | Route | Description |
|------|-------|-------------|
| Vehicles | `/dashboard/fleet/vehicles` | Fleet register — plate, make, model, capacity |
| Drivers | `/dashboard/fleet/drivers` | Driver roster — licence, contacts, status |
| Trips | `/dashboard/fleet/trips` | Trip planning and real-time tracking |
| Fuel Log | `/dashboard/fleet/fuel` | Fuel fill-up records per vehicle |
| Maintenance | `/dashboard/fleet/maintenance` | Service records and upcoming maintenance due dates |
| Incidents | `/dashboard/fleet/incidents` | Accident and damage incident log |
| Reports & AI | `/dashboard/fleet/reports` | Analytics, cost trends, AI-generated insights |

## Upcoming Maintenance Panel

Shows vehicles with maintenance due within 14 days. Displays: Plate Number, Maintenance Type, Next Due Date, Days Until Due (red when ≤ 3 days).

## Recent Trips Panel

Shows the most recent trips with: Trip No, Trip Date, Purpose, Status.
