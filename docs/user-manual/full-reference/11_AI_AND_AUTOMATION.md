# AI and Automation

**URL:** `/dashboard/ai`
**Module:** AI
**Permission:** `ai.view`

---

## Screenshot

![AI Workspace](../screenshots/captured/131_ai.png)
*AI workspace showing demand forecasting and PROPHET model type (implemented as local Holt-Winters).*

---

## AI Workspace Tabs

| Tab | URL | Purpose |
|---|---|---|
| Dashboard | ?tab=dashboard | AI overview and usage stats |
| Chat | ?tab=chat | AI Copilot — natural language queries |
| Predictions | ?tab=predictions | Demand forecasting |
| Formulations | ?tab=formulations | AI-assisted recipe optimisation |
| Recommendations | ?tab=recommendations | Procurement and production suggestions |
| Scenarios | ?tab=scenarios | What-if simulation |
| Compliance | ?tab=compliance | AI-assisted compliance check |
| Governance | ?tab=governance | AI usage policy |
| NL Command | ?tab=nl-command | Natural language ERP commands |
| Logs | ?tab=logs | AI API call log |

---

## AI Mode — Mock vs Live

The ERP has two AI tiers:

| Tier | Requires | Features |
|---|---|---|
| RULE_BASED / STATISTICAL | No external API key needed | Demand forecasting, procurement calculations, production scheduling, payroll |
| LLM_POWERED | `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` required | AI Chat, Formulations, Scenarios, NL Commands |

**RULE_BASED and STATISTICAL features work without any API key.** Demand forecasting uses a local statsmodels implementation — no external service required.

When no LLM API key is set, `AI_PROVIDER=auto` falls back to MockProvider. The `AIModeBanner` shows an amber "MOCK MODE" badge. LLM-powered features return canned demo responses in mock mode.

**To enable live LLM features:** Set `ANTHROPIC_API_KEY` (recommended), `OPENAI_API_KEY`, or `GEMINI_API_KEY` in `.env.production` and restart the backend. The banner turns green ("LIVE AI MODE") automatically.

---

## AI Copilot (Chat)

Requires LLM API key (`LLM_POWERED` tier).

Ask questions in plain English:
- "What is the current stock of flour?"
- "Show me this week's production orders"
- "Which customers are overdue on invoices?"

AI translates to ERP queries and returns results. Responses are labelled as AI-generated. In mock mode, responses are pre-canned demo text.

---

## Natural Language Commands

The NL Command tab allows admin-enabled users to run ERP operations via natural language. Requires `AI_NL_COMMAND_EXECUTION_ENABLED=true` in environment config.

**Disabled by default** — enable only after user training. Requires LLM API key.

---

## Demand Forecasting (PROPHET — Local Holt-Winters)

**Model type in UI:** `PROPHET`
**Implementation:** Local statsmodels Holt-Winters exponential smoothing
**External API required:** No

The `PROPHET` forecast model type in the ERP uses a local Python statsmodels implementation — not Meta's Prophet library and not any external AI API. No API key is required for forecasting.

### How It Works

```
Historical sales data
    ↓
Holt-Winters triple exponential smoothing (statsmodels)
    ↓
Forecast lines per SKU per period
    ↓
DemandForecast + DemandForecastLine records stored in DB
    ↓
MRP consumes forecasts for demand-driven planning
```

**Fallback behaviour:** If a product has fewer than the minimum required data points, the model falls back to simple exponential smoothing. If exponential smoothing also fails (e.g. single data point), the system falls back to the historical mean.

### Forecast Quality

| History available | Behaviour |
|---|---|
| 3+ months of sales data | Full Holt-Winters with trend and seasonality |
| 1–2 months | Exponential smoothing fallback (no seasonality decomposition) |
| Single data point | Historical mean fallback |
| No history | No forecast generated |

### Demand Forecast Seed Data (I6)

The system ships with seeded demand forecasts for all 5 products. These use `ForecastModelType.PROPHET` with status `COMPLETED` and period type `MONTHLY`. They feed the seeded MRP run (`MRP-SEED-001`).

### Tests

Holt-Winters forecasting has a test suite in `backend/tests/`. Tests confirm:
- PROPHET model type maps to local statsmodels (no external API calls)
- Fallback to exponential smoothing when insufficient history
- Fallback to mean when exponential smoothing fails
- Forecast lines generated correctly per product

---

## MRP (Material Requirements Planning)

MRP uses demand forecasts to calculate material requirements and generate procurement suggestions.

MRP run `MRP-SEED-001` is seeded with a 90-day planning horizon covering all 5 products. `POVU-HS` has a `shortage_flag = true` indicating projected stock-out within the planning horizon.

See the Supply Chain manual for full MRP reference.

---

## Known Limitations

| Feature | Status |
|---|---|
| AI Chat | LLM_POWERED — requires ANTHROPIC_API_KEY or OPENAI_API_KEY; mock responses without keys |
| Demand forecasting | STATISTICAL — no external API needed; local Holt-Winters; needs 3+ months sales history for full model |
| NL command execution | LLM_POWERED — disabled by default; admin must enable; requires LLM API key |
| Formulation AI | LLM_POWERED — experimental; review all AI suggestions before applying |
| Scenarios | Simulation only — does not affect live data |
| PROPHET enum | Maps to local statsmodels Holt-Winters — not Meta Prophet library; no pip install of prophet required |
