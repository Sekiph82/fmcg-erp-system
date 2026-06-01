# TASKS

## Tracking Policy

- TASKS.md is the **only active in-repo task tracker**.
- PLANS.md is kept as architecture/strategic reference (not a task tracker).
- CODEX_PROGRESS.md is superseded by this file and deleted after merge.
- TODO files, roadmap/progress/status files are not used anymore.
- External Graphify files are architecture/reference files only — not task trackers.
- Every completed task must update this file.
- Every relevant completed task must also update `C:\Users\sekip\Desktop\graphify-erp-maps\GRAPHIFY_UPDATE_LOG.md`.
- No new tracking files inside the repo.
- Graphify is for architecture mapping, risk detection, and post-change refresh decisions — not a replacement for TASKS.md.

---

## What Graphify Is Used For

Graphify helps us:
- Understand ERP architecture before risky edits
- Identify high-coupling files and god nodes
- Decide whether backend/frontend/docs/scripts maps need refresh after a task
- Prevent editing dangerous areas without audit
- Reduce repeated discovery work

Graphify must NOT:
- Become another task tracker
- Create repo-local permanent outputs (graphify-out/ must NOT be committed)
- Be run as a background service
- Run full repo automatically
- Create hooks, scheduled tasks, daemons, or watchers

**Note:** `graphify-out/` is currently tracked by git (132 files). See TASK-010.

---

## Task Tracking Template

```
### Task ID: TASK-XXX — Task Title

- **Status:** Pending / In Progress / Done / Blocked / Superseded
- **Priority:** P0 / P1 / P2 / P3
- **Category:** UI / GS1 / Product Master / Utilities / Production / Inventory / Finance / AI / Integration / Docs / QA / Cleanup / Security / Deployment
- **Why it matters:**
- **Source / evidence:**
- **Affected area:**
- **Risk:** Low / Medium / High
- **Recommended timing:** Now / Next / Later
- **Needs audit before implementation:** Yes / No
- **Implementation scope:**
- **Do not touch:**
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Created files:** None yet
- **Deleted files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** None yet
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend / frontend / docs / scripts / no
- **Graphify refresh status:** Not needed / Needed / Pending approval / Done
- **Graphify output location if refreshed:** None
- **Notes:**
```

Rules:
1. Every planned task uses this format.
2. When a task completes, update its card — do not create a new file.
3. List exact file paths changed, created, and deleted.
4. List exact test commands and pass/fail results.
5. If Graphify refresh is needed, mark it and ask user before running.
6. TASKS.md is the single source of truth for task status.
7. GRAPHIFY_UPDATE_LOG.md is only for Graphify architecture map refresh history.

---

## Current Priority Queue

---

### Task ID: TASK-001 — Login page POVU logo size

- **Status:** Done
- **Priority:** P0
- **Category:** UI
- **Why it matters:** POVU logo appears too small on the login page.
- **Source / evidence:** User visual review.
- **Affected area:** `frontend/src/app/login/page.tsx`
- **Risk:** Low
- **Recommended timing:** Now
- **Needs audit before implementation:** No
- **Implementation scope:** Logo already exists at `width={64} height={64}` (line 43-44). Increase to user-preferred size (e.g. 96px or 128px).
- **Do not touch:** Auth logic, backend, routing, global layout, other pages
- **Started at:** 2026-05-31
- **Completed at:** 2026-05-31
- **Changed files:**
  - `frontend/src/app/login/page.tsx` (width/height 64 → 128)
  - `TASKS.md` (this card updated)
- **Created files:** None
- **Deleted files:** None
- **Tests / checks run:**
  - `npx tsc --noEmit` → PASS (exit 0)
  - `npm run build` → PASS (exit 0, /login 3.79 kB)
- **Result:** Login page POVU logo increased from 64×64 to 128×128
- **Known limitations:** None
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Graphify output location if refreshed:** None
- **Notes:** Visual-only change. No auth/backend/routing/layout changes. Single line pair changed.

---

### Task ID: TASK-002 — Enable AI live mode

- **Status:** Blocked — waiting for real API key (env examples updated; no backend code change needed)
- **Priority:** P0
- **Category:** AI / Integration
- **Why it matters:** `AI_PROVIDER=auto` with no keys → MockProvider. All AI features (predictions, formulations, recommendations, chat) return canned demo responses. Not acceptable for production.
- **Source / evidence:** `backend/app/core/config.py:123` `AI_PROVIDER: str = "auto"`. `backend/app/services/ai_provider.py:421` "No AI API key found — using mock provider". `.env.development.example` and `.env.production.example` both have all three keys empty.
- **Affected area:** `.env.development` or `.env.production` (actual live env file — NOT the examples)
- **Risk:** Low (config-only change; API key in env only, never committed)
- **Recommended timing:** Now (production blocker)
- **Needs audit before implementation:** No — backend is production-ready. Only real API key needed.
- **Implementation scope:**
  - Backend already supports Anthropic (Claude), OpenAI (GPT-4o), Google Gemini, and Mock.
  - `AI_PROVIDER=auto` auto-selects whichever key is present (Anthropic → OpenAI → Gemini → Mock).
  - `AIModeBanner` frontend component already shows amber "MOCK MODE" or green "LIVE AI MODE" banner.
  - High-risk AI guards (`ai_modes.py` LLM_POWERED tier) already enforce backend permissions + audit logging.
  - **No source code changes needed.** Task is 100% configuration.
  - To enable: add one real key to `.env.development` (dev) or `.env.production` (prod) and restart backend.
- **Do not touch:** `ai_provider.py`, `ai_modes.py`, `ai_service.py`, frontend AI pages, `AIModeBanner.tsx`
- **Started at:** 2026-05-31 (audit)
- **Completed at:**
- **Changed files:**
  - `.env.development.example` (added AI section comment — no values changed)
  - `.env.production.example` (added AI section comment — no values changed)
  - `TASKS.md` (this card)
- **Created files:** None
- **Deleted files:** None
- **Tests / checks run:**
  - Read `backend/app/core/config.py` — AI config confirmed at lines 120-180
  - Read `backend/app/services/ai_provider.py` — full Anthropic/OpenAI/Gemini/Mock factory confirmed
  - Read `backend/app/core/ai_modes.py` — mode classification confirmed (LLM_POWERED, RULE_BASED, STATISTICAL, HYBRID)
  - Read `frontend/src/components/ai/AIModeBanner.tsx` — mock/live banner confirmed
  - Read all three env example files — no keys set
- **Result:** Blocked — backend ready, env examples clarified, real API key required before status can be Done
- **Known limitations:** Cannot be Done until user provides real API key. Key must NOT be committed to git.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Notes:**
  - **How to enable live AI (single step):** In `.env.development` or `.env.production`, set one of:
    - `ANTHROPIC_API_KEY=sk-ant-...` (recommended — model already set to `claude-sonnet-4-6`)
    - `OPENAI_API_KEY=sk-...` (model: `gpt-4o`)
    - `GEMINI_API_KEY=...` (model: `gemini-1.5-pro`)
  - Then restart backend (`docker compose restart backend` or equivalent).
  - `AI_PROVIDER=auto` does NOT need to change — it auto-detects the key.
  - After restart, `AIModeBanner` turns green ("LIVE AI MODE") automatically.
  - LLM_POWERED features affected: predictions, recommendations, scenarios, formulations, copilot chat.
  - RULE_BASED and STATISTICAL modules (procurement, production, payroll, etc.) are unaffected — they never call LLM.

---

### Task ID: TASK-003 — Wire M-Pesa production credentials

- **Status:** Blocked — waiting for Safaricom Daraja credentials (backend production-ready; env examples updated)
- **Priority:** P0
- **Category:** Integration
- **Why it matters:** No real payments possible until Safaricom credentials are configured. Both services fall back to simulation mode when credentials are absent.
- **Source / evidence:**
  - `backend/app/services/mpesa_daraja_service.py` — **production-ready** full Daraja implementation: OAuth2 token, STK Push, status query, callback handling, retry (max 3), duplicate prevention (409), integration logging. Falls back to simulation if `MPESA_CONFIGURED` is false.
  - `backend/app/services/mpesa_service.py` — **placeholder** (older, used by sales module SalesOrder model). `_stk_push_request()` returns fake `ws_CO_PLACEHOLDER_*` IDs. Needs separate attention (TASK-003b — see notes).
  - `backend/app/core/config.py:100-118` — `MPESA_CONFIGURED` property = `bool(CONSUMER_KEY and CONSUMER_SECRET and SHORTCODE and PASSKEY)`.
  - `backend/app/core/integration_capabilities.py:39-56` — status `SANDBOX_READY`, `production_execution_allowed=True`.
  - `docs/planning/GAP-006_REAL_INTEGRATIONS_AUDIT.md` — does NOT exist.
  - `.env.development.example` + `.env.production.example` — M-Pesa section was entirely absent; now added.
- **Affected area:** `.env.development` or `.env.production` (actual live env — NOT the examples)
- **Risk:** Medium (payment integration; Safaricom sandbox testing required before production)
- **Recommended timing:** Now (production blocker)
- **Needs audit before implementation:** No — backend is production-ready. Only real credentials needed.
- **Implementation scope:**
  - `mpesa_daraja_service.py` is ready — no code changes needed.
  - `mpesa_service.py` (sales module) still uses a placeholder `_stk_push_request()`. This is a separate concern — see Notes below.
  - To enable live M-Pesa: set all 5 env vars in `.env.production` (or `.env.development` for sandbox testing) and restart backend.
- **Do not touch:** `mpesa_daraja_service.py` source (already production-ready), payment models, migrations
- **Started at:** 2026-05-31 (audit)
- **Completed at:**
- **Changed files:**
  - `.env.development.example` (added M-Pesa section)
  - `.env.production.example` (added M-Pesa section)
  - `TASKS.md` (this card)
- **Created files:** None
- **Deleted files:** None
- **Tests / checks run:**
  - Read `backend/app/services/mpesa_daraja_service.py` — full Daraja implementation confirmed
  - Read `backend/app/services/mpesa_service.py` — placeholder confirmed (sales module only)
  - Read `backend/app/core/config.py:100-118` — `MPESA_CONFIGURED` property confirmed
  - Read `backend/app/core/integration_capabilities.py:39-56` — `SANDBOX_READY` status confirmed
  - Checked env examples — M-Pesa section was absent (now added)
  - No source code modified
- **Result:** Blocked — backend ready for `mpesa_daraja_service.py`; credentials required for live payments
- **Known limitations:** Real credentials must NOT be committed to git. `mpesa_service.py` (sales module) still uses placeholder — needs separate wiring to Daraja (see Notes).
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no (config-only change; no new graph edges)
- **Graphify refresh status:** Not needed
- **Notes:**
  - **Sales module placeholder wiring — 2026-05-31 — Done:**
    - `mpesa_service._stk_push_request()` was replaced with delegation to `mpesa_daraja_service._stk_push_request()`.
    - `ws_CO_PLACEHOLDER_*` fake IDs eliminated. Now uses `ws_CO_SIM_*` (Daraja simulation) when uncredentialed, or real Daraja ID when credentials set.
    - No model changes, no migrations, no endpoint changes, no frontend changes.
    - Changed: `backend/app/services/mpesa_service.py`
    - Created: `backend/tests/test_mpesa_service_delegation.py`
    - Tests: `pytest tests/test_mpesa_service_delegation.py tests/test_gap006_integration_capabilities.py` → **10/10 PASS**
    - `python -c "import app.main"` → **IMPORT OK** (warnings are pre-existing, unrelated to this change)
    - Graphify refresh: backend — recommended after credential wiring; not running now.
    - Known: `moto_sales_service.py:initiate_stk_push()` placeholder wired in the follow-on sub-task below.
  - **Van/Moto Sales M-Pesa service wiring — 2026-05-31 — Done:**
    - `moto_sales_service.initiate_stk_push()` was replaced with delegation to `mpesa_daraja_service._stk_push_request()`.
    - Independent fake `ws_CO_<timestamp><random>` + `MS-<random>` IDs eliminated. Now uses Daraja simulation pair (`ws_CO_SIM_*`, `SIM_*`) when uncredentialed, or real Daraja IDs when credentials set.
    - Both `checkout_request_id` and `merchant_request_id` now sourced from the shared Daraja service (VanMpesaPayment stores both).
    - No model changes, no migrations, no endpoint changes, no frontend changes.
    - Changed: `backend/app/services/moto_sales_service.py`
    - Created: `backend/tests/test_moto_sales_mpesa_delegation.py`
    - Tests: `pytest tests/test_moto_sales_mpesa_delegation.py tests/test_mpesa_service_delegation.py tests/test_gap006_integration_capabilities.py` → **13/13 PASS**
    - `python -c "import app.main"` → **IMPORT OK**
    - Warnings: `utcnow()` deprecation and SQLAlchemy relationship overlap — both pre-existing, unrelated to this change.
    - Graphify refresh: backend — recommended after credential wiring; not running now.
    - All three M-Pesa service paths (integrations, sales, van/moto sales) now share the same Daraja service for STK Push.
  - **Backend import warning cleanup — 2026-05-31 — Done:**
    - Fixed two pre-existing backend warnings found during M-Pesa test run.
    - Warning 1 — SQLAlchemy `SAWarning: relationship 'TaskDependency.task' overlaps`: added `back_populates="task"` / `back_populates="dependencies"` to both sides of `ProjectTask.dependencies` ↔ `TaskDependency.task` in `backend/app/models/project.py`.
    - Warning 2 — `DeprecationWarning: datetime.utcnow()` (Python 3.12): replaced all 6 occurrences with `datetime.now(timezone.utc)` in `backend/app/services/moto_sales_service.py`; added `timezone` to the datetime import.
    - No model/schema/migration changes, no payment behavior changes.
    - Changed: `backend/app/models/project.py`, `backend/app/services/moto_sales_service.py`
    - Verification: `python -W all -c "import app.main"` → **IMPORT OK**, `SAWarning` for `TaskDependency` GONE (only pre-existing FastAPIDeprecationWarning for `allergen.py` regex remains — out of scope)
    - Tests: `pytest tests/test_moto_sales_mpesa_delegation.py tests/test_mpesa_service_delegation.py tests/test_gap006_integration_capabilities.py` → **13/13 PASS**
    - Graphify refresh: no (structural fix only; no new edges)
  - **Required credentials from Safaricom Daraja portal:**
    - `MPESA_CONSUMER_KEY` — Daraja app consumer key
    - `MPESA_CONSUMER_SECRET` — Daraja app consumer secret
    - `MPESA_SHORTCODE` — Paybill or Till number
    - `MPESA_PASSKEY` — STK Push online passkey
    - `MPESA_CALLBACK_URL` — public HTTPS URL, e.g. `https://yourdomain.com/api/v1/integrations/mpesa/callback`
    - `MPESA_ENV=sandbox` (testing) or `MPESA_ENV=production` (live)
  - **How to enable:**
    1. Register at https://developer.safaricom.co.ke (sandbox) or https://daraja.safaricom.co.ke (production)
    2. Create a Daraja app, get Consumer Key + Secret + Passkey
    3. Set all 6 vars in `.env.production` (never commit)
    4. Restart backend — `MPESA_CONFIGURED` becomes True automatically
    5. `mpesa_daraja_service.py` switches from simulation to real Daraja calls
  - **Technical debt (separate task):** `mpesa_service.py` (used by `SalesOrder` via sales module) has its own placeholder `_stk_push_request()` that is NOT wired to `mpesa_daraja_service.py`. When credentials are available, `mpesa_service.py:35-48` also needs its placeholder replaced with a real Daraja call. This is a low-risk backend change (single function, ~10 lines) but should be done as a follow-on task — do NOT block credential wiring on it.

---

### Task ID: TASK-004 — Wire WhatsApp production config

- **Status:** Blocked — implementation done, waiting for Meta credentials/live test
- **Priority:** P0
- **Category:** Integration
- **Why it matters:** `WhatsAppConfig.is_demo_mode = True` by default — all messages are simulated, nothing is sent to customers. Setting `is_demo_mode=False` currently saves to DB with QUEUED status but never actually calls Meta Cloud API.
- **Source / evidence:**
  - `backend/app/models/whatsapp.py:47` — `is_demo_mode = Column(Boolean, default=True)`
  - `backend/app/api/v1/endpoints/whatsapp.py:89-110` — `send_text`: when `is_demo_mode=False`, sets `status=QUEUED`, `external_id=None` — but no HTTP call to Meta Cloud API
  - `backend/app/api/v1/endpoints/whatsapp.py:132-155` — `send_template`: same gap
  - `backend/app/models/whatsapp.py:43` — `api_token` field exists in DB model but is NEVER READ in the send flow
  - `backend/app/core/integration_capabilities.py:87-93` — `SIMULATED_ONLY`, `production_execution_allowed` not set (defaults False), `live_env_vars=()` (empty — by design: credentials in DB not env)
  - No WhatsApp env vars in `backend/app/core/config.py` — confirmed by search. Architecture is DB-stored credentials (multi-account design).
  - `.env.development.example` / `.env.production.example` — no WhatsApp section (correct — no env vars needed by design)
  - `frontend/src/app/dashboard/whatsapp/page.tsx` — full UI exists: conversations, templates, config tab, send modal. Hardcodes `is_demo_mode: true` on new config creation (line 119). No PATCH endpoint used.
  - `frontend/src/lib/whatsapp.ts` — `waApi` lib has no `updateConfig` or `setLiveMode` function.
  - Webhook verification (`GET /webhook`) reads `webhook_verify_token` from DB — works correctly.
  - Inbound webhook processing (`POST /webhook`) parses Meta Cloud API `entry[].changes[].value` format — works correctly.
  - No app-secret HMAC signature validation on `POST /webhook` — security gap (secondary).
- **Affected area:**
  - `backend/app/api/v1/endpoints/whatsapp.py` (send_text, send_template — add Meta API call; add PATCH /configs/{id})
  - `backend/app/core/integration_capabilities.py` (update status after implementation)
  - `frontend/src/lib/whatsapp.ts` (add `updateConfig` function after PATCH endpoint exists)
  - `frontend/src/app/dashboard/whatsapp/page.tsx` (add toggle for live mode in config tab)
- **Risk:** Medium (customer-facing messaging; Meta template approvals required; no env vars → low credential-leak risk)
- **Recommended timing:** Now
- **Needs audit before implementation:** Audit complete. See notes.
- **Implementation scope:**
  - **NOT config-only — code required.**
  - **No env vars needed** — architecture uses DB-stored credentials (multi-account). No .env changes.
  - **No migrations needed** — all columns (`api_token`, `business_phone_id`, `webhook_verify_token`, `is_demo_mode`) already exist.
  - **No schema changes** — existing model covers all required fields.
  - **Code changes required (smallest possible):**
    1. `whatsapp.py:send_text` — add `httpx` call to `https://graph.facebook.com/v19.0/{config.business_phone_id}/messages` when `not config.is_demo_mode` (~20 lines)
    2. `whatsapp.py:send_template` — same pattern (~20 lines)
    3. `whatsapp.py` — add `PATCH /configs/{id}` endpoint to update `is_demo_mode`, `api_token`, `business_phone_id`, `webhook_verify_token` (~20 lines)
    4. `integration_capabilities.py` — update status from `SIMULATED_ONLY` to `SANDBOX_READY` once code is done (~3 lines)
    5. `whatsapp.ts` / `page.tsx` — add `updateConfig` API call + live-mode toggle UI in Config tab (~20 lines total)
  - Total estimated: ~80 lines across 4 files. No migrations, no schema changes, no new files.
- **Do not touch:** `WhatsAppMessage`, `WhatsAppTemplate` models; message log; notification system; messaging.py (internal team chat — unrelated)
- **Started at:** 2026-05-31 (audit) / 2026-05-31 (implementation)
- **Completed at:** Blocked on Meta credentials
- **Changed files:**
  - `backend/app/api/v1/endpoints/whatsapp.py` (added `_meta_send_text`, `_meta_send_template` helpers; updated `send_text`, `send_template`; added `PATCH /configs/{id}`)
  - `backend/app/schemas/whatsapp.py` (added `WAConfigUpdate` schema)
  - `backend/app/core/integration_capabilities.py` (updated WhatsApp status `SIMULATED_ONLY` → `SANDBOX_READY`, set `production_execution_allowed=True`)
  - `frontend/src/lib/whatsapp.ts` (added `WAConfigUpdate` type, added `updateConfig(id, data)` method)
  - `frontend/src/app/dashboard/whatsapp/page.tsx` (added Edit button in Config tab, edit modal with credential fields + live/demo toggle)
  - `TASKS.md` (this card)
- **Created files:**
  - `backend/tests/test_whatsapp_live_send.py` (6 tests for live send helpers)
- **Deleted files:** None
- **Tests / checks run:**
  - `python -W all -c "import app.main"` → **IMPORT OK** (all warnings pre-existing, none from WhatsApp changes)
  - `pytest tests/test_whatsapp_live_send.py -v` → **6/6 PASS**
  - `npx tsc --noEmit` → **CLEAN** (exit 0)
- **Result:** Live send code complete. Meta Cloud API will be called when `is_demo_mode=False`. Blocked on Meta Business Manager account + credentials.
- **Known limitations:**
  - Meta Business Manager account required
  - WhatsApp Business Account required
  - Phone Number ID required (from Meta developer portal)
  - Permanent System User access token with `whatsapp_business_messaging` permission required
  - Public HTTPS webhook URL required, configured in Meta webhook settings
  - `messages` webhook subscription required in Meta
  - Approved message templates required for `send_template` to succeed in live mode (Meta approval 24-48h)
  - Live send / webhook flow not tested — blocked on real Meta credentials
  - `POST /webhook` HMAC app-secret signature validation not implemented — future hardening
  - `api_token` stored as DB plaintext — model comment notes encryption as future hardening
- **Git commit / branch:** Not committed yet (awaiting user approval)
- **Graphify refresh after implementation:** backend + frontend
- **Graphify refresh status:** Pending user approval — do not run now
- **Next action:** Configure Meta credentials in WhatsApp Config UI (Config tab → Edit → enter Phone Number ID, Access Token, Verify Token, toggle Live mode) and run live sandbox/production test when Meta account is ready.
- **Notes:**
  - **Architecture decision:** WhatsApp credentials are DB-stored per config row, NOT env vars. This supports multiple WA accounts (e.g. Sales team number + Support number). No `.env` changes needed.
  - **Meta credentials to enter via `POST /api/v1/whatsapp/configs` (once PATCH endpoint exists, via PATCH):**
    - `business_phone_id` — Meta Phone Number ID (from Meta developer portal → App → WhatsApp → API Setup)
    - `business_phone_no` — actual phone number in E.164, e.g. `+254700000000`
    - `api_token` — Meta Cloud API permanent access token (System User Token recommended; NOT a short-lived user token)
    - `webhook_verify_token` — any secret string you choose; must match the "Verify token" field in Meta webhook configuration
    - `provider="META"`
    - `is_demo_mode=False` — requires PATCH endpoint (gap #3 above)
  - **Meta setup steps before going live:**
    1. Create Meta Business Manager account at business.facebook.com
    2. Create a WhatsApp Business Account (WABA) and add a phone number
    3. From Meta developer portal → Your App → WhatsApp → API Setup: get Phone Number ID + temporary access token
    4. Create a System User (recommended) and generate a permanent access token with `whatsapp_business_messaging` permission
    5. Under Webhooks: set URL to `https://yourdomain.com/api/v1/whatsapp/webhook`, set Verify Token = value you'll store in `WhatsAppConfig.webhook_verify_token`
    6. Subscribe to `messages` webhook field
    7. Submit message templates for Meta approval (UTILITY templates approve fastest — 24-48h)
  - **WhatsApp API version:** Meta Cloud API v19.0 (or current stable). Not an env var — should be a constant in the endpoint implementation.
  - **No env vars needed:** confirmed by architecture. Env examples do NOT need a WhatsApp section.

---

### Task ID: TASK-005 — eTIMS live integration (KRA Kenya)

- **Status:** Blocked — connector-ready skeleton implemented, waiting for KRA-approved provider / VSCU-OSCU middleware decision and sandbox credentials
- **Priority:** P0
- **Category:** Integration / Deployment
- **Why it matters:** Kenya VAT-registered businesses are legally required to submit invoices to KRA eTIMS. Track A (`tax_regulatory.py`) is the active integration path wired to the frontend at `/dashboard/finance/etims`.
- **Source / evidence:** `backend/app/api/v1/endpoints/tax_regulatory.py` (submit_etims), `backend/app/services/etims_connector.py` (new), `backend/app/core/config.py` (ETIMS_* vars), `backend/app/core/integration_capabilities.py` (ETIMS capability entry).
- **Affected area:** `backend/app/api/v1/endpoints/tax_regulatory.py`, `backend/app/services/etims_connector.py`, `backend/app/core/config.py`, `backend/app/core/integration_capabilities.py`, `.env.development.example`, `.env.production.example`
- **Risk:** High (legal compliance requirement; incorrect submissions can trigger KRA audit)
- **Recommended timing:** Now (legal requirement before go-live) — unblocked once provider is confirmed
- **Do not touch:** Invoice model, payroll model, Track B (`payroll_ke.py`), other tax logic
- **Started at:** 2026-05-31
- **Completed at:** (blocked — implementation skeleton done, not production-ready)
- **Changed files:**
  - `backend/app/services/etims_connector.py` (NEW — connector layer)
  - `backend/app/api/v1/endpoints/tax_regulatory.py` (submit_etims updated)
  - `backend/app/core/config.py` (ETIMS_* vars added)
  - `backend/app/core/integration_capabilities.py` (ETIMS entry added)
  - `.env.development.example` (eTIMS section added)
  - `.env.production.example` (eTIMS section added)
  - `backend/tests/test_etims_skeleton.py` (NEW — 6 tests)
- **Tests / checks run:** `pytest tests/test_etims_skeleton.py` — 6/6 PASSED. `python -c "import app.main"` — CLEAN.
- **Result:** Connector-ready skeleton implemented; live provider validation pending.
- **What IS implemented:**
  - ERP-side invoice payload builder (`build_etims_payload`) — loads header + lines + customer
  - Connector/adapter abstraction (`ETIMSConnector` Protocol, `ETIMSResult` dataclass)
  - `SimulationETIMSConnector` — preserves existing demo behavior (fake TIMS serial, hash, QR data, ACCEPTED status)
  - `HttpETIMSConnector` skeleton — httpx call, normalized response mapping; activated by ETIMS_PROVIDER=http
  - `get_etims_connector(settings)` factory — routes to simulation or HTTP based on config
  - ETIMS_* config vars (ETIMS_PROVIDER, ETIMS_API_URL, ETIMS_SALES_SUBMIT_PATH, ETIMS_PIN, ETIMS_BRANCH_ID, ETIMS_DEVICE_SERIAL_NO, ETIMS_ENV)
  - Integration capabilities entry (SANDBOX_READY, production_execution_allowed=False)
- **What is NOT yet implemented (still blocked):**
  - Real provider/middleware decision still pending (direct KRA OSCU/VSCU, certified middleware, or third-party service)
  - KRA sandbox credentials still required (ETIMS_PIN, ETIMS_BRANCH_ID, ETIMS_DEVICE_SERIAL_NO, ETIMS_API_URL)
  - Official KRA/provider API spec still required (endpoint paths, auth scheme, response format)
  - Device registration/initialization (initialize_device) must be validated later
  - Product KRA item classification code mapping still pending (itemCd / taxTyCd not in Product model)
  - Provider-specific auth header not yet added (Bearer token / HMAC / mTLS — provider-dependent)
  - Not marked production-ready — production_execution_allowed=False
- **Track B payroll_ke.py note:** Track B is a duplicate/legacy eTIMS stub (ke_etims_invoices table). Do NOT remove. Keep until Track A connector-ready flow is validated. Later decision: deprecate, redirect to Track A, or remove with migration.
- **Known limitations:** Requires KRA developer registration, sandbox testing, and provider/middleware selection before any live use.
- **Git commit / branch:** Not committed yet (awaiting approval)
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed after implementation
- **Notes:** Do NOT say "KRA production integration complete." Connector-ready eTIMS skeleton implemented; live provider validation pending.

---

### Task ID: TASK-006 — GS1 routes auth guard (38 unprotected endpoints)

- **Status:** Done
- **Priority:** P1
- **Category:** Security
- **Why it matters:** ALL 36 GS1/barcode/label routes in `gs1.py` have zero auth guards. Any unauthenticated HTTP caller can generate barcodes, create print jobs, trigger AI agents, and read all internal GS1/SSCC/pallet data.
- **Source / evidence:**
  - Full manual read of `backend/app/api/v1/endpoints/gs1.py`. Zero occurrences of `get_current_user` or `require_permission` in that file.
  - Graphify `ERP_GRAPHIFY_ACTION_PLAN.md` line 507: `GS1/Label Printing — Recently changed; 38 backend routes; Community 48 (96 nodes) — gs1.py, gs1_service.py, gs1.py`
  - **Discrepancy:** Graphify said 38 routes; current code has 36 routes. Trust current code — 36 routes confirmed by manual read. 2-route difference likely from Graphify snapshot lag.
  - **Community 133 correction:** Original TASK-006 text incorrectly cited "Community 133 finding for GS1 auth". Community 133 in Graphify is about `adminCredentials`/`limitedCredentials` (E2E test fixture — TASK-007 topic). GS1 is in Community 48 (96 nodes). No explicit Graphify finding about "38 unprotected routes" — that was an inference from the route count.
- **Affected area:** `backend/app/api/v1/endpoints/gs1.py` — single file, all 36 routes. Route prefix: `/api/v1/gs1`.
- **Risk:** Medium-High (data integrity; unauthorized barcode generation; unauthorized label printing; unauthorized AI agent triggering)
- **Recommended timing:** Next
- **Needs audit before implementation:** Done.
- **Implementation scope:** Add `_=Depends(require_permission("gs1", "<action>"))` to each route. Permission codes already defined in module_registry: `gs1.view`, `gs1.create`, `gs1.edit`, `gs1.approve`, `gs1.print`, `gs1.report`, `gs1.admin`. One import line needed: `from app.core.deps import require_permission`.
- **Do not touch:** GS1 service logic, barcode generation algorithm, frontend, schemas, DB schema
- **Started at:** 2026-05-31
- **Completed at:** 2026-05-31
- **Changed files:**
  - `backend/app/api/v1/endpoints/gs1.py` (36 guards added, `printed_by` Query removed)
  - `backend/tests/test_gs1_auth.py` (NEW — 10 tests)
  - `TASKS.md`
- **Tests / checks run:** `pytest tests/test_gs1_auth.py tests/test_gap018_gs1_label_printing.py` — **26/26 PASSED**. `python -c "import app.main"` — CLEAN.
- **Result:** 36/36 GS1 routes guarded. `complete_print_job` now uses `current_user.username` (no `Query("system")` spoofing).
- **Known limitations:** 401 tests require TestClient + real auth session (no TestClient infrastructure in this test suite). 403 behaviour tested directly via `require_permission` dep invocation. Happy-path authorized HTTP tests not added — dependency wiring confirmed by route inspection test.
- **Git commit / branch:** Not committed yet (awaiting approval)
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Pending user approval — do not run now

#### Audit — Routes Found: 36 (all unguarded)

| # | Method | Path | Function | Guard | Sensitivity | Recommended Guard |
|---|--------|------|----------|-------|-------------|------------------|
| 1 | GET | /gs1/dashboard | get_dashboard | None | Auth-only | `gs1.view` |
| 2 | POST | /gs1/config | create_company_config | None | Admin | `gs1.admin` |
| 3 | GET | /gs1/config | list_company_configs | None | Auth-only | `gs1.view` |
| 4 | GET | /gs1/config/{cfg_id} | get_company_config | None | Auth-only | `gs1.view` |
| 5 | POST | /gs1/products | create_product_config | None | Permission | `gs1.create` |
| 6 | GET | /gs1/products | list_product_configs | None | Auth-only | `gs1.view` |
| 7 | GET | /gs1/products/{cfg_id} | get_product_config | None | Auth-only | `gs1.view` |
| 8 | PATCH | /gs1/products/{cfg_id} | update_product_config | None | Permission | `gs1.edit` |
| 9 | GET | /gs1/products/by-product/{product_id} | get_config_by_product | None | Auth-only | `gs1.view` |
| 10 | POST | /gs1/barcode/generate | generate_barcode | None | Permission | `gs1.create` |
| 11 | GET | /gs1/barcode | list_barcodes | None | Auth-only | `gs1.view` |
| 12 | GET | /gs1/barcode/{record_id} | get_barcode | None | Auth-only | `gs1.view` |
| 13 | POST | /gs1/scan/decode | decode_gs1 | None | Auth-only | `gs1.view` |
| 14 | GET | /gs1/scan/decode | decode_gs1_get | None | Auth-only | `gs1.view` |
| 15 | POST | /gs1/sscc/generate | generate_sscc | None | Permission | `gs1.create` |
| 16 | GET | /gs1/sscc | list_sscc_pallets | None | Auth-only | `gs1.view` |
| 17 | GET | /gs1/sscc/{sscc_id} | get_sscc_pallet | None | Auth-only | `gs1.view` |
| 18 | POST | /gs1/sscc/{sscc_id}/lots | add_lot_to_sscc | None | Permission | `gs1.create` |
| 19 | PATCH | /gs1/sscc/{sscc_id}/status | update_sscc_status | None | Permission | `gs1.edit` |
| 20 | POST | /gs1/labels/templates | create_template | None | Permission | `gs1.create` |
| 21 | GET | /gs1/labels/templates | list_templates | None | Auth-only | `gs1.view` |
| 22 | GET | /gs1/labels/templates/{tmpl_id} | get_template | None | Auth-only | `gs1.view` |
| 23 | PATCH | /gs1/labels/templates/{tmpl_id} | update_template | None | Permission | `gs1.edit` |
| 24 | POST | /gs1/labels/print | create_print_job | None | Permission | `gs1.print` |
| 25 | GET | /gs1/labels/print | list_print_jobs | None | Auth-only | `gs1.view` |
| 26 | POST | /gs1/labels/print/{job_id}/complete | complete_print_job | None | Permission | `gs1.print` |
| 27 | POST | /gs1/ai/run-label-validator | run_label_validator | None | Admin | `gs1.admin` |
| 28 | POST | /gs1/ai/run-packaging-optimizer | run_packaging_optimizer | None | Admin | `gs1.admin` |
| 29 | GET | /gs1/ai/recommendations | list_recommendations | None | Auth-only | `gs1.view` |
| 30 | PATCH | /gs1/ai/recommendations/{rec_id} | review_recommendation | None | Permission | `gs1.approve` |
| 31 | GET | /gs1/reports/print-history | print_history | None | Auth-only | `gs1.report` |
| 32 | GET | /gs1/reports/sscc-tracking | sscc_tracking | None | Auth-only | `gs1.report` |
| 33 | GET | /gs1/reports/packaging-hierarchy | packaging_hierarchy | None | Auth-only | `gs1.report` |
| 34 | GET | /gs1/reports/barcode-usage | barcode_usage | None | Auth-only | `gs1.report` |
| 35 | POST | /gs1/scan/dispatch-validate | dispatch_validate | None | Auth-only | `gs1.view` |
| 36 | GET | /gs1/gtin/lookup | gtin_lookup | None | Auth-only | `gs1.view` |

**Guard counts:**
- `gs1.view` — 18 routes (includes scan, decode, SSCC reads, barcode reads)
- `gs1.create` — 6 routes
- `gs1.edit` — 3 routes
- `gs1.print` — 2 routes
- `gs1.report` — 4 routes
- `gs1.approve` — 1 route
- `gs1.admin` — 3 routes

**Breaking risk if guards added:** LOW. Frontend dashboard users are already authenticated. Only risk is undocumented external callers polling these endpoints without a session cookie.

#### Auth pattern to use (from `bom.py` and `consumer_complaints.py`)

```python
# Import (add to gs1.py line 8)
from app.core.deps import require_permission

# Usage
_=Depends(require_permission("gs1", "view"))   # GET reads
_=Depends(require_permission("gs1", "create")) # POST writes
_=Depends(require_permission("gs1", "edit"))   # PATCH
_=Depends(require_permission("gs1", "print"))  # print job create/complete
_=Depends(require_permission("gs1", "report")) # GET /reports/*
_=Depends(require_permission("gs1", "approve"))# AI rec review
_=Depends(require_permission("gs1", "admin"))  # config create, AI agent triggers
```

#### Tests needed (to add during implementation)

1. `GET /gs1/dashboard` unauthenticated → 401
2. `POST /gs1/barcode/generate` unauthenticated → 401
3. `POST /gs1/barcode/generate` no `gs1.create` → 403
4. `POST /gs1/labels/print` no `gs1.print` → 403
5. `POST /gs1/ai/run-label-validator` no `gs1.admin` → 403
6. Authorized user with `gs1.print` can create print job → 201

#### Additional fix to note (non-blocking)

`complete_print_job` uses `printed_by: str = Query("system")` — after auth guard added, replace with `current_user.username` (or `.full_name`). Not blocking the auth guard PR but should be done in same commit.

---

### Task ID: TASK-007 — E2E/admin credentials audit + management user env strategy

- **Status:** Done
- **Priority:** P1
- **Category:** Security / QA
- **Why it matters:** Full credential audit completed. Expanded scope from original E2E-only investigation to include management user seed strategy (CEO/CTO/CMO/COO/admin via env vars).

---

#### AUDIT FINDINGS

**A. Hardcoded credentials — classified**

| File | Credential | Category | Risk |
|------|-----------|----------|------|
| `frontend/e2e/auth.setup.ts:47` | `"Admin1234!"` (literal string) | C — E2E test | Low — dev default only; production E2E must set env var |
| `.env.development.example` (tracked) | `INITIAL_ADMIN_PASSWORD=Admin1234!` | D — documented dev default | Low — documented as dev-only in README |
| `.env.development.example` (tracked) | `DEMO_USER_PASSWORD=Demo1234!` | D — documented dev default | Low |
| `README.md` / `docs/*.md` | `Admin1234!` in login tables | E — documentation | Low — clearly labeled dev default |
| `.env` (untracked) | `INITIAL_ADMIN_PASSWORD=Admin1234!` | Local dev config | Not committed |
| `.env.development` (untracked) | `INITIAL_ADMIN_PASSWORD=Admin1234!` | Local dev config | Not committed |
| `backend/tests/fixtures.py:86` | `"ValidPass1"` | C — unit test fixture | Low — no-DB tests only |
| `backend/tests/test_hardening.py:197` | `"StrongerAdmin1!"` | C — hardening test | Low — tests password policy |
| `backend/tests/test_attack_simulation.py` | `"password"`, `"SecureP@ss1!"` | C — policy tests | Low — testing policy validator |

**No production secrets found in tracked files.** `.env` and `.env.development` are untracked (gitignored). `.env.production.example` uses `CHANGE_ME_*` placeholders correctly.

**B. E2E credential architecture — already good**

- `frontend/e2e/helpers/auth.ts` — `credentials()` reads `process.env.E2E_ADMIN_PASSWORD`, `E2E_ADMIN_USERNAME`, `E2E_LIMITED_PASSWORD`, `E2E_LIMITED_USERNAME`, `E2E_PASSWORD`, `E2E_USERNAME`
- Tests skip (`test.skip`) if env vars not set — no silent fallback
- Only exception: `auth.setup.ts:47` fills `"Admin1234!"` directly — not env-driven

**C. Admin seed architecture — already env-driven**

`backend/app/core/config.py` already has:
- `SEED_INITIAL_ADMIN: bool = True`
- `SEED_DEMO_DATA: bool = False`
- `SYNC_INITIAL_ADMIN_PASSWORD: bool = False`
- `INITIAL_ADMIN_USERNAME: str = "admin"`
- `INITIAL_ADMIN_EMAIL: str = "admin@erp.local"`
- `INITIAL_ADMIN_PASSWORD: str = ""`
- `INITIAL_ADMIN_FULL_NAME: str = "System Administrator"`
- `DEMO_USER_PASSWORD: str = ""`
- Production validator: raises if `INITIAL_ADMIN_PASSWORD` empty or starts with `CHANGE_ME`

**D. Existing management roles (already seeded)**

`backend/app/db/seed.py` — `ROLE_DEFINITIONS` already defines: `owner`, `admin`, `ceo`, `coo`, `cfo`, `cto`, `cmo`, `data_manager`, `finance_manager`, `sales_manager`, and 24 more.

**Missing role:** `technical_manager` — not in `ROLE_DEFINITIONS`.

**E. Existing demo user seed (DEMO_USERS — `SEED_DEMO_DATA=true` only)**

Users created only when `SEED_DEMO_DATA=true`: `ceo`, `coo`, `cfo`, `cto`, `cmo`, `mkt_manager`, `data_manager` — all share one password `DEMO_USER_PASSWORD`. Emails: `ceo@erp.com`, etc.

Problem: C-suite users share a single `DEMO_USER_PASSWORD` — no per-user password env var. They use generic `@erp.com` emails. Flagged for production: management users need individual passwords and real org emails.

**F. `must_change_password` — fully supported**

`User.must_change_password` column exists. Auth endpoint exposes it. Seed currently sets `must_change_password=False` for all users. Can be flipped to `True` to force password change on first login.

---

#### PROPOSED ENV VARIABLE STRATEGY

**Scope:** Management users seeded at bootstrap. Per-user passwords. No shared `DEMO_USER_PASSWORD` for production users.

**Config additions needed in `backend/app/core/config.py`:**

```
# ── Management user seed (optional — only seeded if all 3 vars set) ──────────
ERP_SEED_MANAGEMENT_USERS: bool = False

ERP_ADMIN_EMAIL: str = ""
ERP_ADMIN_PASSWORD: str = ""
ERP_ADMIN_FULL_NAME: str = "System Administrator"

ERP_CEO_EMAIL: str = ""
ERP_CEO_PASSWORD: str = ""
ERP_CEO_FULL_NAME: str = "Chief Executive Officer"

ERP_CTO_EMAIL: str = ""
ERP_CTO_PASSWORD: str = ""
ERP_CTO_FULL_NAME: str = "Chief Technology Officer"

ERP_CMO_EMAIL: str = ""
ERP_CMO_PASSWORD: str = ""
ERP_CMO_FULL_NAME: str = "Chief Marketing Officer"

ERP_COO_EMAIL: str = ""
ERP_COO_PASSWORD: str = ""
ERP_COO_FULL_NAME: str = "Chief Operating Officer"

ERP_TECHNICAL_MANAGER_EMAIL: str = ""
ERP_TECHNICAL_MANAGER_PASSWORD: str = ""
ERP_TECHNICAL_MANAGER_FULL_NAME: str = "Technical Manager"

ERP_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN: bool = True
```

**Production rules:**
- Empty password = skip seeding that user (no silent fallback)
- `ERP_SEED_MANAGEMENT_USERS=false` default — explicit opt-in
- Production validator: if `ERP_SEED_MANAGEMENT_USERS=true` and any password is empty or starts with `CHANGE_ME`, raise `ValueError`
- `must_change_password=True` by default for all seeded management users
- `.env.*.example` files: placeholders only (`CHANGE_ME_*` or empty)

**`technical_manager` role:** Must be added to `ROLE_DEFINITIONS` before this user can be seeded. Suggest: inherits from a combination of `cto`-level IT perms + `factory_manager` ops perms.

---

#### IMPLEMENTATION SCOPE

| # | Change | Required |
|---|--------|----------|
| 1 | `frontend/e2e/auth.setup.ts:47` — replace `"Admin1234!"` with `process.env.E2E_PASSWORD \|\| "Admin1234!"` | Yes (P1 security best practice) |
| 2 | `backend/app/core/config.py` — add `ERP_*` management user vars + production validator | Yes |
| 3 | `backend/app/db/seed.py` — add `seed_management_users()` function; add `technical_manager` role to `ROLE_DEFINITIONS` | Yes |
| 4 | `.env.development.example` — add `ERP_*` placeholder vars (keep `Admin1234!` dev default for `INITIAL_ADMIN_PASSWORD` — documented) | Yes |
| 5 | `.env.production.example` — add `ERP_*` `CHANGE_ME_*` placeholders | Yes |
| 6 | Backend tests — test production validator rejects empty management passwords when `ERP_SEED_MANAGEMENT_USERS=true` | Yes |
| 7 | Docs — update `DEPLOYMENT.md` with management user env vars | Yes |

**Graphify refresh after implementation:** backend (seed + config changed)

---

- **Source / evidence:** `frontend/e2e/auth.setup.ts:47`, `backend/app/db/seed.py:15-58` (DEMO_USERS), `backend/app/core/config.py:28-38`, `.env.development.example:24`
- **Affected area:** `frontend/e2e/auth.setup.ts`, `backend/app/core/config.py`, `backend/app/db/seed.py`, `.env.*.example`, `backend/tests/`
- **Risk:** Low (no schema changes; additive seed logic; env-gated)
- **Recommended timing:** Next (before first production deployment)
- **Do not touch:** Existing demo user logic (`SEED_DEMO_DATA`), production `.env` files, real passwords
- **Started at:** 2026-05-31
- **Completed at:** 2026-05-31
- **Changed files:**
  - `frontend/e2e/auth.setup.ts` — `"Admin1234!"` → `process.env.E2E_PASSWORD || "Admin1234!"`
  - `backend/app/core/config.py` — added `ERP_SEED_MANAGEMENT_USERS`, `ERP_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN`, `ERP_ADMIN/CEO/CTO/CMO/COO/CFO_*` vars, production validator for management seed
  - `backend/app/db/seed.py` — added `seed_management_users()` function
  - `backend/app/main.py` — wired `seed_management_users` into lifespan
  - `.env.development.example` — added `ERP_*` placeholder section
  - `.env.production.example` — added `ERP_*` `CHANGE_ME_*` section with production warning
  - `backend/tests/test_hardening.py` — added 7 management seed tests
  - `docs/DEPLOYMENT.md` — added "Management user seed" section
  - `TASKS.md` — this update
- **Tests / checks run:**
  - `pytest tests/test_hardening.py` → **25/25 PASSED**
  - `python -c 'import app.main'` → CLEAN
  - `npx tsc --noEmit` → CLEAN
- **Result:**
  - E2E password is env-driven (`process.env.E2E_PASSWORD || "Admin1234!"`)
  - Management user seed vars added for Admin/CEO/CTO/CMO/COO/CFO
  - No `technical_manager` role — CTO is the technical management role
  - Production validator rejects `CHANGE_ME` passwords when `ERP_SEED_MANAGEMENT_USERS=true`
  - All seed is idempotent (skips existing users by email)
  - `ERP_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN=true` default forces password reset on first login
- **Known limitations:**
  - Real values must be set in `.env.production` or secret manager — no defaults seeded
  - No users created unless `ERP_SEED_MANAGEMENT_USERS=true` and email+password both set
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Pending user approval — do not run automatically
- **Notes:** `technical_manager` role deliberately not created. `ERP_CTO_*` covers technical management. No `ERP_TECHNICAL_MANAGER_*` vars exist.

---

### Task ID: TASK-008 — Run erp-health-audit.py and address findings

- **Status:** Batch A + B.1 + B.2 + C.1 + C.2 + C.3.1 + C.3.2 + D Done — 0 HIGH; 326 MEDIUM; C.3.3/C.3.4/C.4 pending
- **Priority:** P1
- **Category:** QA / Performance
- **Why it matters:** Previous run (2026-05-16): 52 HIGH / 624 MEDIUM. Current run (2026-05-31): **1 HIGH / 499 MEDIUM / 1 INFO** — 51 HIGH fixed by prior work, 125 MEDIUM fixed.

---

#### AUDIT RUN — 2026-05-31

**Command:** `python scripts/erp-health-audit.py`
**Output:** `docs/AUTOMATED_HEALTH_AUDIT.md`
**Script:** read-only, no DB required, no network

| Severity | Count | Category breakdown |
|----------|-------|--------------------|
| HIGH | 1 | `token_storage` ×1 |
| MEDIUM | 499 | `unbounded_query` ×469, `row_lock` ×30 |
| LOW | 0 | — |
| INFO | 1 | `env_files` ×1 |

---

#### HIGH FINDING

| # | Category | File | Line | Finding | False positive? | Fix scope |
|---|----------|------|------|---------|----------------|-----------|
| 1 | `token_storage` | `frontend/src/app/dashboard/qms/inspections/page.tsx` | 42 | `localStorage.getItem("access_token")` — raw fetch with Bearer token instead of `apiClient` (HttpOnly cookie) | No — real issue | Single file (replace fetch with `apiClient.get`) |

**Stale/solved by prior work:** None — this finding is new/remaining.

**INFO finding:**
- `env_files`: `.env.production` missing — expected (not committed by design). False positive / intentional.

---

#### MEDIUM FINDING GROUPS

**Group 1 — `unbounded_query` in `services/` (358 findings)**
Nature: internal service functions loading full related-entity lists for computation (BOM costing, appraisals, training cycles, payroll, shelf-life). Many are legitimately unbounded by business logic (e.g., BOM costing needs all materials). Risk: performance under large data — not security.

Top files: `dimensions_service.py` ×16, `recall_service.py` ×13, `procurement_suggestion_service.py` ×13, `training_service.py` ×12, `appraisals_service.py` ×12, `ess_service.py` ×11.

**Group 2 — `unbounded_query` in `endpoints/` (111 findings)**
Nature: user-facing API endpoints returning all rows without pagination. Higher priority than Group 1.

Top files: `finance.py` ×10, `procurement.py` ×7, `marketing.py` ×6, `wms.py` ×5, `payroll_ke.py` ×5, `hr.py` ×5, `documents.py` ×5.

**Group 3 — `row_lock` in services (30 findings, 11 files)**
Nature: `with_for_update()` on stock/inventory/sales mutations. These are correct for concurrency safety (prevent double-allocation). Audit flags them for review but they are intentional patterns. Low priority.

Top files: `sales_service.py` ×6, `wms_service.py` ×5, `inventory_service.py` ×4, `maintenance.py` ×4.

---

#### IMPLEMENTATION BATCHES

**Batch A — Immediate HIGH fix (1 change, 1 file)**
- `frontend/src/app/dashboard/qms/inspections/page.tsx:42` — replace raw `fetch` + `localStorage.getItem("access_token")` with `apiClient.get("/api/v1/quality/inspections/", { params })` from `@/lib/api`

**Batch B — Endpoint unbounded queries (medium urgency, 111 findings)**
- Add `.limit()` + pagination to user-facing endpoints that return unbounded lists
- Top priority: `finance.py`, `procurement.py`, `marketing.py`
- Approach: add `skip: int = 0, limit: int = 100` query params pattern already used elsewhere

**Batch B.1 — finance.py audit (AUDIT COMPLETE — 2026-05-31)**

10 findings in `backend/app/api/v1/endpoints/finance.py`. Classification:

| Line | Function | Route | Classification | Action |
|------|----------|-------|---------------|--------|
| 590 | `budget_copy_from` | POST (internal write) | False positive — FK-bounded `budget_id == old.id` | None |
| 728 | `list_fiscal_years` | GET `/accounting/fiscal-years/` | Real unbounded — low risk (~5 rows in practice) | Add limit |
| 758 | `list_period_close_checks` | GET `/accounting/period-close-checks/` | False positive — required `period_id` FK filter | None |
| 806 | `list_recurring_journals` | GET `/accounting/recurring-journals/` | Real unbounded — config table grows | Add limit |
| 902 | `list_posting_rules` | GET `/accounting/posting-rules/` | Real unbounded — optional `source_module` filter | Add limit |
| 942 | `list_inventory_account_mappings` | GET `/accounting/inventory-account-mappings/` | Real unbounded — scales with products | Add limit |
| 1053 | `list_periods` | GET `/accounting/periods/` | Real unbounded — grows 12/year | Add limit |
| 1219 | exchange rates latest | GET `/accounting/exchange-rates/latest/` | False positive — subquery bounded by distinct currencies | None |
| 1450 | `list_sales_invoices` | GET `/accounting/sales-invoices/` | False positive — already has `.limit(limit)` + `Query(100, le=500)` | None |
| 1544 | `list_purchase_invoices` | GET `/accounting/purchase-invoices/` | False positive — already has `.limit(limit)` + `Query(100, le=500)` | None |

**Real unbounded: 5 endpoints** (lines 728, 806, 902, 942, 1053).
**Fix pattern:** add `limit: int = Query(200, le=500)` param + `.limit(limit)` to query.
**False positives: 5** (lines 590, 758, 1219, 1450, 1544) — no changes needed.
**Status: FIXED — 2026-05-31**

**Batch B.1 — finance.py implementation (DONE — 2026-05-31)**

Fixed all 5 real unbounded endpoints in `backend/app/api/v1/endpoints/finance.py`:
- `list_fiscal_years` (line 724) — added `limit: int = Query(200, le=500)` + `.limit(limit)`
- `list_recurring_journals` (line 799) — added `limit: int = Query(200, le=500)` + `.limit(limit)`
- `list_posting_rules` (line 890) — added `limit: int = Query(200, le=500)` + `q.limit(limit)` (preserves `source_module` filter)
- `list_inventory_account_mappings` (line 921) — added `limit: int = Query(200, le=500)` + `q.limit(limit)` (preserves all 4 existing filters)
- `list_periods` (line 1049) — added `limit: int = Query(200, le=500)` + `.limit(limit)`

5 false positives untouched (lines 590, 761, 1231, 1462, 1556 in updated file — all confirmed FPs).

Checks run:
- `python -c "import app.main"` → CLEAN (only pre-existing `allergen.py` FastAPIDeprecationWarning)
- No finance endpoint tests exist
- `python scripts/erp-health-audit.py` → **0 HIGH** / 495 findings (-4 from 499; all 5 real finance.py unbounded cleared; -4 net due to 1-finding offset in regenerated audit doc)

Known limitations:
- No `offset` added — response shape unchanged, no pagination wrapper
- Batch B.2 `procurement.py` (×7 findings) still pending
- Graphify backend refresh not run — will run after full Batch B group complete

**Batch B.2 — Remaining 6 endpoint files (DONE — 2026-05-31)**

Inspected 33 findings across procurement.py, marketing.py, wms.py, payroll_ke.py, hr.py, documents.py.
Classified 22 real + 11 false positives. Fixed all 22.

Fixed functions:
- `procurement.py`: `list_approval_rules`, `list_rfqs`, `list_bpas`, `list_reorder_policies`
- `marketing.py`: `list_segments`, `list_attribution`, `list_stores`, `list_channel_stock`
- `wms.py`: `list_handling_units`, `list_pick_waves`, `list_picking_tasks`, `list_packing_records`, `list_replenishment_tasks`
- `payroll_ke.py`: `list_tax_bands`, `list_statutory_rates`, `list_shif_tiers`
- `hr.py`: `list_shift_templates`, `list_shift_assignments`, `list_leave_balances`, `list_payroll_periods`
- `documents.py`: `list_expiring_documents`, `search_by_tag`

False positives left untouched (11):
- `procurement.py`: `supplier_dashboard` outer (dashboard compute), inner PO/eval loops (FK-bounded)
- `marketing.py`: `list_interactions` (FK path param `cid`), `list_influencer_links` (FK path param `iid`)
- `payroll_ke.py`: `get_run_lines`, `get_run_payslips` (FK path param `run_id`)
- `hr.py`: `export_payroll_period` (FK-bounded + intentional export of all period lines)
- `documents.py`: `list_documents_for_entity` (required entity_type + entity_id), version history (bounded series), `list_tags` (FK path param `doc_id`)

Other endpoint files (not in scope for B.2) — 65 remaining endpoint findings across 37 other endpoint files. Deferred to future batch if needed.

Health audit after B.2: **0 HIGH / 473 findings** (was 495; -22 exactly matching 22 fixes)
No dedicated tests exist for these 6 files. Import check clean.

**Batch C — Service unbounded queries — AUDIT COMPLETE 2026-06-01**

358 service-layer findings across 65 service files. Deep-classified top 5 files (78 findings, 27% of total).

**Top-10 files by count:**

| File | Findings | FP | Real | Notes |
|------|----------|----|------|-------|
| dimensions_service.py | 16 | 13 | 3 | list_allocation_runs, list_reclassifications, list_ai_recs |
| recall_service.py | 13 | 13 | 0 | ALL FK-bounded by `recall_id` — intentional |
| procurement_suggestion_service.py | 13 | 13 | 0 | ALL engine computation (FK-bounded or planning engine) |
| training_service.py | 12 | 7 | 5 | list_sessions, list_assignments, list_certifications, list_feedback, list_ai_recs |
| appraisals_service.py | 12 | 9 | 3 | list_records, list_development_plans, list_ai_recs |
| ess_service.py | 11 | ~5 | ~6 | Employee self-service lists — needs read to confirm |
| sales_service.py | 10 | 10 | 0 | FK-bounded per-order + stock reservation (row_lock nearby) |
| payroll_ke_service.py | 9 | ~7 | ~2 | Mostly statutory tables (small) + payroll computation |
| shelf_life_service.py | 9 | ~9 | 0 | FEFO/expiry monitoring intentionally needs all lots |
| timesheets_service.py | 9 | ~3 | ~6 | List functions grow with headcount × periods |

**Overall estimate (358 findings):**

| Category | Count | Description |
|----------|-------|-------------|
| FP — computation | ~130 | BOM costing, payroll engine, MPS/MRP planning, recall trace, procurement suggestion engine |
| FP — FK-bounded | ~70 | Inner queries bounded by parent ID (recall_id, run_id, order_id) |
| FP — config/small tables | ~25 | Dim types, tax bands, approval rules, skill masters |
| FP — analytics/dashboard | ~20 | Report functions that legitimately need full dataset for aggregation |
| **Real — list functions** | **~70** | List endpoints without effective row cap |
| Chunking candidates | ~25 | Matching algorithms, report execution, shelf-life scan |
| Product decision needed | ~18 | Notifications volume, webhook delivery logs, promotions analytics |

**Sub-batch plan:**

**C.1 — Safe service list-fetch limits (~35 findings, low risk)**
Priority files: training_service.py (5 real), appraisals_service.py (3 real), dimensions_service.py (3 real), ess_service.py (~6), timesheets_service.py (~6), recruitment_service.py (~5), expenses_service.py (~4), notifications_service.py (~3).
Pattern: add `limit: int = 200` param to service function signature + `.limit(limit)` on query.
NOT `Query(200, le=500)` — that is FastAPI endpoint syntax; service-layer uses plain int parameter.

**C.2 — Confirmed FPs (document, no code change)**
- recall_service.py (13): all FK-bounded by `recall_id` — regulatory recall must be complete
- procurement_suggestion_service.py (13): planning engine needs all active materials
- sales_service.py (10): stock reservation with row locks, FK-bounded per order
- shelf_life_service.py (9): FEFO monitoring must see all lots
- payroll_ke_service.py (most): statutory tables + run computation
- All bom_*, mps_*, planning_* services: computation engines

**C.3 — Chunking candidates (defer — needs architecture decision)**
- bank_reconciliation_service.py (6): 3-way match algorithm needs all unmatched items
- invoice_match_service.py (5): invoice matching must see full open set
- report_builder_service.py (4): report execution loads full datasets
- shelf_life_service.py (9): already in C.2 — intentional; chunked scanning is a future enhancement

**C.4 — Product decision needed (defer)**
- webhook_service.py (3): delivery log pagination — what is max retention?
- promotions_service.py (6): analytics or list? Decide before capping.

**Batch C.1 — Safe service list-fetch limits (DONE — 2026-06-01)**

27 functions across 8 service files fixed with `limit: int = 200` + `.limit(limit)`:

| File | Functions fixed |
|------|----------------|
| training_service.py | list_sessions, list_assignments, list_certifications, list_feedback, list_ai_recs |
| appraisals_service.py | list_records, list_development_plans, list_ai_recs |
| dimensions_service.py | list_allocation_runs, list_reclassifications, list_ai_recs |
| notifications_service.py | list_templates, list_schedules, list_ai_recs |
| ess_service.py | list_accounts, list_leave_requests, list_requests, list_ai_recs |
| timesheets_service.py | list_timesheets, list_ai_recs |
| recruitment_service.py | list_postings, list_pipelines, list_interviews, list_offers, list_ai_recs |
| expenses_service.py | list_advances, list_ai_recs |

Checks: `python -c "import ..."` verified all 27 signatures (27/27 passed). Health audit: 473 → 444 MEDIUM (29 resolved).
Pattern: plain Python `limit: int = 200` (NOT FastAPI `Query()` syntax — service layer only).
`list_accounts_raw` (ess_service) skipped — C.3 chunking candidate (used by `broadcast_notification`).

**Status: C.1 DONE. C.2/C.3/C.4 pending.**

**Batch C.2 — Confirmed service-layer false positives (Audited — 2026-06-01)**

354 remaining service-layer findings. Code-verified and classified into 5 FP groups + 2 deferred groups.

**Group A — FK-bounded inner queries (~80 findings)**
These queries are bounded by a parent entity key passed as a parameter. NOT unbounded. Do NOT add `.limit()`.

| File | Functions | Bound |
|------|-----------|-------|
| recall_service.py | contain_recall, list_actions, build_customer_impact | recall_id == param |
| sales_service.py | allocate_so + inner stock queries | so.id (FK per line) |
| timesheets_service.py | add_line, update_line, delete_line, auto_fill_from_attendance | timesheet_id == param |
| bom_costing_service.py | cost_bom inner line fetch | bom_id == param |
| wms_service.py | inner pick/put-away line queries | task_id / header FK |
| notifications_service.py | list_preferences | user_id == param (~8 rows) |
| ess_service.py | get_leave_balances, mark_all_read | employee_id / FK |

**Group B — Computation engines (~70 findings)**
Must process ALL rows to produce correct results. `.limit()` would silently corrupt output.
**CRITICAL: Do NOT add `.limit()` to any of these.**

| File | Functions | Why full scan required |
|------|-----------|----------------------|
| procurement_suggestion_service.py | _engine_logic (× 13) | Must check ALL active materials vs safety stock |
| payroll_ke_service.py | calculate_payroll_run | Must process every active employee |
| bom_costing_service.py | cost_bom recursive lines | Must cost ALL BOM lines or result wrong |
| mps_service.py / mrp_service.py | planning engine queries | MPS/MRP must see full demand/supply picture |
| shop_floor_service.py | AI agent queries | Scheduling must see all open work orders |

**Group C — Regulatory full-scan (~15 findings)**
Must be complete by law or operational necessity (FEFO, recall trace).
**CRITICAL: Do NOT add `.limit()` to any of these.**

| File | Functions | Why |
|------|-----------|-----|
| shelf_life_service.py | list_near_expiry, list_expired, rank_lots_fefo | FEFO must rank ALL lots; expiry scan must be complete |
| recall_service.py | trace overlap with Group A | Full traceability required |
| bom_compliance_service.py | compliance scan | Must check all components |

**Group D — Small config tables (~20 findings)**
Tables with bounded row counts by design (seeded config, reference data).

| File | Functions | Evidence |
|------|-----------|----------|
| appraisals_service.py | list_periods, list_templates | Config — bounded by HR setup |
| training_service.py | list_skills, list_programs | Config — bounded by training catalog |
| payroll_ke_service.py | _get_tax_bands, _get_nhif_tiers | ~5 rows, filtered by tax_year + is_active |
| recruitment_service.py | list_stages | 11 seeded pipeline stages |
| expenses_service.py | list_categories, list_policies | Filtered by active_flag; small config |
| dimensions_service.py | list_dim_types, list_cost_centers, list_validation_rules, list_allocation_rules, list_default_rules | Config reference tables |

**Group E — Analytics / dashboard aggregation (~30 findings)**
Aggregate queries (COUNT, AVG, GROUP BY) or dashboard summaries — not row-returning lists.

| File | Functions |
|------|-----------|
| appraisals_service.py | get_dashboard, report_completion, report_rating_distribution, report_promotions, run_calibration_risk, run_development_plan_agent |
| training_service.py | get_dashboard, report_completion, report_certification_expiry, run_compliance_risk_monitor |
| timesheets_service.py | get_dashboard, report_summary |
| dimensions_service.py | run_ai_agents (×4) |

**Batch C.3 — Chunking candidates (~25 findings, deferred)**
Architecture-level batching required — not a simple `.limit()` fix.
- bank_reconciliation_service.py (6 findings)
- invoice_match_service.py (5 findings)
- report_builder_service.py (4 findings)
- ess_service.py `list_accounts_raw` — used by `broadcast_notification` (must reach ALL active accounts)

**Batch C.4 — Product decisions (~9 findings, deferred)**
Requires product owner decision on retention/capping strategy before any change.
- webhook_service.py (3): delivery log — what is max retention?
- promotions_service.py (6): analytics or list? Decide before capping.

**Recommended C.2 strategy: Option B — narrow `_KNOWN_FP_CONTEXTS` allowlist**
Add targeted suppression entries to `scripts/erp-health-audit.py` `_KNOWN_FP_CONTEXTS` for confirmed FP service files.
- Format: `(os.path.join("services", "filename.py"), re.compile(r"<discriminating_pattern>"))`
- Do NOT suppress entire files. Use discriminating regex matching the FP function context.
- Implementation: pending approval. See `scripts/erp-health-audit.py` lines 1-30.

**EXPLICIT DO-NOT-LIMIT warnings:**
- recall_service.py — recall trace, contain_recall, build_customer_impact
- procurement_suggestion_service.py — _engine_logic, any planning fetch
- shelf_life_service.py — rank_lots_fefo, list_near_expiry, list_expired
- payroll_ke_service.py — calculate_payroll_run
- bom_costing_service.py — cost_bom recursive lines
- mps_service.py / mrp_service.py / shop_floor_service.py — any planning/scheduling engine
- Any function inside a `for` loop that aggregates a full result set

No source code changed during C.2 audit. No `.limit()` added. No suppressions applied yet.

**Batch C.2 — Narrow allowlist implementation (DONE — 2026-06-01)**

Files changed:
- `scripts/erp-health-audit.py` — 19 new `_KNOWN_FP_CONTEXTS` entries added
- `docs/AUTOMATED_HEALTH_AUDIT.md` — regenerated after allowlist applied

Allowlist strategy: Option B (narrow `_KNOWN_FP_CONTEXTS` entries). Each entry uses file-suffix + discriminating regex. No whole-file suppressions. No global suppression.

Confirmed groups suppressed:
- Group A (FK-bounded inner queries): recall_service, sales_service, timesheets_service, bom_costing_service, wms_service, notifications_service, ess_service
- Group B (computation engines): procurement_suggestion_service (13 findings), payroll_ke_service, mps_service, mrp_service, shop_floor_service
- Group C (regulatory full-scan): shelf_life_service, bom_compliance_service
- Group D+E (config tables + analytics): appraisals_service, training_service, recruitment_service, expenses_service, dimensions_service

Confirmed groups NOT suppressed:
- C.3 chunking candidates: bank_reconciliation_service (6), invoice_match_service (5), report_builder_service (4), ess_service.list_accounts_raw (line 663)
- C.4 product-decision items: webhook_service (3), promotions_service (6)
- row_lock findings: 30 (all retained)

Health audit after C.2 implementation:
| Severity | Count |
|----------|-------|
| HIGH | 0 |
| MEDIUM | 340 |
| INFO | 1 |
| **Total** | **341** |

Previous MEDIUM: 444. Suppressed: 104 confirmed service-layer false positives.
No service behavior changed. No `.limit()` added. No ERP business logic touched.

Known limitations:
- 19 allowlist entries must be reviewed when new service functions are added to suppressed files
- Patterns are window-based (8 lines before / 5 lines after scalars().all()) — deep functions may need wider patterns
- C.3/C.4/D batches remain outstanding

**Status: Batch A + B.1 + B.2 + C.1 + C.2 Done — 0 HIGH; confirmed service FPs allowlisted; C.3/C.4/D remain**

**Batch D — row_lock review (informational, 30 findings)**
- Verify each `with_for_update()` is necessary; replace with atomic UPDATE where simpler
- `inventory_service` and `sales_service` are highest priority (stock mutation correctness)

**Batch D — row_lock audit (DONE — 2026-06-01)**

Total findings: 30 across 11 files.

Classification:
- **A — Correct and intentional:** 27 findings
- **B — Atomic UPDATE candidate (later, low urgency):** 3 findings
- **C — Deeper transaction design needed:** 0
- **D — Possibly unnecessary:** 0

**⚠ CRITICAL WARNING: Do NOT remove row locks from stock/inventory/sales/WMS mutation flows without a concurrency test. All Class A locks prevent real data corruption (duplicate rows, negative stock, double-allocation, corrupted sequence numbers).**

**Detailed audit table:**

| File | Line | Function | Locked Entity | Mutation After Lock | Class | Reason | Recommended Action | Risk If Removed |
|------|------|----------|--------------|--------------------|----|--------|-------------------|-|
| `crud/finance.py` | 295 | `upsert_product_cost` | `ProductCost` | Insert or update cost fields (upsert) | A | Upsert: concurrent creates would both see None → duplicate rows | Keep lock | Duplicate ProductCost rows per period |
| `crud/maintenance.py` | 154 | `complete_work_order` | `PMPlan` | Sets `last_completed_date`, `next_due_date` | A | Concurrent WO completions would corrupt plan scheduling dates | Keep lock | Plan next_due_date corrupted by concurrent completions |
| `crud/maintenance.py` | 221 | `create_breakdown` | `Asset` | Sets `asset.status = UNDER_MAINTENANCE` | B | Single-field status set; could be atomic UPDATE later | Keep lock now; atomic UPDATE candidate later | Low — only risk is concurrent breakdown creates racing |
| `crud/maintenance.py` | 246 | `resolve_breakdown` | `Asset` | Sets `asset.status = ACTIVE` only if currently `UNDER_MAINTENANCE` | A | Conditional transition requires read-before-write | Keep lock | Concurrent create/resolve could leave asset in wrong state |
| `crud/maintenance.py` | 325 | `record_spare_usage` | `SparePart` | Decrements `current_stock` | A | Stock counter decrement — concurrent usage records would both read same value → stock goes negative | Keep lock | Spare parts inventory negative or wrong |
| `crud/secondary_sales.py` | 148 | `create_snapshot` | `DistributorInventorySnapshot` | Upsert by (distributor_id, product_id, snapshot_date) | A | Upsert: concurrent uploads for same key would both insert → duplicate snapshot rows | Keep lock | Duplicate distributor snapshots per day |
| `services/inventory_service.py` | 108 | `_get_stock_for_update` | `Stock` | `quantity_on_hand += delta`, recalculate `quantity_available` | A | Core stock quantity mutation — all GRN/issue/transfer/adjust flows go through here | Keep lock | Inventory quantity corruption; negative stock |
| `services/inventory_service.py` | 317 | `adjust_stock` | `Stock` | Reads current qty, computes delta, writes new qty + movement | A | Delta computed from current value — TOCTOU if two adjustments run concurrently | Keep lock | Incorrect adjustment delta; inconsistent movement + stock |
| `services/inventory_service.py` | 371 | `delete_stock_record` | `Stock` | Deletes row after validating `quantity_on_hand == 0` | A | Prevents deletion between zero-check and concurrent receipt | Keep lock | Row deleted while concurrent GRN pushes qty > 0 |
| `services/inventory_service.py` | 444 | reverse/delete movement | `Stock` | Reverses delta; checks new qty ≥ 0 | A | Reversal reads current qty to verify not going negative | Keep lock | Negative stock; or reversal silently applied twice |
| `services/mpesa_service.py` | 120 | `process_callback` (success) | `SalesOrder` | Sets `so.mpesa_reference`, `so.payment_status` | A | M-Pesa callbacks can retry; concurrent callbacks must not both update SO simultaneously | Keep lock | SO payment_status overwritten by concurrent callbacks |
| `services/mpesa_service.py` | 153 | `process_callback` (failure) | `SalesOrder` | Sets `so.payment_status = FAILED` | A | Same function, failure branch — same concurrency concern | Keep lock | Payment status set FAILED on successful callback or vice versa |
| `services/procurement_service.py` | 413 | `post_grn` | `Stock` | `quantity_on_hand += qty`, recalculate `quantity_available` | A | GRN posting receives stock — concurrent postings for same product/warehouse corrupt quantity | Keep lock | Received quantity under-counted |
| `services/procurement_service.py` | 434 | `post_grn` | `POLine` | `received_quantity += qty` | A | Cumulative counter — concurrent GRNs for same PO line would both increment from same base | Keep lock | PO received quantity under-counted; PO may never close |
| `services/production_service.py` | 69 | `_get_material_stock` | `Stock` (MATERIAL) | Material deducted from `quantity_on_hand` before issue | A | Availability check + deduction must be atomic — two concurrent issues both pass check then both deduct | Keep lock | Negative material stock; over-issuance to production |
| `services/production_service.py` | 169 | finished goods receipt | `Stock` (PRODUCT) | `quantity_on_hand += quantity` | A | Concurrent receipts for same product/lot/warehouse corrupt quantity | Keep lock | Finished goods qty under-counted |
| `services/quality_service.py` | 147 | `quarantine_stock` | `Stock` (multiple rows) | `is_blocked = True`, `quantity_available = 0` | A | Must prevent concurrent picking between read and quarantine write | Keep lock | Stock could be picked during quarantine application |
| `services/quality_service.py` | 191 | `release_quarantine` | `Stock` (multiple rows) | `is_blocked = False`, restore `quantity_available` | A | Symmetric with quarantine — prevents concurrent re-quarantine or pick during release | Keep lock | Stock released while concurrent re-quarantine is in progress |
| `services/sales_service.py` | 116 | `allocate_so` | `Stock` | `quantity_reserved += allocation`, `quantity_available -= allocation` | A | **Critical** — prevents double-allocation of same stock to two SOs | Keep lock | Same stock allocated to two orders simultaneously (catastrophic) |
| `services/sales_service.py` | 173 | `_release_so_allocation` | `Stock` | Decrements `quantity_reserved`, restores `quantity_available` | A | Symmetric with allocation — concurrent release + re-allocation race | Keep lock | Over-release or under-release of reservation |
| `services/sales_service.py` | 256 | shipment dispatch | `Stock` | Deducts shipped qty from `quantity_on_hand` | A | Read-validate-deduct must be atomic for correct stock deduction | Keep lock | Stock deducted twice or shipment fails incorrectly |
| `services/sales_service.py` | 301 | `dispatch_so` | `SOLine` | `shipped_quantity += line.quantity` | A | Cumulative counter on shipment dispatch | Keep lock | shipped_quantity under-counted; SO may never reach SHIPPED |
| `services/sales_service.py` | 317 | `dispatch_so` | `SalesOrder` | Transitions `so.status` to SHIPPED or PICKING | A | SO status transition must be serialized to prevent incorrect partial-ship state | Keep lock | SO stuck in wrong status after concurrent dispatch |
| `services/sales_service.py` | 412 | `create_invoice` | `SalesOrder` | Transitions `so.status = INVOICED` if SHIPPED | A | Prevents concurrent invoice creation seeing stale SO status | Keep lock | SO invoiced twice or SO status corrupted |
| `services/utilities_service.py` | 34 | `get_next_number` | `NumberSeries` | `current_number += 1` (sequence counter) | A | **Classic sequence lock** — code comment explicitly states purpose; two concurrent calls would get same sequence number | Keep lock | Duplicate document numbers (PO/SO/GRN/etc.) — compliance failure |
| `services/wms_service.py` | 268 | `assign_stock_to_location` | `Stock` | Sets `stock.location_id` | B | Simple location field update; no quantity mutation; could be atomic UPDATE later | Keep lock now; atomic UPDATE candidate later | Low — concurrent assigns to same stock row race |
| `services/wms_service.py` | 297 | `block_stock` | `Stock` (multiple rows) | `is_blocked = True`, `quantity_reserved/available` updated | A | Must prevent concurrent picking during hold application | Keep lock | Stock picked while WMS hold is being applied |
| `services/wms_service.py` | 343 | `release_stock` | `Stock` (multiple rows) | `is_blocked = False`, restore `quantity_available` | A | Symmetric with block | Keep lock | Stock released while concurrent re-block in progress |
| `services/wms_service.py` | 538 | `approve_stock_count` | `Stock` | `quantity_on_hand += variance` | A | Variance adjustment — concurrent count approvals would both adjust from same base | Keep lock | Stock quantity wrong after concurrent count approvals |
| `services/wms_service.py` | 1052 | `complete_putaway_task` | `Stock` | Sets `stock.location_id` | B | Simple location update; no quantity mutation; could be atomic UPDATE later | Keep lock now; atomic UPDATE candidate later | Low — concurrent putaway tasks for same stock race |

**Recommended implementation plan:**

**D.1 — Document all Class A locks (no code change)**
All 27 Class A findings are correct and intentional. No action needed beyond this audit documentation. The audit script will continue to flag them — these findings should remain visible as a reminder to reviewers that these are load-bearing locks.

**D.2 — Atomic UPDATE candidates (3 findings, low urgency)**
These 3 locks could be replaced with atomic UPDATEs in a future optimization pass:
- `crud/maintenance.py:221` — `UPDATE asset SET status='UNDER_MAINTENANCE' WHERE id=?`
- `services/wms_service.py:268` — `UPDATE stock SET location_id=? WHERE id=?`
- `services/wms_service.py:1052` — `UPDATE stock SET location_id=? WHERE actual_location_id IS DISTINCT FROM ?`

Only pursue D.2 if lock contention on Asset or Stock.location_id is measured as a real bottleneck under load. Do not optimize speculatively.

**D.3 — Deeper transaction design: none required**

**D.4 — Remove unnecessary locks: none — all 30 are justified**

No source code changed during this audit. No `.limit()` added. No `with_for_update()` removed.

**Status: Batch D Audited — row_lock findings classified; 27 intentional / 3 atomic-UPDATE candidates; no code change needed**

**Batch C.3 — Chunking design audit (DONE — 2026-06-01)**

15 flagged findings across 4 files inspected. Finding: most originally-classified C.3 candidates are confirmed false positives (FK-bounded or small config). Only 1 genuine chunking candidate found.

**⚠ WARNING: Do NOT add simple `.limit()` to reconciliation matching, invoice matching (engine functions), or `broadcast_notification`. It would silently drop records or skip employees.**

**C.3 detailed finding classification:**

| File | Line | Function | Real Issue? | Why `.limit()` Unsafe | Design | Action |
|------|------|----------|------------|----------------------|--------|--------|
| `bank_reconciliation_service.py` | 84 | `list_bank_accounts` | No — FP | N/A — few accounts (5-50) | FP → allowlist Group D | Allowlist in C.3.1 |
| `bank_reconciliation_service.py` | 269 | `get_statement_lines` | No — FP | N/A — FK-bounded by `stmt_id` | FP → allowlist Group A | Allowlist in C.3.1 |
| `bank_reconciliation_service.py` | 408 | `run_auto_match` (lines + rules) | No — FP | Lines FK-bounded by `stmt_id`; txns bounded by statement period dates; rules = small config | FP → allowlist Group A + D | Allowlist in C.3.1 |
| `bank_reconciliation_service.py` | 745 | `list_adjustments` | No — FP | N/A — FK-bounded by `stmt_id` | FP → allowlist Group A | Allowlist in C.3.1 |
| `bank_reconciliation_service.py` | 763 | `list_rules` | No — FP | N/A — small reconciliation rules config table | FP → allowlist Group D | Allowlist in C.3.1 |
| `bank_reconciliation_service.py` | 850 | `get_balance_summary` | No — FP | N/A — iterates few active bank accounts | FP → allowlist Group D | Allowlist in C.3.1 |
| `invoice_match_service.py` | 71 | `list_tolerance_rules` | No — FP | N/A — small config, few tolerance rules | FP → allowlist Group D | Allowlist in C.3.1 |
| `invoice_match_service.py` | 95 | `_find_tolerance` | No — FP | N/A — loads same small config to find best match by priority | FP → allowlist Group D | Allowlist in C.3.1 |
| `invoice_match_service.py` | 466 | `_detect_duplicate` | No — FP | N/A — FK-bounded by `supplier_id` + invoice_no/date/amount conditions | FP → allowlist Group A | Allowlist in C.3.1 |
| `invoice_match_service.py` | 607 | `get_duplicate_suspicions` | Mild | Limit truncates audit view — admin must see all unresolved | D — add `.limit(200)` at endpoint only, keep service signature | C.3.4 endpoint guardrail |
| `invoice_match_service.py` | 897 | `list_ai_recs` | Yes — missed C.1 | Safe to limit — missed in C.1 batch | C.1 missed fix — `limit: int = 200` | C.3.2 simple limit |
| `report_builder_service.py` | 357 | `list_reports` | No — FP | N/A — admin report config, bounded by reports created (10-100 typical) | FP → allowlist Group D | Allowlist in C.3.1 |
| `report_builder_service.py` | 514 | `list_schedules` | No — FP | N/A — one schedule per report, small config | FP → allowlist Group D | Allowlist in C.3.1 |
| `report_builder_service.py` | 544 | `list_dashboards` | No — FP | N/A — small admin config | FP → allowlist Group D | Allowlist in C.3.1 |
| `report_builder_service.py` | 662 | `list_ai_recs` | Yes — missed C.1 | Safe to limit — missed in C.1 batch | C.1 missed fix — `limit: int = 200` | C.3.2 simple limit |
| `ess_service.py` | 663 | `list_accounts_raw` → `broadcast_notification` | **Yes — real** | Limit silently skips employees — some won't receive HR announcement | **A — chunked iteration in `broadcast_notification`** | **C.3.3 chunked broadcast** |

**C.3 implementation sub-batches:**

**C.3.1 — Allowlist 11 confirmed FPs (audit script only, no source change)**
Add `_KNOWN_FP_CONTEXTS` entries in `scripts/erp-health-audit.py`:
- `bank_reconciliation_service.py`: pattern `stmt_id\s*==|list_bank_accounts|list_rules|get_balance_summary|BRBankAccount|BRRule`
- `invoice_match_service.py`: pattern `list_tolerance_rules|_find_tolerance|_detect_duplicate|InvoiceMatchTolerance|supplier_id\s*==`
- `report_builder_service.py`: pattern `list_reports|list_schedules|list_dashboards|ReportDefinition|ReportSchedule|ReportDashboard`
Expected result: ~11 fewer MEDIUM findings

**C.3.2 — Two missed C.1 simple limit fixes (low risk, same C.1 pattern)**
- `invoice_match_service.py`: `list_ai_recs` → add `limit: int = 200` param + `.limit(limit)` on query
- `report_builder_service.py`: `list_ai_recs` → add `limit: int = 200` param + `.limit(limit)` on query
Pattern identical to C.1. No response shape change. Can be done in same commit.

**C.3.3 — Broadcast chunking (real change required)**
- `ess_service.broadcast_notification`: refactor to iterate `ESSAccount` in chunks instead of loading all at once
  - Chunk size: 200 employees per batch
  - Cursor key: `ESSAccount.employee_id` (stable UUID, orderable)
  - Pattern: `offset`-based or keyset cursor loop, `db.commit()` per chunk
  - `list_accounts_raw` can be removed or replaced with a chunked generator
  - No API change (endpoint still calls `broadcast_notification`, return count unchanged)
  - Test: broadcast with >200 active accounts; verify all receive notification

**C.3.4 — Endpoint guardrail for get_duplicate_suspicions (very low urgency)**
- In `backend/app/api/v1/endpoints/invoice_match.py`: apply `.limit(200)` at endpoint level
- Keep `invoice_match_service.get_duplicate_suspicions` signature unchanged
- Milestone: only if duplicate log grows beyond ~100 unresolved items in practice

**Priority order:** C.3.1 (allowlist, audit-only, no risk) → C.3.2 (simple, same as C.1) → C.3.3 (broadcast chunking, needs test) → C.3.4 (defer)

No source code changed during this audit. No `.limit()` added. No with_for_update() removed. No Graphify run.

**Status: Batch C.3 Audited — chunking architecture selected; 11 FP identified; 1 real chunk candidate; implementation pending (C.3.1→C.3.3)**

**Batch C.3.1 — Allowlist confirmed C.3 false positives (DONE — 2026-06-01)**

Files changed:
- `scripts/erp-health-audit.py` — 3 new `_KNOWN_FP_CONTEXTS` entries added
- `docs/AUTOMATED_HEALTH_AUDIT.md` — regenerated after allowlist applied

Allowlisted C.3 confirmed false positives (12 findings suppressed):

`bank_reconciliation_service.py` (6 findings suppressed):
- `list_bank_accounts` — few active bank accounts, small config
- `get_statement_lines` — FK-bounded by `stmt_id` (BRStatementLine in window)
- `run_auto_match` inner queries — statement lines FK-bounded by `stmt_id`; txns bounded by period dates; rules = small config (skipped by `.in_()` audit check)
- `list_adjustments` — FK-bounded by `stmt_id`
- `list_rules` — small reconciliation rules config
- `get_balance_summary` — iterates few active bank accounts

`invoice_match_service.py` (3 findings suppressed — only confirmed FPs):
- `list_tolerance_rules` — small config
- `_find_tolerance` — same small config, best-match scan
- `_detect_duplicate` — FK-bounded (PurchaseInvoice in window)

`report_builder_service.py` (3 findings suppressed — only confirmed FPs):
- `list_reports` — admin report config, bounded by user-created reports
- `list_schedules` — one schedule per report, small config
- `list_dashboards` — small admin config

Deliberately NOT suppressed:
- `invoice_match_service.py` list_ai_recs (line 897) — C.3.2 missing limit
- `report_builder_service.py` list_ai_recs (line 662) — C.3.2 missing limit
- `ess_service.py` list_accounts_raw (line 663) — C.3.3 real chunking candidate
- `invoice_match_service.py` get_duplicate_suspicions (line 607) — C.3.4 endpoint guardrail
- `webhook_service.py` (3 findings) — C.4 product decision
- `promotions_service.py` (6 findings) — C.4 product decision
- row_lock findings (30) — all retained

Health audit after C.3.1:
| Severity | Count |
|----------|-------|
| HIGH | 0 |
| MEDIUM | 328 |
| INFO | 1 |
| **Total** | **329** |

Previous MEDIUM: 340. Suppressed: 12 confirmed C.3 false positives. No ERP business logic changed. No `.limit()` added.

Remaining C.3 sub-batches:
- C.3.2: add `limit: int = 200` to `invoice_match_service.list_ai_recs` and `report_builder_service.list_ai_recs`
- C.3.3: implement chunked `broadcast_notification` in `ess_service.py`
- C.3.4: endpoint guardrail for `get_duplicate_suspicions` (defer)

**Batch C.3.2 — Two missed safe service list limits (DONE — 2026-06-01)**

Files changed:
- `backend/app/services/invoice_match_service.py` — `list_ai_recs`: added `limit: int = 200` param + `q.limit(limit)` before execute
- `backend/app/services/report_builder_service.py` — `list_ai_recs`: added `limit: int = 200` param + `q.limit(limit)` before execute

Pattern: plain Python `limit: int = 200` (NOT FastAPI `Query()` — service layer only). Existing ordering and status filter preserved. No response shape change.

Checks run:
- `python -c "import app.main"` → CLEAN (only pre-existing allergen.py FastAPIDeprecationWarning)
- `python scripts/erp-health-audit.py` → **0 HIGH / 326 MEDIUM / 1 INFO** (was 328; -2 matching both fixes)

Remaining C.3.3/C.3.4 still visible:
- `ess_service.py:663` (`list_accounts_raw`) — C.3.3 chunking candidate ✓
- `invoice_match_service.py:607` (`get_duplicate_suspicions`) — C.3.4 defer ✓
- `webhook_service.py` (3), `promotions_service.py` (6) — C.4 ✓
- row_lock (30) ✓

Remaining:
- C.3.3 — implement chunked `broadcast_notification` in `ess_service.py`
- C.3.4 — endpoint guardrail for `get_duplicate_suspicions` (deferred)
- C.4 — product-owner decisions on webhook/promotions

**Status: Batch A + B.1 + B.2 + C.1 + C.2 + C.3.1 + C.3.2 + D Done — 0 HIGH; 326 MEDIUM; C.3.3/C.3.4/C.4 pending**

---

- **Source / evidence:** `scripts/erp-health-audit.py`, `docs/AUTOMATED_HEALTH_AUDIT.md`
- **Affected area:** `frontend/src/app/dashboard/qms/inspections/page.tsx` (Batch A); `backend/app/api/v1/endpoints/` (Batch B)
- **Risk:** HIGH fix = medium (frontend auth pattern change); MEDIUM = low (additive limits)
- **Started at:** 2026-05-31
- **Completed at:** 2026-05-31 (Batch A + B.1 + B.2)
- **Changed files:**
  - `frontend/src/app/dashboard/qms/inspections/page.tsx` — removed `localStorage.getItem("access_token")` + raw fetch; replaced with `apiClient.get` (`withCredentials: true`)
  - `backend/app/api/v1/endpoints/finance.py` — 5 real unbounded endpoints limited
  - `backend/app/api/v1/endpoints/procurement.py` — 4 real unbounded endpoints limited
  - `backend/app/api/v1/endpoints/marketing.py` — 4 real unbounded endpoints limited
  - `backend/app/api/v1/endpoints/wms.py` — 5 real unbounded endpoints limited
  - `backend/app/api/v1/endpoints/payroll_ke.py` — 3 real unbounded endpoints limited
  - `backend/app/api/v1/endpoints/hr.py` — 4 real unbounded endpoints limited
  - `backend/app/api/v1/endpoints/documents.py` — 2 real unbounded endpoints limited
  - `docs/AUTOMATED_HEALTH_AUDIT.md` (script output — regenerated)
  - `TASKS.md` — this update
- **Tests / checks run:**
  - `npx tsc --noEmit` → CLEAN (Batch A)
  - `python -c "import app.main"` → CLEAN (Batch B.1 + B.2)
  - `python scripts/erp-health-audit.py` → **0 HIGH / 473 findings** (was 499 originally; -26 net across all batches)
- **Result:** Batch A + B.1 + B.2 complete. 0 HIGH remains. 27 real endpoint unbounded findings fixed across 7 files. 473 findings remain (service-layer unbounded + row_lock backlog).
- **Known limitations:** Script does not require DB — all findings are static analysis only.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend (if endpoint query patterns change)
- **Graphify refresh status:** Not needed for Batch A (frontend only)
- **Notes:** `row_lock` findings are intentional concurrency safety patterns — do not blindly remove.

---

### Task ID: TASK-009 — Utilities module real factory seed data foundation

- **Status:** Done
- **Priority:** P1
- **Category:** Utilities
- **Why it matters:** Utilities seed data is needed for demos and KPI verification.
- **Source / evidence:** `backend/app/db/seed_utilities.py` EXISTS and is comprehensive. Covers: main power meter, compressor, boiler gas, raw water, soft water, solar inverter, wastewater aeration, chemical dosing, anomaly scenarios (high night compressor, soft water hardness deviation, wastewater pH issue), alarm rules, and `UtilityCostAllocation` records for 30 days.
- **Affected area:** `backend/app/db/seed_utilities.py` (already exists)
- **Risk:** N/A
- **Recommended timing:** Done
- **Needs audit before implementation:** N/A
- **Implementation scope:** Already implemented.
- **Do not touch:** N/A
- **Started at:** Before 2026-05-31 (exact commit unknown)
- **Completed at:** Before 2026-05-31
- **Changed files:**
  - `backend/app/db/seed_utilities.py` (created)
- **Created files:**
  - `backend/app/db/seed_utilities.py`
- **Deleted files:** None
- **Tests / checks run:** File confirmed to exist and contain realistic utility seed data
- **Result:** Done — comprehensive utility seed data including cost allocations
- **Known limitations:** Requires Docker/PostgreSQL running to apply. Run: `python -m app.db.seed_utilities` from backend/.
- **Git commit / branch:** Committed (exact hash not identified — part of prior auto-sync)
- **Graphify refresh after implementation:** backend (already done)
- **Graphify refresh status:** Done (included in 2026-05-31 analysis)
- **Graphify output location if refreshed:** `C:\Users\sekip\Desktop\graphify-erp-maps\backend\`
- **Notes:** This task was already complete before TASKS.md was written. `seed_utilities.py` has 1000+ lines of realistic FMCG factory utility data.

---

### Task ID: TASK-010 — Remove graphify-out/ folders from git tracking

- **Status:** Done
- **Priority:** P1
- **Category:** Cleanup
- **Why it matters:** Multiple graphify-out/ folders were tracked by git (883 total generated files after TASK-006 backend refresh auto-sync committed them in e6b58df). These are generated/binary output files and should not be in version control. External source of truth: `C:\Users\sekip\Desktop\graphify-erp-maps\`.
- **Source / evidence:** `git ls-files` pre-fix: `graphify-out/` (132+), `backend/graphify-out/` (672+22 from TASK-006 refresh), `frontend/graphify-out/` (5), `docs/graphify-out/` (52), `scripts/graphify-out/` (2) = 883 tracked files.
- **Affected area:** All `graphify-out/` folders, `.gitignore`
- **Risk:** Low (removal of generated files; no source code change)
- **Do not touch:** External `C:\Users\sekip\Desktop\graphify-erp-maps\` folder; source code
- **Started at:** 2026-05-31
- **Completed at:** 2026-05-31
- **Changed files:**
  - `.gitignore` — added `graphify-out/`, `backend/graphify-out/`, `frontend/graphify-out/`, `docs/graphify-out/`, `scripts/graphify-out/`
  - `TASKS.md` — this update
  - Removed from git index (files stay on disk): all 883 `graphify-out/` tracked files across all stages
- **Tests / checks run:**
  - `git ls-files graphify-out backend/graphify-out frontend/graphify-out docs/graphify-out scripts/graphify-out` → 0 (clean)
  - External folder verified: `graph.json`, `GRAPH_REPORT.md`, `GRAPHIFY_UPDATE_LOG.md`, `cost.json`, `graph.html`, `graph.json` all present
- **Result:** Graphify outputs no longer tracked by git. Future Graphify refreshes will not trigger auto-sync commits of analysis artifacts.
- **Known limitations:** Local repo `graphify-out/` folders remain on disk (untracked). Delete locally only if approved by user.
- **Git commit / branch:** Pending user commit approval
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Notes:** Root `graphify-out/` useful outputs (`cost.json`, `graph.html`, `graph.json`, `GRAPH_REPORT.md`) copied to external folder top level before untracking. `backend/graphify-out/` outputs were already current in external `backend/` subfolder.

---

### Task ID: TASK-011 — Redis AUTH password for production

- **Status:** Pending
- **Priority:** P2
- **Category:** Deployment / Security
- **Why it matters:** Redis has no AUTH password configured. In production, Redis without AUTH is accessible to any process on the network.
- **Source / evidence:** TASKS.md historical: "A.15 Redis no AUTH — LOW" finding from full repository review (2026-05-17). `docs/PERFORMANCE_REVIEW.md`.
- **Affected area:** `docker-compose.prod.yml`, `backend/app/core/config.py`, `.env.production.example`
- **Risk:** Low (config change; requires Redis restart)
- **Recommended timing:** Soon
- **Needs audit before implementation:** No
- **Implementation scope:** Add `REDIS_PASSWORD` env var; configure `requirepass` in Redis service; update `CELERY_BROKER_URL`/`REDIS_URL` in backend config.
- **Do not touch:** Redis data, cache logic
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** Requires Docker restart.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Notes:** Architecture decision: password management for Redis (manual secret vs Docker secrets vs Vault).

---

### Task ID: TASK-012 — Wire SMTP + test email OTP end-to-end

- **Status:** Pending
- **Priority:** P2
- **Category:** Integration
- **Why it matters:** Email OTP (2FA) was implemented but SMTP credentials were never set in a staging/production environment. `email_sender.py` uses console log in dev mode.
- **Source / evidence:** TASKS.md historical: "Production SMTP not tested end-to-end (requires real SMTP server)." `backend/app/services/email_sender.py`. `.env.production.example` has SMTP vars.
- **Affected area:** `.env.production`, `backend/app/services/email_sender.py`
- **Risk:** Low (config only; email_sender.py already implemented)
- **Recommended timing:** Soon
- **Needs audit before implementation:** No
- **Implementation scope:** Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` in staging env. Test email OTP flow end-to-end.
- **Do not touch:** email_sender.py unless bugs found
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** Requires real SMTP server (Gmail/SendGrid/SES).
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Notes:** OTP hashing (bcrypt) already implemented. Login-verify fixed. Just missing SMTP config.

---

### Task ID: TASK-013 — Playwright smoke re-run (post recent changes)

- **Status:** Pending
- **Priority:** P2
- **Category:** QA
- **Why it matters:** Last confirmed Playwright run: 52/52 pass (2026-05-17). Multiple large changes since then: button recovery waves, GS1 overhaul, compliance fixes, redirect fixes. Smoke tests may have regressions.
- **Source / evidence:** TASKS.md historical: "Playwright smoke re-run to confirm 52/52 still pass after frontend changes." Last run was at the 2026-05-17 stage before all button recovery work.
- **Affected area:** `frontend/e2e/smoke.spec.ts`, Docker environment
- **Risk:** Low (read-only test run)
- **Recommended timing:** Soon
- **Needs audit before implementation:** No
- **Implementation scope:** Run `npm run test:smoke` inside Docker frontend container. Review failures. Fix any regressions.
- **Do not touch:** Business logic unless test failure reveals a real bug
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** Requires Docker running (db, redis, backend, frontend all healthy).
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Notes:** 52 tests: auth (3), dashboard (1), workspaces (C), tabs (D), static/dynamic redirects (E/F), theme/layout (G).

---

### Task ID: TASK-014 — python-jose → PyJWT migration evaluation

- **Status:** Pending
- **Priority:** P2
- **Category:** Security
- **Why it matters:** `python-jose` has known CVEs and is less actively maintained than `PyJWT`. Full repository review flagged this as a Medium security issue.
- **Source / evidence:** TASKS.md historical: "Evaluate python-jose → PyJWT migration (needs test coverage)." `docs/SECURITY_REVIEW.md` — Medium finding.
- **Affected area:** `backend/requirements.txt`, `backend/app/core/security.py` or JWT helper files
- **Risk:** Medium (JWT library swap affects token signing/verification)
- **Recommended timing:** Soon
- **Needs audit before implementation:** Yes — review all files that import `jose` or `python-jose`. Check token format compatibility.
- **Implementation scope:** Audit usage, create test coverage for JWT generation/verification, swap library, verify all tests pass.
- **Do not touch:** Auth flow logic unless forced by library API difference
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** Must verify JWKS endpoint still works if used.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed
- **Notes:** This is an evaluation first. If migration is risky or complex, document and defer.

---

### Task ID: TASK-015 — Production module real data (Phase P1-P11)

- **Status:** Pending
- **Priority:** P2
- **Category:** Production
- **Why it matters:** Production module (orders, work orders, work centers, routing, batch tracking, QC, yield) models exist in backend but KPIs and dashboards show empty data. No realistic seed data for demo or testing.
- **Source / evidence:** PLANS.md — Phases P1-P11. CODEX_PROGRESS.md — `production | ModuleDefinition | view, create, edit, approve, export`. Backend production models confirmed.
- **Affected area:** `backend/app/db/seed.py` or new production seed script
- **Risk:** Low (seed data only)
- **Recommended timing:** Soon
- **Needs audit before implementation:** Yes — inspect production models (orders, work orders, work centers, routing) to understand required field structure.
- **Implementation scope:** Seed realistic FMCG production data: production orders, work orders, work centers, routings, batch records. No new columns.
- **Do not touch:** Production model code
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed
- **Notes:** Coordinate with Utilities (TASK-009) so utility consumption data links to production batches.

---

### Task ID: TASK-016 — Inventory/Stock real data (Phase I1-I7)

- **Status:** Pending
- **Priority:** P2
- **Category:** Inventory
- **Why it matters:** Inventory module (warehouses, products, raw materials, stock tracking, movements) KPIs show empty. No realistic factory stock data.
- **Source / evidence:** PLANS.md — Phases I1-I7. CODEX_PROGRESS.md — `inventory | ModuleDefinition | DEFAULT_ACTIONS`. Backend inventory models confirmed.
- **Affected area:** `backend/app/db/seed.py` or inventory seed script
- **Risk:** Low (seed data only)
- **Recommended timing:** Soon
- **Needs audit before implementation:** Yes — inspect inventory models: warehouses, stock ledger, movements.
- **Implementation scope:** Seed FMCG inventory data: warehouses, locations, raw materials, finished goods, initial stock movements.
- **Do not touch:** Inventory model/schema code
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed
- **Notes:** Must coordinate with Production (TASK-015) — production orders consume inventory.

---

### Task ID: TASK-017 — Finance cost allocation engine (Phase F4-F6)

- **Status:** In Progress (utility layer done; BOM costing done; GL-level cross-module allocation pending)
- **Priority:** P2
- **Category:** Finance
- **Why it matters:** Full cost allocation (utility cost → per machine → per batch → per product → GL journal) is the core value driver.
- **Source / evidence:** Already implemented: `UtilityCostAllocation` model (`backend/app/models/utility_management.py`), `backend/app/crud/utility_billing.py` (CRUD for tariffs/bills/allocations), `backend/app/services/utility_billing_service.py`, `backend/app/services/bom_costing_service.py` (BOM standard_batch_cost including utility_cost), `backend/app/db/seed_utilities.py:953` (_cost_allocations generates 30 days of cost records), `backend/app/services/utility_kpi_service.py`, `backend/app/api/v1/endpoints/utility_billing.py`. Still missing: cross-module GL posting (utility costs → finance journals), product-level profitability report, frontend cost allocation drilldown page.
- **Affected area:** Already done: utility billing + BOM costing layer. Remaining: `backend/app/services/` GL-level cost allocation, frontend profitability page.
- **Risk:** High (touches accounting journals)
- **Recommended timing:** Soon
- **Needs audit before implementation:** Yes — audit what `utility_integration_service.py` and `utility_billing_service.py` already provide before writing new code.
- **Already completed:**
  - `UtilityCostAllocation` ORM + CRUD
  - Utility tariff/billing service
  - BOM costing with `total_batch_cost` including utility_cost
  - Cost allocation seed data (30 days)
  - KPI service
- **Remaining work:**
  - Cross-module GL posting: push utility cost allocations into finance journals
  - Product-level profitability report (F6)
  - Frontend cost allocation drilldown (report page)
- **Started at:** Part of prior GAP implementations (date not tracked)
- **Completed at:**
- **Changed files:** See existing files above
- **Tests / checks run:** Part of prior GAP test runs
- **Result:** In Progress
- **Git commit / branch:** Committed (exact hash not identified)
- **Graphify refresh after implementation:** backend, frontend
- **Graphify refresh status:** Needed when remaining work is done
- **Notes:** TASK-009 (Utilities seed) is Done. TASK-015 (Production seed) still needed for full product-level costing.

---

### Task ID: TASK-018 — Full ERP Reference Manual PDF generation script

- **Status:** Done
- **Priority:** P2
- **Category:** Docs
- **Why it matters:** Provides a combined PDF of all 15 full-reference ERP chapters.
- **Source / evidence:** `docs/user-manual/pdf-export/generate-full-reference-pdf.mjs` EXISTS. Confirmed by glob search. Script header confirms: "FMCG ERP Full Reference Manual — PDF Generator. Run from repo root: `node docs/user-manual/pdf-export/generate-full-reference-pdf.mjs`"
- **Affected area:** `docs/user-manual/pdf-export/generate-full-reference-pdf.mjs`
- **Risk:** N/A
- **Recommended timing:** Done
- **Needs audit before implementation:** N/A
- **Implementation scope:** Already implemented.
- **Do not touch:** N/A
- **Started at:** Before 2026-05-31 (exact date unknown)
- **Completed at:** Before 2026-05-31
- **Changed files:**
  - `docs/user-manual/pdf-export/generate-full-reference-pdf.mjs` (created)
- **Created files:**
  - `docs/user-manual/pdf-export/generate-full-reference-pdf.mjs`
- **Deleted files:** None
- **Tests / checks run:** File existence confirmed
- **Result:** Done — script exists and is ready to run
- **Known limitations:** Requires Node.js 18+, `frontend/node_modules/playwright` installed, `docs/user-manual/screenshots/captured/` with 140 PNGs.
- **Git commit / branch:** Committed (exact hash not identified — part of prior auto-sync)
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Notes:** This task was already complete before TASKS.md was written. Run from repo root: `node docs/user-manual/pdf-export/generate-full-reference-pdf.mjs`

---

### Task ID: TASK-019 — GS1 GTIN coverage — product master completeness

- **Status:** Pending
- **Priority:** P3
- **Category:** GS1 / Product Master
- **Why it matters:** When selecting a product in the GS1 label generator, many products will show a "no GTIN" warning if `ProductGS1Config` and `product.barcode` are both empty. Label printing requires GTIN.
- **Source / evidence:** GS1 integration known limitations in TASKS.md (2026-05-31): "Product Master completeness: Product Name/SKU/GTIN auto-fill only as complete as existing Product Master records."
- **Affected area:** Product Master data, `frontend/src/app/dashboard/gs1/page.tsx`, `GET /api/v1/gs1/products/by-product/{id}`
- **Risk:** Low
- **Recommended timing:** Later
- **Needs audit before implementation:** No
- **Implementation scope:** (1) Bulk-update Product Master records with GTIN-14s via import. (2) Consider adding GS1 config creation flow directly from product page.
- **Do not touch:** GS1 backend code
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed (data-only change)
- **Notes:** This is primarily a data entry task, not a code task.

---

### Task ID: TASK-020 — CRM real integration

- **Status:** Pending
- **Priority:** P3
- **Category:** Integration
- **Why it matters:** `crm_service.py` — "PLACEHOLDER: logs intent, creates/updates CrmCustomerMapping records." No real CRM API is called.
- **Source / evidence:** `backend/app/services/crm_service.py:42-85`. `backend/app/core/integration_capabilities.py:107` STUB_ONLY.
- **Affected area:** `backend/app/services/crm_service.py`, `.env.production`
- **Risk:** Medium
- **Recommended timing:** Later
- **Needs audit before implementation:** Yes — decide which CRM platform (Salesforce, HubSpot, Pipedrive, custom).
- **Implementation scope:** Replace placeholder log calls with real CRM API calls. Depends on CRM vendor selection.
- **Do not touch:** CrmCustomerMapping model unless required
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed
- **Notes:** Blocked on CRM vendor selection.

---

### Task ID: TASK-021 — E-commerce real integration

- **Status:** Pending
- **Priority:** P3
- **Category:** Integration
- **Why it matters:** `ecommerce_service.py:42-45` — "PLACEHOLDER: would call platform API here; simulates 3 orders max." No real orders imported.
- **Source / evidence:** `backend/app/services/ecommerce_service.py:39-109`. `backend/app/core/integration_capabilities.py:115` STUB_ONLY.
- **Affected area:** `backend/app/services/ecommerce_service.py`
- **Risk:** Medium
- **Recommended timing:** Later
- **Needs audit before implementation:** Yes — decide platform (Shopify, WooCommerce, etc.).
- **Implementation scope:** Replace placeholder with real platform API (Shopify REST/GraphQL or WooCommerce REST).
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed
- **Notes:** Blocked on platform vendor selection.

---

### Task ID: TASK-022 — IoT/Machine real integration (MQTT/streaming)

- **Status:** Pending
- **Priority:** P3
- **Category:** Integration / AI
- **Why it matters:** `iot_service.py` — "IoT / Machine Integration Service — placeholder." `integration_capabilities.py:102` — "Current service is a placeholder for a future MQTT/streaming bridge."
- **Source / evidence:** `backend/app/services/iot_service.py:2`. `backend/app/core/integration_capabilities.py:98-102`. GAP-022 (IoT Machine Streaming) is implemented as a module/permissions skeleton but the actual IoT bridge is still a stub.
- **Affected area:** `backend/app/services/iot_service.py`, IoT configuration
- **Risk:** High (real-time machine data; requires factory hardware integration)
- **Recommended timing:** Later
- **Needs audit before implementation:** Yes — review factory hardware, MQTT broker, sensor types.
- **Implementation scope:** Wire MQTT broker connection. Subscribe to machine topics. Map sensor data to IoT readings.
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed
- **Notes:** Requires real factory hardware/MQTT broker. High effort, high value.

---

### Task ID: TASK-023 — Bank API replace mock Kenyan bank sync

- **Status:** Pending
- **Priority:** P3
- **Category:** Integration
- **Why it matters:** `bank_api_service.py` — "Bank API / Open Banking service with mock Kenyan bank sync." Generates fake transactions with `MOCK-` prefix.
- **Source / evidence:** `backend/app/services/bank_api_service.py:1,144`. `backend/app/core/integration_capabilities.py:134`. `backend/app/models/bank_api.py:24` `MOCK = "MOCK"` default.
- **Affected area:** `backend/app/services/bank_api_service.py`, bank API model
- **Risk:** Medium (financial data; requires bank API agreement)
- **Recommended timing:** Later
- **Needs audit before implementation:** Yes — determine which Kenyan bank(s) to integrate and their Open Banking API docs.
- **Implementation scope:** Replace mock sync with real bank API (Equity Bank, KCB, NCBA, or Pesalink).
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed
- **Notes:** Blocked on bank API agreement/credentials.

---

### Task ID: TASK-024 — Label printer SDK integration (ZPL/EPL/TSPL)

- **Status:** Pending
- **Priority:** P3
- **Category:** GS1
- **Why it matters:** `barcode_service.py:6` — "Printing: Returns a print job record (placeholder — integrate with label printer SDK)." `integration_capabilities.py:126` — "Label generation exists; physical printer SDK integration is still a placeholder." Current implementation is browser print only.
- **Source / evidence:** `backend/app/services/barcode_service.py:6`. GS1 label printing known limitations (browser print only, no ZPL/EPL/TSPL).
- **Affected area:** `backend/app/services/barcode_service.py`, new `backend/app/services/label_printer_service.py`
- **Risk:** Medium (printer driver integration; platform-specific)
- **Recommended timing:** Later
- **Needs audit before implementation:** Yes — determine printer model (Zebra ZT/GK/GX, TSC TTP, Godex G300) and network/USB connectivity.
- **Implementation scope:** Add ZPL/EPL/TSPL generation for specific printer model. Send to printer via network (TCP/IP) or Windows spooler.
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed
- **Notes:** Do not add `jsPDF`, `pdfmake`, `puppeteer`, or printer drivers to frontend. Backend-side ZPL generation only.

---

### Task ID: TASK-025 — Prophet/AI demand forecasting

- **Status:** Pending
- **Priority:** P3
- **Category:** AI
- **Why it matters:** `forecast_service.py:5` — "Prophet-style AI forecasting is stubbed for future integration." Falls back to Exponential Smoothing. `models/mrp.py:21` — `PROPHET = "PROPHET"` AI-ready stub.
- **Source / evidence:** `backend/app/services/forecast_service.py:5,231`. `backend/app/models/mrp.py:21`. PLANS.md Phase AI1-AI6.
- **Affected area:** `backend/app/services/forecast_service.py`
- **Risk:** Medium (ML library dependency; Prophet requires `pystan`)
- **Recommended timing:** Later
- **Needs audit before implementation:** Yes — evaluate whether Prophet (Meta's library) or a simpler alternative (Holt-Winters already there) is sufficient.
- **Implementation scope:** Implement real Prophet or ARIMA-based forecasting in `forecast_service.py`.
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed
- **Notes:** Requires TASK-002 (AI live mode) and historical sales/production data (TASK-015/016).

---

### Task ID: TASK-026 — Multi-replica migration safety

- **Status:** Pending
- **Priority:** P3
- **Category:** Deployment
- **Why it matters:** In a multi-replica deployment, multiple containers may run `alembic upgrade head` simultaneously, causing race conditions on migrations.
- **Source / evidence:** TASKS.md historical: "C.31: Multi-replica migration race." `docs/DEPLOYMENT.md:149` — "Multi-replica warning: ensure only one container runs migrations." `docs/DEPLOYMENT.md:291-294` — documented and guidance given: "use a Kubernetes init container or a separate migration job for multi-replica setups." `backend/scripts/prod_bootstrap.py` exists with `BOOTSTRAP_PRODUCTION=true` guard and empty-DB check. NO `pg_advisory_lock` code exists.
- **Affected area:** `backend/scripts/dev_migrate.py`, `backend/scripts/prod_bootstrap.py`, `docker-compose.prod.yml`
- **Risk:** Low in single-replica; High in multi-replica
- **Recommended timing:** Later
- **Needs audit before implementation:** Yes — review `docs/DEPLOYMENT.md:291-294` and decide: pg_advisory_lock vs init container vs external migration job.
- **Implementation scope:** Add `pg_advisory_lock` or use a dedicated migration runner container that exits before app containers start.
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending (documented only; no code fix applied)
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Notes:** Not urgent for single-replica deployment. DEPLOYMENT.md documents the risk and gives guidance, but no code implementation exists.

---

### Task ID: TASK-027 — Next ERP module gap implementation (GAP-026+)

- **Status:** Pending
- **Priority:** P2
- **Category:** Various (per gap)
- **Why it matters:** GAP-001 through GAP-025 complete. The ERP roadmap continues with further module depth. Next gap TBD from ERP_ROADMAP_AND_MANUAL_PLAN.md.
- **Source / evidence:** CODEX_PROGRESS.md "Next Task: Continue from GAP-025A. Inspect the next unimplemented gap in TASKS.md roadmap." `docs/planning/ERP_ROADMAP_AND_MANUAL_PLAN.md`.
- **Affected area:** TBD per gap
- **Risk:** Medium
- **Recommended timing:** Soon
- **Needs audit before implementation:** Yes — read `docs/planning/ERP_ROADMAP_AND_MANUAL_PLAN.md` and identify next unimplemented gap. Create audit doc before implementation.
- **Implementation scope:** Audit → Schema Design → Migration → Models → Schemas → Service → Endpoints → Frontend → Permissions → Tests → Docs → Checks (12-step GAP pattern).
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend, frontend
- **Graphify refresh status:** Needed
- **Notes:** Follow 12-step GAP pattern established in GAP-001 through GAP-025.

---

## Completed / Historical Summary

| Date | Task | Result |
|---|---|---|
| 2026-05-31 | Backend import warning cleanup — SQLAlchemy `TaskDependency.task` overlap + `datetime.utcnow()` deprecation | Done. 13/13 tests pass, IMPORT OK |
| 2026-05-31 | GS1 Product Master integration — auto-fill product name/SKU/GTIN/weight, A4 pagination fix, row-print copies fix | Done. tsc CLEAN, build CLEAN |
| 2026-05-31 | GS1 professional label printing — template/preset/copies/PDF export/print history | Done. tsc CLEAN, build CLEAN |
| 2026-05-31 | GS1 barcode create/print bug fix — full generate+print UI added to gs1 page | Done. 16/16 tests pass |
| 2026-05-31 | Post button-recovery verification — 482/482 pytest, tsc CLEAN, build CLEAN, 0 broken action cards | Done |
| 2026-05-31 | Graphify ERP-wide analysis — backend/frontend/docs/scripts mapped | Done. Reports at `C:\Users\sekip\Desktop\graphify-erp-maps\` |
| 2026-05-31 | Tracking consolidation — TASKS.md becomes single source of truth; CODEX_PROGRESS.md deleted | Done |
| 2026-05-24 | Compliance regulatory certs JSON fix — bare fetch → API_BASE prefix | Done. tsc CLEAN, build CLEAN |
| 2026-05-24 | ERP button recovery — 141/141 live smoke, 0 broken action cards, 313/313 valid routes | Done |
| 2026-05-22 | Wave 2A/2B/2C — 47 unresolved BVT → 0 | Done. tsc CLEAN, build 757 pages |
| 2026-05-22 | Six broken action cards fix — 6 → 0 | Done |
| 2026-05-22 | Wave 1A/1B/1C — 353 broken targets → 0 | Done |
| 2026-05-20 | MPS redirect stub recovery — 4 broken action targets fixed | Done |
| 2026-05-19 | PDF export pipeline — Kenya Go-Live Manual 17.5 MB, 45/45 images | Done |
| 2026-05-19 | Screenshot manual system — 140/140 routes captured | Done |
| 2026-05-18 | 2FA OTP (email + SMS) implementation | Done. 478/478 tests |
| 2026-05-17 | Playwright smoke — 52/52 pass (exit 0) | Done |
| 2026-05-17 | CI verification pass — all local CI commands pass | Done |
| 2026-05-17 | Full repository review — health 72/100, 5 safe fixes applied | Done |
| 2026-05-17 | Docker dev startup fix — 5 root causes resolved | Done |
| 2026-05-16 | GAP-025: Multi-Company/Branch — module promoted, 22 tests pass | Done |
| 2026-05-16 | GAP-022/023/024: IoT, Predictive Maintenance, AI Prompt Registry | Done |
| 2026-05-16 | GAP-001 through GAP-021: All 21 gaps complete (accounting, security, WMS, APS, procurement, CRM, HRMS, GS1, etc.) | Done |
| 2026-05-16 | Performance pass 1+2 — 35 indexes, unbounded queries fixed across 13+ files | Done |
| 2026-05-17 | Page consolidation passes 1–6 — D=0 | Done |

---

## Post-Task Update Rule

At the end of every future Claude Code task:

1. Run `git status --short`.
2. Identify changed files.
3. Update TASKS.md task card (status, changed files, created files, deleted files, tests/checks, result, known limitations, git commit/branch).
4. Update `C:\Users\sekip\Desktop\graphify-erp-maps\GRAPHIFY_UPDATE_LOG.md` if the task changed architecture, backend, frontend, docs, scripts, or important workflow.
5. If backend/frontend/docs/scripts changed and Graphify refresh may be useful, ask user before running.
6. Never run full repo Graphify unless user explicitly approves.
7. Never create a new tracking file inside the repo.
8. Never create hooks, scheduled tasks, daemons, watchers, or background automation.
9. Never add `graphify-out/` to git.

---

## Do Not Do Now

- Full repo Graphify rerun (unless user approves)
- Large backend rewrite
- New migrations without audit
- Direct Zebra/TSC/Godex printer drivers in frontend
- Fake AI features or fake integration data
- Deleting archived recovery reports (`docs/archive/` or `docs/planning/` GAP docs)
- Scheduled/background automation
- Creating new tracking files inside the repo
- Deleting `graphify-out/` from git without user confirmation (TASK-010)
- Deleting `PLANS.md` — it is kept as architecture/strategic reference
