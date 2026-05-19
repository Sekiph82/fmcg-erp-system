# Field Visits, Market Intelligence & Analytics

---

## Field Visits

**Route:** `/dashboard/marketing?tab=visits`  
**Permission required:** `marketing.view`

### What It Does

The Visits tab logs field sales and trade audit visits. Each visit records the outlet, rep, visit type, objectives, and outcomes including shelf audit scores, competitor observations, and action items.

![Visits tab](../../../screenshots/captured/module-ui/marketing/marketing/visits-tab.png)
*Field Visits tab showing visit log with outlet, rep, type, date, and outcomes.*

### Visit Types

| Value | Label |
|---|---|
| `SALES` | Sales Visit |
| `MARKETING` | Marketing Activation |
| `TRADE_AUDIT` | Trade Audit |
| `MERCHANDISING` | Merchandising Check |
| `FEEDBACK` | Customer Feedback |
| `STORE_CHECK` | Store Check |

### Visit Fields

| Field | Description |
|---|---|
| `visit_type` | Type of visit |
| `outlet_name` | Outlet or customer visited |
| `region` | Geographic region |
| `rep_name` | Sales or marketing rep |
| `visit_date` | Date of visit |
| `objectives` | Planned objectives |
| `outcomes` | Recorded outcomes |
| `shelf_score` | Shelf compliance score (0–100) |
| `competitor_notes` | Competitor observations |
| `action_items` | Follow-up actions |

---

## Market Intelligence

**Route:** `/dashboard/marketing?tab=market-intel`  
**Permission required:** `marketing.view`

### What It Does

The Market Intelligence tab aggregates competitor data — pricing, promotions, new product launches, market share movements, and distribution observations collected during field visits and structured audits.

![Market Intelligence tab](../../../screenshots/captured/module-ui/marketing/marketing/market-intel-tab.png)
*Market Intelligence tab showing competitor intelligence records.*

### Market Intelligence Survey Types

| Value | Label |
|---|---|
| `CUSTOMER_FEEDBACK` | Customer Feedback |
| `MARKET_AUDIT` | Market Audit |
| `RETAILER_FEEDBACK` | Retailer Feedback |
| `BRAND_AWARENESS` | Brand Awareness |
| `COMPETITOR_CHECK` | Competitor Check |
| `PRODUCT_FEEDBACK` | Product Feedback |
| `SHELF_AUDIT` | Shelf Audit |

---

## Marketing Analytics

**Route:** `/dashboard/marketing?tab=analytics`  
**Permission required:** `marketing.view`

### What It Does

The Analytics tab provides cross-channel marketing performance analysis — campaign ROI rankings, spend efficiency, channel attribution, and trend comparisons over configurable time ranges.

![Marketing Analytics tab](../../../screenshots/captured/module-ui/marketing/marketing/analytics-tab.png)
*Marketing Analytics tab showing cross-channel ROI, spend breakdown, and trend charts.*

### Key Metrics

| Metric | Formula |
|---|---|
| Campaign ROI | `actual_revenue / budget × 100 − 100` |
| Cost per Acquisition | `spend / conversions` |
| Revenue per KES Spent | `actual_revenue / total_spend` |
| Uplift % | `(promoted_sales − baseline) / baseline × 100` |
