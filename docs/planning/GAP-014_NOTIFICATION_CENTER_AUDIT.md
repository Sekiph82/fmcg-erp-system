# GAP-014 Notification Center Completeness — Audit

## Existing Implementation

| Layer | Status | Files |
|---|---|---|
| DB migration | EXISTS | `backend/alembic/versions/d6e7f8a9c0b1_notification_center.py` — creates 5 tables |
| ORM models | EXISTS | `backend/app/models/notifications.py` — 5 models, 6 enums |
| Schemas | EXISTS | `backend/app/schemas/notifications.py` — 13 schema classes |
| Service layer | EXISTS | `backend/app/services/notifications_service.py` — 24+ functions |
| API endpoints | EXISTS | `backend/app/api/v1/endpoints/notifications.py` — 24 routes |
| Frontend client | EXISTS | `frontend/src/lib/notifications_center.ts` — 23-method TypeScript client |
| Module registry | PARTIAL | Listed as `EndpointRouteDefinition`, not `ModuleDefinition` |
| Permissions in seed | MISSING | Zero `notification.*` entries in `backend/app/db/seed.py` |
| Auth on endpoints | MISSING | All routes use only `Depends(get_db)`, no `require_permission` |

---

## Models

`backend/app/models/notifications.py`

| Model | Table | Key columns |
|---|---|---|
| `Notification` | `nc_notifications` | `notification_id`, `user_id`, `title`, `message`, `notification_type`, `priority`, `channel`, `status`, `source_module`, `source_entity_id`, `deep_link_url`, `action_url`, `scheduled_at`, `sent_at`, `read_at`, `metadata_json` |
| `NotificationPreference` | `nc_notification_preferences` | `pref_id`, `user_id`, `notification_type`, `channel`, `enabled`, `quiet_hours_start/end`, `threshold_level` |
| `NotificationTemplate` | `nc_notification_templates` | `template_id`, `template_code`, `notification_type`, `channel`, `title_template`, `message_template`, `variables_schema` |
| `NotificationSchedule` | `nc_notification_schedules` | `schedule_id`, `trigger_event`, `template_id`, `delay_minutes`, `recurrence_rule`, `is_active`, `last_run_at`, `next_run_at` |
| `NCNotifAIRecommendation` | `nc_ai_recommendations` | `rec_id`, `agent_type`, `status`, `title`, `body`, `score`, `actioned_by`, `actioned_at` |

Enums: `NotificationType`, `NotificationPriority`, `NotificationChannel`, `NotificationStatus`, `NCNotifAIAgentType`, `NCNotifAIRecStatus`.

---

## Endpoints

`backend/app/api/v1/endpoints/notifications.py` — 24 routes, all with only `Depends(get_db)`.

| Route group | Routes |
|---|---|
| Core | GET `/dashboard`, GET `/`, POST `/`, GET `/unread-count`, GET `/{id}`, PATCH `/{id}/read`, POST `/mark-all-read`, DELETE `/{id}` |
| Bulk/template send | POST `/send/bulk`, POST `/send/from-template` |
| Preferences | GET `/preferences/{user_id}`, POST `/preferences/{user_id}`, POST `/preferences/{user_id}/seed-defaults` |
| Templates | POST `/templates`, GET `/templates`, GET `/templates/{id}`, POST `/templates/seed-defaults` |
| Schedules | POST `/schedules`, GET `/schedules`, POST `/schedules/process-due`, DELETE `/schedules/{id}` |
| Reports | GET `/reports/delivery`, GET `/reports/unread`, GET `/reports/failed` |
| AI | POST `/ai/run-optimizer`, POST `/ai/run-behavior-analyzer`, GET `/ai/recommendations`, PATCH `/ai/recommendations/{id}` |

---

## Critical Findings

### CRITICAL-001: No authentication or authorization on any endpoint
All 24 routes accept requests without any token or permission check. Any unauthenticated caller can read, create, delete notifications, modify user preferences, and run AI agents.

### CRITICAL-002: No permission codes in seed or registry
`PERMISSIONS` in `seed.py` has zero `notification.*` entries. `registry_permission_codes()` returns nothing for notifications because the module is in `ENDPOINT_ROUTE_DEFINITIONS`, not `MODULE_DEFINITIONS`.

### CRITICAL-003: Module stuck in ENDPOINT_ROUTE_DEFINITIONS
`notifications` is an `EndpointRouteDefinition` at `module_registry.py:388`. It must be promoted to `ModuleDefinition` to get permission code generation, sidebar group assignment, and proper AI mode configuration.

### MEDIUM-001: User identity comes from query parameter, not auth context
Routes like `GET /unread-count?user_id=...`, `GET /preferences/{user_id}`, and `POST /mark-all-read?user_id=...` accept `user_id` as a string parameter rather than deriving it from the authenticated user. This means any caller can read or modify any user's notifications.

### MEDIUM-002: Schedule triggering is stub
`POST /schedules/process-due` exists as an endpoint but must be called manually. No real scheduler (Celery, APScheduler, cron) is wired. `next_run_at` is computed but never acted on.

### MEDIUM-003: Multi-channel delivery is not implemented
`NotificationChannel` enum includes `email`, `sms`, `whatsapp` but service functions only write rows to `nc_notifications`; no actual email/SMS/WhatsApp delivery is attempted.

### LOW-001: AI recommendations are heuristic-only
`run_optimizer` and `run_behavior_analyzer` produce static/heuristic recommendations without ML inference or live data analysis.

---

## What Is NOT Missing

- Schema design: all required tables exist, no new columns needed for the auth gap
- Service layer: CRUD, template rendering, preference upsert, dashboard aggregation, AI agent stubs all present
- Frontend client: TypeScript API client complete with 23 methods and display helpers
- Migration: `d6e7f8a9c0b1` already applied in the live DB (verified in GAP-DB-001)

---

## Scope for GAP-014

Based on this audit, the required work is:

1. **GAP-014B** (Schema): No new tables needed. Document permission action set and module promotion plan.
2. **GAP-014C** (Migration): Skip — no schema changes needed.
3. **GAP-014D** (Models): Skip — models complete.
4. **GAP-014E** (Schemas): Skip — schemas complete.
5. **GAP-014F** (Services): No changes needed at service layer.
6. **GAP-014G** (Endpoints): Add `require_permission` to all 24 routes.
7. **GAP-014H** (Frontend): Verify nav uses correct permission keys; no new pages needed.
8. **GAP-014I** (Permissions): Promote to `ModuleDefinition`; add seed codes; update admin role.
9. **GAP-014J** (Tests): Focused unit tests for registry/seed contract and permission guards.
10. **GAP-014K** (Docs): Implementation notes.
11. **GAP-014L** (Checks): Final verification pass.
