from decimal import Decimal

import pytest

from app.core.module_registry import registry_permission_codes
from app.db.seed import PERMISSIONS, ROLE_DEFINITIONS
from app.schemas.finance import (
    AccountingPostingBatchRead,
    CurrencyRevaluationRunCreate,
    FiscalYearCreate,
    JournalReversalCreate,
    PaymentAllocationCreate,
    RecurringJournalTemplateCreate,
)
from app.services.finance_service import validate_journal_lines_balance


def test_finance_configure_permission_registered_and_seeded():
    registry_codes = registry_permission_codes()
    seed_codes = {f"{module}.{action}" for module, action, *_ in PERMISSIONS}

    assert "finance.configure" in registry_codes
    assert "finance.configure" in seed_codes
    assert "finance.configure" in ROLE_DEFINITIONS["cfo"]["permissions"]
    assert "finance.configure" in ROLE_DEFINITIONS["finance_manager"]["permissions"]
    assert "procurement.configure" not in registry_codes
    assert "production.configure" not in registry_codes


def test_accounting_core_routes_are_registered():
    from app.api.v1.endpoints.finance import router

    route_paths = {route.path for route in router.routes}
    assert "/journal/{entry_id}/reverse" in route_paths
    assert "/accounting/fiscal-years/" in route_paths
    assert "/accounting/period-close-checks/" in route_paths
    assert "/accounting/recurring-journals/" in route_paths
    assert "/accounting/posting-batches/" in route_paths
    assert "/accounting/posting-rules/" in route_paths
    assert "/accounting/payment-allocations/" in route_paths
    assert "/accounting/currency-revaluations/" in route_paths


def test_accounting_core_schemas_import_and_rebuild():
    for schema in (
        FiscalYearCreate,
        JournalReversalCreate,
        RecurringJournalTemplateCreate,
        AccountingPostingBatchRead,
        PaymentAllocationCreate,
        CurrencyRevaluationRunCreate,
    ):
        schema.model_rebuild()


def test_validate_journal_lines_balance_accepts_balanced_lines():
    debit, credit = validate_journal_lines_balance(
        [
            {"account_id": "a", "debit": Decimal("100.00"), "credit": Decimal("0")},
            {"account_id": "b", "debit": Decimal("0"), "credit": Decimal("100.00")},
        ]
    )

    assert debit == Decimal("100.00")
    assert credit == Decimal("100.00")


@pytest.mark.parametrize(
    "lines, expected",
    [
        ([], "at least one line"),
        ([{"debit": Decimal("-1"), "credit": Decimal("0")}], "cannot be negative"),
        ([{"debit": Decimal("1"), "credit": Decimal("1")}], "both debit and credit"),
        ([{"debit": Decimal("0"), "credit": Decimal("0")}], "either a debit or credit"),
        (
            [
                {"debit": Decimal("100.00"), "credit": Decimal("0")},
                {"debit": Decimal("0"), "credit": Decimal("99.00")},
            ],
            "unbalanced",
        ),
    ],
)
def test_validate_journal_lines_balance_rejects_invalid_lines(lines, expected):
    with pytest.raises(ValueError, match=expected):
        validate_journal_lines_balance(lines)
