# GAP-005 Frontend / Backend Parity Audit

## Scope

GAP-005 audits production-grade parity between the Next.js dashboard surface and the FastAPI backend API surface. This audit is documentation-only and does not change business logic.

## What Exists

- The frontend has a very large dashboard surface: 106 top-level directories under `frontend/src/app/dashboard`.
- The backend has a very large API surface: 136 endpoint modules under `backend/app/api/v1/endpoints` excluding health/init files.
- There are 86 exact normalized matches between backend endpoint module names and dashboard directory names, before accounting for intentional aliases such as `company` -> `companies`, `quotation` -> `quotes`, `notifications` -> `notification-center`, and `price_list` -> `price-lists`.
- `frontend/src/lib/api.ts` centralizes Axios with `NEXT_PUBLIC_API_URL`, `withCredentials: true`, and response handling for cookie auth.
- There are many frontend API client modules under `frontend/src/lib`; 101 library files reference API client or Axios-style helpers.
- Core operational modules have real frontend/backend wiring:
  - Inventory: dashboard page, shared client, scoped row action UX, backend inventory routes.
  - Procurement: PR/PO flows, shared client, backend procurement routes.
  - Production: plan/order flows, shared client, backend production routes.
  - Quality: inspection flows, shared client, backend quality routes.
  - Finance: accounting controls, shared client, backend finance routes.
  - Sales: customer/order/invoice areas, shared client, backend sales routes.
- Cookie auth and effective access helpers exist in the frontend auth context.
- Sidebar visibility is permission-aware and now also uses backend module manifest filtering for known registry permissions.
- GAP-004 added browser E2E scaffolding and stable selectors for core workflow screens.

## Partial Areas

### Backend-Owned Module Registry

The backend module registry owns core modules:

- users
- roles
- inventory
- production
- procurement
- sales
- finance
- quality
- maintenance
- utilities
- ai

The wider backend route registry covers many additional endpoints, but the full frontend navigation surface is still not completely generated from backend-owned metadata.

Impact: module visibility and parity can drift between frontend navigation, frontend API clients, and backend routes.

### API Client Consistency

Many frontend pages use typed clients in `frontend/src/lib`, which is the correct pattern. However, at least 51 dashboard pages still contain raw `/api/v1/...` paths directly in page components.

Examples include:

- IoT
- logs compliance/retention
- allergen cleaning
- copacking
- ESG carbon
- mobile
- payroll
- finance VAT/eTIMS
- quality certificates and complaints
- NPD
- containers
- QMS supplier safety / audit checklists
- van sales route optimizer

Impact:

- Browser requests can accidentally hit `localhost:3000/api/v1/...` instead of the backend URL.
- Calls may bypass `withCredentials`, cookie auth, shared interceptors, and consistent error handling.
- It becomes harder to test role/scope behavior consistently.

This is the same class of issue that previously caused frontend console errors for routes such as `/api/v1/notifications/...` resolving against the frontend host.

### Naming and Route Aliases

Several frontend route names intentionally differ from backend endpoint modules:

- `companies` frontend vs `company` backend
- `developer` frontend vs `api_portal` backend
- `messages` frontend vs `messaging` backend
- `notification-center` frontend vs `notifications` backend
- `price-lists` frontend vs `price_list` backend
- `projects` frontend vs `project` backend
- `quotes` frontend vs `quotation` backend
- `tax` frontend vs `tax_regulatory` backend

These aliases are manageable, but they should be documented in a parity manifest so they do not look like missing modules.

### Placeholder / Stub Signals

The repo still contains some explicit placeholder or stub signals:

- `backend/app/api/v1/endpoints/api_portal.py` exposes GraphQL information as a stub.
- `frontend/src/app/dashboard/documents/new/page.tsx` labels file attachment as placeholder.
- `frontend/src/app/dashboard/hr/payroll/page.tsx` identifies salary structure as placeholder/export-ready.
- `frontend/src/app/dashboard/custom-fields/workflow-rules/page.tsx` notes the backend automation engine is wired as a future stub.
- `frontend/src/app/dashboard/ai/nl-command/page.tsx` still shows stub execution-log language.

Impact: these areas should remain marked partial until real production workflows are implemented and tested.

## Missing / Risky Areas

1. No single frontend/backend parity manifest exists for route aliases, required permissions, API client path, and page path.
2. Raw browser `fetch("/api/v1/...")` calls remain in many dashboard pages.
3. Full sidebar/navigation is not yet backend-owned for every module.
4. Several modules have frontend pages and backend endpoints but no E2E smoke coverage yet.
5. Some pages still use direct page-level API logic instead of shared typed clients.
6. Error/loading/empty-state patterns are inconsistent across older module pages.
7. Production-grade parity is difficult to enforce in CI without a route/client/page manifest or static checks.

## Recommended GAP-005 Direction

GAP-005 should not start with a database migration. The immediate parity need is a frontend/API contract layer and incremental cleanup.

Recommended next design direction for GAP-005B:

1. Create a documented module parity manifest, likely in code or generated docs, that maps:
   - backend route key
   - backend prefix
   - frontend dashboard route
   - frontend API client file
   - sidebar key
   - required view permission
   - E2E smoke status
2. Add a small static check that flags direct `/api/v1` usage in dashboard pages unless explicitly allowed.
3. Convert high-risk raw fetch pages to shared API clients first:
   - notification center / notifications
   - IoT
   - QMS
   - quality certificates / complaints
   - NPD
   - finance VAT/eTIMS
4. Keep route aliases explicit instead of trying to rename working modules.
5. Expand browser smoke coverage after each cleanup slice.

## Suggested Acceptance for Later GAP-005 Tasks

- No new dashboard page should use raw `/api/v1` calls directly.
- Shared clients should use `apiClient` so cookie auth and backend base URL are respected.
- Every sidebar item should map to a backend permission or documented external/no-backend route.
- Every core operational module should have at least one browser smoke test.
- Stub/placeholder pages should remain visibly tracked as partial, not silently treated as done.

## Audit Commands Used

```powershell
Get-ChildItem -Path frontend\src\app\dashboard -Directory
Get-ChildItem -Path frontend\src\lib -File
Get-ChildItem -Path backend\app\api\v1\endpoints -File
rg -n "ModuleDefinition\(|EndpointRouteDefinition\(" backend\app\core\module_registry.py
rg -l "/api/v1/" frontend\src\app\dashboard -g "*.tsx"
rg -n "TODO|stub|placeholder|mock|not implemented|coming soon" frontend\src\app\dashboard backend\app\api\v1\endpoints -g "*.tsx" -g "*.py"
```

