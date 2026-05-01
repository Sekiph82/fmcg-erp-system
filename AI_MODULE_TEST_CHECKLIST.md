# AI Module Test Checklist

**Project:** FMCG ERP (Kenya)  
**Last Updated:** 2026-05-01

---

## Prerequisites

```bash
# Start all services
start-dev.bat     # or: docker compose --env-file .env.development up -d

# Verify backend is up
curl http://localhost:8000/health

# Verify frontend is up
curl http://localhost:3000
```

---

## 1. AI Health Endpoint

**Endpoint:** `GET /api/v1/ai/health/`

| Test | Expected | Pass? |
|---|---|---|
| Hit endpoint with no API key configured | `{"status": "ok", "provider": "mock", "mode": "mock"}` | |
| Hit endpoint with GEMINI_API_KEY set | `{"status": "ok", "provider": "gemini", "mode": "live"}` | |
| Hit endpoint with invalid key | `{"status": "ok", "provider": "gemini", "mode": "live"}` (key not validated at startup) | |

```bash
curl http://localhost:8000/api/v1/ai/health/
```

---

## 2. AI Status Endpoint

**Endpoint:** `GET /api/v1/ai/status/`

```bash
curl http://localhost:8000/api/v1/ai/status/
```

Expected (with Gemini key):
```json
{
  "provider": "gemini",
  "configured": true,
  "model": "gemini-1.5-pro",
  "mode": "live"
}
```

Expected (no API keys):
```json
{
  "provider": "auto",
  "configured": false,
  "model": "gpt-4o",
  "mode": "mock"
}
```

---

## 3. ERP Copilot Chat

**Endpoint:** `POST /api/v1/ai/chat/`  
**Auth:** Bearer token required  
**UI:** `http://localhost:3000/dashboard/ai/chat`

### 3a. With real API key (Gemini)

```bash
TOKEN="your-access-token"
curl -X POST http://localhost:8000/api/v1/ai/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the current inventory status?"}'
```

**Expected response shape:**
```json
{
  "answer": "Based on the ERP data...",
  "provider": "gemini",
  "model": "gemini-1.5-pro",
  "mode": "live",
  "erp_context_used": ["sales_90d", "inventory", "master_data", "date"],
  "tokens": {"prompt": 500, "completion": 200},
  "latency_ms": 1500
}
```

### 3b. With no API key (mock mode)

Expected: `answer` starts with `[MOCK/DEV MODE — ...]` — clearly labeled  
Expected: `mode: "mock"`  
Expected: No ERP facts fabricated

### 3c. With missing ERP data (empty DB)

Expected: Answer says "No sales data available" / "inventory data shows 0 items"  
Expected: Does NOT make up numbers

### 3d. Empty message

```bash
curl -X POST http://localhost:8000/api/v1/ai/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": ""}'
```
Expected: HTTP 400 — "Message cannot be empty"

### 3e. Too-long message (>2000 chars)

Expected: HTTP 400 — "Message too long"

---

## 4. Prediction Generation

**Endpoint:** `POST /api/v1/ai/predictions/generate/`  
**Auth + Permission:** `ai.create` required  
**UI:** `http://localhost:3000/dashboard/ai/predictions`

```bash
curl -X POST http://localhost:8000/api/v1/ai/predictions/generate/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prediction_types": ["sales_forecast", "stock_depletion"]}'
```

**What should happen:**
1. Backend calls `_gather_erp_context()` → DB queries (no crash after bug fix)
2. ERP context assembled and injected into prompt
3. LLM (or mock) returns structured JSON
4. Predictions stored in `ai_predictions` table
5. Response includes prediction list

**With mock provider:** Returns `MOCK_PREDICTION` deterministic stub  
**With real provider:** Returns LLM-generated predictions based on live ERP data

**Check if bug is fixed:** Should NOT get HTTP 500 with "column stocks.reorder_point does not exist"

---

## 5. Deterministic Forecast Baseline

**Endpoint:** `GET /api/v1/ai/forecast-baseline/`

```bash
curl http://localhost:8000/api/v1/ai/forecast-baseline/ \
  -H "Authorization: Bearer $TOKEN"
```

**Expected (with invoice data in DB):**
```json
{
  "baseline_forecast_kes": 2500000,
  "moving_average_kes": 2450000,
  "trend_pct": 3.5,
  "method": "weighted_moving_average_3m",
  "data_quality": "good",
  "confidence": 0.75,
  "monthly_history_kes": [2300000, 2450000, 2600000],
  "note": "Baseline uses weighted 3-month moving average..."
}
```

**Expected (with no invoice data):**
```json
{
  "baseline_forecast_kes": 0,
  "method": "moving_average_3m",
  "data_quality": "insufficient",
  "confidence": 0.0,
  "note": "No sales data available for baseline computation."
}
```

---

## 6. Recommendation Generation

```bash
curl -X POST http://localhost:8000/api/v1/ai/recommendations/generate/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"focus_area": "stock"}'
```

Expected: List of recommendations, each with category, title, priority, expected_impact

---

## 7. Scenario Simulation

```bash
curl -X POST http://localhost:8000/api/v1/ai/scenarios/simulate/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_type": "price_change",
    "parameters": {"product": "Liquid Detergent 1L", "change_pct": 10}
  }'
```

Expected: Scenario with risks, opportunities, revenue_change_pct, recommendation

---

## 8. Formulation Generation

```bash
curl -X POST http://localhost:8000/api/v1/ai/formulations/generate/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_category": "liquid_detergent",
    "target_properties": {"fragrance": "lemon", "cleaning_power": "high"},
    "cost_target": 0.50,
    "performance_priority": "balanced"
  }'
```

Expected: Full formulation with ingredients (INCI, CAS, %), process steps, cost breakdown

---

## 9. AI Dashboard

```bash
curl http://localhost:8000/api/v1/ai/dashboard/ \
  -H "Authorization: Bearer $TOKEN"
```

Expected: stats (prediction/rec counts), recent_predictions, critical_recommendations, provider info

---

## 10. AI Logs

```bash
curl "http://localhost:8000/api/v1/ai/logs/?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

Expected: List of requests with provider, model, tokens, latency, status

---

## 11. Frontend UI Checks

| Screen | URL | Check |
|---|---|---|
| AI Dashboard | `/dashboard/ai` | KPI cards load, generate buttons work |
| ERP Copilot | `/dashboard/ai/chat` | Can type and get response, mock badge shown when no key |
| Predictions | `/dashboard/ai/predictions` | Generate button creates predictions |
| Recommendations | `/dashboard/ai/recommendations` | Action/dismiss buttons work |
| Scenarios | `/dashboard/ai/scenarios` | Scenario form submits |
| Formulations | `/dashboard/ai/formulations` | Formulation builder works |
| AI Logs | `/dashboard/ai/logs` | Log list shows requests |

---

## 12. Failure Scenarios

| Scenario | Expected Behavior |
|---|---|
| No API key configured | Mock provider used, response labeled `[MOCK/DEV MODE]` |
| Invalid API key | HTTP 500 from LLM provider, logged in `ai_requests` table |
| Empty ERP database | Context has zeros, LLM responds with "insufficient data" |
| DB connection failure | `_gather_erp_context` catches per-query, returns partial context |
| LLM returns invalid JSON | `parse_json()` fails → HTTP 500, logged as FAILED in `ai_requests` |
| LLM timeout | Exception raised → FAILED logged, HTTP 500 |
| Message too long | HTTP 400 before any LLM call |

---

## 13. Known Limitations (as of 2026-05-01)

- Confidence scores in predictions are LLM-estimated, not statistically computed from data variance
- No retry logic for transient LLM API failures
- No streaming for long responses (chat waits for full response)
- No agent multi-step reasoning (single-turn calls only)
- Formulation engine only supports the categories in the prompt
- No RAG / vector search — ERP context is limited to what `_gather_erp_context` fetches

---

## 14. Environment Configuration

```bash
# For mock mode (no cost, deterministic responses)
# Leave all AI keys empty in .env.development

# For Gemini (current .env.development)
GEMINI_API_KEY=your-key-here
AI_PROVIDER=auto   # or: gemini

# For Claude (Anthropic)
ANTHROPIC_API_KEY=your-key-here
AI_PROVIDER=auto   # auto-detects, Anthropic wins over others

# For OpenAI
OPENAI_API_KEY=your-key-here
AI_PROVIDER=openai
```

**Security Note:** The current `.env.development` contains an active Gemini API key.  
Rotate this key if the `.env.development` file has been committed to git or shared.
