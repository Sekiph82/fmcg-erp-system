from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.access_control import can_modify_record, can_view_record
from app.core.module_registry import ENDPOINT_ROUTE_DEFINITIONS, MODULE_DEFINITIONS
from app.models.crm import CRMRecord, CRMStatus
from app.models.quotation import Quotation, QuoteStatus
from app.models.sales import Customer, SOStatus, SalesOrder
from app.services.commercial_access_service import (
    build_commercial_access_hint,
    can_change_commercial_status,
    commercial_module_key,
    ensure_commercial_action_allowed,
    inherit_commercial_scope,
)


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent


def _read_backend(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _read_frontend(path: str) -> str:
    return (REPO_ROOT / "frontend" / path).read_text(encoding="utf-8")


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


def _user(roles=None, access_scopes=None, is_superuser=False):
    return SimpleNamespace(
        is_superuser=is_superuser,
        roles=roles or [],
        access_scopes=access_scopes or [],
    )


def test_gap010_broad_sales_view_does_not_grant_out_of_region_customer_edit() -> None:
    sales_manager = _user(
        roles=[
            _role(
                "Regional Sales Manager",
                permissions=[
                    _permission("sales.view_all"),
                    _permission("sales.edit_own_region"),
                ],
                access_scopes=[
                    _scope("sales_region", "Nairobi", can_view=True, can_edit=True),
                ],
            )
        ]
    )
    nairobi_customer = Customer(code="C-NBO", name="Nairobi Retailer", sales_region_id="Nairobi", is_active=True)
    mombasa_customer = Customer(code="C-MBA", name="Mombasa Retailer", sales_region_id="Mombasa", is_active=True)

    assert can_view_record(sales_manager, "sales", mombasa_customer) is True
    assert can_modify_record(sales_manager, "sales", "edit", nairobi_customer) is True
    assert can_modify_record(sales_manager, "sales", "edit", mombasa_customer) is False

    access = build_commercial_access_hint(sales_manager, mombasa_customer)
    assert access.can_view is True
    assert access.view_only is True
    assert access.can_edit is False
    assert "cannot modify" in (access.reason or "")


def test_gap010_commercial_scope_inheritance_and_status_locks() -> None:
    customer = Customer(
        code="C-SCOPE",
        name="Scoped Customer",
        company_id="00000000-0000-0000-0000-000000000001",
        branch_id="00000000-0000-0000-0000-000000000002",
        sales_region_id="Nairobi",
        sales_team_id="Modern Trade",
        customer_group_id="Supermarkets",
        is_active=True,
    )
    order = SalesOrder(
        order_no="SO-SCOPE",
        customer_id="00000000-0000-0000-0000-000000000003",
        order_date="2026-05-15",
        requested_delivery_date="2026-05-20",
        status=SOStatus.DRAFT,
    )

    inherit_commercial_scope(order, customer)

    assert str(order.company_id) == "00000000-0000-0000-0000-000000000001"
    assert str(order.branch_id) == "00000000-0000-0000-0000-000000000002"
    assert order.sales_region_id == "Nairobi"
    assert commercial_module_key(order) == "sales"
    assert can_change_commercial_status(order, "edit") is True

    order.status = SOStatus.CONFIRMED
    assert can_change_commercial_status(order, "edit") is False


def test_gap010_quote_convert_requires_status_permission_and_scope() -> None:
    sales_manager = _user(
        roles=[
            _role(
                "Regional Sales Manager",
                permissions=[
                    _permission("sales.view_all"),
                    _permission("sales.convert_own_region"),
                ],
                access_scopes=[
                    _scope("sales_region", "Nairobi", can_view=True, can_create=True),
                ],
            )
        ]
    )
    allowed_quote = Quotation(
        quote_no="QT-NBO",
        version=1,
        customer_id="00000000-0000-0000-0000-000000000011",
        status=QuoteStatus.ACCEPTED,
        quote_date="2026-05-15",
        sales_region_id="Nairobi",
    )
    outside_quote = Quotation(
        quote_no="QT-MBA",
        version=1,
        customer_id="00000000-0000-0000-0000-000000000012",
        status=QuoteStatus.ACCEPTED,
        quote_date="2026-05-15",
        sales_region_id="Mombasa",
    )
    draft_quote = Quotation(
        quote_no="QT-DRAFT",
        version=1,
        customer_id="00000000-0000-0000-0000-000000000013",
        status=QuoteStatus.DRAFT,
        quote_date="2026-05-15",
        sales_region_id="Nairobi",
    )

    assert build_commercial_access_hint(sales_manager, allowed_quote).can_convert is True
    assert build_commercial_access_hint(sales_manager, outside_quote).can_convert is False
    assert build_commercial_access_hint(sales_manager, draft_quote).can_convert is False

    with pytest.raises(HTTPException) as excinfo:
        ensure_commercial_action_allowed(sales_manager, outside_quote, "convert")
    assert excinfo.value.status_code == 403

    with pytest.raises(HTTPException) as status_exc:
        ensure_commercial_action_allowed(sales_manager, draft_quote, "convert")
    assert status_exc.value.status_code == 422


def test_gap010_crm_scoped_edit_and_superuser_bypass() -> None:
    crm_user = _user(
        roles=[
            _role(
                "CRM Manager",
                permissions=[
                    _permission("crm.view_all"),
                    _permission("crm.edit_own_region"),
                ],
                access_scopes=[
                    _scope("sales_region", "Nairobi", can_view=True, can_edit=True),
                ],
            )
        ]
    )
    admin = _user(is_superuser=True)
    nairobi_lead = CRMRecord(company_name="Nairobi Lead", status=CRMStatus.OPEN, sales_region_id="Nairobi")
    mombasa_lead = CRMRecord(company_name="Mombasa Lead", status=CRMStatus.OPEN, sales_region_id="Mombasa")

    assert commercial_module_key(nairobi_lead) == "crm"
    assert can_view_record(crm_user, "crm", mombasa_lead) is True
    assert can_modify_record(crm_user, "crm", "edit", nairobi_lead) is True
    assert can_modify_record(crm_user, "crm", "edit", mombasa_lead) is False

    outside_access = build_commercial_access_hint(crm_user, mombasa_lead)
    assert outside_access.view_only is True
    assert outside_access.can_edit is False
    assert build_commercial_access_hint(admin, mombasa_lead).can_edit is True


def test_gap010_registry_and_seed_contracts_are_scope_aware() -> None:
    modules = {module.key: module for module in MODULE_DEFINITIONS}

    assert "sales" in modules
    assert "crm" in modules
    assert "convert" in modules["sales"].permission_actions
    assert "convert" in modules["crm"].permission_actions
    assert modules["crm"].import_path == "app.api.v1.endpoints.crm_pipeline"
    assert not any(route.key == "crm_pipeline" for route in ENDPOINT_ROUTE_DEFINITIONS)

    seed_source = _read_backend("app/db/seed.py")
    for permission in (
        "sales.view_all",
        "sales.edit_own_region",
        "sales.convert_own_region",
        "crm.view_all",
        "crm.create_own_region",
        "crm.edit_own_region",
        "crm.convert_own_region",
    ):
        assert permission in seed_source

    assert '"regional_sales_manager"' in seed_source
    assert '"sales.edit_all"' not in seed_source.split('"regional_sales_manager"', 1)[1].split('"scoped_finance_manager"', 1)[0]
    assert '"crm.edit_all"' not in seed_source.split('"regional_sales_manager"', 1)[1].split('"scoped_finance_manager"', 1)[0]


def test_gap010_frontend_contracts_expose_view_only_commercial_rows() -> None:
    sales_types = _read_frontend("src/lib/sales.ts")
    quote_types = _read_frontend("src/lib/quotations.ts")
    crm_types = _read_frontend("src/lib/crm_pipeline.ts")
    customers_page = _read_frontend("src/app/dashboard/sales/customers/page.tsx")
    orders_page = _read_frontend("src/app/dashboard/sales/orders/page.tsx")
    quotes_page = _read_frontend("src/app/dashboard/sales/quotes/page.tsx")
    crm_page = _read_frontend("src/app/dashboard/crm/pipeline/page.tsx")

    assert "interface CommercialAccessHint" in sales_types
    assert "can_convert" in sales_types
    assert "access?: CommercialAccessHint" in quote_types
    assert "withCredentials: true" in crm_types

    for source in (customers_page, orders_page, quotes_page, crm_page):
        assert "View only" in source

    assert "disabled={r.access?.can_edit === false}" in customers_page
    assert "(access?.can_convert ?? true)" in quotes_page
    assert "draggable={rec.access?.can_edit !== false}" in crm_page
