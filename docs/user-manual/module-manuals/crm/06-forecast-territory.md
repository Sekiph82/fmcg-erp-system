# Forecast & Territory

---

## Revenue Forecast

**Route:** `/dashboard/crm?tab=forecast`  
**Permission required:** `crm.view`

### What It Does

The Forecast tab projects revenue from open pipeline records over a configurable number of months. It calculates both raw and probability-weighted values to support sales planning and target-setting.

![Forecast tab](../../../screenshots/captured/module-ui/crm/crm/forecast-tab.png)
*Forecast tab showing projected revenue by month.*

### Forecast API

`GET /api/v1/crm/forecast?months_ahead=6`

Returns a month-by-month breakdown of expected close dates, expected revenue, and weighted revenue based on active probability percentages.

---

## Territory Management

**Route:** `/dashboard/crm?tab=territory`  
**Permission required:** `crm.view`

### What It Does

The Territory tab defines geographic or account-based territories and assigns sales reps. It provides performance summaries per territory including open records, won records, pipeline value, and win rate.

![Territory tab](../../../screenshots/captured/module-ui/crm/crm/territory-tab.png)
*Territory tab showing territory performance cards.*

### Territory Fields

| Field | Description |
|---|---|
| `territory_code` | Short identifier (e.g., NRB-NORTH) |
| `territory_name` | Display name |
| `region` | Geographic region grouping |
| `parent_territory_id` | Parent territory for hierarchy |
| `assigned_rep_ids` | Comma-separated rep UUIDs |
| `active_flag` | Whether territory is active |

### Territory Performance Metrics

| Metric | Description |
|---|---|
| Total Records | All CRM records in this territory |
| Open Records | Records with status OPEN |
| Won Records | Closed WON |
| Lost Records | Closed LOST |
| Pipeline Value | Sum of expected_revenue |
| Weighted Value | Probability-weighted pipeline |
| Win Rate % | Won / (Won + Lost) × 100 |

### Territory APIs

| Action | Endpoint |
|---|---|
| List territories | `GET /api/v1/crm/territories` |
| Create territory | `POST /api/v1/crm/territories` |
| Update territory | `PATCH /api/v1/crm/territories/{id}` |
| Performance summary | `GET /api/v1/crm/territories/performance` |

### Access Control

CRM records carry `territory_id`. When a user's territory scope does not include a record's territory, the record is shown as "View only" on the pipeline board and edit actions are disabled.
