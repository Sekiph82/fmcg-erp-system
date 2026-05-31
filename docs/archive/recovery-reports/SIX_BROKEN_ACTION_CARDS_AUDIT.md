# Six Broken Action Cards — Audit

**Date:** 2026-05-22  
**Source:** `node scripts/find-broken-action-cards.js`

---

## Card 1 — calendar/events

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/calendar/new-event/page.tsx:89` |
| Label | View Events |
| Current href | `/dashboard/calendar/events` |
| Redirect target | `/dashboard/communication?tab=calendar` (redirect stub in page file) |
| Target in middleware | NOT in redirect map — redirect is in `calendar/events/page.tsx` itself |
| Real page in current code | Redirect stub |
| Real page in git history | YES — `674b6c5` has full EventsPage with calendarApi, table, filter |
| Fix pattern | C — restore from git, add to BYPASS |

---

## Card 2 — finance/accounting/controls

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/finance/accounting/page.tsx:99` |
| Label | Accounting Controls |
| Current href | `/dashboard/finance/accounting/controls` |
| Redirect target | `/dashboard/finance?tab=accounting` (redirect stub in page file) |
| Target in middleware | NOT in redirect map — redirect is in the page stub itself |
| Real page in current code | Redirect stub |
| Real page in git history | NO — `674b6c5` has no `controls/page.tsx`; Auto-sync commits only have the stub |
| Fix pattern | A — update source link to redirect destination directly |

---

## Card 3 — marketing/ecommerce/stores/new

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/marketing/ecommerce/stores/page.tsx:37` |
| Label | Create Store (button) |
| Current href | `router.push("/dashboard/marketing/ecommerce/stores/new")` |
| Redirect target | `/dashboard/marketing?tab=ecommerce&drawer=create` |
| Real page in current code | Redirect stub |
| Real page in git history | Not checked — redirect destination IS the correct create UX |
| Fix pattern | B — update source to push directly to redirect destination |

---

## Card 4 — recruitment/candidates/new

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/recruitment/candidates/page.tsx:27` |
| Label | Add Candidate |
| Current href | `/dashboard/recruitment/candidates/new` |
| Redirect target | `/dashboard/hr?tab=recruitment&drawer=create` |
| Real page in current code | Redirect stub |
| Real page in git history | Not checked — redirect destination IS the correct create UX |
| Fix pattern | B — update source link to redirect destination directly |

---

## Card 5 — reports/marketing → CRM

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/reports/marketing/page.tsx:669` |
| Label | CRM Profiles → |
| Current href | `/dashboard/marketing/crm` |
| Redirect target | `/dashboard/marketing?tab=overview` (middleware line 53) |
| Real page in current code | Redirect stub |
| Real page in git history | YES — `674b6c5` has full CRMPage with marketingApi, table, status filters |
| Fix pattern | C — restore from git, remove from redirect map, add to BYPASS |

---

## Card 6 — reports/marketing → surveys

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/reports/marketing/page.tsx:673` |
| Label | Surveys → |
| Current href | `/dashboard/marketing/surveys` |
| Redirect target | `/dashboard/marketing?tab=overview` (middleware line 59) |
| Real page in current code | Redirect stub |
| Real page in git history | YES — `674b6c5` has full SurveysPage with marketingApi, survey cards, type filter |
| Fix pattern | C — restore from git, remove from redirect map, add to BYPASS |
