"""Commercial access helpers for CRM, sales, and quotation workflows."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.core.access_control import can_modify_record, can_view_record, forbidden_detail
from app.models.crm import CRMRecord, CRMStatus, CRMTerritory
from app.models.quotation import Quotation, QuoteStatus
from app.models.sales import Customer, SalesOrder, SOStatus
from app.schemas.sales import CommercialAccessHint


COMMERCIAL_SCOPE_FIELDS = (
    "company_id",
    "branch_id",
    "sales_region_id",
    "sales_team_id",
    "customer_group_id",
)

COMMERCIAL_ACTION_STATUSES: dict[str, dict[str, set[str]]] = {
    "customer": {
        "edit": {"ACTIVE"},
        "delete": set(),
    },
    "sales_order": {
        "edit": {SOStatus.DRAFT.value},
        "approve": {SOStatus.DRAFT.value, SOStatus.CONFIRMED.value},
        "cancel": {SOStatus.DRAFT.value, SOStatus.CONFIRMED.value, SOStatus.ALLOCATED.value, SOStatus.PICKING.value},
        "convert": set(),
    },
    "quotation": {
        "edit": {QuoteStatus.DRAFT.value},
        "approve": {QuoteStatus.DRAFT.value, QuoteStatus.SENT.value},
        "convert": {QuoteStatus.ACCEPTED.value},
        "cancel": {QuoteStatus.DRAFT.value, QuoteStatus.SENT.value},
        "delete": {QuoteStatus.DRAFT.value},
    },
    "crm_record": {
        "edit": {CRMStatus.OPEN.value, CRMStatus.ON_HOLD.value},
        "convert": {CRMStatus.OPEN.value},
        "cancel": {CRMStatus.OPEN.value, CRMStatus.ON_HOLD.value},
        "delete": {CRMStatus.OPEN.value},
    },
    "territory": {
        "edit": {"ACTIVE"},
        "delete": set(),
    },
}


def commercial_document_key(record: Any) -> str:
    if isinstance(record, Customer):
        return "customer"
    if isinstance(record, SalesOrder):
        return "sales_order"
    if isinstance(record, Quotation):
        return "quotation"
    if isinstance(record, CRMRecord):
        return "crm_record"
    if isinstance(record, CRMTerritory):
        return "territory"
    name = record.__class__.__name__.lower()
    if "quotation" in name:
        return "quotation"
    if "salesorder" in name or "sales_order" in name:
        return "sales_order"
    if "crmrecord" in name or "crm_record" in name:
        return "crm_record"
    if "territory" in name:
        return "territory"
    if "customer" in name:
        return "customer"
    return name


def commercial_module_key(record: Any) -> str:
    document_key = commercial_document_key(record)
    if document_key in {"crm_record", "territory"}:
        return "crm"
    return "sales"


def inherit_commercial_scope(target: Any, source: Any, overwrite: bool = False) -> None:
    for field_name in COMMERCIAL_SCOPE_FIELDS:
        if not hasattr(target, field_name) or not hasattr(source, field_name):
            continue
        if overwrite or getattr(target, field_name, None) is None:
            setattr(target, field_name, getattr(source, field_name, None))


def _status_value(record: Any) -> str | None:
    if isinstance(record, Customer):
        return "ACTIVE" if getattr(record, "is_active", False) else "INACTIVE"
    if isinstance(record, CRMTerritory):
        return "ACTIVE" if getattr(record, "active_flag", False) else "INACTIVE"
    value = getattr(record, "status", None)
    if value is None:
        return None
    return str(getattr(value, "value", value))


def can_change_commercial_status(record: Any, action: str) -> bool:
    document_key = commercial_document_key(record)
    allowed_statuses = COMMERCIAL_ACTION_STATUSES.get(document_key, {}).get(action)
    if allowed_statuses is None:
        return True
    if not allowed_statuses:
        return False
    return _status_value(record) in allowed_statuses


def build_commercial_access_hint(user: Any, record: Any, module: str | None = None) -> CommercialAccessHint:
    module_key = module or commercial_module_key(record)
    can_view = can_view_record(user, module_key, record)
    actions = {
        "can_create": can_modify_record(user, module_key, "create", record),
        "can_edit": can_change_commercial_status(record, "edit") and can_modify_record(user, module_key, "edit", record),
        "can_delete": can_change_commercial_status(record, "delete") and can_modify_record(user, module_key, "delete", record),
        "can_approve": can_change_commercial_status(record, "approve") and can_modify_record(user, module_key, "approve", record),
        "can_convert": can_change_commercial_status(record, "convert") and can_modify_record(user, module_key, "convert", record),
        "can_discount_approve": can_change_commercial_status(record, "approve") and can_modify_record(user, module_key, "approve", record),
        "can_cancel": can_change_commercial_status(record, "cancel") and can_modify_record(user, module_key, "cancel", record),
        "can_export": can_modify_record(user, module_key, "export", record),
        "can_import": can_modify_record(user, module_key, "import", record),
    }
    mutation_allowed = any(actions.values())
    reason = None
    if can_view and not mutation_allowed:
        reason = "You can view this commercial record but cannot modify it in this scope or status."
    return CommercialAccessHint(
        can_view=can_view,
        view_only=can_view and not mutation_allowed,
        reason=reason,
        **actions,
    )


def ensure_commercial_action_allowed(user: Any, record: Any, action: str, module: str | None = None) -> CommercialAccessHint:
    if action != "view" and not can_change_commercial_status(record, action):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Commercial record status does not allow {action}.",
        )
    module_key = module or commercial_module_key(record)
    allowed = can_view_record(user, module_key, record) if action == "view" else can_modify_record(user, module_key, action, record)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=forbidden_detail("You can view this record only if your permissions and scopes allow it."),
        )
    return build_commercial_access_hint(user, record, module_key)
