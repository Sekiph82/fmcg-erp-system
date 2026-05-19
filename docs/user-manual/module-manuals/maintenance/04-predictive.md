# Predictive Maintenance

**Route:** `/dashboard/maintenance?tab=predictive`  
**Permission required:** `maintenance.view` (generate: `maintenance.predict`, review: `maintenance.review_prediction`)

## What It Does

Displays rule-based failure predictions derived from IoT sensor trends, machine state events, system alerts, and breakdown history. Each prediction identifies an at-risk asset, the predicted failure mode, recommended action, and confidence level.

![Predictive Tab](../../../screenshots/captured/module-ui/maintenance/predictive/predictive-tab.png)
*Predictive Maintenance — KPI tiles, filter bar, and prediction queue with risk badges and confidence bars.*

## KPI Tiles

| KPI | Description |
|-----|-------------|
| Predictions | Total count matching current filter |
| Open | Predictions awaiting review |
| High Risk | CRITICAL + HIGH risk predictions |
| Avg Confidence | Mean confidence across all filtered predictions. Sub-label: count due within 14 days |

## Generate Predictions

The **Generate Predictions** button runs the prediction engine for the selected time horizon (14 / 30 / 60 / 90 days). Requires `maintenance.predict` permission.

## Filter Bar

| Filter | Options |
|--------|---------|
| Status | All · OPEN · REVIEWED · WORK_ORDER_CREATED · DISMISSED |
| Risk | All · LOW · MEDIUM · HIGH · CRITICAL |
| Horizon Days | 14 · 30 · 60 · 90 |
| Reviewer | Text field — name recorded on review actions |

## Prediction Risk Levels

| Level | Color |
|-------|-------|
| LOW | Green |
| MEDIUM | Amber |
| HIGH | Orange |
| CRITICAL | Red |

## Prediction Status

| Status | Meaning |
|--------|---------|
| OPEN | Generated, awaiting engineer review |
| REVIEWED | Reviewed but no action taken yet |
| WORK_ORDER_CREATED | A PM work order has been planned |
| DISMISSED | Dismissed after review (false positive or low priority) |

## Prediction Queue Card

Each prediction shows:

| Field | Description |
|-------|-------------|
| Asset Name | Asset name and asset_no |
| Risk Level | Colour-coded badge |
| Status | Current review status badge |
| Failure Mode | Predicted type of failure |
| Days Until Failure | Countdown — red ≤ 7 days, orange ≤ 14 days |
| Predicted Date | Expected failure date |
| Recommended Action | System-generated maintenance recommendation |
| Evidence Summary | Source signals used to generate the prediction |
| Confidence Bar | Visual percentage bar + numeric % |
| Source Metrics | Per-metric trend %, reading count (if available) |

## Review Actions (OPEN predictions only)

Requires `maintenance.review_prediction` permission.

| Action | Resulting Status |
|--------|-----------------|
| Mark Reviewed | REVIEWED |
| Work Order Planned | WORK_ORDER_CREATED |
| Dismiss | DISMISSED |

A free-text **Review Note** can be added before any action.

API: `GET /api/v1/maintenance/predictions`, `POST /api/v1/maintenance/predictions/generate`, `PUT /api/v1/maintenance/predictions/{id}/review`
