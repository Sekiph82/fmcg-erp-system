"""HR/payroll access and workflow helpers.

These helpers keep the first GAP-011 enforcement slice centralized. Endpoint
rollout happens in later subtasks, but the rules live here so HR, payroll,
timesheets, and ESS do not each invent their own permission checks.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.core.access_control import (
    can_access_scope,
    can_modify_record,
    can_perform_in_scope,
    can_view_record,
    forbidden_detail,
    has_any_permission,
    has_permission,
    permission_code,
    resolve_record_scopes,
)


HR_SCOPE_FIELDS = ("company_id", "branch_id", "department_id", "cost_center_id")

HR_ACTION_STATUSES: dict[str, dict[str, set[str]]] = {
    "employee": {
        "edit": {"ACTIVE", "INACTIVE", "ON_LEAVE"},
        "delete": set(),
        "archive": {"ACTIVE", "INACTIVE", "ON_LEAVE", "TERMINATED"},
        "terminate": {"ACTIVE", "ON_LEAVE"},
    },
    "leave": {
        "edit": {"PENDING", "DRAFT"},
        "approve": {"PENDING", "SUBMITTED"},
        "cancel": {"PENDING", "APPROVED", "SUBMITTED"},
    },
    "attendance": {
        "edit": {"PRESENT", "ABSENT", "LATE", "LEAVE", "HALF_DAY"},
    },
    "timesheet": {
        "edit": {"draft", "rejected"},
        "submit": {"draft", "rejected"},
        "approve": {"submitted"},
        "finalize": {"manager_approved"},
        "reject": {"submitted", "manager_approved"},
    },
    "payroll_run": {
        "manage": {"DRAFT", "CALCULATED"},
        "calculate": {"DRAFT", "CALCULATED"},
        "approve": {"CALCULATED"},
        "pay": {"APPROVED"},
        "cancel": {"DRAFT", "CALCULATED"},
        "export": {"CALCULATED", "APPROVED", "PAID"},
    },
    "payslip": {
        "view": {"APPROVED", "PAID", "SENT", "ISSUED"},
        "send": {"APPROVED", "PAID"},
    },
}

PAYROLL_SCOPE_ACTION_BY_ACTION = {
    "calculate": "edit",
    "manage": "edit",
    "pay": "post",
    "send": "export",
}


def _status_value(record: Any) -> str | None:
    for field_name in ("status", "approval_status", "employment_status"):
        value = getattr(record, field_name, None)
        if value is not None:
            return str(getattr(value, "value", value))
    if hasattr(record, "is_active"):
        return "ACTIVE" if bool(getattr(record, "is_active")) else "INACTIVE"
    return None


def hr_document_key(record: Any) -> str:
    name = record.__class__.__name__.lower()
    if "payrollrun" in name or "payroll_run" in name:
        return "payroll_run"
    if "payslip" in name:
        return "payslip"
    if "timesheet" in name:
        return "timesheet"
    if "leave" in name:
        return "leave"
    if "attendance" in name:
        return "attendance"
    if "employee" in name:
        return "employee"
    return name


def inherit_hr_scope(target: Any, source: Any, overwrite: bool = False) -> None:
    for field_name in HR_SCOPE_FIELDS:
        if not hasattr(target, field_name) or not hasattr(source, field_name):
            continue
        if overwrite or getattr(target, field_name, None) is None:
            setattr(target, field_name, getattr(source, field_name, None))


def can_change_hr_status(record: Any, action: str) -> bool:
    document_key = hr_document_key(record)
    allowed_statuses = HR_ACTION_STATUSES.get(document_key, {}).get(action)
    if allowed_statuses is None:
        return True
    if not allowed_statuses:
        return False
    status_value = _status_value(record)
    return status_value in allowed_statuses


def _module_candidates(module: str) -> tuple[str, ...]:
    if module == "payroll":
        return ("payroll", "payroll_ke")
    return (module,)


def _action_for_scope(module: str, action: str) -> str:
    if module == "payroll":
        return PAYROLL_SCOPE_ACTION_BY_ACTION.get(action, action)
    return action


def can_view_hr_record(user: Any, module: str, record: Any) -> bool:
    return any(can_view_record(user, candidate, record) for candidate in _module_candidates(module))


def can_modify_hr_record(user: Any, module: str, action: str, record: Any) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    if not can_change_hr_status(record, action):
        return False

    for candidate in _module_candidates(module):
        if has_permission(user, permission_code(candidate, f"{action}_all")):
            return True
        if has_permission(user, permission_code(candidate, action)):
            return True
        if can_modify_record(user, candidate, _action_for_scope(module, action), record):
            return True

    scope_action = _action_for_scope(module, action)
    own_permissions = []
    for candidate in _module_candidates(module):
        own_permissions.extend(
            [
                permission_code(candidate, f"{action}_own_scope"),
                permission_code(candidate, f"{scope_action}_own_scope"),
            ]
        )
    if not has_any_permission(user, own_permissions):
        return False

    if module == "payroll":
        return any(
            can_perform_in_scope(user, scope_type, scope_id, scope_action)
            for scope_type, scope_id in resolve_record_scopes(record, module)
        )

    return any(
        can_access_scope(user, module, scope_action, scope_type, scope_id)
        for scope_type, scope_id in resolve_record_scopes(record, module)
    )


def user_owns_employee(user: Any, employee_or_id: Any) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    employee_id = getattr(employee_or_id, "id", employee_or_id)
    user_id = getattr(user, "id", None)
    linked_user_id = getattr(employee_or_id, "user_id", None)
    if linked_user_id is not None and user_id is not None and str(linked_user_id) == str(user_id):
        return True
    for scope in getattr(user, "access_scopes", []) or []:
        if not getattr(scope, "is_active", True):
            continue
        if getattr(scope, "scope_type", None) == "employee" and getattr(scope, "scope_id", None) in (str(employee_id), "ALL"):
            return True
    return False


def build_hr_access_hint(user: Any, record: Any, module: str = "hr") -> dict[str, Any]:
    can_view = can_view_hr_record(user, module, record)
    actions = {
        "can_edit": can_modify_hr_record(user, module, "edit", record),
        "can_delete": can_modify_hr_record(user, module, "delete", record),
        "can_approve": can_modify_hr_record(user, module, "approve", record),
        "can_manage": can_modify_hr_record(user, module, "manage", record),
        "can_export": can_modify_hr_record(user, module, "export", record),
    }
    mutation_allowed = any(actions.values())
    reason = None
    if can_view and not mutation_allowed:
        reason = "You can view this HR/payroll record but cannot modify it in this scope or status."
    return {
        "can_view": can_view,
        "view_only": can_view and not mutation_allowed,
        "reason": reason,
        **actions,
    }


def ensure_hr_action_allowed(user: Any, record: Any, action: str, module: str = "hr") -> dict[str, Any]:
    if action != "view" and not can_change_hr_status(record, action):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"HR/payroll record status does not allow {action}.",
        )
    allowed = can_view_hr_record(user, module, record) if action == "view" else can_modify_hr_record(user, module, action, record)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=forbidden_detail("You can view this HR/payroll record only if your permissions and scopes allow it."),
        )
    return build_hr_access_hint(user, record, module)
