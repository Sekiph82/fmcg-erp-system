# GAP-014 Notification Center — Schema Design

## Decision: No New Tables Required

All five required tables already exist and were applied in the live DB (verified in GAP-DB-001):

| Table | Migration |
|---|---|
| `nc_notifications` | `d6e7f8a9c0b1` |
| `nc_notification_preferences` | `d6e7f8a9c0b1` |
| `nc_notification_templates` | `d6e7f8a9c0b1` |
| `nc_notification_schedules` | `d6e7f8a9c0b1` |
| `nc_ai_recommendations` | `d6e7f8a9c0b1` |

GAP-014C (migration) is **SKIPPED**. GAP-014D (models) is **SKIPPED**. GAP-014E (schemas) is **SKIPPED**.

---

## Permission Action Set

Six permission actions cover the full endpoint surface:

| Action code | Protects |
|---|---|
| `notifications.view` | GET notifications list, GET single notification, GET unread count, GET dashboard, GET AI recommendations |
| `notifications.manage` | PATCH mark-read, POST mark-all-read, DELETE notification, GET/POST/PATCH preferences |
| `notifications.send` | POST create notification, POST send/bulk, POST send/from-template |
| `notifications.configure` | POST/GET/DELETE templates, POST seed-templates, POST/GET/DELETE schedules, POST seed-preferences |
| `notifications.report` | GET reports/delivery, GET reports/unread, GET reports/failed |
| `notifications.admin` | POST schedules/process-due, POST AI agents (optimizer, behavior-analyzer), PATCH AI recommendations |

---

## Module Promotion Plan

`notifications` moves from `ENDPOINT_ROUTE_DEFINITIONS` to `MODULE_DEFINITIONS`:

```python
ModuleDefinition(
    key="notifications",
    label="Notification Center",
    route_prefix="/notifications",
    import_path="app.api.v1.endpoints.notifications",
    permission_actions=("view", "manage", "send", "configure", "report", "admin"),
    sidebar_group="Communication",
    icon_key="bell",
    ai_mode=AIMode.RULE_BASED,
    critical=False,
)
```

---

## Seed Role Grants

| Role | Permissions |
|---|---|
| `admin` | All 6: view, manage, send, configure, report, admin |
| `manager` / `supervisor` | view, manage, send, report |
| `staff` / `operator` | view, manage |

---

## Endpoint Permission Mapping

| Action | Routes |
|---|---|
| `notifications.view` | GET `/dashboard`, GET `/`, GET `/unread-count`, GET `/{id}`, GET `/ai/recommendations` |
| `notifications.manage` | PATCH `/{id}/read`, POST `/mark-all-read`, DELETE `/{id}`, GET `/preferences/{user_id}`, POST `/preferences/{user_id}` |
| `notifications.send` | POST `/`, POST `/send/bulk`, POST `/send/from-template` |
| `notifications.configure` | POST `/templates`, GET `/templates`, GET `/templates/{id}`, POST `/templates/seed-defaults`, POST `/schedules`, GET `/schedules`, DELETE `/schedules/{id}`, POST `/preferences/{user_id}/seed-defaults` |
| `notifications.report` | GET `/reports/delivery`, GET `/reports/unread`, GET `/reports/failed` |
| `notifications.admin` | POST `/schedules/process-due`, POST `/ai/run-optimizer`, POST `/ai/run-behavior-analyzer`, PATCH `/ai/recommendations/{id}` |
