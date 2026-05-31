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
    - Known: `moto_sales_service.py:initiate_stk_push()` still has its own independent placeholder for VanMpesaPayment model (van sales module) — separate follow-on if needed.
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

- **Status:** Pending
- **Priority:** P0
- **Category:** Integration
- **Why it matters:** `WhatsAppConfig.is_demo_mode = True` by default — all messages are simulated, nothing is sent to customers.
- **Source / evidence:** `backend/app/models/whatsapp.py:47`. `backend/app/core/integration_capabilities.py:87-92` (STUB_ONLY). Graphify action plan: production blocker.
- **Affected area:** `backend/app/models/whatsapp.py`, WhatsApp service/router, `.env.production`
- **Risk:** Medium (customer-facing messaging; test template approvals needed)
- **Recommended timing:** Now
- **Needs audit before implementation:** Yes — review WhatsApp Business API setup requirements (Meta Business Manager, phone number, template approvals).
- **Implementation scope:** Configure real WhatsApp Business API credentials (`WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`). Set `is_demo_mode=False` via API config endpoint.
- **Do not touch:** Message log model, notification system
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** Requires approved Meta Business Manager account and message templates.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed after implementation
- **Notes:** WhatsApp template messages must be pre-approved by Meta before sending.

---

### Task ID: TASK-005 — eTIMS live integration (KRA Kenya)

- **Status:** Pending
- **Priority:** P0
- **Category:** Integration / Deployment
- **Why it matters:** `payroll_ke.py:452` — "Stub: submit invoice to KRA eTIMS." `tax_regulatory.py:215` — "Simulation-ready: set ETIMS_API_URL in config to enable live calls." Kenya VAT-registered businesses are legally required to submit invoices to KRA eTIMS.
- **Source / evidence:** `backend/app/api/v1/endpoints/payroll_ke.py:448-456`. `backend/app/models/tax_regulatory.py:212-222`. `backend/app/core/integration_capabilities.py:786` (status: "beta"). Graphify action plan: production deployment blocker.
- **Affected area:** `backend/app/api/v1/endpoints/payroll_ke.py`, `backend/app/models/tax_regulatory.py`, `backend/app/models/payroll_ke.py`, `.env.production`
- **Risk:** High (legal compliance requirement; incorrect submissions can trigger KRA audit)
- **Recommended timing:** Now (legal requirement before go-live)
- **Needs audit before implementation:** Yes — review eTIMS API docs (https://etims.kra.go.ke/), review existing `ETimsSubmission` model and `etims_submit` endpoint.
- **Implementation scope:** Replace stub return in `etims_submit` with real KRA eTIMS API call. Wire `ETIMS_API_URL`, `ETIMS_API_KEY` env vars.
- **Do not touch:** Invoice model, payroll model, other tax logic
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** Requires KRA developer registration, sandbox testing, and certificate installation for production.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed after implementation
- **Notes:** Test in KRA sandbox environment first. This is the highest compliance risk before go-live.

---

### Task ID: TASK-006 — GS1 routes auth guard (38 unprotected endpoints)

- **Status:** Pending
- **Priority:** P1
- **Category:** Security
- **Why it matters:** Graphify backend graph (Community 133) found 38 GS1 routes with no auth guard. Any unauthenticated caller can generate and print barcodes.
- **Source / evidence:** Graphify backend GRAPH_REPORT.md Community 133 finding. `backend/app/api/v1/endpoints/` gs1/barcode router inspection needed.
- **Affected area:** `backend/app/api/v1/endpoints/` (GS1/barcode/label endpoints)
- **Risk:** Medium (data integrity; unauthorized label generation)
- **Recommended timing:** Next
- **Needs audit before implementation:** Yes — run `grep -n "router\." backend/app/api/v1/endpoints/gs1*.py` to confirm which routes lack `Depends(get_current_user)` or `require_permission`.
- **Implementation scope:** Add `Depends(get_current_user)` or `RequirePermission("gs1.print")` to unprotected GS1 endpoints. Do not change business logic.
- **Do not touch:** GS1 service logic, barcode generation algorithm, frontend
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** None expected.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed after implementation
- **Notes:** Graphify finding: `adminCredentials`, `limitedCredentials` — also check E2E test file for exposed test credentials.

---

### Task ID: TASK-007 — E2E test credentials investigation

- **Status:** Needs Audit (low risk — verified no production credential leak)
- **Priority:** P1
- **Category:** Security / QA
- **Why it matters:** Graphify frontend graph (Community 133) found `adminCredentials` and `limitedCredentials` nodes — investigated; they are just JS variable names reading from env vars, not hardcoded passwords.
- **Source / evidence:** `frontend/e2e/helpers/auth.ts` — `credentials()` helper uses `process.env.E2E_ADMIN_PASSWORD` etc. `frontend/e2e/auth.setup.ts:47` — `"Admin1234!"` hardcoded (this is the documented dev default from README.md, not a production secret). `frontend/e2e/critical-workflows.spec.ts` — `adminCredentials = credentials("admin")` reads from env vars.
- **Affected area:** `frontend/e2e/auth.setup.ts` only
- **Risk:** Low (not a production credential; documented dev default)
- **Recommended timing:** Next
- **Needs audit before implementation:** Already investigated.
- **Already completed:** Credentials helper uses env vars. No production secrets committed.
- **Remaining work (optional):** Replace hardcoded `"Admin1234!"` in `auth.setup.ts:47` with `process.env.E2E_PASSWORD || "Admin1234!"` for best practice. Not urgent.
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** Code search confirmed
- **Result:** Investigation complete — low risk. Optional cleanup remains.
- **Known limitations:** None.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Notes:** Graphify node names (`adminCredentials`, `limitedCredentials`) do not indicate hardcoded passwords — they are variable names for env-var-sourced credential objects.

---

### Task ID: TASK-008 — Run erp-health-audit.py and address findings

- **Status:** Pending
- **Priority:** P1
- **Category:** QA / Performance
- **Why it matters:** Last known run (2026-05-16) showed 52 HIGH / 624 MEDIUM findings. Subsequent code fixes addressed many. Current state unknown. Unbounded queries, missing guards, and other issues may remain.
- **Source / evidence:** `scripts/erp-health-audit.py`. TASKS.md historical: "python scripts/erp-health-audit.py → 52 HIGH / 624 MEDIUM findings". `check_unbounded_queries()` is a god node in scripts Graphify (7 edges). Previous rounds of fixes (Passes 1-2) fixed many but not all.
- **Affected area:** `scripts/erp-health-audit.py`, backend app code per findings
- **Risk:** Medium (query performance and security)
- **Recommended timing:** Next
- **Needs audit before implementation:** No — just run the script, review output, then decide which findings to fix.
- **Implementation scope:** Run script, analyze output, fix remaining HIGH findings, document MEDIUM findings. Do not over-fix — focus on real unbounded queries and security issues.
- **Do not touch:** Working business logic unless directly flagged as broken
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** Requires Docker/PostgreSQL running for some checks.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed if backend query code changed
- **Notes:** `check_unbounded_queries()` in scripts has 7 Graphify edges — well-connected audit tool.

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

- **Status:** Pending (awaiting user decision — do NOT act without explicit approval)
- **Priority:** P1
- **Category:** Cleanup
- **Why it matters:** Multiple graphify-out/ folders are tracked by git (863 total generated files). These are generated/binary output files and should not be in version control. They belong at `C:\Users\sekip\Desktop\graphify-erp-maps\` (already there).
- **Source / evidence:** `git ls-files` results: `graphify-out/` (132), `backend/graphify-out/` (672), `frontend/graphify-out/` (5), `docs/graphify-out/` (52), `scripts/graphify-out/` (2) = 863 tracked files. User rule: "Do not add graphify-out/ to git."
- **Affected area:** All `graphify-out/` folders, `.gitignore`
- **Risk:** Low (removal of generated files; no source code change — but large git history modification)
- **Recommended timing:** Next (when user approves)
- **Needs audit before implementation:** Yes — confirm external folder has all important outputs AND confirm user explicitly approves before touching git.
- **Implementation scope:** (1) Verify `C:\Users\sekip\Desktop\graphify-erp-maps\` has all 4 stage outputs. (2) Run `git rm -r --cached graphify-out/ backend/graphify-out/ frontend/graphify-out/ docs/graphify-out/ scripts/graphify-out/`. (3) Add all `graphify-out/` patterns to `.gitignore`. (4) Commit.
- **Do not touch:** External `C:\Users\sekip\Desktop\graphify-erp-maps\` folder; source code
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** After `git rm --cached`, folders remain locally but become untracked. Correct behavior.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Notes:** User said "Do not delete graphify-out file" — this task requires explicit user approval before any git rm is run.

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
