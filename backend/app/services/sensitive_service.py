"""M45.S01.T017 sensitive-data classification and masking.

Built-in fields an administrator may classify (customer KRA PIN, contact details, credit limit...) plus custom fields
with cf_definitions.sensitive_flag. Users without data.view_sensitive see masked values in screens, API responses and
CSV exports; a reveal returns one value and is written to the audit log. Retention hook: a classified field with
retention_days is cleared on records that have been inactive that long.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_data import SensitiveField

CLASSIFIABLE = {"customer": ("tax_id", "phone", "email", "address", "delivery_address", "credit_limit", "gps_lat", "gps_lng"),
                "contact": ("phone", "email")}
DEFAULT_ON = {("customer", "tax_id")}
RIGHT = "data.view_sensitive"


def can_view(user) -> bool:
    from app.core.access_control import has_permission
    return bool(getattr(user, "is_superuser", False) or has_permission(user, RIGHT))


def mask(value: Any) -> Any:
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        return None                              # numbers (e.g. credit limit) are withheld, not partly shown
    tail = value[-3:] if len(value) > 6 else ""
    return "•••" + tail


async def policy(db: AsyncSession) -> dict[str, set[str]]:
    rows = {(r.entity, r.field): r.enabled for r in (await db.execute(select(SensitiveField))).scalars()}
    out: dict[str, set[str]] = {e: set() for e in CLASSIFIABLE}
    for e, fields in CLASSIFIABLE.items():
        for f in fields:
            if rows.get((e, f), (e, f) in DEFAULT_ON):
                out[e].add(f)
    return out


def apply(obj, entity: str, pol: dict[str, set[str]], user) -> Any:
    """Mask the classified attributes of a response object/dict in place for users without the right."""
    if can_view(user):
        return obj
    for f in pol.get(entity, ()):
        if isinstance(obj, dict):
            if f in obj:
                obj[f] = mask(obj[f])
        elif hasattr(obj, f):
            setattr(obj, f, mask(getattr(obj, f)))
    if not isinstance(obj, dict) and hasattr(obj, "masked_fields"):
        obj.masked_fields = sorted(pol.get(entity, ()))
    return obj


async def reveal(db: AsyncSession, user, entity: str, record_id: uuid.UUID, field: str) -> Any:
    from app.services import pat_service as pats
    if field not in CLASSIFIABLE.get(entity, ()):
        raise ValueError("Unknown field.")
    if not can_view(user):
        pats.audit(db, user, "SENSITIVE_REVEAL_REFUSED", entity, str(record_id), {"field": field})
        raise PermissionError("You do not have the right to see sensitive data.")
    model = _model(entity)
    obj = await db.get(model, record_id)
    if obj is None:
        raise LookupError("Not found.")
    pats.audit(db, user, "SENSITIVE_REVEALED", entity, str(record_id), {"field": field})
    v = getattr(obj, field)
    return str(v) if v is not None else None


def _model(entity: str):
    from app.models.crm import CRMContact
    from app.models.sales import Customer
    return {"customer": Customer, "contact": CRMContact}[entity]


async def set_field(db: AsyncSession, entity: str, field: str, enabled: bool, retention_days: Optional[int], user: str) -> None:
    from sqlalchemy.dialects.postgresql import insert
    if field not in CLASSIFIABLE.get(entity, ()):
        raise ValueError("This field cannot be classified.")
    await db.execute(insert(SensitiveField).values(id=uuid.uuid4(), entity=entity, field=field, enabled=enabled,
                                                   retention_days=retention_days, updated_by=user, updated_at=datetime.now(timezone.utc))
                     .on_conflict_do_update(constraint="uq_cd_sensitive_field",
                                            set_={"enabled": enabled, "retention_days": retention_days, "updated_by": user,
                                                  "updated_at": datetime.now(timezone.utc)}))


async def apply_retention(db: AsyncSession, now: Optional[datetime] = None) -> int:
    """Clear classified customer fields with a retention period on customers inactive for longer than that."""
    from app.models.sales import Customer
    now = now or datetime.now(timezone.utc)
    n = 0
    for sf in (await db.execute(select(SensitiveField).where(SensitiveField.entity == "customer", SensitiveField.enabled.is_(True),
                                                             SensitiveField.retention_days.is_not(None)))).scalars():
        res = await db.execute(update(Customer).where(Customer.is_active.is_(False),
                                                      Customer.updated_at < now - timedelta(days=sf.retention_days),
                                                      getattr(Customer, sf.field).is_not(None))
                               .values({sf.field: None}))
        n += res.rowcount or 0
    return n
