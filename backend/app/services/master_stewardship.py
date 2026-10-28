"""Direct, permission-controlled master-data writes with audit evidence."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.audit import log_event
from app.models.audit_log import AuditEvent
from app.models.master import SupplierQualificationStatus


_NON_BUSINESS_FIELDS = {"id", "created_at", "updated_at"}
_REDACTED_FIELDS = {
    "address",
    "contact_person",
    "compliance_notes",
    "email",
    "mpesa_phone_number",
    "phone",
    "registration_no",
    "tax_id",
    "tax_pin",
}


def _record_values(record: Any) -> dict[str, Any]:
    values = {
        column.name: getattr(record, column.name)
        for column in record.__table__.columns
        if column.name not in _NON_BUSINESS_FIELDS
    }
    return jsonable_encoder(values, custom_encoder={Decimal: str})


def _audit_values(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: "[REDACTED]" if key in _REDACTED_FIELDS and value is not None else value
        for key, value in values.items()
    }


def _target_name(record: Any) -> str | None:
    for field in ("name", "sku", "code"):
        value = getattr(record, field, None)
        if value:
            return str(value)
    return None


async def record_master_data_change(
    db: AsyncSession,
    *,
    record: Any,
    actor: Any,
    action: str,
    permission: str,
    before: dict[str, Any] | None = None,
) -> None:
    """Write the master mutation and its audit event in the caller's transaction.

    Updates store only changed fields. Contact/address/tax identifiers are marked
    as redacted in the audit values, while the changed field names remain visible.
    The audit row is committed together with the master-data write by the route.
    """
    after = _record_values(record)
    normalized_action = action.upper()
    if normalized_action == "CREATE":
        changed_fields = sorted(after)
        before_values: dict[str, Any] = {}
        after_values = after
        event_type = AuditEvent.MASTER_DATA_CREATED
    elif normalized_action == "UPDATE":
        previous = before or {}
        changed_fields = sorted(
            key for key, value in after.items() if previous.get(key) != value
        )
        if not changed_fields:
            return
        before_values = {key: previous.get(key) for key in changed_fields}
        after_values = {key: after.get(key) for key in changed_fields}
        event_type = AuditEvent.MASTER_DATA_UPDATED
    else:
        raise ValueError(f"Unsupported master-data stewardship action: {action}")

    await log_event(
        db,
        event_type=event_type,
        actor_id=getattr(actor, "id", None),
        actor_email=getattr(actor, "email", None),
        actor_name=getattr(actor, "full_name", None),
        module=record.__tablename__,
        target_type=record.__tablename__,
        target_id=str(record.id),
        target_name=_target_name(record),
        before_value=_audit_values(before_values),
        after_value=_audit_values(after_values),
        details={
            "workflow": "DIRECT_AUTHORIZED_EDIT",
            "approval_required": False,
            "required_permission": permission,
            "changed_fields": changed_fields,
        },
    )


def snapshot_master_data(record: Any) -> dict[str, Any]:
    """Capture a comparison snapshot before an update; do not persist it directly."""
    return _record_values(record)


def apply_supplier_qualification_actor(
    record: Any,
    actor: Any,
    *,
    previous_status: Any = None,
) -> None:
    """Keep supplier approval lineage aligned with direct authorized qualification edits."""
    new_status = getattr(record.qualification_status, "value", record.qualification_status)
    old_status = getattr(previous_status, "value", previous_status)
    if (
        new_status == SupplierQualificationStatus.APPROVED.value
        and old_status != SupplierQualificationStatus.APPROVED.value
    ):
        record.approved_by_id = actor.id
        record.approved_at = datetime.now(timezone.utc)
    elif (
        new_status != SupplierQualificationStatus.APPROVED.value
        and old_status == SupplierQualificationStatus.APPROVED.value
    ):
        record.approved_by_id = None
        record.approved_at = None
