# Six Broken Action Cards — Fix Report

**Date:** 2026-05-22  
**Branch:** main

---

## Summary

| Metric | Value |
|--------|-------|
| Broken action cards before | 6 |
| Broken action cards after | 0 |
| Pages restored from git | 5 |
| Source links updated (no restore) | 3 |
| BYPASS routes added | 5 |
| Redirect map entries removed | 2 (middleware.ts + routeRedirectMap.ts) |
| Audit script BYPASS entries added | 5 |

---

## Fixes Applied

### Card 1 — calendar/new-event → calendar/events

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/calendar/new-event/page.tsx:89` |
| Old target | `/dashboard/calendar/events` (redirect stub → `/dashboard/communication?tab=calendar`) |
| New target | `/dashboard/calendar/events` (restored real page) |
| Fix pattern | C — restore from git `674b6c5`, add to BYPASS |
| Git history page | YES — EventsPage with calendarApi, event table, type/status filters |
| BYPASS added | `/dashboard/calendar/events` |
| Redirect removed | No (was in page stub only, not redirect map) |

---

### Card 2 — finance/accounting → controls

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/finance/accounting/page.tsx:99` |
| Old target | `/dashboard/finance/accounting/controls` (redirect stub → `/dashboard/finance?tab=accounting`) |
| New target | `/dashboard/finance?tab=accounting` (direct) |
| Fix pattern | A — update source link to redirect destination (no real page in git) |
| Git history page | NO — only redirect stubs in all commits |
| BYPASS added | None |
| Redirect removed | No (was in page stub only, not redirect map) |

---

### Card 3 — marketing/ecommerce/stores → stores/new

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/marketing/ecommerce/stores/page.tsx:37` |
| Old target | `router.push("/dashboard/marketing/ecommerce/stores/new")` (redirect → `/dashboard/marketing?tab=ecommerce&drawer=create`) |
| New target | `router.push("/dashboard/marketing?tab=ecommerce&drawer=create")` (direct) |
| Fix pattern | B — update source to push directly to correct create UX |
| Git history page | Not checked — redirect destination is the correct UX |
| BYPASS added | None |
| Redirect removed | No |

---

### Card 4 — recruitment/candidates → candidates/new

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/recruitment/candidates/page.tsx:27` |
| Old target | `href="/dashboard/recruitment/candidates/new"` (redirect → `/dashboard/hr?tab=recruitment&drawer=create`) |
| New target | `href="/dashboard/hr?tab=recruitment&drawer=create"` (direct) |
| Fix pattern | B — update source link to redirect destination directly |
| Git history page | Not checked — redirect destination is the correct UX |
| BYPASS added | None |
| Redirect removed | No |

---

### Card 5 — reports/marketing → marketing/crm

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/reports/marketing/page.tsx:669` |
| Old target | `/dashboard/marketing/crm` (redirect → `/dashboard/marketing?tab=overview`) |
| New target | `/dashboard/marketing/crm` (restored real page) |
| Fix pattern | C — restore from git `674b6c5`, remove from redirect maps, add to BYPASS |
| Git history page | YES — CRMPage with marketingApi, CRM profile table, status filters |
| BYPASS added | `/dashboard/marketing/crm`, `/dashboard/marketing/crm/followup` |
| Redirect removed | YES — removed from `middleware.ts` and `routeRedirectMap.ts` |

**Also restored:** `marketing/crm/followup/page.tsx` (linked from CRM page, real page in `674b6c5` — CRMFollowUpPage with overdue/today/upcoming follow-up sections)

---

### Card 6 — reports/marketing → marketing/surveys

| Field | Value |
|-------|-------|
| Source file | `frontend/src/app/dashboard/reports/marketing/page.tsx:673` |
| Old target | `/dashboard/marketing/surveys` (redirect → `/dashboard/marketing?tab=overview`) |
| New target | `/dashboard/marketing/surveys` (restored real page) |
| Fix pattern | C — restore from git `674b6c5`, remove from redirect maps, add to BYPASS |
| Git history page | YES — SurveysPage with marketingApi, survey cards, type filter |
| BYPASS added | `/dashboard/marketing/surveys`, `/dashboard/marketing/surveys/new` |
| Redirect removed | YES — removed from `middleware.ts` and `routeRedirectMap.ts` |

**Also restored:** `marketing/surveys/new/page.tsx` (linked from surveys page, real page in `674b6c5` — NewSurveyPage with full create form, JSON questions field, region/date/type fields)

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/app/dashboard/calendar/events/page.tsx` | Restored from git `674b6c5` |
| `frontend/src/app/dashboard/marketing/crm/page.tsx` | Restored from git `674b6c5` |
| `frontend/src/app/dashboard/marketing/crm/followup/page.tsx` | Restored from git `674b6c5` |
| `frontend/src/app/dashboard/marketing/surveys/page.tsx` | Restored from git `674b6c5` |
| `frontend/src/app/dashboard/marketing/surveys/new/page.tsx` | Restored from git `674b6c5` |
| `frontend/src/app/dashboard/finance/accounting/page.tsx` | Updated action card href |
| `frontend/src/app/dashboard/marketing/ecommerce/stores/page.tsx` | Updated router.push target |
| `frontend/src/app/dashboard/recruitment/candidates/page.tsx` | Updated Link href |
| `frontend/src/middleware.ts` | Removed crm/surveys from redirect map; added 5 BYPASS entries |
| `frontend/src/lib/routeRedirectMap.ts` | Removed crm/surveys entries |
| `scripts/audit-visible-import-graph.js` | Synced BYPASS set (+5 entries, -2 redirect entries) |

---

## Verification

| Check | Result |
|-------|--------|
| `find-broken-action-cards.js` before | 6 |
| `find-broken-action-cards.js` after | **0** |
| Type-check | **CLEAN** |
| Build | **CLEAN** |
| Route redirect drift | **0 issues** |
| Workspace tab checks | **All pass** |
| Visible broken targets (unique) | 47 (was 48 — 1 resolved; crm/surveys/calendar were within the 48) |

---

## Remaining Broken Action Cards

**0** — all user-visible broken action cards resolved.

---

## Next Task

**47 unresolved visible targets — design pass** — requires user/stakeholder approval:
- ~38 dynamic detail routes (`/dashboard/users/${id}` etc.) → need subview/modal pattern
- ~10 new pages requiring design decisions
