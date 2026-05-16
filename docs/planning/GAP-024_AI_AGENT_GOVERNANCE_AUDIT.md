# GAP-024 AI Agent Governance and Prompt Registry — Audit

## Scope

Inspect current AI agent governance implementation and prompt registry state.
Identify gaps before schema design and implementation.

## What Exists

### ORM Models (`backend/app/models/ai.py`)

| Model | Table | Purpose |
|---|---|---|
| AIRequest | ai_requests | Audit log of every AI API call (type, provider, model, token counts, latency) |
| AIPrediction | ai_predictions | Stored prediction results (type, subject, confidence, risk_level, trend, summary) |
| AIRecommendation | ai_recommendations | Stored recommendations (category, priority, action_data, actioned/dismissed flags) |
| AIFormulation | ai_formulations | AI-generated chemical formulations (approve/favorite flow) |
| AIScenario | ai_scenarios | Scenario simulations (type, input_params, risks, opportunities) |
| NLCommandLog | ai_nl_commands | Natural language command parse/confirm/execute log |
| AIAgentPolicy | ai_agent_policies | Governance policy per agent (allowed/forbidden actions, token budget, human approval flag) |
| AIAgentRun | ai_agent_runs | Execution audit log per agent run (status, tokens, cost, anomaly_flag) |

**No `AIPrompt` model exists.** No `ai_prompts` table. Prompts are hard-coded in service logic.

### Endpoints (`backend/app/api/v1/endpoints/ai.py`)

All primary endpoints use `require_permission("ai", action)` guards:

| Endpoint | Permission |
|---|---|
| GET /ai/dashboard/ | ai.view |
| GET /ai/status/ | ai.view |
| GET /ai/modes/ | ai.view |
| POST /ai/predictions/generate/ | ai.create |
| GET /ai/predictions/ | ai.view |
| DELETE /ai/predictions/{id}/archive/ | ai.edit |
| POST /ai/recommendations/generate/ | ai.create |
| GET /ai/recommendations/ | ai.view |
| POST /ai/recommendations/{id}/action/ | ai.edit |
| POST /ai/recommendations/{id}/dismiss/ | ai.edit |
| POST /ai/scenarios/simulate/ | ai.create |
| GET /ai/scenarios/ | ai.view |
| GET /ai/scenarios/{id}/ | ai.view |
| POST /ai/formulations/generate/ | ai.create |
| GET /ai/formulations/ | ai.view |
| GET /ai/formulations/{id}/ | ai.view |
| POST /ai/formulations/{id}/approve/ | ai.approve |
| POST /ai/formulations/{id}/favorite/ | ai.edit |
| GET /ai/logs/ | ai.view |
| POST /ai/chat/ | ai.create |
| POST /ai/nl-command | ai.create |
| GET /ai/nl-command/{id}/preview | ai.view |
| POST /ai/nl-command/{id}/execute | ai.approve |
| POST /ai/nl-command/{id}/reject | ai.edit |
| GET /ai/nl-command/history | ai.view |
| POST /ai/governance/policies | ai.create |
| GET /ai/governance/policies | ai.view |
| PATCH /ai/governance/policies/{id}/toggle | ai.edit |
| POST /ai/governance/runs | ai.create |
| GET /ai/governance/runs | ai.view |
| GET /ai/governance/dashboard | ai.view |

**Two endpoints use bare `Depends(get_current_user)` instead of `require_permission`:**
- `GET /ai/forecast-baseline/` — deterministic (no LLM), but still needs a proper permission guard
- `GET /ai/health/` — lightweight health check, acceptable with just auth but inconsistent

No prompt registry endpoints exist.

### Module Registry (`backend/app/core/module_registry.py`)

```python
ModuleDefinition(
    key="ai",
    label="AI & Intelligence",
    permission_actions=("view", "create", "edit", "approve", "export"),
    ...
)
```

`export` is declared in module registry but **not seeded** in `PERMISSIONS`.

`configure` is not declared in registry or seeded.

### Permission Seeds (`backend/app/db/seed.py`)

Only 4 tuples seeded for `ai`:

```python
("ai", "view",    ...)
("ai", "create",  ...)
("ai", "edit",    ...)
("ai", "approve", ...)
```

Missing: `ai.export` (declared in registry), `ai.configure` (not declared anywhere).

### Frontend Pages (`frontend/src/app/dashboard/ai/`)

9 pages + 1 layout, 0 with `RequirePermission` guards:

| Page | Current Guard |
|---|---|
| ai/page.tsx | None |
| ai/chat/page.tsx | None |
| ai/compliance/page.tsx | None |
| ai/formulations/page.tsx | None |
| ai/governance/page.tsx | None |
| ai/logs/page.tsx | None |
| ai/nl-command/page.tsx | None |
| ai/predictions/page.tsx | None |
| ai/recommendations/page.tsx | None |
| ai/scenarios/page.tsx | None |

### Schemas

No `backend/app/schemas/ai.py` file exists. Schemas are defined inline in the endpoint file as Pydantic `BaseModel` subclasses.

### Tests

No `backend/tests/test_gap024_ai*.py`. No AI governance contract tests.

## Gaps Summary

| # | Gap | Severity |
|---|---|---|
| 1 | No `AIPrompt` ORM model or `ai_prompts` DB table | High |
| 2 | No prompt CRUD endpoints or `ai.configure` permission | High |
| 3 | `ai.export` seeded in registry but missing from seed PERMISSIONS | Medium |
| 4 | `ai.configure` not declared in registry permission_actions | Medium |
| 5 | `GET /forecast-baseline/` uses bare `get_current_user` | Low |
| 6 | `GET /health/` uses bare `get_current_user` | Low |
| 7 | No `RequirePermission` on any of 9+ AI frontend pages | High |
| 8 | No AI governance contract tests | Medium |
| 9 | No role grants for `ai.export` or `ai.configure` | Medium |

## Recommended Implementation Sequence

- **GAP-024B** — Schema design: `AIPrompt` model fields, permission family expansion, role grants
- **GAP-024C** — Alembic reconciliation migration for `ai_prompts` table
- **GAP-024D** — Add `AIPrompt` ORM model to `app/models/ai.py`
- **GAP-024E** — Create `app/schemas/ai.py` with prompt create/update/read schemas
- **GAP-024F** — Add prompt resolution helper to `app/services/ai_service.py`
- **GAP-024G** — Add prompt CRUD endpoints to `app/api/v1/endpoints/ai.py` with `ai.configure`; fix forecast-baseline and health guards
- **GAP-024H** — Add `ai.export` + `ai.configure` to seed PERMISSIONS and module registry; update role grants
- **GAP-024I** — Add `RequirePermission` page guards to all AI frontend pages
- **GAP-024J** — Create `backend/tests/test_gap024_ai_agent_governance.py`
- **GAP-024K** — Implementation notes doc
- **GAP-024L** — Final checks, update TASKS.md + CODEX_PROGRESS.md
