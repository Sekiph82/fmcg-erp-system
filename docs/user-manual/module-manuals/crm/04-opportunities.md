# Opportunities Management

**Route:** `/dashboard/crm?tab=opportunities`  
**Permission required:** `crm.view`

## What It Does

The Opportunities tab lists qualified records that represent active sales pursuits with a defined expected revenue and close date. It shows total pipeline and weighted pipeline calculations.

![Opportunities tab](../../../screenshots/captured/module-ui/crm/crm/opportunities-tab.png)
*Opportunities tab showing summary bars, filter dropdowns, and the opportunity table.*

## Summary Bars

| Metric | Description |
|---|---|
| Open Opportunities | Count of records with status OPEN |
| Total Pipeline | Sum of `expected_revenue` across filtered records |
| Weighted Pipeline | Sum of `expected_revenue × probability_pct / 100` |

## Opportunities Table Columns

| Column | Description |
|---|---|
| Code | `opportunity_code` |
| Company | `company_name` |
| Stage | Current pipeline stage |
| Temp | Temperature badge |
| Prob % | `probability_pct` |
| Expected Rev | `expected_revenue` |
| Weighted | `expected_revenue × probability_pct / 100` |
| Close Date | `expected_close_date` |
| Rep | `assigned_rep_id` |
| Status | Status badge |
| Actions | `View` link |

## Filters

| Filter | Values |
|---|---|
| Status | OPEN · WON · LOST · ON_HOLD · ARCHIVED |
| Stage | Dynamic list of configured pipeline stages |

![Opportunities filter dropdowns expanded](../../../screenshots/captured/module-ui/crm/opportunities/opportunities-dropdowns.png)
*Status and stage filter dropdowns expanded on the Opportunities tab.*

## Creating a New Opportunity

Click `+ New Opportunity` to open the create modal.

![New Opportunity form](../../../screenshots/captured/module-ui/crm/opportunities/new-opportunity-form.png)
*New Opportunity modal.*

### New Opportunity Form Fields

| Field | Type | Required |
|---|---|---|
| Company Name | Text | Yes |
| Contact Person | Text | No |
| Email | Email input | No |
| Expected Revenue | Number | No |
| Expected Close Date | Date picker | No |
| Stage | Select from active stages | No |
| Assigned Rep ID | Text | No |

## Lifecycle Actions (Record Detail)

| Action | Endpoint |
|---|---|
| Qualify | `POST /api/v1/crm/records/{id}/qualify` |
| Convert to Opportunity | `POST /api/v1/crm/records/{id}/convert-to-opportunity` |
| Close Won | `POST /api/v1/crm/records/{id}/close-won` |
| Close Lost | `POST /api/v1/crm/records/{id}/close-lost` |
| Put On Hold | `POST /api/v1/crm/records/{id}/on-hold` |
| Reopen | `POST /api/v1/crm/records/{id}/reopen` |
