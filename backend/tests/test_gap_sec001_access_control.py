from types import SimpleNamespace
from pathlib import Path

from app.core.access_control import (
    can_modify_by_status,
    can_modify_record,
    can_modify_scope,
    can_perform_in_scope,
    can_view_record,
    get_effective_modules,
    get_effective_permission_codes,
    get_effective_scopes,
    has_permission,
)


def permission(code: str):
    module, action = code.split(".", 1)
    return SimpleNamespace(code=code, module=module, action=action, is_active=True)


def scope(scope_type: str, scope_id: str, **actions):
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


def role(name: str, permissions=None, access_scopes=None, is_active=True):
    return SimpleNamespace(
        name=name,
        is_active=is_active,
        permissions=permissions or [],
        access_scopes=access_scopes or [],
    )


def user(roles=None, access_scopes=None, is_superuser=False):
    return SimpleNamespace(
        is_superuser=is_superuser,
        roles=roles or [],
        access_scopes=access_scopes or [],
    )


def test_broad_inventory_view_does_not_grant_out_of_scope_edit():
    warehouse_manager = user(
        roles=[
            role(
                "Warehouse Manager",
                permissions=[
                    permission("inventory.view_all"),
                    permission("inventory.edit_own_scope"),
                ],
                access_scopes=[
                    scope("warehouse", "nairobi", can_view=True, can_edit=True),
                ],
            )
        ]
    )

    nairobi_stock = SimpleNamespace(warehouse_id="nairobi", status="DRAFT")
    mombasa_stock = SimpleNamespace(warehouse_id="mombasa", status="DRAFT")

    assert can_view_record(warehouse_manager, "inventory", mombasa_stock) is True
    assert can_modify_record(warehouse_manager, "inventory", "edit", nairobi_stock) is True
    assert can_modify_record(warehouse_manager, "inventory", "edit", mombasa_stock) is False


def test_user_scope_override_wins_over_role_scope():
    scoped_user = user(
        roles=[
            role(
                "Role Grant",
                permissions=[permission("inventory.edit_own_scope")],
                access_scopes=[scope("warehouse", "nairobi", can_edit=True)],
            )
        ],
        access_scopes=[scope("warehouse", "nairobi", can_edit=False)],
    )

    assert can_perform_in_scope(scoped_user, "warehouse", "nairobi", "edit") is False


def test_effective_scope_payload_merges_roles_and_user_overrides():
    scoped_user = user(
        roles=[
            role(
                "Role Grant",
                permissions=[permission("inventory.view_own_scope")],
                access_scopes=[
                    scope("warehouse", "nairobi", can_view=True),
                    scope("warehouse", "mombasa", can_view=True),
                ],
            )
        ],
        access_scopes=[scope("warehouse", "mombasa", can_view=False, can_edit=True)],
    )

    effective = {
        (item["scope_type"], item["scope_id"]): item
        for item in get_effective_scopes(scoped_user)
    }

    assert effective[("warehouse", "nairobi")]["can_view"] is True
    assert effective[("warehouse", "nairobi")]["source"] == "role"
    assert effective[("warehouse", "mombasa")]["can_view"] is False
    assert effective[("warehouse", "mombasa")]["can_edit"] is True
    assert effective[("warehouse", "mombasa")]["source"] == "user"


def test_permissions_filter_inactive_roles_and_permissions():
    scoped_user = user(
        roles=[
            role("Inactive Role", permissions=[permission("finance.post_all")], is_active=False),
            role(
                "Active Role",
                permissions=[
                    permission("finance.view_all"),
                    SimpleNamespace(code="finance.edit_all", is_active=False),
                ],
            ),
        ]
    )

    assert get_effective_permission_codes(scoped_user) == ["finance.view_all"]
    assert get_effective_modules(scoped_user) == ["finance"]
    assert has_permission(scoped_user, "finance.edit_all") is False


def test_status_lock_blocks_mutation_for_non_superuser():
    finance_user = user(roles=[role("Finance", permissions=[permission("finance.edit_all")])])
    posted_invoice = SimpleNamespace(company_id="company-1", status="POSTED")

    assert can_modify_by_status("finance", "edit", "POSTED") is False
    assert can_modify_record(finance_user, "finance", "edit", posted_invoice) is False


def test_production_view_all_does_not_grant_out_of_scope_release():
    production_manager = user(
        roles=[
            role(
                "Production Manager",
                permissions=[
                    permission("production.view_all"),
                    permission("production.release_own_scope"),
                    permission("production.close_own_scope"),
                    permission("production.cancel_own_scope"),
                ],
                access_scopes=[
                    scope("warehouse", "nairobi-fg", can_view=True, can_release=True, can_cancel=True),
                ],
            )
        ]
    )

    nairobi_order = SimpleNamespace(target_warehouse_id="nairobi-fg", status="PLANNED")
    mombasa_order = SimpleNamespace(target_warehouse_id="mombasa-fg", status="PLANNED")

    assert can_view_record(production_manager, "production", mombasa_order) is True
    assert can_modify_scope(production_manager, "production", "release", "warehouse", "nairobi-fg") is True
    assert can_modify_scope(production_manager, "production", "release", "warehouse", "mombasa-fg") is False
    assert can_modify_record(production_manager, "production", "close", nairobi_order) is True
    assert can_modify_record(production_manager, "production", "cancel", mombasa_order) is False


def test_sales_view_all_does_not_grant_out_of_region_edit():
    sales_manager = user(
        roles=[
            role(
                "Sales Manager",
                permissions=[
                    permission("sales.view_all"),
                    permission("sales.create_own_region"),
                    permission("sales.edit_own_region"),
                ],
                access_scopes=[
                    scope("sales_region", "Nairobi", can_view=True, can_create=True, can_edit=True),
                ],
            )
        ]
    )

    nairobi_customer = SimpleNamespace(region="Nairobi", status="DRAFT")
    mombasa_customer = SimpleNamespace(region="Mombasa", status="DRAFT")

    assert can_view_record(sales_manager, "sales", mombasa_customer) is True
    assert can_modify_scope(sales_manager, "sales", "create", "sales_region", "Nairobi") is True
    assert can_modify_scope(sales_manager, "sales", "edit", "sales_region", "Nairobi") is True
    assert can_modify_scope(sales_manager, "sales", "edit", "sales_region", "Mombasa") is False
    assert can_modify_record(sales_manager, "sales", "edit", nairobi_customer) is True
    assert can_modify_record(sales_manager, "sales", "edit", mombasa_customer) is False


def test_procurement_view_all_does_not_grant_out_of_department_approval():
    buyer = user(
        roles=[
            role(
                "Procurement Manager",
                permissions=[
                    permission("procurement.view_all"),
                    permission("procurement.create_own_scope"),
                    permission("procurement.edit_own_scope"),
                    permission("procurement.approve_own_scope"),
                ],
                access_scopes=[
                    scope("department", "Packaging", can_view=True, can_create=True, can_edit=True, can_approve=True),
                ],
            )
        ]
    )

    packaging_pr = SimpleNamespace(department="Packaging", status="DRAFT")
    engineering_pr = SimpleNamespace(department="Engineering", status="DRAFT")

    assert can_view_record(buyer, "procurement", engineering_pr) is True
    assert can_modify_scope(buyer, "procurement", "create", "department", "Packaging") is True
    assert can_modify_scope(buyer, "procurement", "edit", "department", "Packaging") is True
    assert can_modify_scope(buyer, "procurement", "approve", "department", "Packaging") is True
    assert can_modify_record(buyer, "procurement", "approve", packaging_pr) is True
    assert can_modify_record(buyer, "procurement", "approve", engineering_pr) is False


def test_quality_view_all_does_not_grant_out_of_scope_release():
    quality_manager = user(
        roles=[
            role(
                "Quality Manager",
                permissions=[
                    permission("quality.view_all"),
                    permission("quality.create_own_scope"),
                    permission("quality.edit_own_scope"),
                    permission("quality.approve_own_scope"),
                    permission("quality.release_own_scope"),
                ],
                access_scopes=[
                    scope("warehouse", "nairobi-qc", can_view=True, can_create=True, can_edit=True, can_approve=True, can_release=True),
                ],
            )
        ]
    )

    nairobi_lot = SimpleNamespace(warehouse_id="nairobi-qc", status="IN_PROGRESS")
    mombasa_lot = SimpleNamespace(warehouse_id="mombasa-qc", status="IN_PROGRESS")

    assert can_view_record(quality_manager, "quality", mombasa_lot) is True
    assert can_modify_scope(quality_manager, "quality", "approve", "warehouse", "nairobi-qc") is True
    assert can_modify_scope(quality_manager, "quality", "release", "warehouse", "nairobi-qc") is True
    assert can_modify_record(quality_manager, "quality", "release", nairobi_lot) is True
    assert can_modify_record(quality_manager, "quality", "release", mombasa_lot) is False


def test_finance_view_scope_does_not_grant_out_of_company_posting():
    finance_manager = user(
        roles=[
            role(
                "Finance Manager",
                permissions=[
                    permission("finance.view_own_scope"),
                    permission("finance.create_own_scope"),
                    permission("finance.post_own_scope"),
                ],
                access_scopes=[
                    scope("company", "company-a", can_view=True, can_create=True, can_post=True),
                ],
            )
        ]
    )

    own_company_entry = SimpleNamespace(company_id="company-a", status="DRAFT")
    other_company_entry = SimpleNamespace(company_id="company-b", status="DRAFT")
    posted_entry = SimpleNamespace(company_id="company-a", status="POSTED")

    assert can_view_record(finance_manager, "finance", own_company_entry) is True
    assert can_view_record(finance_manager, "finance", other_company_entry) is False
    assert can_modify_scope(finance_manager, "finance", "post", "company", "company-a") is True
    assert can_modify_record(finance_manager, "finance", "post", own_company_entry) is True
    assert can_modify_record(finance_manager, "finance", "post", other_company_entry) is False
    assert can_modify_record(finance_manager, "finance", "post", posted_entry) is False


def test_superuser_bypasses_permission_and_scope_checks():
    admin = user(is_superuser=True)
    record = SimpleNamespace(warehouse_id="mombasa", status="POSTED")

    assert get_effective_permission_codes(admin) == ["*"]
    assert can_view_record(admin, "inventory", record) is True
    assert can_modify_record(admin, "inventory", "edit", record) is True


def test_seed_defines_scope_aware_permissions_and_conservative_roles():
    from app.db.seed import DEFAULT_ROLE_ACCESS_SCOPES, PERMISSIONS, ROLE_DEFINITIONS

    permission_codes = {f"{module}.{action}" for module, action, *_ in PERMISSIONS}
    for code in {
        "inventory.view_all",
        "inventory.edit_own_scope",
        "inventory.adjust_own_scope",
        "inventory.transfer_own_scope",
        "sales.create_own_region",
        "sales.edit_own_region",
        "production.create_own_scope",
        "production.release_own_scope",
        "production.cancel_own_scope",
        "procurement.create_all",
        "quality.create_own_scope",
        "quality.release_own_scope",
        "finance.create_own_scope",
        "finance.post_own_scope",
        "users.manage",
        "roles.manage",
    }:
        assert code in permission_codes

    warehouse_manager = ROLE_DEFINITIONS["warehouse_manager"]["permissions"]
    assert "inventory.view_all" in warehouse_manager
    assert "inventory.edit_own_scope" in warehouse_manager
    assert "inventory.transfer_own_scope" in warehouse_manager
    assert "inventory.edit_all" not in warehouse_manager

    assert DEFAULT_ROLE_ACCESS_SCOPES["owner"][0]["scope_id"] == "ALL"
    assert DEFAULT_ROLE_ACCESS_SCOPES["admin"][0]["can_edit"] is True
    assert "warehouse_manager" not in DEFAULT_ROLE_ACCESS_SCOPES


def test_critical_endpoint_modules_call_scoped_access_helpers():
    backend_root = Path(__file__).resolve().parents[1]
    endpoint_expectations = {
        "inventory.py": ["_require_warehouse_action", "_require_transfer_scope"],
        "production.py": ["_require_order_action", "_require_order_create_scope"],
        "sales.py": ["_require_customer_action", "_require_so_action"],
        "procurement.py": ["_require_procurement_action", "_require_procurement_view"],
        "quality.py": ["_require_inspection_action", "_require_inspection_view"],
        "finance.py": ["_require_finance_action", "_require_finance_view"],
    }

    for filename, required_snippets in endpoint_expectations.items():
        source = (backend_root / "app" / "api" / "v1" / "endpoints" / filename).read_text(encoding="utf-8", errors="ignore")
        for snippet in required_snippets:
            assert snippet in source, f"{filename} is missing scoped access helper {snippet}"
