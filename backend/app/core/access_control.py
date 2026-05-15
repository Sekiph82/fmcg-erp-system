from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from fastapi import Depends, HTTPException, status


SCOPE_ACTION_FIELDS = (
    "can_view",
    "can_create",
    "can_edit",
    "can_delete",
    "can_approve",
    "can_post",
    "can_release",
    "can_cancel",
    "can_export",
    "can_import",
    "can_transfer",
    "can_adjust",
    "can_receive",
    "can_dispatch",
)

ACTION_FIELD_BY_ACTION = {
    "view": "can_view",
    "view_all": "can_view",
    "view_own_scope": "can_view",
    "create": "can_create",
    "edit": "can_edit",
    "update": "can_edit",
    "delete": "can_delete",
    "approve": "can_approve",
    "post": "can_post",
    "release": "can_release",
    "close": "can_release",
    "cancel": "can_cancel",
    "convert": "can_create",
    "discount_approve": "can_approve",
    "export": "can_export",
    "import": "can_import",
    "transfer": "can_transfer",
    "adjust": "can_adjust",
    "receive": "can_receive",
    "dispatch": "can_dispatch",
}

SCOPE_PERMISSION_ALIASES = {
    "branch": ("branch",),
    "company": ("company",),
    "cost_center": ("cost_center",),
    "customer_group": ("customer_group", "customer"),
    "department": ("department",),
    "employee_department": ("employee_department", "department"),
    "factory": ("factory",),
    "global": ("scope", "global"),
    "machine": ("machine",),
    "product_category": ("product_category", "category"),
    "production_line": ("production_line", "line"),
    "project": ("project",),
    "quality_lab": ("quality_lab", "lab"),
    "sales_region": ("sales_region", "region"),
    "sales_team": ("sales_team", "team"),
    "supplier_category": ("supplier_category", "supplier"),
    "utility_area": ("utility_area", "area"),
    "warehouse": ("warehouse", "scope"),
}

COMMON_RECORD_SCOPE_FIELDS = {
    "company_id": "company",
    "branch_id": "branch",
    "warehouse_id": "warehouse",
    "source_warehouse_id": "warehouse",
    "destination_warehouse_id": "warehouse",
    "target_warehouse_id": "warehouse",
    "from_warehouse_id": "warehouse",
    "to_warehouse_id": "warehouse",
    "factory_id": "factory",
    "production_line_id": "production_line",
    "department_id": "department",
    "department": "department",
    "employee_department_id": "employee_department",
    "sales_region_id": "sales_region",
    "region": "sales_region",
    "sales_team_id": "sales_team",
    "customer_group_id": "customer_group",
    "supplier_category_id": "supplier_category",
    "product_category_id": "product_category",
    "quality_lab_id": "quality_lab",
    "cost_center_id": "cost_center",
    "project_id": "project",
    "machine_id": "machine",
    "utility_area_id": "utility_area",
}

LOCKED_STATUSES = {
    "APPROVED",
    "CANCELLED",
    "CLOSED",
    "COMPLETED",
    "LOCKED",
    "POSTED",
    "RELEASED",
    "REVERSED",
}

STATUS_MUTATION_ACTIONS = {
    "adjust",
    "approve",
    "cancel",
    "close",
    "create",
    "delete",
    "dispatch",
    "edit",
    "post",
    "receive",
    "release",
    "transfer",
    "update",
}


def permission_code(module: str, action: str) -> str:
    return f"{module}.{action}"


def get_effective_permission_codes(user: Any) -> list[str]:
    if getattr(user, "is_superuser", False):
        return ["*"]

    codes: set[str] = set()
    for role in getattr(user, "roles", []) or []:
        if not getattr(role, "is_active", False):
            continue
        for permission in getattr(role, "permissions", []) or []:
            if not getattr(permission, "is_active", True):
                continue
            code = getattr(permission, "code", None)
            if code:
                codes.add(code)
    return sorted(codes)


def get_effective_modules(user: Any) -> list[str]:
    if getattr(user, "is_superuser", False):
        return ["*"]
    modules = {code.split(".", 1)[0] for code in get_effective_permission_codes(user) if "." in code}
    return sorted(modules)


def has_permission(user: Any, permission: str) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    permissions = set(get_effective_permission_codes(user))
    return "*" in permissions or permission in permissions


def has_any_permission(user: Any, permissions: Iterable[str]) -> bool:
    return any(has_permission(user, permission) for permission in permissions)


def _action_field(action: str) -> str:
    normalized = action.strip().lower()
    return ACTION_FIELD_BY_ACTION.get(normalized, f"can_{normalized}")


def _scope_id(value: Any) -> str:
    return str(value)


def _scope_to_dict(scope: Any, source: str) -> dict[str, Any]:
    data = {
        "scope_type": getattr(scope, "scope_type"),
        "scope_id": getattr(scope, "scope_id"),
        "scope_name": getattr(scope, "scope_name", None),
        "is_active": getattr(scope, "is_active", True),
        "source": source,
    }
    for field in SCOPE_ACTION_FIELDS:
        data[field] = bool(getattr(scope, field, False))
    return data


def _merge_scope_dict(target: dict[str, Any], scope: Any) -> None:
    if not target.get("scope_name") and getattr(scope, "scope_name", None):
        target["scope_name"] = getattr(scope, "scope_name")
    for field in SCOPE_ACTION_FIELDS:
        target[field] = bool(target.get(field)) or bool(getattr(scope, field, False))


def get_effective_scopes(user: Any, scope_type: str | None = None) -> list[dict[str, Any]]:
    if getattr(user, "is_superuser", False):
        scope = {
            "scope_type": scope_type or "global",
            "scope_id": "ALL",
            "scope_name": "All scopes",
            "source": "user",
            "is_active": True,
        }
        for field in SCOPE_ACTION_FIELDS:
            scope[field] = True
        return [scope]

    role_scopes: dict[tuple[str, str], dict[str, Any]] = {}
    for role in getattr(user, "roles", []) or []:
        if not getattr(role, "is_active", False):
            continue
        for scope in getattr(role, "access_scopes", []) or []:
            if not getattr(scope, "is_active", True):
                continue
            if scope_type and getattr(scope, "scope_type") != scope_type:
                continue
            key = (getattr(scope, "scope_type"), getattr(scope, "scope_id"))
            if key not in role_scopes:
                role_scopes[key] = _scope_to_dict(scope, "role")
            else:
                _merge_scope_dict(role_scopes[key], scope)

    effective = role_scopes
    for scope in getattr(user, "access_scopes", []) or []:
        if not getattr(scope, "is_active", True):
            continue
        if scope_type and getattr(scope, "scope_type") != scope_type:
            continue
        key = (getattr(scope, "scope_type"), getattr(scope, "scope_id"))
        effective[key] = _scope_to_dict(scope, "user")

    return sorted(effective.values(), key=lambda item: (item["scope_type"], item["scope_id"]))


def _find_user_scope(user: Any, scope_type: str, scope_id: str) -> Any | None:
    for scope in getattr(user, "access_scopes", []) or []:
        if not getattr(scope, "is_active", True):
            continue
        if getattr(scope, "scope_type") == scope_type and getattr(scope, "scope_id") == scope_id:
            return scope
    return None


def _role_scope_allows(user: Any, scope_type: str, scope_id: str, action_field: str) -> bool:
    for role in getattr(user, "roles", []) or []:
        if not getattr(role, "is_active", False):
            continue
        for scope in getattr(role, "access_scopes", []) or []:
            if not getattr(scope, "is_active", True):
                continue
            if getattr(scope, "scope_type") != scope_type:
                continue
            if getattr(scope, "scope_id") not in (scope_id, "ALL"):
                continue
            if bool(getattr(scope, action_field, False)):
                return True
    return False


def can_perform_in_scope(user: Any, scope_type: str, scope_id: Any, action: str) -> bool:
    if getattr(user, "is_superuser", False):
        return True

    action_field = _action_field(action)
    if action_field not in SCOPE_ACTION_FIELDS:
        return False

    normalized_scope_id = _scope_id(scope_id)

    # User-specific rows are explicit overrides for the same exact scope, then global scope.
    user_scope = _find_user_scope(user, scope_type, normalized_scope_id)
    if user_scope is not None:
        return bool(getattr(user_scope, action_field, False))

    user_global_scope = _find_user_scope(user, scope_type, "ALL")
    if user_global_scope is not None:
        return bool(getattr(user_global_scope, action_field, False))

    return _role_scope_allows(user, scope_type, normalized_scope_id, action_field)


def _own_permission_candidates(module: str, action: str, scope_type: str) -> list[str]:
    aliases = SCOPE_PERMISSION_ALIASES.get(scope_type, (scope_type, "scope"))
    candidates = [permission_code(module, f"{action}_own_scope")]
    candidates.extend(permission_code(module, f"{action}_own_{alias}") for alias in aliases)
    return list(dict.fromkeys(candidates))


def can_access_scope(user: Any, module: str, action: str, scope_type: str, scope_id: Any) -> bool:
    if getattr(user, "is_superuser", False):
        return True

    if has_permission(user, permission_code(module, f"{action}_all")):
        return True

    own_permissions = _own_permission_candidates(module, action, scope_type)
    if not has_any_permission(user, own_permissions):
        return False
    return can_perform_in_scope(user, scope_type, scope_id, action)


def can_view_scope(user: Any, module: str, scope_type: str, scope_id: Any) -> bool:
    if has_permission(user, permission_code(module, "view")):
        return True
    return can_access_scope(user, module, "view", scope_type, scope_id)


def can_modify_scope(user: Any, module: str, action: str, scope_type: str, scope_id: Any) -> bool:
    return can_access_scope(user, module, action, scope_type, scope_id)


def resolve_record_scopes(record: Any, module: str | None = None) -> list[tuple[str, str]]:
    scopes: list[tuple[str, str]] = []
    for field_name, scope_type in COMMON_RECORD_SCOPE_FIELDS.items():
        value = getattr(record, field_name, None)
        if value is not None:
            scopes.append((scope_type, _scope_id(value)))
    return list(dict.fromkeys(scopes))


def _record_status(record: Any) -> str | None:
    for field_name in ("status", "workflow_status", "state"):
        value = getattr(record, field_name, None)
        if value is None:
            continue
        return getattr(value, "value", value)
    return None


def can_modify_by_status(module: str, action: str, status_value: Any) -> bool:
    normalized_action = action.strip().lower()
    if normalized_action not in STATUS_MUTATION_ACTIONS:
        return True
    if status_value is None:
        return True
    normalized_status = str(getattr(status_value, "value", status_value)).strip().upper()
    if normalized_status in LOCKED_STATUSES:
        return False
    if module == "finance" and normalized_status in {"APPROVED", "POSTED"} and normalized_action not in {"reverse", "export"}:
        return False
    return True


def can_view_record(user: Any, module: str, record: Any) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    if has_permission(user, permission_code(module, "view")) or has_permission(user, permission_code(module, "view_all")):
        return True
    scopes = resolve_record_scopes(record, module)
    return any(can_access_scope(user, module, "view", scope_type, scope_id) for scope_type, scope_id in scopes)


def can_modify_record(user: Any, module: str, action: str, record: Any) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    if not can_modify_by_status(module, action, _record_status(record)):
        return False
    if has_permission(user, permission_code(module, f"{action}_all")):
        return True
    scopes = resolve_record_scopes(record, module)
    return any(can_modify_scope(user, module, action, scope_type, scope_id) for scope_type, scope_id in scopes)


def forbidden_detail(detail: str) -> dict[str, str]:
    return {"error": "forbidden", "detail": detail}


def require_any_permission(permissions: Iterable[str]):
    from app.core.deps import get_current_user

    async def _check(current_user=Depends(get_current_user)):
        if not has_any_permission(current_user, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=forbidden_detail("Required permission is missing."),
            )
        return current_user

    return _check


def require_scoped_permission(
    permission_all: str,
    permission_scoped: str,
    scope_type: str,
    scope_id: str,
    action: str,
):
    from app.core.deps import get_current_user

    async def _check(current_user=Depends(get_current_user)):
        if has_permission(current_user, permission_all):
            return current_user
        if not has_permission(current_user, permission_scoped):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=forbidden_detail("Required scoped permission is missing."),
            )
        if not can_perform_in_scope(current_user, scope_type, scope_id, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=forbidden_detail("You can view this record but cannot modify it in this scope."),
            )
        return current_user

    return _check


def require_record_access(
    module: str,
    action: str,
    record_loader: Callable[..., Any | Awaitable[Any]],
):
    from app.core.deps import get_current_user

    async def _check(current_user=Depends(get_current_user)):
        record = record_loader()
        if hasattr(record, "__await__"):
            record = await record
        allowed = can_view_record(current_user, module, record) if action == "view" else can_modify_record(current_user, module, action, record)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=forbidden_detail("You can view this record but cannot modify it in this scope."),
            )
        return current_user

    return _check
