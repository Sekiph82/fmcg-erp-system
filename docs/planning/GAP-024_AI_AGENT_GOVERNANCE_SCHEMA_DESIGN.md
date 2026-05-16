# GAP-024 AI Agent Governance and Prompt Registry — Schema Design

## Objectives

1. Add `AIPrompt` ORM model + `ai_prompts` table for versioned prompt registry.
2. Add `ai.export` (missing from seed) and `ai.configure` (new) permission tuples.
3. Update `ai` ModuleDefinition `permission_actions` to include `configure`.
4. Add role grants for `export` and `configure`.
5. Add `RequirePermission` page guards to all AI frontend pages.
6. Fix bare `get_current_user` on two low-risk endpoints.

## `AIPrompt` Model

### Purpose

Central registry for prompt templates used by AI service functions.
Supports versioning (integer version), active/inactive state, and module ownership.
Enables audit trail of which prompt version was used for each AI call.

### Fields

| Field | Type | Notes |
|---|---|---|
| id | UUID PK | |
| key | String(100) | Unique slug: `predictions.demand_forecast`, `chat.system`, `formulation.generate` |
| version | Integer | Monotonically increasing per key. Latest active = highest active version. |
| title | String(255) | Human-readable label |
| module | String(50) | Owning module key (`ai`, `npd`, `maintenance`, etc.) |
| prompt_type | String(50) | `system`, `user`, `few_shot`, `rag_context` |
| content | Text | The prompt text. May include `{variable}` placeholders. |
| variables | JSON | List of expected placeholder names, e.g. `["product_category", "target_cost"]` |
| is_active | Boolean | Only one version per key should be active at a time (enforced in service layer). |
| notes | Text | Change notes / rationale |
| created_by | String(200) | username of creator |

### Indexes

- Unique constraint on `(key, version)`.
- Index on `(key, is_active)` for fast active-version lookup.

### Table Name

`ai_prompts`

## Permission Family Expansion

| Action | Code | Purpose | Public |
|---|---|---|---|
| view | ai.view | Dashboard, predictions, recommendations, logs | True |
| create | ai.create | Generate predictions, recommendations, scenarios, formulations, chat | False |
| edit | ai.edit | Action/dismiss recommendations, archive predictions | False |
| approve | ai.approve | Approve formulations, execute NL commands | False |
| export | ai.export | Export AI audit logs, governance reports | False |
| configure | ai.configure | Create/update/deactivate prompt templates in registry | False |

`configure` is restricted to admin and CTO only. Prompt content directly affects AI outputs — changes must be controlled.

## Module Registry Update

```python
ModuleDefinition(
    key="ai",
    permission_actions=("view", "create", "edit", "approve", "export", "configure"),
    ...
)
```

## Role Grants

| Role | New Grants |
|---|---|
| admin | ai.export, ai.configure |
| cto | ai.export, ai.configure |
| coo | ai.export |
| executive | ai.export |
| owner | ai.export, ai.configure |

Existing grants (view/create/edit/approve) remain unchanged for roles that already have them.

## Endpoint Permission Mapping

### New Prompt CRUD Endpoints

| Endpoint | Permission |
|---|---|
| GET /ai/prompts/ | ai.configure |
| POST /ai/prompts/ | ai.configure |
| GET /ai/prompts/{id}/ | ai.configure |
| PUT /ai/prompts/{id}/ | ai.configure |
| POST /ai/prompts/{key}/deactivate | ai.configure |

### Fixed Endpoints (bare `get_current_user` → `require_permission`)

| Endpoint | Old Guard | New Guard |
|---|---|---|
| GET /ai/forecast-baseline/ | get_current_user | ai.view |
| GET /ai/health/ | get_current_user | get_current_user (keep — it is a health check, not a data endpoint) |

`/health/` is acceptable with just auth since it returns no business data.
`/forecast-baseline/` should require `ai.view` for consistency.

## Frontend Guard Mapping

| Page | Permission |
|---|---|
| ai/page.tsx | ai.view |
| ai/chat/page.tsx | ai.create |
| ai/compliance/page.tsx | ai.view |
| ai/formulations/page.tsx | ai.view |
| ai/governance/page.tsx | ai.view |
| ai/logs/page.tsx | ai.view |
| ai/nl-command/page.tsx | ai.view |
| ai/predictions/page.tsx | ai.view |
| ai/recommendations/page.tsx | ai.view |
| ai/scenarios/page.tsx | ai.view |

## Migration Strategy

- Single additive reconciliation migration: `20260516_0040_ai_prompt_registry_reconciliation.py`.
- Creates `ai_prompts` table using `_has_table()` guard.
- Creates no enum types (all String columns).
- Does not touch existing AI tables.
- Single head after merge: `20260516_0040`.

## Schema File

Create `backend/app/schemas/ai.py` with:
- `AIPromptCreate` — key, version, title, module, prompt_type, content, variables, notes
- `AIPromptUpdate` — title, content, variables, notes, is_active
- `AIPromptRead` — all fields + id + created_by + created_at
