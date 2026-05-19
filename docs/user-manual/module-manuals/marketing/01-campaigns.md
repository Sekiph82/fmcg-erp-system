# Campaigns

**Route:** `/dashboard/marketing?tab=campaigns`  
**Permission required:** `marketing.view`

## Marketing Overview Dashboard

**Route:** `/dashboard/marketing?tab=overview`

The Overview tab shows aggregate campaign and promotion health at a glance.

![Marketing Overview tab](../../../screenshots/captured/module-ui/marketing/marketing/overview-tab.png)
*Marketing dashboard with campaign KPIs, ROI metrics, campaign status breakdown, budget vs actual chart, promotions by region, and recent campaign activity.*

### Campaign KPIs

| KPI | Description |
|---|---|
| Active Campaigns | Campaigns with status ACTIVE |
| Planned Campaigns | Campaigns with status PLANNED |
| Total Budget | Sum of campaign budgets |
| Actual Revenue | Sum of actual revenue attributed to campaigns |
| Expected ROI | `total_expected_revenue / total_budget` |
| Actual ROI | `total_actual_revenue / total_budget` |
| Total Promotions | All promotion records |
| Active Promotions | Promotions with status ACTIVE |

### Charts

- **Campaign Count by Status** — horizontal bar chart per status
- **Budget vs Actual Revenue (Top 10)** — dual bar per campaign (budget vs actual)
- **Promotions by Region** — bar chart of active promotions per region
- **Recent Campaign Activity** — list of campaigns sorted by update time

---

## Campaigns Tab

![Campaigns tab](../../../screenshots/captured/module-ui/marketing/marketing/campaigns-tab.png)
*Campaigns list showing code, name, type, status, budget, expected vs actual revenue, ROI, and dates.*

### Campaign Fields

| Field | Description |
|---|---|
| `campaign_code` | Auto-generated reference |
| `campaign_name` | Display name |
| `campaign_type` | Category (see below) |
| `objective` | Campaign objective text |
| `region` | Target region |
| `status` | Lifecycle status |
| `start_date` / `end_date` | Campaign dates |
| `budget` | Planned spend |
| `expected_revenue` | Projected revenue |
| `actual_revenue` | Recorded revenue |

### Campaign Types

| Value | Label |
|---|---|
| `TRADE` | Trade / BTL |
| `DIGITAL` | Digital |
| `RETAIL` | Retail |
| `DISTRIBUTOR` | Distributor |
| `LAUNCH` | Product Launch |
| `SEASONAL` | Seasonal |
| `LOYALTY` | Loyalty |
| `AWARENESS` | Brand Awareness |
| `ACQUISITION` | Customer Acquisition |
| `RETENTION` | Customer Retention |

### Campaign Status Lifecycle

```
DRAFT → PLANNED → ACTIVE → COMPLETED
                ↘ PAUSED ↗
                ↘ CANCELLED
```

| Status | Color | Meaning |
|---|---|---|
| `DRAFT` | Grey | In preparation |
| `PLANNED` | Blue | Scheduled, not yet started |
| `ACTIVE` | Green | Running |
| `PAUSED` | Amber | Temporarily stopped |
| `COMPLETED` | Sky | Ended successfully |
| `CANCELLED` | Red | Abandoned |

### Creating a New Campaign

Click `+ New Campaign` or navigate to `/dashboard/marketing/campaigns/new`.

![New Campaign form](../../../screenshots/captured/module-ui/marketing/campaigns/new-campaign-form.png)
*New Campaign form.*

### New Campaign Form Fields

| Field | Type | Required |
|---|---|---|
| Campaign Name | Text | Yes |
| Campaign Type | Select | Yes |
| Objective | Textarea | No |
| Region | Text | No |
| Start Date | Date | No |
| End Date | Date | No |
| Budget | Number | No |
| Expected Revenue | Number | No |

API: `POST /api/v1/marketing/campaigns`
