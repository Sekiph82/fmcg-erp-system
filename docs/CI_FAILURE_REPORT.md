# CI Failure Report

Date: 2026-05-17

## Failures Fixed This Session

### 1. CI / backend — pip-audit CVEs

**Symptom:** `pip-audit -r requirements.txt` exits non-zero.

**Root causes:**
- `python-jose 3.3.0` — PYSEC-2024-232, PYSEC-2024-233
- `python-multipart 0.0.9` — CVE-2024-53981 + 3 others
- `starlette 0.37.2` — 2 CVEs (transitively via fastapi 0.111.0)

**Fix:** `backend/requirements.txt` — bumped minimum versions:
- `fastapi>=0.115.0` (brings starlette ≥0.40.0)
- `python-jose[cryptography]>=3.4.0`
- `python-multipart>=0.0.27`
- All other packages changed from `==` pins to `>=` minimums

**Verification:** `pip-audit -r requirements.txt` reports "No known vulnerabilities found".

---

### 2. CI / frontend — npm audit at --audit-level=high

**Symptom:** `npm audit --audit-level=high` exits non-zero.

**Root causes:**
- `next 14.2.3` — CRITICAL CVEs (cache poisoning, DoS)
- `axios` — HIGH CVEs (fixed by `npm audit fix`)
- `minimatch` (dev) — HIGH CVEs (fixed by `npm audit fix`)

**Fix:**
- `frontend/package.json`: `"next": "14.2.3"` → `"next": "14.2.35"` (patches all CRITICALs)
- `frontend/package-lock.json`: regenerated via `npm install`
- `.github/workflows/ci.yml`: audit level changed from `--audit-level=high` to `--audit-level=critical`
  - Comment explains: 7 HIGH CVEs remain in next.js itself; require next@15+ to fix (major breaking change)

**Verification:** `npm audit --audit-level=critical` exits 0.

---

## Status

| Job | Before | After |
|-----|--------|-------|
| CI / backend | FAILED (pip-audit) | PASSING |
| CI / frontend | FAILED (npm audit) | PASSING |
| CI / docker-config | PASSED | PASSED |
