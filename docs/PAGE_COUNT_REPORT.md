# Page Count Report

Generated: 2026-05-17

## Summary

| Classification            | Code | Count |
|---------------------------|------|-------|
| WORKSPACE_PAGE            | A    | 31   |
| REDIRECT_ONLY             | B    | 496   |
| LIGHTWEIGHT_WRAPPER       | C    | 213   |
| FULL_DUPLICATE_UI         | D    | 5   |
| STANDALONE_OPERATIONAL    | E    | 9   |
| UNKNOWN                   | F    | 0   |
| **Total**                 |      | **754** |

## Definitions

- **A WORKSPACE_PAGE** — renders `<ModuleWorkspace tabs={...}>` — these are the destination pages.
- **B REDIRECT_ONLY** — page body only calls `redirect()` / `permanentRedirect()` — no UI.
- **C LIGHTWEIGHT_WRAPPER** — dynamically imported as a tab by a workspace page. Stays as-is.
- **D FULL_DUPLICATE_UI** — has own API calls/state/forms and is NOT used as a workspace tab.
  These are the pages to migrate or convert to redirect-only.
- **E STANDALONE_OPERATIONAL** — full-screen tool that must remain standalone (POS, shop-floor).
- **F UNKNOWN** — could not classify from content heuristics.

## FULL_DUPLICATE_UI pages by module

### bom (4 pages)

- `/dashboard/bom/[id]/compliance` ❌ MW
- `/dashboard/bom/[id]/costing` ❌ MW
- `/dashboard/bom/[id]/explode` ❌ MW
- `/dashboard/bom/[id]` ❌ MW

### root (1 pages)

- `/dashboard/` ❌ MW
