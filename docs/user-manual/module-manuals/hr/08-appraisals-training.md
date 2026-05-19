# Performance Appraisals & Training Management

---

## Performance Appraisals

**Route:** `/dashboard/hr?tab=appraisals`  
**Permission required:** `hr.view`

### What It Does

The Appraisals tab manages performance review cycles from self-review through manager and HR review to final calibration. It tracks scores, ratings, development plans, and promotion recommendations.

![Appraisals tab](../../../screenshots/captured/module-ui/hr/hr/appraisals-tab.png)
*Performance Appraisals tab showing KPI summary, rating distribution chart, and department average scores.*

### Appraisals KPIs

| KPI | Description |
|---|---|
| Total Appraisals | All appraisal records |
| Self Review Pending | Appraisals awaiting employee self-review |
| Manager Review Pending | Appraisals awaiting manager review |
| HR Review Pending | Appraisals awaiting HR review |
| Calibration Pending | Appraisals awaiting calibration |
| Completed | Fully closed appraisals |
| Avg Final Score | Average final appraisal score (%) |
| Promotion Recs | Active promotion recommendations |
| Open Dev Plans | Open development plans |

### Rating Distribution

Ratings are tracked with color-coded distribution:

| Rating | Color | Meaning |
|---|---|---|
| `excellent` | Green | Exceeds expectations significantly |
| `good` | Blue | Meets and exceeds expectations |
| `meets_expectations` | Yellow | Meets expectations |
| `improvement_needed` | Red | Below expectations |

### Appraisal Workflow

```
Appraisal period opened → appraisal records created
    → Employee completes self-review
    → Manager reviews and scores
    → HR review / moderation
    → Calibration committee review
    → Final score and rating set
    → Development plan and promotion decision recorded
```

### Appraisals Navigation

| Section | Route |
|---|---|
| Appraisal Periods | `/dashboard/appraisals/periods` |
| Templates | `/dashboard/appraisals/templates` |
| All Records | `/dashboard/appraisals/records` |
| New Appraisal | `/dashboard/appraisals/records/new` |
| Self Review | `/dashboard/appraisals/self-review` |
| Manager Queue | `/dashboard/appraisals/manager-queue` |
| HR Review | `/dashboard/appraisals/hr-review` |
| Development Plans | `/dashboard/appraisals/development-plans` |
| Reports | `/dashboard/appraisals/reports` |
| AI Insights | `/dashboard/appraisals/ai` |

---

## Training & Skills Management

**Route:** `/dashboard/hr?tab=training`  
**Permission required:** `hr.view`

### What It Does

The Training tab manages learning programs, sessions, employee skill profiles, certifications, and training feedback. It provides visibility into skill gaps and upcoming certification expirations.

![Training tab](../../../screenshots/captured/module-ui/hr/hr/training-tab.png)
*Training tab showing KPI grid with program counts, assignment status, certification status, skill gaps, and average feedback.*

### Training KPIs

| KPI | Description |
|---|---|
| Total Programs | All training programs defined |
| Active Programs | Programs currently running |
| Upcoming Sessions | Sessions scheduled in the future |
| Total Assignments | All training assignments |
| Completed | Assignments completed |
| Overdue | Assignments past their due date |
| Certifications | Total certifications issued |
| Expiring Soon | Certifications expiring in the near term |
| Expired | Certifications already expired |
| Skill Profiles | Employee skill profiles on record |
| Skill Gaps | Identified gaps between required and actual skills |
| Avg Feedback | Average training feedback rating (out of 5) |

### Training Navigation

| Section | Route |
|---|---|
| Training Programs | `/dashboard/training/programs` |
| Sessions / Calendar | `/dashboard/training/sessions` |
| Skill Matrix | `/dashboard/training/skill-matrix` |
| Assignments | `/dashboard/training/assignments` |
| Certifications | `/dashboard/training/certifications` |
| Feedback | `/dashboard/training/feedback` |
| Reports | `/dashboard/training/reports` |
| AI Insights | `/dashboard/training/ai` |
