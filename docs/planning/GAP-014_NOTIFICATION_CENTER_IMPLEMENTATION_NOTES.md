# GAP-014 Notification Center Implementation Notes

## Summary

GAP-014 hardened the Notification Center module that already existed in the codebase. The module had zero authentication on all 24 endpoints, no permission codes in the module registry or seed, and was registered only as a loose `EndpointRouteDefinition`. This gap adds `require_permission` guards to all 24 endpoints, promotes `notifications` to a full `ModuleDefinition`, seeds 6 permission codes, corrects the frontend nav permission keys, and adds focused tests. No schema, model, or service changes were needed.

---

## Implemented Scope

| Sub-area | What was done |
|---|---|
| Endpoint auth | Added `require_permission` to all 24 notification endpoints |
| Module registry | Promoted `notifications` to `MODULE_DEFINITIONS`; removed from `ENDPOINT_ROUTE_DEFINITIONS` |
| Seed | Added 6 `notifications.*` permission codes; added all 6 to admin role; added view/manage/send/report to CEO/exec roles |
| Frontend nav | Updated `nav-config.tsx` notification-center section from `hr.view` to correct `notifications.*` keys |
| Tests | Added `backend/tests/test_gap014_notification_center_access.py` with 9 focused unit tests |

---

## Migration / Models / Schemas / Services

No changes. All pre-existing:

| Layer | Status |
|---|---|
| Migration (`d6e7f8a9c0b1`) | Already applied in live DB (GAP-DB-001) |
| Models (`backend/app/models/notifications.py`) | 5 models, 6 enums — complete |
| Schemas (`backend/app/schemas/notifications.py`) | 13 schema classes — complete |
| Services (`backend/app/services/notifications_service.py`) | 24+ functions — complete |

---

## Endpoints

### `backend/app/api/v1/endpoints/notifications.py`

All 24 routes now carry `dependencies=[Depends(require_permission("notifications", "<action>"))]`.

| Permission | Routes |
|---|---|
| `notifications.view` | GET `/dashboard`, GET `/`, GET `/unread-count`, GET `/{id}`, GET `/ai/recommendations` |
| `notifications.manage` | PATCH `/{id}/read`, POST `/mark-all-read`, DELETE `/{id}`, GET `/preferences/{user_id}`, POST `/preferences/{user_id}` |
| `notifications.send` | POST `/`, POST `/send/bulk`, POST `/send/from-template` |
| `notifications.configure` | POST `/templates`, GET `/templates`, GET `/templates/{id}`, POST `/templates/seed-defaults`, POST `/schedules`, GET `/schedules`, DELETE `/schedules/{id}`, POST `/preferences/{user_id}/seed-defaults` |
| `notifications.report` | GET `/reports/delivery`, GET `/reports/unread`, GET `/reports/failed` |
| `notifications.admin` | POST `/schedules/process-due`, POST `/ai/run-optimizer`, POST `/ai/run-behavior-analyzer`, PATCH `/ai/recommendations/{id}` |

---

## Module Registry

### `backend/app/core/module_registry.py`

| Change | Detail |
|---|---|
| Removed | `EndpointRouteDefinition(key="notifications", ...)` |
| Added | `ModuleDefinition(key="notifications", label="Notification Center", route_prefix="/notifications", import_path="app.api.v1.endpoints.notifications", permission_actions=("view", "manage", "send", "configure", "report", "admin"), sidebar_group="Communication", icon_key="bell", ai_mode=RULE_BASED, critical=False)` |

---

## Permissions and Seed

### `backend/app/db/seed.py`

Six permission codes added to `PERMISSIONS`:

| Code | Label |
|---|---|
| `notifications.view` | View Notifications |
| `notifications.manage` | Manage Notifications |
| `notifications.send` | Send Notifications |
| `notifications.configure` | Configure Notifications |
| `notifications.report` | Report Notifications |
| `notifications.admin` | Admin Notifications |

Role grants:
- `admin`: all 6 codes
- CEO / exec roles: `notifications.view`, `notifications.manage`, `notifications.send`, `notifications.report`

---

## Frontend

### `frontend/src/components/nav-config.tsx`

Notification Center section permission keys updated from `hr.view` to correct module-specific codes:

| Nav item | Old permission | New permission |
|---|---|---|
| Section guard | `hr.view` | `notifications.view` |
| Dashboard | `hr.view` | `notifications.view` |
| All Notifications | `hr.view` | `notifications.view` |
| Preferences | `hr.view` | `notifications.manage` |
| Templates | `hr.view` | `notifications.configure` |
| Schedules | `hr.view` | `notifications.configure` |
| Reports | `hr.view` | `notifications.report` |
| AI Insights | `hr.view` | `notifications.view` |

---

## Tests

### `backend/tests/test_gap014_notification_center_access.py`

9 focused unit tests; no DB required.

| Group | Tests |
|---|---|
| Registry/seed contracts | `notifications` in MODULE_DEFINITIONS, not ENDPOINT_ROUTE_DEFINITIONS; all 6 codes in registry; all 6 in seed; admin has all 6; admin has at minimum view/manage/admin |
| Route registration | `register_module_routes` produces no errors; notification paths appear in the registered router |
| Module definition properties | Correct 6 permission actions; not marked critical; route prefix `/notifications` |

All 9 passed.

---

## Known Limitations

| Area | Limitation |
|---|---|
| User identity | Routes still accept `user_id` as a query/path string; not derived from auth token. Any authenticated user can read/modify any other user's notifications by passing their `user_id`. |
| Schedule triggering | `process_due_schedules` is an HTTP endpoint; no real scheduler (Celery/APScheduler) triggers it automatically. |
| Multi-channel delivery | `email`, `sms`, `whatsapp` channels are stored but no actual delivery is attempted; service writes rows only. |
| AI agents | `run_optimizer` and `run_behavior_analyzer` use heuristic/static logic. |
