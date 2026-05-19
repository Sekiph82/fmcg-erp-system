# Pipeline Stages & Win/Loss Analysis

---

## Pipeline Stage Configuration

**Route:** `/dashboard/crm?tab=stages`  
**Permission required:** `crm.view`

### What It Does

The Stages tab defines the pipeline stages through which leads and opportunities move. Stages control the Kanban board columns, default probability percentages, and terminal status logic.

![Stages tab](../../../screenshots/captured/module-ui/crm/crm/stages-tab.png)
*Stage configuration table showing sequence, color, code, name, type, default probability, and active status.*

### Stage Fields

| Field | Description |
|---|---|
| `stage_code` | Uppercase identifier (e.g., QUALIFIED) |
| `stage_name` | Display name |
| `stage_type` | Classification (see below) |
| `default_probability` | Default win probability % for this stage |
| `sequence_no` | Display order on the board |
| `color_code` | Hex color for the column header accent |
| `active_flag` | Whether stage appears on the board |

### Stage Types

| Type | Description |
|---|---|
| `LEAD` | Lead qualification stages |
| `OPPORTUNITY` | Active sales stages |
| `NURTURING` | Long-term hold/nurture |
| `TERMINAL` | Won or Lost — hidden from pipeline board |

### Buttons

| Button | Action |
|---|---|
| `Seed Defaults` | Calls `POST /api/v1/crm/stages/seed-defaults` to load a standard stage set |
| `+ New Stage` | Opens create modal |

### New Stage Form Fields

| Field | Type | Required |
|---|---|---|
| Stage Code | Text (uppercased) | Yes |
| Stage Name | Text | Yes |
| Stage Type | Select | Yes |
| Default Probability % | Number 0–100 | No |
| Sequence No | Number | No |
| Color | Color picker | No |

---

## Win/Loss Analysis

**Route:** `/dashboard/crm?tab=win-loss`  
**Permission required:** `crm.view`

### What It Does

The Win/Loss tab provides aggregate analysis of closed deals — conversion rates, average deal size, common win and loss reasons, and competitor impact on outcomes.

![Win/Loss tab](../../../screenshots/captured/module-ui/crm/crm/win-loss-tab.png)
*Win/Loss analysis showing closed deal breakdowns.*

### Loss Reasons

| Code | Label |
|---|---|
| `PRICE_TOO_HIGH` | Price Too High |
| `COMPETITOR_RELATION` | Competitor Relationship |
| `PRODUCT_MISMATCH` | Product Mismatch |
| `TIMELINE_ISSUE` | Timeline Issue |
| `NO_BUDGET` | No Budget |
| `NO_RESPONSE` | No Response |
| `COMPETITOR_PROMO` | Competitor Promotion |
| `DISTRIBUTOR_CONFLICT` | Distributor Conflict |
| `CAPACITY_SUPPLY` | Capacity / Supply Issue |
| `INTERNAL_FOLLOWUP` | Internal Follow-up Failure |
| `OTHER` | Other |

### Win Reasons

| Code | Label |
|---|---|
| `BETTER_PRICE` | Better Price |
| `BETTER_PRODUCT_FIT` | Better Product Fit |
| `FASTER_RESPONSE` | Faster Response |
| `STRONGER_RELATION` | Stronger Relationship |
| `AVAILABILITY` | Product Availability |
| `TECHNICAL_SUPPORT` | Technical Support |
| `PROMOTION_SUPPORT` | Promotion Support |
| `OTHER` | Other |

### Win/Loss API

`GET /api/v1/crm/reports/win-loss` — returns aggregate counts and percentages for each win and loss reason code.
