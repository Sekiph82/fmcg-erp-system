# GAP-005 Frontend / Backend Parity Schema Design

## Decision

No database schema or Alembic migration is required for GAP-005.

The audit found a contract/parity problem, not a persisted business-data problem. The right design is a repository-owned parity contract that can be checked in CI and used by developers while converting dashboard pages away from raw `/api/v1` browser calls.

## Why No Database Table

Frontend/backend parity metadata is build-time and source-code metadata:

- backend route key and prefix
- frontend dashboard route
- frontend API client module
- route alias notes
- required view permission
- E2E smoke status
- whether direct page-level API calls are allowed

Persisting this in PostgreSQL would add runtime complexity without improving ERP data integrity. The source of truth should stay near the code that owns routes and clients.

## Proposed Code-Level Contract

Add a lightweight manifest in a later implementation task. The likely location is:

```text
frontend/src/lib/moduleParity.ts
```

Proposed TypeScript shape:

```ts
export type ParityStatus = "complete" | "partial" | "missing" | "external";

export interface ModuleParityEntry {
  key: string;
  backendRouteKey: string;
  backendPrefix: string;
  frontendRoute: string;
  frontendClient?: string;
  requiredViewPermissions: string[];
  aliases?: string[];
  status: ParityStatus;
  e2eSmoke?: boolean;
  allowRawApiPath?: boolean;
  notes?: string;
}
```

The manifest should start with critical workflow modules and known aliases:

- inventory
- procurement
- production
- quality
- finance
- sales
- notifications / notification-center
- qms
- iot
- npd
- documents

## Static Check Design

Add a small script in a later implementation task, likely:

```text
frontend/scripts/check-api-parity.mjs
```

Responsibilities:

1. Scan `frontend/src/app/dashboard/**/*.tsx` for raw `/api/v1/` usage.
2. Allow exceptions only when listed in the parity manifest with `allowRawApiPath: true` and a note.
3. Check that each manifest `frontendRoute` exists.
4. Check that each manifest `frontendClient` exists when defined.
5. Report missing route/client mappings without modifying files.

This should be a non-destructive CI/developer check, not a runtime feature.

Suggested script command:

```json
{
  "check:api-parity": "node scripts/check-api-parity.mjs"
}
```

## Backend Registry Relationship

The backend already has:

- core `MODULE_DEFINITIONS`
- broad `EndpointRouteDefinition` entries
- `/api/v1/modules/manifest`
- `/api/v1/modules/permissions/coverage`

GAP-005 should not duplicate the backend registry. The frontend parity manifest should reference backend route keys/prefixes and document intentional aliases while future work can gradually move more navigation metadata backend-side.

## Raw API Path Cleanup Strategy

Do not convert all 51 raw `/api/v1` page usages in one large edit.

Prioritize modules that affect current user pain or critical ERP workflows:

1. notification center / notifications
2. IoT
3. QMS
4. quality certificates and consumer complaints
5. NPD
6. finance VAT/eTIMS

Each conversion should:

- add or reuse a typed client in `frontend/src/lib`
- use `apiClient` so `NEXT_PUBLIC_API_URL`, `withCredentials`, and response interceptors apply
- preserve current UI and route behavior
- include a focused type-check or browser smoke check where possible

## Dependencies

- GAP-005A audit
- existing `frontend/src/lib/api.ts`
- existing backend `module_registry.py`
- existing E2E scaffolding from GAP-004

## Acceptance Criteria for Later Implementation

- A parity manifest exists and documents critical module route/client mappings.
- A static check reports raw `/api/v1` dashboard usage unless explicitly allowlisted.
- Package scripts expose the check.
- The check can run locally without Docker or secrets.
- No database migration is added for this parity metadata.

