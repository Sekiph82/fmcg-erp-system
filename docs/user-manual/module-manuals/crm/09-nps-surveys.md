# NPS Tracking & Surveys

---

## NPS Tracking

**Route:** `/dashboard/crm?tab=nps`  
**Permission required:** `crm.view`

### What It Does

The NPS tab tracks Net Promoter Score across customer surveys. It displays an overall NPS score, promoter/passive/detractor breakdown, score distribution (0–10), per-survey scores, and per-customer classification.

![NPS tab](../../../screenshots/captured/module-ui/crm/crm/nps-tab.png)
*NPS tab showing overall score gauge, score distribution bars, active surveys, customer NPS table, and verbatim feedback.*

### NPS Score Interpretation

| Score Range | Classification |
|---|---|
| 9–10 | Promoter |
| 7–8 | Passive |
| 0–6 | Detractor |

NPS = % Promoters − % Detractors

| NPS Range | Rating |
|---|---|
| ≥ 50 | Excellent |
| 30–49 | Good |
| 0–29 | Fair |
| < 0 | Poor |

### KPI Panel

| Metric | Description |
|---|---|
| NPS Score | Calculated NPS (displayed as +score or −score) |
| Promoters | Count of 9–10 responses |
| Passives | Count of 7–8 responses |
| Detractors | Count of 0–6 responses |
| Total Responses | All logged NPS responses |
| Avg Score | Average raw score across all responses |

### Score Distribution

Bar chart showing response count per score (0–10). Color-coded: green for 9–10, amber for 7–8, red for 0–6.

### NPS by Customer Table

| Column | Description |
|---|---|
| Customer | Customer name |
| Avg Score | Average NPS score for this customer |
| Responses | Number of responses |
| Classification | PROMOTER / PASSIVE / DETRACTOR |

### Verbatim Feedback

The bottom section shows top detractor and promoter comments with customer name and score.

### Logging an NPS Response

Click `+ Log Response` to open the log modal.

![Log NPS Response form](../../../screenshots/captured/module-ui/crm/nps/log-response-form.png)
*Log NPS Response modal with survey selector, customer ID, score selector (0–10), and comment.*

### Log Response Form Fields

| Field | Type | Required |
|---|---|---|
| Survey | Select from active surveys | Yes |
| Customer ID (UUID) | Text | Yes |
| Score (0–10) | Button selector | Yes |
| Comment | Textarea | No |
| Channel | Text (defaults to `manual`) | No |

API: `POST /api/v1/nps/responses`

### Manage Surveys Link

The `Manage Surveys` button navigates to `/dashboard/nps/surveys` for survey CRUD.

---

## Surveys

**Route:** `/dashboard/crm?tab=surveys`  
**Permission required:** `crm.view`

### What It Does

The Surveys tab manages the full lifecycle of employee and customer surveys — from creation through active collection to closed analysis. Surveys can be anonymous or attributed.

![Surveys tab](../../../screenshots/captured/module-ui/crm/crm/surveys-tab.png)
*Surveys tab showing KPI cards, active survey list, filter chips, and surveys table.*

### Survey KPI Cards

| KPI | Description |
|---|---|
| Total Surveys | All surveys in the system |
| Active | Surveys with status ACTIVE |
| Closed | Surveys with status CLOSED |
| Total Responses | Responses across all surveys |

### Survey Status Lifecycle

```
DRAFT → ACTIVE → CLOSED → ARCHIVED
```

| Status | Meaning |
|---|---|
| `DRAFT` | Created, not yet collecting responses |
| `ACTIVE` | Open for responses |
| `CLOSED` | Collection ended, results available |
| `ARCHIVED` | Soft-deleted |

### Surveys Table Columns

| Column | Description |
|---|---|
| Title | Survey name (links to detail) |
| Type | Survey category (e.g., PULSE, ENGAGEMENT, EXIT) |
| Questions | Count of questions |
| Responses | Count of submissions |
| Dates | `start_date → end_date` |
| Anon | Whether anonymous |
| Status | Status badge |
| Actions | View · Respond · Results · Launch · Close |

### Creating a Survey

Click `+ New Survey` to navigate to `/dashboard/surveys/new`.

### Survey Actions

| Action | Available When | Effect |
|---|---|---|
| Launch | DRAFT | Sets status to ACTIVE |
| Respond | ACTIVE | Navigate to `/dashboard/surveys/{id}/respond` |
| Results | ACTIVE or CLOSED | Navigate to `/dashboard/surveys/{id}/results` |
| Close | ACTIVE | Sets status to CLOSED |
