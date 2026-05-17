# Performance Review

Date: 2026-05-17

---

## Backend

### Unbounded Queries (HIGH RISK)

**35 CRUD files** call `scalars().all()` without pagination. Affected files include:

| File | Unbounded calls | Risk at scale |
|------|----------------|---------------|
| `crud/audit.py` | 1 | Very high — audit logs grow unbounded |
| `crud/chemical_treatment.py` | 3 | Medium |
| `crud/esg.py` | 5 | Medium |
| `crud/field_sales.py` | 4 | Medium |
| `crud/finance.py` | 2 | High — financial records accumulate |
| `crud/delivery.py` | 2 | Medium |
| `crud/distribution.py` | 1 | Medium |
| `crud/boiler.py` | 1 | Low |
| `crud/compressor.py` | 1 | Low |
| ... + 26 more files | | |

**Fix pattern:**
```python
# Before
result = await db.execute(select(Model))
return list(result.scalars().all())

# After
async def list_items(db, limit: int = 200, offset: int = 0):
    result = await db.execute(select(Model).limit(limit).offset(offset))
    return list(result.scalars().all())
```

Add `limit`/`offset` to all list endpoints and document max page size in API docs.

---

### N+1 Query Risks

- `deps.py::get_current_user` uses `selectinload(User.roles).selectinload(Role.permissions)` and `selectinload(User.roles).selectinload(Role.access_scopes)` — this is correct, 3 queries total per request. ✅
- `seed.py` does full permission/role upsert on EVERY startup — inefficient for production (459 permissions × role assignments). Should be skipped when unchanged.
- Reports/exports that join many tables may generate N+1 if `selectinload` is not used consistently in CRUD.

---

### Heavy Startup Imports

All 100+ model files are imported at startup via `import app.models`. This is necessary for SQLAlchemy model registration. On a cold start this takes ~2–3s.

The seed run (459 permission upserts, 35 role upserts) adds ~200ms DB round-trips on every backend start.

**Optimization opportunity:** Cache a hash of the PERMISSIONS/ROLE_DEFINITIONS lists. If DB permission count matches and hash matches, skip the upsert loop.

---

### Healthcheck Overhead

- `/live` — no DB, instant. ✅
- `/ready` — DB check with 8s cache TTL. ✅
- `/health` — same cached check. ✅

Healthchecks are correctly implemented with caching.

---

### Export Streaming

Not verified whether large report exports stream the response or load the full result set in memory. For CSV/XLSX exports with 100k+ rows, streaming via `StreamingResponse` is essential.

**Action:** Audit `analytics.py`, `finance.py`, and `reporting` endpoints for bulk export paths. Add `StreamingResponse` with generator patterns for any export that could exceed 10k rows.

---

### DB Pool Settings

| Setting | Dev | Prod |
|---------|-----|------|
| pool_size | 5 | 20 |
| max_overflow | 10 | 20 |
| pool_recycle | 1800s | 1800s |
| pool_timeout | 30s | 30s |
| pool_pre_ping | true | true |

For a single-replica production deployment, 40 total connections is adequate. For 2+ replicas, connection count multiplies and PostgreSQL default `max_connections=100` may be exceeded.

---

### Caching Opportunities

Currently no application-level caching beyond:
- DB health TTL (8s) in main.py
- Redis used for: token blocklist, login rate limiting

Caching candidates:
- `GET /api/v1/modules/manifest` — static, seed-driven. Cache for 1 hour.
- `GET /api/v1/roles` — changes rarely. Cache with invalidation on role update.
- Dashboard KPI aggregates — expensive aggregation queries. Cache for 5 minutes.

---

### Lock Contention

`seed.py` runs `delete(role_permission)` + bulk insert on every startup. This full permission table replacement takes a write lock. If multiple backend replicas start simultaneously, this can deadlock.

**Fix:** Wrap role permission seeding in a try/except for deadlock errors with retry, or use an advisory lock.

---

## Frontend

### Route Bundle Size

- First Load JS shared: 90.9 kB — acceptable for an enterprise app
- Individual route bundles: 1.5–9.4 kB — excellent
- No large single-page bundles observed

### 697 Physical Routes (Build Performance)

Next.js generates 697 static pages. This adds ~30s to the build process and increases Docker build cache invalidation. For an ERP used by a small number of internal users, static generation of all pages is unnecessary — these should be server-rendered (SSR) on demand.

Consider switching workspace pages to `generateStaticParams` with `dynamicParams = false` only for stable catalog pages, and using `export const dynamic = 'force-dynamic'` for operational pages.

### Large Components

- `Sidebar.tsx` is likely a large component (handles 100+ navigation items, search, permission gating). Consider code-splitting navigation sections.
- `AuthContext.tsx` loads all user permissions on first render. For users with 300+ permission codes, string array search is O(n). Consider converting to `Set<string>` for O(1) lookup.

```typescript
// Optimization: use Set instead of array for permission lookup
const permissionSet = useMemo(() => new Set(user?.permission_codes ?? []), [user]);
const hasPermission = (code: string) => permissionSet.has(code) || ...
```

### Repeated API Calls

On login: `POST /api/v1/auth/login` + `GET /api/v1/auth/me` (two round trips). The login response already contains `must_change_password` but `getMe` is needed for full user object. Acceptable, no optimization needed.

### Client-Side Heavy Rendering

The permission-aware sidebar renders on the client using a large navigation tree. Initial render may flicker if user data is not immediately available. Loading state in `AuthContext` (the `loading` boolean) prevents premature render.

---

## Docker

### Resource Limits

| Service | CPU | Memory |
|---------|-----|--------|
| db (dev) | 1.0 | 512M |
| db (prod) | 2.0 | 1G |
| redis (dev) | 0.5 | 128M |
| redis (prod) | 0.5 | 256M |
| backend (dev) | 2.0 | 1G |
| backend (prod) | 2.0 | 1G |
| frontend (dev) | 1.0 | 512M |
| frontend (prod) | 1.0 | 512M |

Production backend 1G is borderline if unbounded queries are triggered (large result sets in memory). Increase to 2G or fix pagination first.

### Startup Time

Backend startup: ~60–90s (large model import + migration + seed + uvicorn bind). This is why `start_period: 90s` is needed. Normal for an ERP of this size.

### Build Cache

Backend Docker build: reinstalls all pip packages on any `requirements.txt` change. Prod Dockerfile correctly caches pip layer before COPY of app code. ✅

Frontend Docker build: `npm ci` before `COPY .`. ✅

---

## Recommended Priority

1. Add pagination to top 10 largest CRUD list queries (audit, finance, esg, field_sales)
2. Optimize permission lookup to Set in AuthContext
3. Verify export streaming for finance/analytics reports
4. Add seeding startup optimization (skip if unchanged)
5. Increase prod backend memory limit to 2G until pagination is in place
