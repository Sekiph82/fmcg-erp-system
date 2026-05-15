from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from app.models.master import Supplier, SupplierQualificationStatus, SupplierRiskLevel
from app.models.procurement import (
    AutoReorderPolicy,
    GoodsReceipt,
    GRNStatus,
    ProcurementApprovalRule,
    PRStatus,
    PurchaseOrder,
    PurchaseRequisition,
)
from app.schemas.procurement import ProcurementAccessHint, ProcurementApprovalRuleCreate, PRRead
from app.services.procurement_service import (
    can_change_procurement_status,
    inherit_procurement_scope,
    procurement_document_amount,
)


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_gap009_migration_contains_scope_and_approval_rule_contracts() -> None:
    source = _read("alembic/versions/20260514_0030_procurement_scope_governance.py")

    for table_name in (
        "purchase_requisitions",
        "purchase_orders",
        "goods_receipts",
        "rfq_requests",
        "blanket_purchase_agreements",
        "auto_reorder_policies",
    ):
        assert table_name in source

    for token in (
        "company_id",
        "branch_id",
        "cost_center_id",
        "supplier_qualification_status",
        "supplier_risk_level",
        "procurement_approval_rules",
        "ck_procurement_approval_rules_approver",
    ):
        assert token in source


def test_gap009_models_expose_supplier_governance_and_procurement_scope_fields() -> None:
    assert "supplier_category" in Supplier.__table__.columns
    assert "qualification_status" in Supplier.__table__.columns
    assert "risk_level" in Supplier.__table__.columns
    assert SupplierQualificationStatus.APPROVED.value == "APPROVED"
    assert SupplierRiskLevel.CRITICAL.value == "CRITICAL"

    for model in (
        PurchaseRequisition,
        PurchaseOrder,
        GoodsReceipt,
        AutoReorderPolicy,
    ):
        for column_name in ("company_id", "branch_id", "cost_center_id", "department"):
            assert column_name in model.__table__.columns

    assert ProcurementApprovalRule.__tablename__ == "procurement_approval_rules"
    assert "approver_role_id" in ProcurementApprovalRule.__table__.columns


def test_gap009_schemas_expose_access_hints_and_approval_rules() -> None:
    hint = ProcurementAccessHint(can_view=True, view_only=True, reason="scope")
    assert hint.view_only is True
    assert "access" in PRRead.model_fields

    rule = ProcurementApprovalRuleCreate(
        rule_name="Scoped PO approval",
        document_type="PO",
        approver_role_id="00000000-0000-0000-0000-000000000001",
    )
    assert rule.document_type.value == "PO"


def test_gap009_service_helpers_copy_scope_and_lock_statuses() -> None:
    pr = PurchaseRequisition(
        pr_no="PR-T",
        requester_id="00000000-0000-0000-0000-000000000001",
        required_date="2026-05-14",
        status=PRStatus.APPROVED,
        company_id="00000000-0000-0000-0000-000000000002",
        branch_id="00000000-0000-0000-0000-000000000003",
        cost_center_id="00000000-0000-0000-0000-000000000004",
        department="Manufacturing",
    )
    po = PurchaseOrder(
        po_no="PO-T",
        supplier_id="00000000-0000-0000-0000-000000000005",
        order_date="2026-05-14",
        expected_delivery_date="2026-05-20",
    )

    inherit_procurement_scope(po, pr)

    assert str(po.company_id) == "00000000-0000-0000-0000-000000000002"
    assert str(po.branch_id) == "00000000-0000-0000-0000-000000000003"
    assert po.department == "Manufacturing"
    assert can_change_procurement_status(pr, "convert") is True

    posted_grn = GoodsReceipt(
        grn_no="GRN-T",
        po_id="00000000-0000-0000-0000-000000000006",
        received_date="2026-05-14",
        warehouse_id="00000000-0000-0000-0000-000000000007",
        status=GRNStatus.POSTED,
    )
    assert can_change_procurement_status(posted_grn, "post") is False


def test_gap009_document_amount_uses_pr_or_po_line_values() -> None:
    record = SimpleNamespace(
        lines=[
            SimpleNamespace(quantity=Decimal("2"), estimated_unit_cost=Decimal("3.50")),
            SimpleNamespace(ordered_quantity=Decimal("5"), unit_price=Decimal("10")),
        ]
    )
    assert procurement_document_amount(record) == Decimal("57.00")


def test_gap009_endpoint_frontend_and_seed_contracts() -> None:
    endpoint_source = _read("app/api/v1/endpoints/procurement.py")
    frontend_source = (ROOT.parent / "frontend/src/lib/procurement.ts").read_text(encoding="utf-8")
    page_source = (ROOT.parent / "frontend/src/app/dashboard/procurement/page.tsx").read_text(encoding="utf-8")
    seed_source = _read("app/db/seed.py")

    for token in (
        "approval-rules",
        "build_procurement_access_hint",
        "ensure_procurement_action_allowed",
    ):
        assert token in endpoint_source

    assert "ProcurementAccessHint" in frontend_source
    assert "ProcurementApprovalRule" in frontend_source
    assert "View only" in page_source

    for permission in (
        "procurement.receive_own_scope",
        "procurement.post_own_scope",
        "procurement.cancel_own_scope",
        "procurement.export_own_scope",
        "procurement.import_own_scope",
    ):
        assert permission in seed_source
