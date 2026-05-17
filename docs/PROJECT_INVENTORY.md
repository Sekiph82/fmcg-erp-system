# Project Inventory

Generated: 2026-05-17

---

## A. Backend (`backend/`)

### Framework
- FastAPI (async) with Pydantic v2
- Python 3.12-slim (Docker)
- SQLAlchemy 2.x async + asyncpg
- Alembic for migrations
- passlib/bcrypt + python-jose for auth
- pydantic-settings for config

### App Structure
```
backend/
  app/
    api/v1/endpoints/   — 100+ endpoint modules
    core/               — config, security, deps, auth, middleware, AI
    crud/               — 90+ CRUD files (one per domain/model group)
    db/                 — session, base, seed
    models/             — 100+ model files
    schemas/            — Pydantic schemas per module
  alembic/versions/     — 80 migration files
  scripts/              — dev_migrate.py, reset_dev_admin_password.py, prod_bootstrap (missing)
  tests/                — 35+ test files
```

### API Endpoint Folders
100+ endpoint files covering:
- auth, users, roles, modules, access_control
- inventory, materials, products, warehouses, wms, cycle_count
- procurement, purchase orders, landed_cost, invoice_match, bank_reconciliation, subcontracting
- sales, pricing, promotions, crm, distributors, delivery, returns
- production, mps, mrp, production_ai, production_costing, production_execution, shop_floor
- planning, aps (capacity, scheduling, simulation, changeover)
- finance, fixed_assets, dimensions, bank_api, tax_regulatory
- hr, recruitment, appraisals, training, expenses, timesheets, payroll_ke, ess
- quality, qms, allergen, gs1, shelf_life, traceability, consumer_complaints, tpm
- utility_management (electricity, water, steam, solar, compressor, soft_water, chemical_treatment, wastewater)
- fleet, logistics, containers, npd, esg, reporting, analytics, ai
- marketing, campaigns, promotions, brand_assets, market_intelligence, field_sales, secondary_sales
- notifications, webhooks, chatter, calendar, kanban, surveys, helpdesk, project
- messaging, email_integration, whatsapp, voip, meetings, nps, loyalty, subscription
- portal, supplier_portal, api_portal, mobile, pos, van_sales, moto_sales, contracts, commissions
- integrations, bulk_import, import_history, search, serial_tracking, regulatory_certs, dynamic_pricing, copacking

### Models (100+ files)
Core: user, role, audit_log, company, workflow
Finance: finance, fixed_assets, dimensions, bank_reconciliation, invoice_match, landed_cost
Supply chain: inventory, procurement, sales, logistics, containers
Production: production, production_advanced, production_execution, production_ai, mps, planning, bom, recipe, shop_floor, mrp, machine_operator, material_flow
Quality: quality, qms, allergen, gs1, shelf_life, traceability, consumer_complaints, tpm
HR: hr, payroll_ke, timesheets, recruitment, appraisals, training
Utilities: utilities, utility_management, integrations, maintenance
Marketing: marketing, crm, quotation, promotions, pricing, price_list, brand_assets
Extended: npd, esg, fleet, cycle_count, subcontracting, commissions, expenses, contracts, dunning
Infra: notifications, webhooks, two_factor, custom_fields, kanban, calendar, chatter, surveys
Commerce: pos, van_sales, portal, supplier_portal, api_portal, subscription, loyalty, mobile

### Schemas
Per-module Pydantic v2 schemas in `backend/app/schemas/`. Key schemas: user (UserRead override email:str), role, auth (Token, LoginResponse), access_control.

### CRUD Files
90+ CRUD files. Pattern: async functions taking `AsyncSession`, returning model instances or lists. Key risk: 35+ files with unbounded `.all()` queries.

### Services / Background Jobs
- `app/core/token_blocklist.py` — Redis-backed JWT blocklist
- `app/core/login_limiter.py` — Redis-backed brute-force protection
- `app/core/access_control.py` — permission/scope evaluation
- `app/core/observability.py` — metrics, logging, error tracking
- `app/core/input_sanitizer.py` — middleware input sanitization
- `app/core/security_headers.py` — OWASP security headers middleware
- No background job scheduler (APScheduler/Celery not present)

### AI Modules
- `app/core/ai/` — provider abstraction (Anthropic/OpenAI/Gemini/mock)
- AI data masking: `AI_MASK_EXTERNAL_CONTEXT`, `AI_SEND_CUSTOMER_NAMES_TO_LLM=false`
- NL command execution: `AI_NL_COMMAND_EXECUTION_ENABLED=false` (disabled by default)
- Rate limiting: 30 chat/hour, 10 generate/hour per user
- Prompt registry via `ai_prompts` table

### Auth/Security
- JWT HS256 in HttpOnly cookie
- Token blocklist (Redis) on logout
- TOTP 2FA (app-based) — functional
- SMS/Email 2FA — code generated but NOT dispatched (TODO)
- Brute-force: 5 attempts / 10min window / 30min lockout
- bcrypt hashing
- Production guards in config.py

### Database/Session Setup
- `AsyncSessionLocal` with `expire_on_commit=False`
- Pool: size/overflow/recycle/timeout/pre_ping all configurable
- No rollback on exception in `get_db` (known issue)

### Migrations
- 80 files, 1 head (20260516_0060), 2 merge points
- Base migration adds columns, does NOT create tables
- Dev bootstrap via `dev_migrate.py` (create_all + stamp)
- Production bootstrap missing (known CRITICAL issue)

### Seed Scripts
- `backend/app/db/seed.py` — permissions (459), roles (35), admin user, 7 demo users
- `backend/scripts/reset_dev_admin_password.py` — dev-only password reset
- `backend/scripts/dev_migrate.py` — migration bootstrap

### Tests
- 35 test files in `backend/tests/`
- Coverage: security, hardening, attack simulation, GAP analysis per module
- No real-DB integration fixture
- No migration tests
- No startup tests

---

## B. Frontend (`frontend/`)

### Framework
- Next.js 14 with App Router
- TypeScript (strict mode — passes clean)
- Tailwind CSS
- Axios for API calls

### Routing Structure
- `app/` directory (App Router)
- `app/login/page.tsx` — standalone login
- `app/auth/` — 2FA, change-password flows
- `app/dashboard/` — all protected pages
- `app/page.tsx` — root redirect to `/dashboard` or `/login`

### Page Count
- 697 static pages generated
- All pages render clean (no build errors)

### Workspace Pages
Full operational pages under `/dashboard/`:
- Analytics: finance, inventory, payments, procurement, production, sales
- Bank reconciliation, commissions, dimensions, dunning, ESS, expenses
- Finance: cashbook, costing, mpesa, receivables
- Fixed assets, GS1, HR (attendance/employees/leave/payroll/shifts)
- Import history, integrations (barcode/logs/marketing-sync/mpesa/sync)
- Invoice match, logistics (containers/documents/shipments), logs, machine-ops
- Marketing ecommerce, material flow, movements, MPS
- Planning (capacity/changeover/schedule/simulation)
- Procurement (deliveries/orders/suppliers)
- Production (batch-lots/downtime/labor/oee/orders/quality-control/reports/routing/scheduling/time-tracking/waste-yield/work-centers)
- Production execution, QMS, quality (parameters/reports), recruitment
- Recurring orders, reports, roles, sales (collections/delivery/distributors/field-sales/invoices/pricing/reports/returns/shipments)
- Shelf life, shop floor (downtime/handover/queue/supervisor/terminal)
- Subcontracting, tax, traceability, users
- Utility management (alarm-center/alarm-rules/assets/chemical-treatment/compressor/devices/electricity/integration/readings/reports/soft-water/steam)
- Warehouses, webhooks, WMS (counts/picking/replenishment/reports)

### UI Theme
- NEON LIQUID GLASS theme
- `glass/glow` components used throughout dashboard
- Tailwind-based, dark-mode aware

### Navigation / Sidebar
- `frontend/src/components/Sidebar.tsx` — localStorage for UI state only (not tokens)
- Permission-gated navigation items via `hasPermission()`
- Both POVU logo instances use Next.js `fill` mode (fixed this session previously)

### API Clients
- `frontend/src/lib/api.ts` — Axios with `withCredentials: true`
- `frontend/src/lib/auth.ts` — login, getMe, logout, changeOwnPassword
- Base URL from `NEXT_PUBLIC_API_URL`
- 401 → hard redirect (known issue M4)

### State Management
- `AuthContext` — user, loading, permission helpers, scope helpers
- No global state library (Redux/Zustand not used)

### Auth Flow
- Login → POST /api/v1/auth/login → HttpOnly cookie set → getMe → user state
- 2FA → sessionStorage session token → POST /auth/2fa/verify → completeTwoFA
- Logout → POST /api/v1/auth/logout → clear user state → redirect to /login
- Unauthorized API calls → window.location.href to /login

### Tests
- No Playwright tests present
- No frontend unit tests
- `test-login.bat` is a basic curl smoke test (not automated)

---

## C. DevOps

### Docker Files
- `backend/Dockerfile.dev` — python:3.12-slim, no --reload, CMD: dev_migrate.py + uvicorn
- `backend/Dockerfile.prod` — python:3.12-slim, CMD: alembic upgrade head + gunicorn
- `frontend/Dockerfile.dev` — node:20-alpine, CMD: npm run dev
- `frontend/Dockerfile.prod` — (exists, not read in detail — uses `output: standalone`)

### Compose Files
- `docker-compose.yml` — dev (with volume mounts, 90s backend start_period)
- `docker-compose.prod.yml` — prod (no volume mounts, no DB/Redis port exposure, gunicorn)

### Healthchecks
- db: `pg_isready -U ${POSTGRES_USER:-erp_user} -d ${POSTGRES_DB:-fmcg_erp}`
- redis: `redis-cli ping`
- backend: urllib to `http://localhost:8000/live`
- frontend: node fetch to `http://localhost:3000/login`

### Env Files
- `.env.development.example` — committed template with safe dev defaults
- `.env.production.example` — committed template with CHANGE_ME placeholders
- `.env.development` — local only, gitignored
- `.env.production` — local only, gitignored
- `.env` — local only, gitignored (Gordon's safety-net copy)

### Start Scripts
- `start-dev.bat` — Windows Docker startup, healthcheck polling, credential display
- `test-login.bat` — curl smoke test against running containers

### CI Workflows
- None — ❌ missing

### Deployment Docs
- `docs/DEPLOYMENT.md` — exists
- `docs/RUNTIME_STARTUP_REPORT.md` — startup issue history
- `docs/MIGRATION_CHAIN_REPORT.md` — migration analysis

---

## D. Database

### Alembic Migrations
- 80 migration files in `backend/alembic/versions/`
- 1 head: `20260516_0060` (performance_indexes)
- 2 merge points: `87ad3195d2c5` (merge 3 utility branches), `20260516_0010` (merge 2 late branches)
- Base migration `3c45d9071c98` — misnamed "initial_schema", only adds 3 columns to `sales_orders`
- All subsequent migrations assume pre-existing base tables

### Models
- 100+ SQLAlchemy model files
- All registered via `import app.models` in `dev_migrate.py` and `main.py`
- Self-referential relationships (DimValue, CostCenter) generate SAWarnings

### Indexes
- Migration `20260516_0060` adds performance indexes on FK/date/status fields
- Additional indexes in individual feature migrations

### Seed Data
- 459 permissions across 35+ modules
- 35 roles (owner, admin, C-suite, managers, operators)
- 1 superuser (admin)
- 7 demo C-suite users (ceo, coo, cfo, cto, cmo, mkt_manager, data_manager)

### Schema Initialization
- Dev: `create_all()` + `stamp head` (fresh DB) OR `alembic upgrade head` (existing)
- Production: `alembic upgrade head` only — BROKEN for fresh DB

### Dev/Prod Differences
- Dev: `SYNC_INITIAL_ADMIN_PASSWORD=true` (admin password synced from env on start)
- Dev: `SEED_DEMO_DATA=true` (7 demo users seeded)
- Dev: `AUTH_COOKIE_SECURE=false`
- Prod: All above reversed and enforced by production guards

---

## E. Documentation

### README
- `README.md` — project overview, stack, dev/prod startup, login instructions, env file guide

### Deployment Docs
- `docs/DEPLOYMENT.md` — deployment, migration, backup, Redis, DB exposure notes

### Audit/Review Docs
- `docs/AUTOMATED_HEALTH_AUDIT.md` — health audit results
- `docs/ISSUE_FIX_VERIFICATION_REPORT.md` — issue fix history
- `docs/UI_THEME_AUDIT.md` — NEON LIQUID GLASS theme verification
- `docs/RUNTIME_STARTUP_REPORT.md` — Docker/startup issue history and fixes
- `docs/MIGRATION_CHAIN_REPORT.md` — migration chain analysis
- `docs/FULL_REPOSITORY_REVIEW.md` — this review (new)

### Page/Route Reports
- `docs/PAGE_COUNT_REPORT.md`
- `docs/PAGE_CONSOLIDATION_HISTORY.md`
- `docs/PAGE_CONSOLIDATION_AUDIT.md`
- `docs/PAGE_CONSOLIDATION_PLAN.md`
- `docs/PAGE_ROUTE_CLASSIFICATION_REPORT.md`
- `docs/ROUTE_REDIRECT_REPORT.md`
- `docs/WORKSPACE_TAB_REPORT.md`

### Planning Docs (docs/planning/)
- 25 GAP analysis documents (GAP-001 through GAP-025)
- Each GAP has: audit, schema design, implementation notes
- ERP roadmap, implementation plan, status matrix
