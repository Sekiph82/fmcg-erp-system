# AI and Automation

**URL:** `/dashboard/ai`  
**Module:** AI  
**Permission:** `ai.view`

---

## Screenshot

> Screenshot pending: AI workspace — Chat tab

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

## AI Copilot (Chat)

Ask questions in plain English:
- "What is the current stock of flour?"
- "Show me this week's production orders"
- "Which customers are overdue on invoices?"

AI translates to ERP queries and returns results. Responses are labelled as AI-generated.

**Important:** AI runs in mock mode if no API key is configured. Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in the production environment to enable real AI.

---

## Natural Language Commands

The NL Command tab allows admin-enabled users to run ERP operations via natural language. Requires `AI_NL_COMMAND_EXECUTION_ENABLED=true` in environment config.

**Disabled by default** — enable only after user training.

---

## Demand Forecasting

Predictions tab uses historical sales data and ML to forecast:
- Demand by SKU and region
- Production plan suggestions
- Stock level recommendations

Requires at least 3 months of sales history for meaningful predictions.

---

## Known Limitations

| Feature | Status |
|---|---|
| AI Chat | Requires ANTHROPIC_API_KEY or OPENAI_API_KEY; mock mode without keys |
| Demand forecasting | Requires 3+ months sales history |
| NL command execution | Disabled by default; admin must enable |
| Formulation AI | Experimental — review all AI suggestions before applying |
| Scenarios | Simulation only — does not affect live data |
