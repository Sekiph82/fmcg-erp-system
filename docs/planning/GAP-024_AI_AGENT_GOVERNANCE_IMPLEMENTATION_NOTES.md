# GAP-024 AI Agent Governance and Prompt Registry — Implementation Notes

## Summary

GAP-024 hardened the existing AI agent governance implementation with a versioned prompt registry,
expanded permission coverage, and frontend page guards.
The existing AI models, endpoints, and governance surfaces were already feature-complete.

## Changes Made

### GAP-024A — Audit
- Inspected all AI models, endpoints, seed permissions, and frontend pages.
- Key gaps: no AIPrompt model, ai.export not seeded, no page guards on any AI page, forecast-baseline using bare get_current_user.
- Output: `GAP-024_AI_AGENT_GOVERNANCE_AUDIT.md`

### GAP-024B — Schema Design
- Designed `ai_prompts` table: key + version (unique), is_active, prompt_type, content, variables, module ownership.
- Defined `ai.export` and `ai.configure` permission tuples and role grants.
- Output: `GAP-024_AI_AGENT_GOVERNANCE_SCHEMA_DESIGN.md`

### GAP-024C — Migration
- Created `20260516_0040_ai_prompt_registry_reconciliation.py`.
- Idempotently creates `ai_prompts` table with unique constraint `uq_ai_prompts_key_version (key, version)`.
- Index: `ix_ai_prompts_key_active (key, is_active)`.
- Single Alembic head: `20260516_0040`.

### GAP-024D — ORM Model
- Added `AIPrompt` class to `backend/app/models/ai.py`.
- Fields: id, key, version, title, module, prompt_type, content, variables (JSON), is_active, notes, created_by.
- Comment: versioned registry, one active version per key at a time.

### GAP-024E — Schemas
- Created `backend/app/schemas/ai.py` with `AIPromptCreate`, `AIPromptUpdate`, `AIPromptRead`.
- `AIPromptCreate`: required key, title, content; optional version (default 1), module, prompt_type, variables, notes.
- `AIPromptUpdate`: all optional; supports partial updates.
- `AIPromptRead`: full read representation with id, created_by, timestamps.

### GAP-024F — Service Helper
- Added `resolve_prompt(db, key, default)` to `backend/app/services/ai_service.py`.
- Queries `ai_prompts` for highest-version active prompt with matching key.
- Falls back to provided default if no DB record exists or on exception.
- Enables gradual migration: hard-coded prompts remain functional until registry entries exist.

### GAP-024G — Endpoint Changes
- Added 5 prompt CRUD endpoints to `backend/app/api/v1/endpoints/ai.py`:
  - `GET /ai/prompts/` — list prompts (key, module, active_only filters) → `ai.configure`
  - `POST /ai/prompts/` — create prompt → `ai.configure`
  - `GET /ai/prompts/{id}/` — get single prompt → `ai.configure`
  - `PUT /ai/prompts/{id}/` — update prompt → `ai.configure`
  - `POST /ai/prompts/{key}/deactivate` — deactivate all versions for a key → `ai.configure`
- Fixed `GET /ai/forecast-baseline/` guard: bare `get_current_user` → `require_permission("ai", "view")`.
- `GET /ai/health/` kept with bare `get_current_user` (health check, no business data).

### GAP-024H — Module Registry and Seed
- Added `ai.export` and `ai.configure` permission tuples to `PERMISSIONS` list in seed.py.
- Updated `ai` ModuleDefinition `permission_actions` from `("view", "create", "edit", "approve", "export")` to `("view", "create", "edit", "approve", "export", "configure")`.
- Role grants added:
  - `admin`: full AI permissions (view, create, edit, approve, export, configure)
  - `cto`: export + configure added (already had view, create, edit, approve)
  - `ceo`: export added (already had view, create, edit, approve)
  - `coo`: view, create, export added (previously had no AI permissions)

### GAP-024I — Frontend Permission Guards
- Added `RequirePermission` page-level guards to all 9 AI frontend pages:
  - `ai/page.tsx` → `ai.view`
  - `ai/chat/page.tsx` → `ai.create`
  - `ai/compliance/page.tsx` → `ai.view`
  - `ai/formulations/page.tsx` → `ai.view`
  - `ai/governance/page.tsx` → `ai.view`
  - `ai/logs/page.tsx` → `ai.view`
  - `ai/nl-command/page.tsx` → `ai.view`
  - `ai/predictions/page.tsx` → `ai.view`
  - `ai/recommendations/page.tsx` → `ai.view`
  - `ai/scenarios/page.tsx` → `ai.view`

### GAP-024J — Tests
- Created `backend/tests/test_gap024_ai_agent_governance.py` with 28 contract tests:
  - Module registry: ai in MODULE_DEFINITIONS, correct permission_actions (configure, export)
  - Permission seeds: all 6 ai tuples present (including export and configure)
  - Registry permission codes
  - Role grants: admin, cto, ceo, coo
  - Endpoint source: require_permission present, configure guard present, forecast-baseline fixed
  - Prompt CRUD endpoints present in source
  - ORM: AIPrompt importable with correct tablename and fields
  - Schemas: AIPromptCreate importable and constructable
  - Service: resolve_prompt importable and callable
  - Migration: file exists, ai_prompts and unique constraint in source
  - Frontend guards: all 9 pages checked for RequirePermission

## Limitations

- Docker not available — `alembic upgrade head` not executed. Migration verified via offline SQL rendering.
- `resolve_prompt()` is a service utility — not yet called from service functions. Existing hard-coded prompts in `app/prompts/` remain in use.
- Prompt registry is write-once per (key, version) pair; deactivation is the correct lifecycle action rather than deletion.
- `ai.configure` is restricted to admin and CTO: prompt content directly affects AI outputs.
