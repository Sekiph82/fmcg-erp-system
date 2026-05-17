# QA Test Plan

Date: 2026-05-17

---

## 1. Current Tests Found

### Backend Tests (35 files in `backend/tests/`)

| File | Coverage |
|------|---------|
| `test_security.py` | Password policy, JWT, brute-force protection |
| `test_hardening.py` | Security header checks |
| `test_attack_simulation.py` | CSRF, injection, XSS simulation |
| `test_load_simulation.py` | Load/concurrency simulation |
| `test_manual_audit_docs.py` | Manual audit doc generation |
| `test_gap001_accounting_core.py` | Finance module structural tests |
| `test_gap002_posting_integration.py` | Posting integration structural tests |
| `test_gap_sec001_access_control.py` | Access control structural tests |
| `test_gap006_integration_capabilities.py` | Integration capabilities |
| `test_gap007_aps_planning_service.py` | APS planning service |
| `test_gap008_wms_service.py` | WMS service |
| `test_gap009_procurement_maturity.py` | Procurement maturity |
| `test_gap010_crm_sales_commercial_access.py` | CRM/sales access |
| `test_gap011_hrms_payroll_access.py` | HRMS/payroll access |
| `test_gap012_document_knowledge_access.py` | Document/knowledge access |
| `test_gap013_report_builder_access.py` | Report builder |
| `test_gap014_notification_center_access.py` | Notification center |
| `test_gap015_navigation_registry.py` | Navigation registry |
| `test_gap016_api_docs_metadata.py` | API docs metadata |
| `test_gap017_haccp_workflow.py` | HACCP workflow |
| `test_gap018_gs1_label_printing.py` | GS1 label printing |
| `test_gap019_shelf_life_fefo.py` | Shelf life FEFO |
| `test_gap020_consumer_complaint_recall.py` | Consumer complaint recall |
| `test_gap021_npd_formula_governance.py` | NPD formula governance |
| `test_gap022_iot_machine_streaming.py` | IoT machine streaming |
| `test_gap023_ml_predictive_maintenance.py` | Predictive maintenance |
| `test_gap024_ai_agent_governance.py` | AI agent governance |
| `test_gap025_multi_company_branch.py` | Multi-company/branch |
| `e2e/test_workflow_fixtures.py` | E2E workflow fixtures |
| `e2e/test_role_expectations.py` | Role expectations |

**Observation:** Most tests are structural/import tests or use mock fixtures. No tests confirmed to run against a real PostgreSQL database. Running these tests does not guarantee the migration chain, seeding, or API flow is correct.

---

## 2. Missing Tests

| Gap | Priority | Notes |
|-----|---------|-------|
| Real-DB integration tests (login → me → logout) | HIGH | Currently all auth tests appear structural |
| Migration chain test (fresh DB → alembic current = head) | HIGH | No test verifies migration works end-to-end |
| Startup seeding test (permissions count, roles count) | HIGH | No test verifies seed correctness |
| Pagination boundary test (limit/offset in list endpoints) | HIGH | No test for unbounded queries |
| 2FA TOTP login flow | MEDIUM | No automated test for complete 2FA login |
| Permission enforcement test (403 when missing perm) | HIGH | No confirmed test for RBAC enforcement |
| Export streaming test | MEDIUM | No test for large data exports |
| `UserRead.email` round-trip test | MEDIUM | Should test `.local` TLD doesn't fail after our fix |

---

## 3. Backend Test Plan

### Unit Tests (no DB required)
- Password policy: ✅ covered in `test_security.py`
- JWT encode/decode: ✅ covered
- Brute-force counter: ✅ covered
- Permission code parsing: add test for `hasPermission()` edge cases
- Config production guards: add test that bad SECRET_KEY fails validation

### Integration Tests (require real DB)
- Fresh DB bootstrap via `dev_migrate.py` → `alembic current == head`
- Seeding: permission count = 459, role count = 35, admin user exists
- Login with admin credentials → 200 response with cookie
- `/auth/me` → 200 with correct user data
- Login with wrong credentials → 401
- Login after lockout → 429 or 403
- Permission-gated endpoint → 403 when missing permission
- Superuser bypass → 200 for all endpoints
- Logout → cookie cleared, subsequent `/auth/me` → 401

### Recommended Test Framework
```
pytest + pytest-asyncio + httpx (async test client)
Fixture: fresh DB per test session via docker-compose test profile
```

---

## 4. Frontend Test Plan

### Unit Tests
- `AuthContext.hasPermission()` with various permission codes
- `AuthContext.hasModule()` edge cases
- `AuthContext.canPerformInScope()` with global vs. scoped access

### Integration Tests
- Login form: submit → cookie set → redirect to dashboard
- 401 response → redirect to /login
- Permission-gated button: hidden when missing perm, visible when present

### Recommended: Playwright E2E Tests

```typescript
// tests/e2e/login.spec.ts
test('login with valid credentials', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[data-testid="login-username"]', 'admin');
  await page.fill('[data-testid="login-password"]', 'Admin1234!');
  await page.click('[data-testid="login-submit"]');
  await expect(page).toHaveURL('/dashboard');
});

test('login with invalid credentials shows error', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[data-testid="login-username"]', 'admin');
  await page.fill('[data-testid="login-password"]', 'wrongpassword');
  await page.click('[data-testid="login-submit"]');
  await expect(page.locator('[data-testid="login-error"]')).toBeVisible();
});
```

---

## 5. Playwright Smoke Test Plan

### Required Before Any Deployment

```
1. Docker startup
   - start-dev.bat completes without error
   - All containers show "healthy"
   - /live returns {"status":"ok"}
   - /ready returns {"status":"ok","database":"connected"}

2. Login flow
   - Admin login → dashboard
   - Admin login → /auth/me 200
   - Wrong password → "Invalid username or password"
   - Server error → "Server error — please try again"

3. Demo users
   - CEO login → dashboard
   - CMO login → dashboard
   - CFO login → dashboard

4. Dashboard load
   - No console errors on /dashboard
   - Sidebar renders with navigation items
   - Permission-gated items show/hide correctly for different roles

5. Core workspace flows
   - Sales workspace loads tabs
   - Inventory workspace loads tabs
   - Finance workspace loads tabs
   - Production workspace loads tabs
   - HR workspace loads tabs
   - Quality workspace loads tabs

6. Logout
   - Logout clears session
   - Subsequent /dashboard access redirects to /login
```

---

## 6. API Contract Test Plan

For each major API group, verify:
- GET list returns paginated response with `items` and `total`
- GET detail returns 404 for non-existent ID
- POST create validates required fields (400 on missing)
- PUT/PATCH update changes correct fields
- DELETE soft-deletes or hard-deletes as appropriate
- All endpoints return 401 without cookie
- All endpoints with `require_permission()` return 403 when role lacks permission

Priority endpoints to contract-test:
1. `/api/v1/auth/login`, `/auth/me`, `/auth/logout`
2. `/api/v1/inventory` (list, create, update)
3. `/api/v1/sales` (list, create)
4. `/api/v1/production/orders` (list, create)
5. `/api/v1/procurement` (list, create, approve)

---

## 7. Migration Test Plan

```bash
# Test 1: Fresh DB bootstrap (dev)
docker compose --env-file .env.development down -v
docker compose --env-file .env.development up --build -d
docker compose --env-file .env.development exec backend alembic current
# Expected: "20260516_0060 (head)"

# Test 2: Existing DB with Alembic (no-op upgrade)
docker compose --env-file .env.development restart backend
docker compose --env-file .env.development logs backend | grep "upgrade"
# Expected: "Alembic upgrade complete"

# Test 3: Schema check
docker compose --env-file .env.development exec backend alembic check
# Expected: "No new upgrade operations detected" OR list of unapplied migrations
```

---

## 8. Docker Startup Test Plan

```bat
:: Full reset
docker compose --env-file .env.development down -v
docker compose --env-file .env.development up --build -d

:: Wait 90 seconds for startup
timeout /t 90

:: Verify health
docker compose --env-file .env.development ps
:: Expected: all services "healthy"

:: Verify backend
curl -s http://localhost:8000/live
:: Expected: {"status":"ok"}

curl -s http://localhost:8000/ready
:: Expected: {"status":"ok","database":"connected"}

:: Verify login
test-login.bat
:: Expected: LOGIN OK: admin credentials work and /auth/me works
```

---

## 9. Permission / RBAC Test Plan

### Role Matrix Tests

For each role test that:
- `owner`: can access ALL endpoints
- `admin`: can access user/role management, cannot access finance approve
- `ceo`: can view all, can approve, cannot create/edit directly
- `cfo`: can access finance fully, cannot access production edit
- `warehouse_operator`: can access inventory, cannot access finance
- `shop_floor_operator`: can access only shop_floor and production view
- `read_only_auditor`: can view assigned scopes, cannot create/edit anything

### Permission Boundary Tests

- Missing `inventory.view` → GET /inventory returns 403
- Having `inventory.view` but missing `inventory.edit` → PATCH /inventory returns 403
- Superuser → all endpoints return 200

---

## 10. AI Safety Test Plan

- `AI_PROVIDER=mock` → all AI endpoints return mock responses, no external calls
- `AI_NL_COMMAND_EXECUTION_ENABLED=false` → NL command endpoint returns 403/501
- Customer data masking → verify customer names not included in prompts
- Rate limit enforcement → 31st chat request in an hour returns 429

---

## 11. Regression Test Checklist

Run before any merge to main:

- [ ] Backend: `python -m compileall app -q` — no syntax errors
- [ ] Backend: `alembic check` — no unapplied migrations
- [ ] Backend: `pytest tests/test_security.py tests/test_hardening.py -v` — all pass
- [ ] Frontend: `tsc --noEmit` — no type errors
- [ ] Frontend: `npm run build` — clean build, no errors
- [ ] Smoke: `test-login.bat` — LOGIN OK
- [ ] Docker: `docker compose --env-file .env.development config --quiet` — no errors
