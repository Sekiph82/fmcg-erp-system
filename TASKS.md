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

- **Status:** Pending
- **Priority:** P0
- **Category:** UI
- **Why it matters:** POVU logo appears too small on the login page.
- **Source / evidence:** User visual review.
- **Affected area:** `frontend/src/app/(auth)/login/page.tsx` or equivalent login layout
- **Risk:** Low
- **Recommended timing:** Now
- **Needs audit before implementation:** No
- **Implementation scope:** Increase logo size only. Find logo `<img>` or `<Image>` in login page and increase width/height CSS.
- **Do not touch:** Auth logic, backend, routing, global layout, other pages
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Created files:** None yet
- **Deleted files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** None yet
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Graphify output location if refreshed:** None
- **Notes:** Small visual fix only.

---

### Task ID: TASK-002 — Enable AI live mode

- **Status:** Pending
- **Priority:** P0
- **Category:** AI / Integration
- **Why it matters:** `AI_PROVIDER=mock` or `auto` with no API key means all AI features return fake responses. No AI value in production.
- **Source / evidence:** `backend/app/core/config.py:123` `AI_PROVIDER: str = "auto"`. `backend/app/services/ai_provider.py:421` "No AI API key found — using mock provider". Graphify action plan: production deployment blocker.
- **Affected area:** `.env.development`, `.env.production`, `backend/app/core/config.py`
- **Risk:** Low (config-only change if API key is available)
- **Recommended timing:** Now
- **Needs audit before implementation:** No
- **Implementation scope:** Set `AI_PROVIDER=anthropic` (or `openai`/`gemini`) in env files. Add real API key. No code changes unless key validation fails.
- **Do not touch:** AI service code, AI provider logic, frontend AI pages
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Created files:** None yet
- **Deleted files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** Requires real API key from Anthropic/OpenAI/Google.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Notes:** Highest feature unlock per effort. Once set, all AI formulation, predictive maintenance, APS optimization features become live.

---

### Task ID: TASK-003 — Wire M-Pesa production credentials

- **Status:** Pending
- **Priority:** P0
- **Category:** Integration
- **Why it matters:** `mpesa_service.py` returns fake IDs (`ws_CO_PLACEHOLDER_*`). `mpesa_daraja_service.py` uses `fake_checkout`/`fake_merchant` simulation. No real payments possible.
- **Source / evidence:** `backend/app/services/mpesa_service.py:39-46`. `backend/app/services/mpesa_daraja_service.py:115-126`. Graphify action plan: production deployment blocker.
- **Affected area:** `backend/app/services/mpesa_service.py`, `backend/app/services/mpesa_daraja_service.py`, `.env.production`
- **Risk:** Medium (payment integration; needs Safaricom sandbox testing first)
- **Recommended timing:** Now
- **Needs audit before implementation:** Yes — review GAP-006 audit (`docs/planning/GAP-006_REAL_INTEGRATIONS_AUDIT.md`) and integration capability registry first.
- **Implementation scope:** Replace placeholder Daraja stub with live STK Push call using real `MPESA_CONSUMER_KEY`/`MPESA_CONSUMER_SECRET`/`MPESA_PASSKEY` from Safaricom.
- **Do not touch:** Payment model/schema unless required, other integrations
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** Requires Safaricom Business shortcode and approved Daraja API credentials.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed after implementation
- **Notes:** Test in Safaricom sandbox before prod. Never commit real credentials.

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

- **Status:** Pending
- **Priority:** P1
- **Category:** Security / QA
- **Why it matters:** Graphify frontend graph (Community 133) found `adminCredentials` and `limitedCredentials` nodes — potential hardcoded test credentials in frontend E2E tests. Must verify these are not committed passwords.
- **Source / evidence:** Graphify frontend GRAPH_REPORT.md Community 133 nodes.
- **Affected area:** `frontend/e2e/` test files
- **Risk:** Medium (if real credentials hardcoded in committed files)
- **Recommended timing:** Next
- **Needs audit before implementation:** Yes — read `frontend/e2e/` files and search for `adminCredentials`, `limitedCredentials`, hardcoded passwords.
- **Implementation scope:** If real credentials are hardcoded, move to environment variables or fixture files excluded by .gitignore.
- **Do not touch:** E2E test logic, auth flow
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** None.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Notes:** This is read-only investigation first. Only modify if real credentials found.

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

- **Status:** Pending
- **Priority:** P1
- **Category:** Utilities
- **Why it matters:** Utilities module (water, electricity, soft water, boiler, compressed air, solar, chemicals, wastewater) exists in backend but has no realistic seed data. Dashboard shows empty charts. Useless for demos, testing, or KPI verification.
- **Source / evidence:** PLANS.md — Phases U1-U22 defined. U22 = Seed Data. CODEX_PROGRESS.md — module registry shows `utilities | ModuleDefinition | DEFAULT_ACTIONS`. Backend utility models exist.
- **Affected area:** `backend/app/db/seed.py` or new `backend/scripts/seed_utilities.py`
- **Risk:** Low (seed data only; no model changes)
- **Recommended timing:** Next
- **Needs audit before implementation:** Yes — inspect what utility data structures exist in `backend/app/models/` before writing seed data.
- **Implementation scope:** Create realistic FMCG factory utility seed records: assets, devices, readings, utility transactions, tariffs. No new DB columns.
- **Do not touch:** Utility models/schemas/endpoints unless broken
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Known limitations:** Only useful with Docker/PostgreSQL running.
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend
- **Graphify refresh status:** Needed
- **Notes:** PLANS.md phases U1-U22 describe the full Utilities build. Before adding seed data, verify U1-U14 (asset CRUD, readings, transactions, tariffs) are implemented.

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

- **Status:** Pending
- **Priority:** P2
- **Category:** Finance
- **Why it matters:** Cost allocation (utility cost → per machine → per batch → per product) is the core value driver of this ERP. Without it, product costing and profitability are not available. PLANS.md Phase F4-F6 explicitly defines this as a required phase.
- **Source / evidence:** PLANS.md — Phases F4 (Cost Allocation), F5 (Product Costing), F6 (Profitability). GAP-001/GAP-002 completed accounting core and posting integration, but cost allocation still pending.
- **Affected area:** `backend/app/crud/finance.py`, `backend/app/services/` cost allocation service, new frontend cost allocation page
- **Risk:** High (core business logic; incorrect costing affects financial reports)
- **Recommended timing:** Soon (foundational to ERP value)
- **Needs audit before implementation:** Yes — review GAP-001/002 implementation notes to understand what posting infrastructure exists. Read `docs/planning/GAP-001_ACCOUNTING_CORE_IMPLEMENTATION_NOTES.md`.
- **Implementation scope:** Implement cost allocation service: distribute utility costs (from TASK-009) per machine/line/batch/product. Frontend cost allocation report.
- **Do not touch:** Accounting journal logic, existing finance endpoints
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** backend, frontend
- **Graphify refresh status:** Needed
- **Notes:** Requires TASK-009 (Utilities seed data) and TASK-015 (Production seed data) to be meaningful.

---

### Task ID: TASK-018 — Full ERP Reference Manual PDF generation script

- **Status:** Pending
- **Priority:** P2
- **Category:** Docs
- **Why it matters:** Kenya Go-Live Manual PDF was generated (2026-05-19). Full ERP Reference Manual PDF was listed as remaining work.
- **Source / evidence:** TASKS.md historical: "Full ERP Reference Manual PDF (create generate-full-reference-pdf.mjs, same pipeline)." `docs/user-manual/pdf-export/generate-kenya-pdf.mjs` exists as template.
- **Affected area:** `docs/user-manual/pdf-export/`, `docs/user-manual/full-reference/`
- **Risk:** Low (new script only; no source code changes)
- **Recommended timing:** Soon
- **Needs audit before implementation:** No
- **Implementation scope:** Create `generate-full-reference-pdf.mjs` following `generate-kenya-pdf.mjs` pattern. Combine all 15 full-reference chapters.
- **Do not touch:** Kenya Go-Live PDF script, existing manual content
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** docs
- **Graphify refresh status:** Needed if docs structure changes
- **Notes:** Generated PDF is gitignored. Script gets committed.

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
- **Source / evidence:** TASKS.md historical: "C.31: Multi-replica migration race." `docs/DEPLOYMENT.md` — documented, not yet fixed.
- **Affected area:** `backend/scripts/dev_migrate.py`, `backend/scripts/prod_bootstrap.py`, `docker-compose.prod.yml`
- **Risk:** Low in single-replica; High in multi-replica
- **Recommended timing:** Later
- **Needs audit before implementation:** Yes — review `docs/DEPLOYMENT.md` architecture decision section.
- **Implementation scope:** Add `pg_advisory_lock` or use a dedicated migration runner container that exits before app containers start.
- **Started at:**
- **Completed at:**
- **Changed files:** None yet
- **Tests / checks run:** None yet
- **Result:** Pending
- **Git commit / branch:** Not committed yet
- **Graphify refresh after implementation:** no
- **Graphify refresh status:** Not needed
- **Notes:** Not urgent for single-replica deployment.

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
