from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.module_registry import ENDPOINT_ROUTE_DEFINITIONS, MODULE_DEFINITIONS
from app.services.hr_payroll_access_service import (
    build_hr_access_hint,
    can_modify_hr_record,
    ensure_hr_action_allowed,
    inherit_hr_scope,
    user_owns_employee,
)


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent


class EmployeeRecord(SimpleNamespace):
    pass


class PayrollRunRecord(SimpleNamespace):
    pass


def _read_backend(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="ignore")


def _read_frontend(path: str) -> str:
    return (REPO_ROOT / "frontend" / path).read_text(encoding="utf-8", errors="ignore")


def _permission(code: str):
    module, action = code.split(".", 1)
    return SimpleNamespace(code=code, module=module, action=action, is_active=True)


def _scope(scope_type: str, scope_id: str, **actions):
    defaults = {
        "can_view": False,
        "can_create": False,
        "can_edit": False,
        "can_delete": False,
        "can_approve": False,
        "can_post": False,
        "can_release": False,
        "can_cancel": False,
        "can_export": False,
        "can_import": False,
        "can_transfer": False,
        "can_adjust": False,
        "can_receive": False,
        "can_dispatch": False,
    }
    defaults.update(actions)
    return SimpleNamespace(
        scope_type=scope_type,
        scope_id=scope_id,
        scope_name=None,
        is_active=True,
        **defaults,
    )


def _role(name: str, permissions=None, access_scopes=None, is_active=True):
    return SimpleNamespace(
        name=name,
        is_active=is_active,
        permissions=permissions or [],
        access_scopes=access_scopes or [],
    )


def _user(roles=None, access_scopes=None, is_superuser=False, user_id="user-1"):
    return SimpleNamespace(
        id=user_id,
        is_superuser=is_superuser,
        roles=roles or [],
        access_scopes=access_scopes or [],
    )


def test_gap011_hr_broad_view_does_not_grant_out_of_scope_employee_edit() -> None:
    hr_user = _user(
        roles=[
            _role(
                "Scoped HR Manager",
                permissions=[
                    _permission("hr.view_all"),
                    _permission("hr.edit_own_scope"),
                ],
                access_scopes=[
                    _scope("department", "people-ops", can_view=True, can_edit=True),
                ],
            )
        ]
    )
    own_department_employee = EmployeeRecord(
        department_id="people-ops",
        employment_status="ACTIVE",
    )
    other_department_employee = EmployeeRecord(
        department_id="production",
        employment_status="ACTIVE",
    )

    assert build_hr_access_hint(hr_user, other_department_employee, module="hr")["can_view"] is True
    assert can_modify_hr_record(hr_user, "hr", "edit", own_department_employee) is True
    assert can_modify_hr_record(hr_user, "hr", "edit", other_department_employee) is False
    assert build_hr_access_hint(hr_user, other_department_employee, module="hr")["view_only"] is True


def test_gap011_payroll_permission_is_separate_from_generic_hr_view() -> None:
    hr_only_user = _user(roles=[_role("HR Viewer", permissions=[_permission("hr.view")])])
    payroll_viewer = _user(roles=[_role("Payroll Viewer", permissions=[_permission("payroll.view")])])
    payroll_record = PayrollRunRecord(status="DRAFT", company_id="company-a", department_id="people-ops")

    assert build_hr_access_hint(hr_only_user, payroll_record, module="payroll")["can_view"] is False
    assert build_hr_access_hint(payroll_viewer, payroll_record, module="payroll")["can_view"] is True


def test_gap011_scoped_payroll_manage_is_limited_to_assigned_department() -> None:
    payroll_manager = _user(
        roles=[
            _role(
                "Scoped Payroll Manager",
                permissions=[_permission("payroll.view"), _permission("payroll.manage_own_scope")],
                access_scopes=[
                    _scope("department", "people-ops", can_view=True, can_edit=True),
                ],
            )
        ]
    )
    own_department_run = PayrollRunRecord(status="DRAFT", department_id="people-ops")
    other_department_run = PayrollRunRecord(status="DRAFT", department_id="production")

    assert can_modify_hr_record(payroll_manager, "payroll", "manage", own_department_run) is True
    assert can_modify_hr_record(payroll_manager, "payroll", "manage", other_department_run) is False
    assert build_hr_access_hint(payroll_manager, other_department_run, module="payroll")["view_only"] is True


def test_gap011_payroll_status_locks_and_admin_bypass() -> None:
    payroll_approver = _user(roles=[_role("Payroll Approver", permissions=[_permission("payroll_ke.approve")])])
    admin = _user(is_superuser=True)
    draft_run = PayrollRunRecord(status="DRAFT", company_id="company-a")
    calculated_run = PayrollRunRecord(status="CALCULATED", company_id="company-a")

    assert can_modify_hr_record(payroll_approver, "payroll", "approve", calculated_run) is True
    assert can_modify_hr_record(payroll_approver, "payroll", "approve", draft_run) is False
    assert can_modify_hr_record(admin, "payroll", "approve", draft_run) is True

    with pytest.raises(HTTPException) as excinfo:
        ensure_hr_action_allowed(payroll_approver, draft_run, "approve", module="payroll")
    assert excinfo.value.status_code == 422


def test_gap011_hr_scope_inheritance_and_employee_self_ownership() -> None:
    employee = SimpleNamespace(
        id="employee-1",
        user_id="user-1",
        company_id="company-a",
        branch_id="branch-a",
        department_id="people-ops",
        cost_center_id="cc-hr",
    )
    timesheet = SimpleNamespace(company_id=None, branch_id=None, department_id=None, cost_center_id=None)
    same_user = _user(user_id="user-1")
    other_user = _user(user_id="user-2")

    inherit_hr_scope(timesheet, employee)

    assert timesheet.company_id == "company-a"
    assert timesheet.branch_id == "branch-a"
    assert timesheet.department_id == "people-ops"
    assert timesheet.cost_center_id == "cc-hr"
    assert user_owns_employee(same_user, employee) is True
    assert user_owns_employee(other_user, employee) is False


def test_gap011_registry_and_seed_contracts_keep_payroll_explicit() -> None:
    modules = {module.key: module for module in MODULE_DEFINITIONS}

    assert modules["hr"].route_prefix == "/hr"
    assert modules["payroll_ke"].route_prefix == "/payroll-ke"
    assert "approve" in modules["payroll_ke"].permission_actions
    assert "export" in modules["payroll_ke"].permission_actions
    assert not any(route.key == "hr" for route in ENDPOINT_ROUTE_DEFINITIONS)
    assert not any(route.key == "payroll_ke" for route in ENDPOINT_ROUTE_DEFINITIONS)

    seed_source = _read_backend("app/db/seed.py")
    for permission in (
        "hr.view_own_scope",
        "hr.edit_own_scope",
        "employees.view_own_scope",
        "payroll.view",
        "payroll.manage_own_scope",
        "payroll_ke.view",
        "payroll_ke.create",
        "payroll_ke.approve",
        "payroll_ke.export",
    ):
        assert permission in seed_source

    scoped_hr_block = seed_source.split('"scoped_hr_manager"', 1)[1].split('"read_only_auditor"', 1)[0]
    assert '"payroll.manage_own_scope"' in scoped_hr_block
    assert '"payroll_ke.create"' not in scoped_hr_block
    assert '"payroll_ke.approve"' not in scoped_hr_block


def test_gap011_frontend_contracts_guard_sensitive_payroll_surfaces() -> None:
    nav_source = _read_frontend("src/components/nav-config.tsx")
    auth_source = _read_frontend("src/context/AuthContext.tsx")
    payroll_page = _read_frontend("src/app/dashboard/payroll/page.tsx")
    profiles_page = _read_frontend("src/app/dashboard/payroll/profiles/page.tsx")
    reports_page = _read_frontend("src/app/dashboard/payroll/reports/page.tsx")
    run_page = _read_frontend("src/app/dashboard/payroll/runs/[id]/page.tsx")
    hr_types = _read_frontend("src/lib/hr.ts")
    payroll_types = _read_frontend("src/lib/payrollKe.ts")

    assert 'permission: "payroll_ke.view"' in nav_source
    assert 'payroll_ke: "/dashboard/payroll"' in auth_source
    assert 'RequirePermission permission="payroll_ke.view"' in payroll_page
    assert 'RequirePermission permission="payroll_ke.view"' in profiles_page
    assert 'RequirePermission permission="payroll_ke.view"' in reports_page
    assert 'RequirePermission permission="payroll_ke.view"' in run_page
    assert 'hasPermission("payroll_ke.create")' in payroll_page
    assert 'hasPermission("payroll_ke.approve")' in run_page
    assert 'hasPermission("payroll_ke.export")' in reports_page
    assert "View only" in profiles_page
    assert "Export restricted" in reports_page
    assert "interface HRScopeFields" in hr_types
    assert "interface PayrollScopeFields" in payroll_types
