# FMCG ERP — Commercial: CRM & Marketing Manual v2

**Version:** 2.0 (post-recovery)  
**Date:** 2026-05-24  
**Audience:** Commercial Managers, Sales Managers, CRM Officers, Marketing Managers, Brand Managers  
**Modules Covered:** CRM · Marketing · Trade Promotion Management (TPM)

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [CRM Overview](#2-crm-overview)
3. [Leads Management](#3-leads-management)
4. [Opportunities Pipeline](#4-opportunities-pipeline)
5. [Activities & Follow-ups](#5-activities--follow-ups)
6. [Sales Forecast](#6-sales-forecast)
7. [Territory Management](#7-territory-management)
8. [Pipeline Stages Configuration](#8-pipeline-stages-configuration)
9. [Win/Loss Analysis](#9-winloss-analysis)
10. [Customer Loyalty Programme](#10-customer-loyalty-programme)
11. [Net Promoter Score (NPS)](#11-net-promoter-score-nps)
12. [Surveys](#12-surveys)
13. [Marketing Module](#13-marketing-module)
14. [Marketing Campaigns](#14-marketing-campaigns)
15. [Trade Promotion Management (TPM)](#15-trade-promotion-management-tpm)
16. [Common Mistakes & Troubleshooting](#16-common-mistakes--troubleshooting)
17. [Related Modules](#17-related-modules)

---

## 1. Module Overview

**What it does:** Manages customer relationship management (leads, opportunities, customer retention), marketing campaign execution, and trade promotion management for FMCG channel spending.

**Who uses it:**
- Commercial Manager — monitors pipeline, forecasts, and trade spend
- Sales Manager — manages territories, team pipeline, and win/loss analysis
- CRM Officer — maintains leads, opportunities, and customer interactions
- Marketing Manager — creates and tracks marketing campaigns
- Brand Manager — manages TPM budgets and promotional calendars

**When to use it:**
- When tracking a new business lead
- When managing a sales opportunity through the pipeline
- When planning and executing a marketing campaign
- When processing trade promotion agreements with distributors
- When running customer loyalty points
- When conducting an NPS survey

**Modules at a glance:**

| Feature | Route | Purpose |
|---------|-------|---------|
| CRM | `/dashboard/crm` | Customer relationship management |
| Marketing | `/dashboard/marketing` | Campaign and trade promotion management |

---

## 2. CRM Overview

**Route:** `/dashboard/crm`  
**Required permission:** `crm.view`

![CRM Overview](../../user-manual/screenshots/captured/module-ui/crm/crm/overview-tab.png)
*CRM overview — pipeline value, lead count, opportunities by stage, and win rate.*

### Tabs

| Tab | Purpose |
|-----|---------|
| Overview | CRM KPI dashboard |
| Pipeline | Visual sales pipeline (Kanban) |
| Leads | Lead register |
| Opportunities | Opportunity register |
| Activities | Calls, meetings, tasks, emails |
| Forecast | Revenue forecast by period |
| Territory | Territory and rep assignment |
| Stages | Configure pipeline stages |
| Win/Loss | Win and loss analysis |
| Loyalty | Customer loyalty programme |
| NPS | Net Promoter Score tracking |
| Surveys | Customer surveys |

---

## 3. Leads Management

**Tab:** Leads

### What it does
Track initial prospects — unqualified contacts or companies showing interest. A Lead is converted to an Opportunity when qualified.

![Leads Tab](../../user-manual/screenshots/captured/module-ui/crm/crm/leads-tab.png)
*Leads list with source, owner, status, and last activity.*

### Creating a Lead

Click **+ New Lead**:

![New Lead Form](../../user-manual/screenshots/captured/module-ui/crm/leads/new-lead-form.png)

| Field | Required | Notes |
|-------|----------|-------|
| Lead Name / Company | Yes | Contact name or company |
| Email | No | Contact email |
| Phone | No | Contact phone |
| Lead Source | Yes | How lead was acquired |
| Owner | Yes | Assigned sales rep |
| Industry | No | Business sector |
| Country | No | Location |
| Estimated Value | No | Potential deal size |
| Notes | No | Initial context |

**Lead Source Dropdown:**

![Lead Source Dropdown](../../user-manual/screenshots/captured/module-ui/crm/leads/new-lead-source-dropdown.png)

**Lead Source values:** Website / Referral / Cold Call / Trade Show / LinkedIn / Marketing Campaign / Partner / Other

**Lead Dropdowns:**

![Leads Dropdowns](../../user-manual/screenshots/captured/module-ui/crm/leads/leads-dropdowns.png)
*Status, owner, and territory dropdowns on the lead form.*

### Lead Status Values

| Status | Meaning |
|--------|---------|
| NEW | Just captured; not yet contacted |
| CONTACTED | Initial contact made |
| QUALIFIED | Lead assessed; meets criteria |
| CONVERTED | Converted to Opportunity |
| DISQUALIFIED | Not a prospect; closed out |

### Converting a Lead to Opportunity
Open lead → click **Convert to Opportunity** → system creates Opportunity with lead data pre-filled. Lead status set to CONVERTED.

---

## 4. Opportunities Pipeline

**Tab:** Opportunities (list) · Pipeline (Kanban view)

### What it does
Track qualified sales opportunities through the deal pipeline from initial engagement to close.

![Pipeline Tab](../../user-manual/screenshots/captured/module-ui/crm/crm/pipeline-tab.png)
*Pipeline Kanban view — opportunities grouped by stage with deal value.*

![Opportunities Tab](../../user-manual/screenshots/captured/module-ui/crm/crm/opportunities-tab.png)
*Opportunities list view with stage, expected close date, and probability.*

### Creating an Opportunity

Click **+ New Opportunity**:

![New Opportunity Form](../../user-manual/screenshots/captured/module-ui/crm/opportunities/new-opportunity-form.png)

| Field | Required | Notes |
|-------|----------|-------|
| Opportunity Name | Yes | Descriptive deal name |
| Customer / Account | Yes | Link to customer master |
| Stage | Yes | Current pipeline stage |
| Expected Close Date | Yes | Target date to close |
| Deal Value | Yes | Estimated revenue |
| Probability % | Yes | Win probability |
| Owner | Yes | Sales rep responsible |
| Products | No | Products in scope |
| Next Step | No | What happens next |

**Opportunity Dropdowns:**

![Opportunities Dropdowns](../../user-manual/screenshots/captured/module-ui/crm/opportunities/opportunities-dropdowns.png)
*Stage, owner, and territory dropdowns.*

### Pipeline Stage Values
Configured in CRM → Stages tab. Default:
1. Prospecting
2. Qualification
3. Proposal Sent
4. Negotiation
5. Verbal Commitment
6. **Closed Won**
7. **Closed Lost**

### Forecast Contribution
Each open opportunity contributes to forecast at: Deal Value × Probability %. Weighted pipeline shown in Forecast tab.

---

## 5. Activities & Follow-ups

**Tab:** Activities

### What it does
Log all customer interactions — calls made, meetings held, emails sent, tasks assigned.

![Activities Tab](../../user-manual/screenshots/captured/module-ui/crm/crm/activities-tab.png)
*Activity log — scheduled and completed interactions by type, date, and owner.*

**Activity types:** Call / Email / Meeting / Demo / Proposal / Follow-up / Task

**Creating an activity:**
1. Activities → **+ New Activity** (or open opportunity/lead → Add Activity)
2. Set type, date/time, owner, notes
3. Link to opportunity or customer
4. Mark as completed when done

Activities not marked complete appear in each rep's daily to-do list.

---

## 6. Sales Forecast

**Tab:** Forecast

![Forecast Tab](../../user-manual/screenshots/captured/module-ui/crm/crm/forecast-tab.png)
*Sales forecast — pipeline-weighted revenue by period and rep.*

**Forecast views:**
- Weighted: Sum of (Deal Value × Probability)
- Best Case: Sum of all open deals
- Committed: Only stage ≥ Verbal Commitment

Use the period picker to view monthly/quarterly/annual forecast.

---

## 7. Territory Management

**Tab:** Territory

### What it does
Assign customers, leads, and opportunities to geographic territories. Map sales reps to territories.

![Territory Tab](../../user-manual/screenshots/captured/module-ui/crm/crm/territory-tab.png)
*Territory map and assignment table — rep to territory to customer mappings.*

---

## 8. Pipeline Stages Configuration

**Tab:** Stages

### What it does
Configure the stages used in the opportunity pipeline. Add, rename, reorder, and set probability defaults per stage.

![Stages Tab](../../user-manual/screenshots/captured/module-ui/crm/crm/stages-tab.png)
*Pipeline stage configuration — name, order, default probability, and type (open/won/lost).*

**Admin only** — changes affect all reps' pipelines immediately.

---

## 9. Win/Loss Analysis

**Tab:** Win/Loss

### What it does
Analyze why deals were won or lost. Track win rate by product, customer segment, competitor, and time period.

![Win Loss Tab](../../user-manual/screenshots/captured/module-ui/crm/crm/win-loss-tab.png)
*Win/loss analysis — reasons, volume, and value of won and lost opportunities.*

**On closing an opportunity (Won or Lost):**
- Select reason (Required for Lost: Price / Competition / Timeline / Budget / Product Fit / Other)
- Enter notes
- For Lost: enter competitor name (optional)

Data aggregates in Win/Loss tab for trend analysis.

---

## 10. Customer Loyalty Programme

**Tab:** Loyalty

### What it does
Manage customer loyalty points — earn on purchases, redeem for discounts or rewards.

![Loyalty Tab](../../user-manual/screenshots/captured/module-ui/crm/crm/loyalty-tab.png)
*Loyalty programme — enrolled customers, points balances, and redemption history.*

### Enrolling a Customer

Click **+ Enroll**:

![Enroll Form](../../user-manual/screenshots/captured/module-ui/crm/loyalty/enroll-form.png)

| Field | Required |
|-------|----------|
| Customer | Yes |
| Programme | Yes |
| Enrollment Date | Yes |
| Starting Points | No (default 0) |

**Points earn rate:** Configured per programme — e.g. "1 point per KES 100 spent"  
**Redemption:** Customer requests redemption → generates discount on next invoice

---

## 11. Net Promoter Score (NPS)

**Tab:** NPS

### What it does
Track customer satisfaction via NPS surveys — measure promoters, passives, and detractors.

![NPS Tab](../../user-manual/screenshots/captured/module-ui/crm/crm/nps-tab.png)
*NPS dashboard — overall NPS score, trend, and customer distribution.*

### Logging an NPS Response

Click **+ Log Response**:

![NPS Log Response Form](../../user-manual/screenshots/captured/module-ui/crm/nps/log-response-form.png)

| Field | Required | Notes |
|-------|----------|-------|
| Customer | Yes | |
| Survey Date | Yes | |
| Score | Yes | 0–10 |
| Verbatim Feedback | No | Customer comment |
| Channel | No | Email / Phone / In-Person |

**NPS Categories:**
- 0–6: Detractor
- 7–8: Passive
- 9–10: Promoter

**NPS Score = % Promoters − % Detractors**

---

## 12. Surveys

**Tab:** Surveys

### What it does
Create and distribute customer surveys. Track responses and analyze results.

![Surveys Tab](../../user-manual/screenshots/captured/module-ui/crm/crm/surveys-tab.png)
*Survey management — active surveys, response rates, and results summary.*

---

## 13. Marketing Module

**Route:** `/dashboard/marketing`

![Marketing Overview](../../user-manual/screenshots/captured/128_marketing.png)
*Marketing module — campaign management and trade promotion workspace.*

### Tabs

| Tab | Purpose |
|-----|---------|
| Campaigns | Marketing campaign management |
| TPM | Trade Promotion Management |

---

## 14. Marketing Campaigns

**Tab:** Campaigns

### What it does
Plan, execute, and measure marketing campaigns — digital, trade, consumer, and PR.

![Campaigns Tab](../../user-manual/screenshots/captured/module-ui/crm/crm/overview-tab.png)

**Accessing campaigns:** Marketing → Campaigns tab.

![Marketing Campaigns](../../user-manual/screenshots/captured/129_marketing-campaigns.png)
*Campaigns list with status, channel, budget, and ROI.*

**Campaign types:** Digital / Trade / Consumer / Events / PR / Social Media

**Creating a Campaign:**
1. Marketing → Campaigns → **+ New Campaign**
2. Set name, type, channel, budget, start/end dates
3. Define target audience
4. Set success metrics (reach, conversions, ROI)
5. Launch and track actuals vs. plan

---

## 15. Trade Promotion Management (TPM)

**Tab:** TPM

### What it does
Manage trade promotion spend — promotional agreements with distributors, retailer listing fees, off-invoice discounts, display fees, and co-op advertising.

![TPM Tab](../../user-manual/screenshots/captured/130_marketing-tpm.png)
*TPM dashboard — total trade spend, by customer and by promotion type.*

**TPM activities:**
| Activity | Description |
|----------|-------------|
| Off-Invoice Discount | Price reduction applied on invoice |
| Volume Rebate | Retrospective rebate on target achievement |
| Display Fee | Payment for in-store display/gondola end |
| Listing Fee | One-time fee to list a new SKU |
| Co-op Advertising | Shared advertising cost with retailer |
| Sampling | Product sampling event costs |

**TPM workflow:**
1. Commercial team negotiates deal with customer
2. TPM agreement created in system with terms
3. Spend tracked against budget as invoices or credit notes raised
4. Monthly accrual posted to Finance
5. Year-end settlement reconciliation

---

## 16. Common Mistakes & Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Lead conversion creates duplicate customer | Customer already exists | Search existing customers before converting; link rather than create |
| Pipeline value inflated | Old won/lost deals still showing as open | Close won/lost opportunities with correct status |
| NPS score not updating | New responses not yet in current period | Refresh date range filter on NPS dashboard |
| TPM budget overspent | No budget alert configured | Set TPM budget alert threshold in marketing settings |
| Campaign ROI shows 0 | Revenue not linked to campaign | Tag sales orders with campaign reference |
| Loyalty points not accruing | Customer not enrolled in active programme | Enroll customer and verify programme is active |

---

## 17. Related Modules

| This Action | Connects To |
|-------------|-------------|
| Lead converted to customer | Sales → Customers master |
| Opportunity won → order | Sales → Orders |
| Loyalty redemption | Sales → Discount on invoice |
| TPM accrual | Finance → Journal (trade spend accrual) |
| Campaign → sales order | Sales → Order (campaign reference) |
| NPS low score | CRM → Activity (follow-up task) |

---

*End of Commercial CRM & Marketing Manual v2*
