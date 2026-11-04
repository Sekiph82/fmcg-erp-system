"""Tolerance configuration and exception approval policy tests for M34.S04.T002."""
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from types import SimpleNamespace
from uuid import uuid4

from app.api.v1.endpoints import invoice_match
from app.models.invoice_match import MatchLineStatus
from app.schemas.invoice_match import MatchDecisionRequest, ToleranceRuleCreate, ToleranceRuleUpdate
from app.services import invoice_match_service
from app.services.invoice_match_service import (
    InvoiceMatchApprovalRoleError,
    _validate_exception_approval,
)


def test_tolerance_rule_create_requires_a_name_and_finite_nonnegative_values():
    with pytest.raises(ValidationError, match="rule_name"):
        ToleranceRuleCreate(rule_name="   ")

    with pytest.raises(ValidationError, match="finite and nonnegative"):
        ToleranceRuleCreate(rule_name="Synthetic policy", price_tolerance_pct=Decimal("-0.01"))

    for value in (Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(ValidationError, match="finite"):
            ToleranceRuleCreate(rule_name="Synthetic policy", price_tolerance_pct=value)

    policy = ToleranceRuleCreate(
        rule_name="  Synthetic policy  ",
        quantity_tolerance_pct=Decimal("0"),
        approval_role_required=" finance_manager ",
    )
    assert policy.rule_name == "Synthetic policy"
    assert policy.approval_role_required == "finance_manager"


def test_tolerance_update_supports_explicit_clear_without_nulling_rule_name():
    update = ToleranceRuleUpdate(
        approval_role_required=None,
        quantity_tolerance_abs=None,
    )
    assert update.model_dump(exclude_unset=True) == {
        "approval_role_required": None,
        "quantity_tolerance_abs": None,
    }

    with pytest.raises(ValidationError, match="rule_name"):
        ToleranceRuleUpdate(rule_name=None)

    with pytest.raises(ValidationError, match="quantity_tolerance_pct"):
        ToleranceRuleUpdate(quantity_tolerance_pct=None)

    with pytest.raises(ValidationError, match="finite and nonnegative"):
        ToleranceRuleUpdate(tax_tolerance_pct=Decimal("-1"))


def test_absolute_and_percentage_tolerances_must_both_pass_when_both_are_configured():
    rule = ToleranceRuleCreate(
        rule_name="Synthetic combined tolerance",
        quantity_tolerance_pct=Decimal("5"),
        quantity_tolerance_abs=Decimal("0.1"),
        price_tolerance_pct=Decimal("10"),
        price_tolerance_abs=Decimal("1"),
        tax_tolerance_pct=Decimal("0"),
    )
    status = invoice_match_service._evaluate_line_status(
        po_line=object(),
        grn_lines=[object()],
        invoiced_qty=Decimal("10.2"),
        billable_qty=Decimal("10"),
        qty_var_pct=Decimal("2"),
        price_var_pct=Decimal("2"),
        tax_var=Decimal("0"),
        rule=rule,
        qty_var_abs=Decimal("0.2"),
        price_var_abs=Decimal("2"),
    )
    assert status == MatchLineStatus.QUANTITY_MISMATCH

    price_status = invoice_match_service._evaluate_line_status(
        po_line=object(),
        grn_lines=[object()],
        invoiced_qty=Decimal("10"),
        billable_qty=Decimal("10"),
        qty_var_pct=Decimal("0"),
        price_var_pct=Decimal("2"),
        tax_var=Decimal("0"),
        rule=rule,
        qty_var_abs=Decimal("0"),
        price_var_abs=Decimal("2"),
    )
    assert price_status == MatchLineStatus.PRICE_MISMATCH


def test_exception_approval_requires_configured_role_and_justification():
    policy = {
        "duplicate_flag": False,
        "review_required": True,
        "line_statuses": [MatchLineStatus.PRICE_MISMATCH],
        "required_roles": {"Finance_Manager"},
        "actor_role_names": {"finance_staff"},
        "justification": "Synthetic exception evidence",
    }

    with pytest.raises(InvoiceMatchApprovalRoleError, match="Finance_Manager"):
        _validate_exception_approval(**policy)

    _validate_exception_approval(**{**policy, "actor_role_names": {"finance_manager"}})
    _validate_exception_approval(**{**policy, "actor_role_names": {"*"}})
    _validate_exception_approval(**{
        **policy,
        "line_statuses": [MatchLineStatus.MATCHED_WITHIN_TOLERANCE],
        "actor_role_names": {"finance_manager"},
    })

    with pytest.raises(ValueError, match="justification is required"):
        _validate_exception_approval(**{**policy, "justification": "  "})


@pytest.mark.parametrize(
    "status",
    [
        MatchLineStatus.MISSING_PO,
        MatchLineStatus.MISSING_GRN,
        MatchLineStatus.BLOCKED,
        MatchLineStatus.OVERBILLED,
    ],
)
def test_structural_and_overbilling_exceptions_are_not_approvable(status):
    with pytest.raises(ValueError, match="cannot be exception-approved"):
        _validate_exception_approval(
            duplicate_flag=False,
            review_required=True,
            line_statuses=[status],
            required_roles=set(),
            actor_role_names={"finance_manager"},
            justification="Synthetic reviewed exception",
        )


def test_duplicate_or_exactly_matched_invoice_cannot_be_exception_approved():
    common = {
        "review_required": True,
        "line_statuses": [MatchLineStatus.PRICE_MISMATCH],
        "required_roles": set(),
        "actor_role_names": {"finance_manager"},
        "justification": "Synthetic reviewed exception",
    }
    with pytest.raises(ValueError, match="Duplicate-suspected"):
        _validate_exception_approval(duplicate_flag=True, **common)

    with pytest.raises(ValueError, match="no tolerance exception"):
        _validate_exception_approval(
            duplicate_flag=False,
            **{**common, "line_statuses": [MatchLineStatus.FULLY_MATCHED]},
        )


@pytest.mark.asyncio
async def test_api_maps_missing_tolerance_role_to_forbidden(monkeypatch):
    user = SimpleNamespace(
        email="synthetic.finance@example.invalid",
        is_superuser=False,
        roles=[SimpleNamespace(name="finance_staff")],
    )

    async def reject_missing_role(_db, _header_id, _payload, *, actor_role_names):
        assert actor_role_names == {"finance_staff"}
        raise invoice_match_service.InvoiceMatchApprovalRoleError("finance_manager required")

    monkeypatch.setattr(invoice_match.svc, "submit_review", reject_missing_role)
    with pytest.raises(HTTPException) as error:
        await invoice_match.approve_exception(
            uuid4(),
            MatchDecisionRequest(
                expected_run_at="2026-11-04T12:00:00",
                justification="Synthetic request",
            ),
            db=None,
            current_user=user,
        )

    assert error.value.status_code == 403


def test_superuser_is_passed_as_explicit_role_override():
    user = SimpleNamespace(is_superuser=True, roles=[])
    assert invoice_match._actor_role_names(user) == {"*"}
