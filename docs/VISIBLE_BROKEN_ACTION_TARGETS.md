# Visible Broken Action Targets

**Date:** 2026-05-21
**Total:** 3

## Statistics

| Metric | Count |
|--------|-------|
| Critical | 0 |
| High | 3 |
| Medium | 0 |
| Git: real page found | 0 |
| Recommendation: RESTORE FROM GIT | 0 |
| Recommendation: CONVERT TO SUBVIEW | 1 |
| Recommendation: CREATE NEW PAGE | 2 |

## Commercial / CRM (1)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0001 | nps/page.tsx | /dashboard/crm?tab=NPSPage | `/dashboard/nps/surveys` | high | NONE | CONVERT_TO_WORKSPACE_SUBVIEW |

## Documents & Communication (1)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0002 | knowledge-base/page.tsx | /dashboard/documents?tab=KnowledgeBasePage | `/dashboard/knowledge-base/categories` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |

## Commercial / Sales (1)

| ID | Source | Visible At | Target | Severity | Git | Recommendation |
|----|--------|-----------|--------|----------|-----|----------------|
| BVT-0003 | secondary-sales/page.tsx | /dashboard/sales?tab=SecondarySalesPage | `/dashboard/secondary-sales/${h.id` | high | NONE | CREATE_NEW_REAL_PAGE_REQUIRED |

