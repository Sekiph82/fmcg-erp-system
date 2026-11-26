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


# ── M47.S01.T010 field-level permissions ─────────────────────────────────────
# Rules: role name → field key → HIDDEN (removed from reads, writes refused) or READ_ONLY (shown, writes refused), for
# CRM contacts ("contact": standard fields and contact properties) and custom objects ("co:<type key>"). A user with
# several roles gets the strictest rule of any of them. Superusers and data administrators (roles.manage) are exempt.
ACCESS = ("HIDDEN", "READ_ONLY")
CONTACT_FIELDS = ("full_name", "email", "phone", "job_title", "lifecycle_stage", "language", "owner_user_id",
                  "company_id", "source", "notes")
_KEY_RE = r"^[a-z][a-z0-9_]{0,59}$"


def fp_exempt(user) -> bool:
    from app.core.access_control import has_any_permission
    return bool(getattr(user, "is_superuser", False) or has_any_permission(user, ("roles.manage",)))


def _role_names(user) -> set[str]:
    return {r.name for r in getattr(user, "roles", []) or [] if getattr(r, "is_active", True)}


async def field_rules(db: AsyncSession, entity: str, user) -> dict[str, str]:
    """{field_key: HIDDEN | READ_ONLY} that apply to this user (empty when exempt)."""
    from app.models.m47_platform import FieldPermissionRule
    roles = _role_names(user)
    if fp_exempt(user) or not roles:
        return {}
    out: dict[str, str] = {}
    for r in (await db.execute(select(FieldPermissionRule).where(FieldPermissionRule.entity == entity,
                                                                 FieldPermissionRule.role_name.in_(roles)))).scalars():
        if out.get(r.field_key) != "HIDDEN":
            out[r.field_key] = r.access
    return out


def strip_hidden(data: dict, rules: dict[str, str]) -> dict:
    """Remove hidden keys (in place) from a response dict and from its nested "properties" / "data" dicts."""
    hidden = [k for k, a in rules.items() if a == "HIDDEN"]
    for d in (data, data.get("properties"), data.get("data")):
        if isinstance(d, dict):
            for k in hidden:
                d.pop(k, None)
    if hidden:
        data["hidden_fields"] = sorted(hidden)
    return data


def check_write(rules: dict[str, str], new: dict, old: dict) -> None:
    """Refuse a change to a restricted field (sending the unchanged value back is fine)."""
    bad = sorted(k for k in rules if k in new and new[k] != old.get(k))
    if bad:
        raise PermissionError(f"You may not change: {', '.join(bad)}.")


async def validate_rule(db: AsyncSession, entity: str, field_key: str, access: str) -> None:
    import re
    if access not in ACCESS:
        raise ValueError("access must be HIDDEN or READ_ONLY.")
    if not re.fullmatch(_KEY_RE, field_key or ""):
        raise ValueError("Invalid field key.")
    if entity == "contact":
        return                                   # standard fields or contact properties (any well-formed key)
    if entity.startswith("co:"):
        from app.models.custom_objects import CustomObjectType
        t = (await db.execute(select(CustomObjectType).where(CustomObjectType.key == entity[3:]))).scalar_one_or_none()
        if t is None:
            raise ValueError("Unknown custom object type.")
        if field_key not in {f["key"] for f in t.fields}:
            raise ValueError("This object type has no such field.")
        return
    raise ValueError("entity must be 'contact' or 'co:<object key>'.")
