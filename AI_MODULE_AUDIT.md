# AI Module Audit

**Audit Date:** 2026-05-01  
**Auditor:** Claude Code  
**Project:** FMCG ERP (Kenya)

---

## 1. Executive Summary

| Question | Answer |
|---|---|
| Is the AI module real or UI-only? | **Mostly real** — backend, DB, and provider abstraction all exist. Two critical bugs prevent actual execution. |
| Is prediction functional? | **Partially** — pipeline exists and is wired, but a SQL bug (`Stock.reorder_point` not a column on `stocks` table) crashes every prediction call. |
| Is there real model integration? | **Yes** — Anthropic (Claude), OpenAI (GPT-4o), Google Gemini (real async calls), and a clean MockProvider. Auto-detection present. `.env.development` has an active Gemini key. |
| Can it answer real ERP questions? | **No free-form chat** — there is no `/ai/chat/` endpoint. Users can generate predictions/recommendations/scenarios/formulations, but cannot ask arbitrary ERP copilot questions. |

**Verdict: Partially Working — would work if two bugs are fixed and chat endpoint added.**

---

## 2. Frontend Findings

| File | Purpose | Triggers | API Call | Status |
|---|---|---|---|---|
| `frontend/src/app/dashboard/ai/page.tsx` | AI dashboard with KPIs, recent preds, critical recs | Page load + Generate buttons | `GET /ai/dashboard/`, `POST /ai/predictions/generate/`, `POST /ai/recommendations/generate/` | ✅ Real — connected to real API |
| `frontend/src/app/dashboard/ai/predictions/page.tsx` | List/archive predictions with filters | Generate, archive | `POST /ai/predictions/generate/`, `GET /ai/predictions/`, `DELETE /ai/predictions/{id}/archive/` | ✅ Real |
| `frontend/src/app/dashboard/ai/recommendations/page.tsx` | List recs, action/dismiss | Generate, action, dismiss | `POST /ai/recommendations/generate/`, `GET /ai/recommendations/`, action/dismiss mutations | ✅ Real |
| `frontend/src/app/dashboard/ai/scenarios/page.tsx` | What-if scenario simulator | Submit scenario form | `POST /ai/scenarios/simulate/` | ✅ Real |
| `frontend/src/app/dashboard/ai/formulations/page.tsx` | Product formulation builder | Submit form | `POST /ai/formulations/generate/` | ✅ Real |
| `frontend/src/app/dashboard/ai/compliance/page.tsx` | Compliance/document hub | Unknown | Unknown — needs inspection | ⚠️ May be stub |
| `frontend/src/app/dashboard/ai/logs/page.tsx` | AI request audit log | Page load | `GET /ai/logs/` | ✅ Real |
| `frontend/src/lib/aiApi.ts` | TypeScript API client | All pages | All 16 methods wired | ✅ Real — complete client |

**Missing frontend:**
- No chat/copilot UI — no free-form question input anywhere
- No `/ai/chat/` call in `aiApi.ts`
- No forecast visualization (just text summaries)
- No "mock mode" indicator shown to users

---

## 3. Backend Findings

### ai_provider.py

| Component | Status | Notes |
|---|---|---|
| `AnthropicProvider` | ✅ Real | Async, proper token tracking |
| `OpenAIProvider` | ✅ Real | Async, proper token tracking |
| `GeminiProvider` | ✅ Real | Async via `run_in_executor`, usage metadata |
| `MockProvider` | ✅ Real | Deterministic stubs, labeled "mock" |
| `get_ai_provider()` | ✅ Real | Auto-detects key, singleton |
| Provider for "auto" setting with Gemini key | ✅ Works | Picks Gemini correctly |

### ai_service.py

| Function | Status | Bug |
|---|---|---|
| `_gather_erp_context()` | ❌ **BROKEN** | Queries `Stock.reorder_point` — this column does not exist on `stocks` table. `reorder_point` lives on `Product`/`Material` in `master.py`. Every AI call that reaches this function will throw `column "stocks.reorder_point" does not exist`. |
| `_log_request()` | ❌ **BROKEN** | Does `AIProviderEnum(settings.AI_PROVIDER)` — `AIProvider` enum only has `ANTHROPIC`, `OPENAI`, `MOCK`. If `AI_PROVIDER="auto"` or `"gemini"`, this throws `ValueError`. |
| `generate_predictions()` | ⚠️ Would work | Blocked by two bugs above |
| `generate_recommendations()` | ⚠️ Would work | Blocked by two bugs above |
| `simulate_scenario()` | ⚠️ Would work | Blocked by two bugs above |
| `generate_formulation()` | ⚠️ Would work | Partially — formulation does separate material query, may avoid `_gather_erp_context` bug |
| `get_ai_dashboard()` | ⚠️ Partial | May work if DB tables exist |
| `chat()` / ERP Copilot | ❌ **MISSING** | No free-form chat function exists |

### ai.py (endpoints)

| Endpoint | Status |
|---|---|
| `GET /ai/status/` | ✅ Works — no DB call |
| `GET /ai/dashboard/` | ⚠️ May work if predictions table exists |
| `POST /ai/predictions/generate/` | ❌ Broken — hits `_gather_erp_context` bug |
| `POST /ai/recommendations/generate/` | ❌ Broken — same |
| `POST /ai/scenarios/simulate/` | ❌ Broken — same |
| `POST /ai/formulations/generate/` | ✅ Likely works — different context path |
| All GET list endpoints | ✅ Work — pure DB reads |
| `POST /ai/chat/` | ❌ **MISSING** — endpoint does not exist |

### ai.py (models)

| Model | Status |
|---|---|
| `AIProvider` enum | ❌ Missing `GEMINI` and `AUTO` values |
| `AIRequest` table | ✅ |
| `AIPrediction` table | ✅ |
| `AIRecommendation` table | ✅ |
| `AIFormulation` table | ✅ |
| `AIScenario` table | ✅ |

---

## 4. Prompt and Agent Findings

| Item | Status |
|---|---|
| `SYSTEM_PROMPT_FMCG` | ✅ Exists — FMCG domain expert prompt, Kenya/East Africa context |
| `PREDICTION_SCHEMA` | ✅ Exists — JSON schema string |
| `RECOMMENDATION_SCHEMA` | ✅ Exists |
| `SCENARIO_SCHEMA` | ✅ Exists |
| `FORMULATION_SCHEMA` | ✅ Exists — detailed, includes CAS numbers |
| Copilot/chat prompt | ❌ **MISSING** |
| Agent orchestration | ❌ Not present — single-turn LLM calls only, no multi-step agents |
| Tool registry | ❌ Not present — ERP data pulled manually in `_gather_erp_context` |
| Prompt files (separate) | ❌ All inline in `ai_service.py` |
| Mock responses | ✅ 4 deterministic stubs (FORMULATION, PREDICTION, RECOMMENDATION, SCENARIO) |

---

## 5. Prediction Findings

| Question | Answer |
|---|---|
| Exists in UI? | ✅ Yes — predictions page, archive, filters |
| Exists in backend? | ✅ Yes — `generate_predictions()` function |
| Connected end-to-end? | ❌ No — SQL bug prevents execution |
| Statistical/ML forecasting? | ❌ No — pure LLM-generated numbers |
| Deterministic baseline? | ❌ No — no moving average, weighted average, or trend logic |
| Forecast output schema? | ✅ Defined and parsed |
| Confidence from data? | ❌ No — confidence is LLM-hallucinated, not computed from data variance |

**What happens right now when prediction is triggered:**
1. Frontend calls `POST /ai/predictions/generate/`
2. Backend enters `generate_predictions()`
3. Calls `_gather_erp_context()`
4. SQL query: `Stock.reorder_point` → **PostgreSQL error: column "stocks.reorder_point" does not exist**
5. Exception propagates → HTTP 500
6. Frontend receives error

**With mock provider:** Same crash — `_gather_erp_context` runs before provider selection.

---

## 6. Gap Analysis

| Gap | Severity | Fix |
|---|---|---|
| `Stock.reorder_point` SQL bug | 🔴 CRITICAL | Join Product/Material for reorder_point |
| `AIProvider` enum missing GEMINI/AUTO | 🔴 CRITICAL | Add values, fix `_log_request` |
| No `/ai/chat/` endpoint | 🔴 HIGH | Add copilot function + endpoint |
| No deterministic forecast baseline | 🟠 MEDIUM | Add moving average computation |
| No chat UI | 🟠 MEDIUM | Add chat page/component |
| Mock mode not shown to users | 🟡 LOW | Show "Dev/Mock Mode" badge |
| Prompts all inline | 🟡 LOW | Extract to constants (already in same file) |
| No agent orchestration | 🟡 LOW | Single-turn is acceptable for V1 |
| No tool registry | 🟡 LOW | ERP context gathering works as tool layer |
| Confidence not data-derived | 🟡 LOW | Add statistical confidence calculation |
| No retry logic | 🟡 LOW | Add simple retry on transient errors |

---

## 7. Recommended Fix Plan

### Phase 1 — Make current AI module truly functional (THIS RUN)
1. Fix `Stock.reorder_point` SQL bug in `_gather_erp_context`
2. Add `GEMINI` and `AUTO` to `AIProvider` enum; fix `_log_request` provider mapping
3. Add `generate_chat_response()` to `ai_service.py`
4. Add `POST /ai/chat/` endpoint to `ai.py`
5. Add `chat()` to `aiApi.ts`
6. Add deterministic sales baseline to `generate_predictions()`
7. Create `AI_MODULE_TEST_CHECKLIST.md`

### Phase 2 — Make prediction truly functional
1. Pull last 12 months of sales data by product
2. Compute moving average forecast (3-month window)
3. Calculate confidence from data completeness and variance
4. Pass structured baseline to LLM for explanation only (not fabrication)

### Phase 3 — Add specialist ERP agents
1. Inventory Agent (reorder alerts, FEFO recommendations)
2. Finance Agent (cash flow, aging analysis)
3. Production Agent (capacity, scheduling)
4. Supplier Agent (lead time risk, alternatives)

---

## 8. Verdict

**"Partially Working — blocked by two critical bugs"**

The AI module architecture is solid:
- Real provider abstraction (Anthropic/OpenAI/Gemini/Mock)
- Real prompt engineering with ERP context
- Real database persistence of AI results
- Real frontend connected to real endpoints
- Active Gemini API key in `.env.development`

However, **every prediction/recommendation/scenario call will throw HTTP 500** due to the `Stock.reorder_point` SQL bug. Formulations may work. Status endpoint works. GET lists work (if any data exists).

The module is one bug-fix away from being functional for predictions, and needs one endpoint added for free-form chat.
