# GAP-DB-001 Live PostgreSQL Migration Verification

## Task

`GAP-DB-001: Apply and verify live PostgreSQL migrations after GAP-SEC-001`

## Result

Status: DONE

Verified on local development PostgreSQL at `2026-05-14T17:43:57+03:00`.

## Configuration Confirmed

- Development Compose file: `docker-compose.yml`
- Development env file: `.env.development`
- PostgreSQL service: `db`
- Redis service: `redis`
- Backend service: `backend`
- Alembic config: `backend/alembic.ini`
- Alembic runtime URL source: `app.core.config.settings.DATABASE_URL`
- Backend container DB URL target: Compose-provided `db:5432` service host

No production compose file was used. No volumes were deleted or reset.

## Commands Run

Docker and service startup:

```powershell
Start-Process -FilePath 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -WindowStyle Hidden
docker compose --env-file .env.development up -d db redis
docker compose --env-file .env.development ps
docker compose --env-file .env.development exec -T db pg_isready -U erp_user -d fmcg_erp
```

Alembic:

```powershell
docker compose --env-file .env.development exec -T backend alembic heads
docker compose --env-file .env.development exec -T backend alembic current
docker compose --env-file .env.development exec -T backend alembic upgrade head
docker compose --env-file .env.development exec -T backend alembic current
docker compose --env-file .env.development exec -T backend alembic heads
```

Schema verification:

```sql
SELECT version_num FROM alembic_version ORDER BY version_num;

SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'access_scopes'
ORDER BY ordinal_position;

SELECT conname, contype
FROM pg_constraint
WHERE conrelid = 'access_scopes'::regclass
ORDER BY conname;

SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'access_scopes'
ORDER BY indexname;
```

Backend checks:

```powershell
docker compose --env-file .env.development exec -T backend python -m py_compile app/core/access_control.py app/models/user.py app/models/role.py app/main.py
docker compose --env-file .env.development exec -T backend python -c "import app.main; print('backend import ok')"
.\venv\Scripts\python.exe -m pytest tests\test_gap_sec001_access_control.py tests\test_hardening.py::test_get_current_user_accepts_cookie_token tests\test_hardening.py::test_module_manifest_treats_scoped_view_permissions_as_module_visibility tests\test_attack_simulation.py::TestRBACControls -q
```

Runtime smoke:

```powershell
Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8000/health' -TimeoutSec 10
Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8000/api/v1/auth/me' -TimeoutSec 10
```

## Verification Details

Alembic:

- `alembic heads`: `20260511_0040 (head)`
- `alembic current`: `20260511_0040 (head)`
- `alembic upgrade head`: succeeded
- `alembic_version`: `20260511_0040`

`access_scopes` columns verified:

- `id`
- `user_id`
- `role_id`
- `scope_type`
- `scope_id`
- `scope_name`
- `can_view`
- `can_create`
- `can_edit`
- `can_delete`
- `can_approve`
- `can_post`
- `can_release`
- `can_cancel`
- `can_export`
- `can_import`
- `can_transfer`
- `can_adjust`
- `can_receive`
- `can_dispatch`
- `is_active`
- `created_at`
- `updated_at`

Constraints verified:

- `access_scopes_pkey`
- `access_scopes_user_id_fkey`
- `access_scopes_role_id_fkey`
- `ck_access_scopes_exactly_one_owner`

Indexes verified:

- `ix_access_scopes_user_id`
- `ix_access_scopes_role_id`
- `ix_access_scopes_scope`
- `ix_access_scopes_user_scope_type`
- `ix_access_scopes_role_scope_type`
- `uq_access_scopes_user_scope`
- `uq_access_scopes_role_scope`

Additional columns verified:

- `permissions.is_active`
- `roles.is_system_role`
- `journal_entries.company_id`
- `journal_entries.branch_id`
- `journal_entries.cost_center_id`

Backend checks:

- py_compile passed.
- `import app.main` passed.
- Focused access-control/RBAC tests passed: 22 tests.
- `GET /health` returned `200`.
- Unauthenticated `GET /api/v1/auth/me` returned `401`, confirming the route is live and protected.

Authenticated `/auth/me` response shape was not called because `.env.development` does not contain local admin credentials. This does not block migration verification; the response schema and route behavior are already covered by focused tests.

## Remaining Notes

- Existing unrelated SQLAlchemy overlap warnings still appear during backend import. They are not caused by GAP-DB-001.
- Existing manual screenshot blocker remains unrelated to live migration verification.

