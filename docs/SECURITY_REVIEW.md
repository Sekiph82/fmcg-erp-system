# Security Review

Date: 2026-05-17  
Prior audit: 0 HIGH findings (per `docs/AUTOMATED_HEALTH_AUDIT.md`)  
This review: 1 CRITICAL (fixed), 0 HIGH open, 3 MEDIUM, 2 LOW

---

## 1. Secrets

| Item | Status | Notes |
|------|--------|-------|
| `.env` files in gitignore | ✅ | `.env`, `.env.development`, `.env.production` all gitignored |
| `.env` never committed | ✅ | `git ls-files .env` returns nothing; no git log history |
| `.env.development.example` | ✅ | Safe defaults only — `changeme`, empty API keys |
| `.env.production.example` | ✅ | All `CHANGE_ME_*` placeholders, no real values |
| Local `.env` has real Gemini key | ⚠️ | Not in git, but key is real (`AIzaSy...`). Rotate if repo is ever made public. |
| Production SECRET_KEY guard | ✅ | Config rejects `changeme` or `CHANGE_ME*` when `ENVIRONMENT=production` |

**Action required:** The local `.env` file has a real Gemini API key. If this repository is ever made public, ensure `.env` has been excluded from all git history (currently clean — never committed).

---

## 2. Auth

| Item | Status | Notes |
|------|--------|-------|
| JWT in HttpOnly cookie | ✅ | `erp_access_token` cookie, HttpOnly, no JS access |
| `AUTH_COOKIE_SECURE=false` in dev | ✅ | Expected; production guard enforces `true` |
| `SameSite=lax` | ✅ | CSRF protection for cross-origin requests |
| Token NOT returned in body | ✅ | `AUTH_RETURN_TOKEN_IN_BODY=false` |
| Token blocklist on logout | ✅ | Redis-backed JTI blocklist |
| JTI per token | ✅ | Each JWT has unique `jti` claim |
| JWT expiry | ✅ | 8 hours access token (`ACCESS_TOKEN_EXPIRE_MINUTES=480`) |
| Password hashing | ✅ | bcrypt via passlib |
| Password policy enforced | ✅ | Min 8 chars, uppercase, lowercase, digit |
| `PASSWORD_REQUIRE_SPECIAL=false` in dev | ⚠️ | Production guard forces `true` |
| Brute-force protection | ✅ | 5 attempts / 10min / 30min lockout, IP + username |
| TOTP 2FA | ✅ | Functional |
| SMS/Email 2FA OTP dispatch | ❌ | Code generated, not sent — `# TODO: dispatch OTP via notification service` |
| Admin seed rules | ✅ | `SEED_INITIAL_ADMIN=true` creates once, subsequent starts skip |
| `SYNC_INITIAL_ADMIN_PASSWORD` | ✅ | Dev only, production guard rejects it |
| Default admin password in dev | ✅ | `Admin1234!` is documented dev-only default |

**MEDIUM — M1:** SMS/Email 2FA users cannot complete login. OTP is generated but never sent. Either wire OTP delivery or disable SMS/Email 2FA mode in UI until implemented.

---

## 3. Authorization

| Item | Status | Notes |
|------|--------|-------|
| Backend permission checks | ✅ | `require_permission(module, action)` dependency on each endpoint |
| Superuser bypass | ✅ | `is_superuser` bypasses permission check (admin only) |
| Frontend permission gates | ✅ | `hasPermission()`, `hasModule()` in AuthContext |
| Scope-based access control | ✅ | `access_scopes` table with per-scope flags |
| Role management | ✅ | 35 predefined roles, custom roles via API |
| Destructive action restrictions | ✅ | `roles.delete`, `users.delete`, `inventory.delete` require explicit perms |
| `is_superuser` count | ✅ | Only `admin` user is superuser in seed |

**LOW — L1:** The `require_permission()` check only verifies role-based permissions, not scope-based access. A user with `inventory.view` can see inventory from all warehouses even if their `access_scopes` only grants one warehouse. Scope enforcement is frontend-only. For true multi-tenant isolation, scope filtering must be applied in CRUD queries.

---

## 4. CORS

| Item | Status | Notes |
|------|--------|-------|
| No wildcard CORS | ✅ | `BACKEND_CORS_ORIGINS` is explicit list |
| Dev CORS | ✅ | `["http://localhost:3000"]` — minimal |
| Production CORS | ✅ | `.env.production.example` uses `["https://yourdomain.example.com"]` |
| `allow_credentials=True` | ✅ | Required for cookie-based auth |
| `allow_methods=["*"]` | ⚠️ | Permits all methods. For production, restrict to `["GET","POST","PUT","PATCH","DELETE","OPTIONS"]` |

---

## 5. AI Safety

| Item | Status | Notes |
|------|--------|-------|
| Customer names masked | ✅ | `AI_SEND_CUSTOMER_NAMES_TO_LLM=false` |
| Supplier names masked | ✅ | `AI_SEND_SUPPLIER_NAMES_TO_LLM=false` |
| Financial totals sent | ⚠️ | `AI_SEND_FINANCIAL_TOTALS_TO_LLM=true` — review for sensitive contexts |
| Product names sent | ✅ | `AI_SEND_PRODUCT_NAMES_TO_LLM=true` — acceptable for FMCG |
| NL command execution disabled | ✅ | `AI_NL_COMMAND_EXECUTION_ENABLED=false` |
| Mock mode available | ✅ | `AI_PROVIDER=mock` for testing |
| Rate limits | ✅ | 30 chat/hour, 10 generate/hour per user |
| Dry-run / approval | ⚠️ | Not verified in this review — check AI command endpoints |

---

## 6. File Uploads / Downloads

| Item | Status | Notes |
|------|--------|-------|
| Bulk import endpoints | ✅ | `bulk_import.py` endpoint present |
| Path traversal | Not verified | Filename sanitization not confirmed in this review |
| MIME type checks | Not verified | Not confirmed in this review |
| Size limits | ⚠️ | No explicit upload size limit observed in config |
| File streaming for exports | Not verified | Large report exports may load entire result in memory |

**MEDIUM — M2:** Verify that `bulk_import.py` sanitizes filenames and validates MIME types. Add `MAX_UPLOAD_SIZE_MB` config and enforce it. Consider streaming large CSV exports.

---

## 7. Logging

| Item | Status | Notes |
|------|--------|-------|
| Passwords not logged | ✅ | No password in log statements observed |
| Tokens not logged | ✅ | No token value logged |
| Request IDs in logs | ✅ | `x-request-id` propagated through middleware |
| Audit trail on login | ✅ | `AuditEvent.LOGIN_FAILED`, `LOGIN_SUCCESS` logged to DB |
| AI context not logged at INFO | ✅ | AI masking controls external data; internal logs at DEBUG |
| Slow request threshold | ✅ | Warns at >500ms |

---

## 8. Dependencies

| Item | Status | Notes |
|------|--------|-------|
| Python deps | ⚠️ | `pip audit` not run in this review — run before production |
| Node deps | ⚠️ | `npm audit` not run in this review — run before production |
| `python-jose` | ⚠️ | `python-jose` has known JWT vulnerabilities in older versions. Consider migrating to `PyJWT>=2.4` which is actively maintained |

**LOW — L2:** Run `pip audit` on `backend/requirements.txt` and `npm audit` on `frontend/package.json` before any production deployment. Address any HIGH or CRITICAL CVEs.

**MEDIUM — M3:** Evaluate replacing `python-jose` with `PyJWT`. `python-jose` is less actively maintained and has had algorithm confusion vulnerabilities. `PyJWT>=2.4` with explicit algorithm lists is more secure.

---

## Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 1 | FIXED (`UserRead.email` causing `/auth/me` 500) |
| HIGH | 0 | — |
| MEDIUM | 3 | 2FA OTP, file upload validation, PyJWT migration |
| LOW | 2 | Scope enforcement in CRUD, dependency audit |
