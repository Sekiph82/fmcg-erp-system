"""One "waiting for my approval" inbox across modules (M40.S02.T001).

Each entry names a model, the status values that mean "waiting for a decision", the permissions of the people who
decide, and the screen where they decide. The inbox lists what the signed-in user may decide; a background tick sends
each newly waiting item once to its approvers' notification bell (deduplicated by reference)."""
from __future__ import annotations

import asyncio
import importlib
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import String, and_, cast, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# key, label, "module:Model", status column, waiting values, decider permissions, screen
ENTRIES: list[tuple[str, str, str, str, tuple[str, ...], tuple[str, ...], str]] = [
    ("purchase_request", "Purchase request", "procurement:PurchaseRequisition", "status", ("PENDING_APPROVAL",), ("procurement.approve", "procurement.approve_all"), "/dashboard/procurement?tab=purchase-requests"),
    ("purchase_order", "Purchase order (draft)", "procurement:PurchaseOrder", "status", ("DRAFT",), ("procurement.approve", "procurement.approve_all"), "/dashboard/procurement?tab=orders"),
    ("rfq_award", "Supplier award", "procurement:RFQAward", "status", ("PENDING_APPROVAL",), ("procurement.approve", "procurement.approve_all"), "/dashboard/procurement?tab=rfq"),
    ("supplier_document", "Supplier document", "supplier_portal:SPDocument", "review_status", ("PENDING",), ("procurement.edit",), "/dashboard/procurement?tab=supplier-portal"),
    ("leave", "Leave request", "hr:LeaveRequest", "approval_status", ("PENDING",), ("hr.approve",), "/dashboard/hr?tab=leave"),
    ("ess_leave", "Leave request (self-service)", "ess:ESSLeaveRequest", "status", ("SUBMITTED",), ("hr.approve",), "/dashboard/hr?tab=ess"),
    ("ess_request", "Employee request", "ess:ESSRequest", "status", ("SUBMITTED", "IN_REVIEW"), ("hr.approve",), "/dashboard/hr?tab=ess"),
    ("expense_manager", "Expense claim (manager)", "expenses:ExpenseClaim", "status", ("SUBMITTED",), ("hr.approve",), "/dashboard/hr?tab=expenses"),
    ("expense_finance", "Expense claim (finance)", "expenses:ExpenseClaim", "status", ("MANAGER_APPROVED",), ("finance.approve",), "/dashboard/hr?tab=expenses"),
    ("timesheet", "Timesheet", "timesheets:TimesheetHeader", "status", ("SUBMITTED",), ("hr.approve",), "/dashboard/hr?tab=timesheets"),
    ("payroll_run", "Payroll run", "payroll_ke:PayrollRun", "status", ("CALCULATED",), ("payroll_ke.approve",), "/dashboard/payroll"),
    ("stock_count", "Stock count", "wms:StockCount", "status", ("PENDING_APPROVAL",), ("cycle_count.perform",), "/dashboard/warehouses?tab=wms"),
    ("count_adjustment", "Cycle-count adjustment", "cycle_count:CountAdjustment", "status", ("PENDING",), ("cycle_count.approve", "inventory.approve"), "/dashboard/inventory?tab=cycle-count"),
    ("return", "Customer return", "returns_mgmt:ReturnOrder", "status", ("SUBMITTED",), ("sales.approve",), "/dashboard/sales?tab=returns"),
    ("portal_signup", "Shop sign-up", "portal:PortalAccount", "portal_status", ("PENDING",), ("partner_portal.manage_access",), "/dashboard/sales?tab=portal"),
    ("portal_claim", "Shop claim", "portal:PortalClaim", "status", ("SUBMITTED",), ("sales.edit",), "/dashboard/sales?tab=portal"),
    ("portal_draft", "Shop draft order", "portal:PortalDraftOrder", "status", ("SUBMITTED",), ("sales.edit",), "/dashboard/sales?tab=portal"),
    ("promo_override", "Promotion override", "promotions:PromoOverrideRequest", "status", ("PENDING",), ("promotions.approve", "marketing.approve", "sales.approve"), "/dashboard/marketing?tab=promotions"),
    ("campaign", "Marketing campaign", "marketing:Campaign", "approval_status", ("PENDING",), ("campaigns.approve", "marketing.approve"), "/dashboard/marketing?tab=campaigns"),
    ("trade_spend", "Trade spend", "marketing:TradeSpend", "approval_status", ("PENDING",), ("trade_spend.approve", "marketing.approve"), "/dashboard/marketing?tab=trade-spend"),
    ("brand_spend", "Brand spend", "marketing:BrandSpend", "approval_status", ("PENDING",), ("brand_spend.approve", "marketing.approve"), "/dashboard/marketing?tab=brand-spend"),
    ("studio_budget", "Campaign budget above finance cap", "m49_studio:StudioBudgetRequest", "status", ("PENDING",), ("finance.approve",), "/dashboard/my-approvals"),   # M49.S01.T012; requester refused by the endpoint
    ("tpm_claim", "Trade promotion claim", "tpm:TPMClaim", "status", ("SUBMITTED",), ("trade_spend.approve", "promotions.approve", "marketing.approve"), "/dashboard/marketing?tab=tpm"),
    ("brand_asset", "Brand asset review", "brand_assets:AssetApprovalStage", "status", ("PENDING",), ("marketing.approve", "campaigns.approve", "quality.approve"), "/dashboard/quality?tab=brand-assets"),
    ("shelf_life_extension", "Shelf-life extension", "shelf_life:ShelfLifeExtension", "status", ("PENDING",), ("shelf_life.approve", "quality.approve"), "/dashboard/inventory?tab=shelf-life"),
    ("supplier_food_safety", "Supplier food-safety approval", "quality:SupplierFoodSafetyApproval", "status", ("PENDING",), ("quality.approve",), "/dashboard/quality?tab=qms"),
    ("quote_discount", "Quotation discount", "quotation:Quotation", "approval_status", ("PENDING_DISCOUNT",), ("sales.approve", "sales.approve_all"), "/dashboard/sales/quotes"),
    ("so_discount", "Sales order discount", "sales:SalesOrder", "approval_status", ("PENDING_DISCOUNT",), ("sales.approve", "sales.approve_all"), "/dashboard/sales/orders"),
]
# nobody decides their own document (the decision endpoints refuse it too)
_NOT_OWN = {"quote_discount", "so_discount"}
# extra fields the inline Approve/Reject buttons need to build the decision URL
_CTX = {"rfq_award": ("rfq_id",), "brand_asset": ("asset_id",), "count_adjustment": ("entry_id",)}
_REF_ATTRS = ("quote_no", "pr_no", "po_no", "leave_no", "request_no", "claim_no", "order_no", "return_no", "count_no", "run_no",
              "reference", "reference_no", "number", "code", "name", "title", "shop_name")
_PER_ENTRY = 20
_SCOPED_BATCH = 500   # scoped approvers: rows are checked in Python, batch by batch over all waiting rows


def _model(path: str):
    mod, cls = path.split(":")
    return getattr(importlib.import_module(f"app.models.{mod}"), cls)


def _pk(model):
    return model.__mapper__.primary_key[0]


def _pk_value(row) -> str:
    mapper = type(row).__mapper__
    return str(getattr(row, mapper.get_property_by_column(mapper.primary_key[0]).key))


def _ref(row: Any) -> str:
    for attr in _REF_ATTRS:
        v = getattr(row, attr, None)
        if v:
            return str(v)[:80]
    return _pk_value(row)[:8]


def _scoped(perms: tuple[str, ...]) -> tuple[str, str]:
    """The (module, action) whose own-scope rights (e.g. procurement.approve_own_scope) decide row by row."""
    module, action = perms[0].split(".", 1)
    return module, action.removesuffix("_all")


def _codes(user) -> set[str]:
    from app.core.access_control import get_effective_permission_codes

    return set(get_effective_permission_codes(user))


def _access(user, perms: tuple[str, ...]) -> str | None:
    """'all' = decides every row; 'scoped' = only rows inside the user's scopes; None = not a decider.
    Mirrors can_modify_record: *_all is unscoped; a plain right is unscoped only for users without any scope."""
    from app.core.access_control import ACTION_FIELD_BY_ACTION, _has_any_scope, has_permission

    codes = _codes(user)
    if getattr(user, "is_superuser", False) or "*" in codes or any(f"{p.removesuffix('_all')}_all" in codes for p in perms):
        return "all"
    module, action = _scoped(perms)
    if any(has_permission(user, p) for p in perms):
        # rights outside the standard scope actions (e.g. manage_access) cannot be scope-checked per row
        return "scoped" if _has_any_scope(user) and action in ACTION_FIELD_BY_ACTION else "all"
    return "scoped" if any(c.startswith(f"{module}.{action}_own") for c in codes) else None


def _may_decide(user, perms: tuple[str, ...], row) -> bool:
    from app.core.access_control import can_modify_record

    module, action = _scoped(perms)
    return can_modify_record(user, module, action, row)


def can_decide_any(user) -> bool:
    """Shows the "My Approvals" menu: the user decides at least one kind of item."""
    return any(_access(user, e[5]) for e in ENTRIES)


def _only_next_stage(model):
    """Brand-asset stages are decided in order: only the lowest open stage of each asset is waiting for a decision."""
    from sqlalchemy.orm import aliased

    earlier = aliased(model)
    return ~exists().where(earlier.asset_id == model.asset_id, earlier.stage_order < model.stage_order,
                           earlier.status != "APPROVED")


def _draft(model):
    return model.status == "DRAFT"   # a discount is decided only while the document is still a draft


_ROW_FILTER = {"brand_asset": _only_next_stage, "quote_discount": _draft, "so_discount": _draft}


def _waiting(key: str, model, col: str, values: tuple[str, ...]):
    cond = getattr(model, col).in_(values)
    return and_(cond, _ROW_FILTER[key](model)) if key in _ROW_FILTER else cond


async def _rows(db: AsyncSession, model, cond, limit: int, extra=None, newest=False, offset: int = 0, by: str = "created_at"):
    q = select(model).where(cond)
    if extra is not None:
        q = q.where(extra)
    if hasattr(model, by):
        q = q.order_by(getattr(model, by).desc() if newest else getattr(model, by).asc(), _pk(model))
    else:
        q = q.order_by(_pk(model))
    return (await db.execute(q.offset(offset).limit(limit))).scalars().all()


async def _scoped_rows(db: AsyncSession, model, cond, user, perms) -> tuple[int, list]:
    """Every waiting row the scoped user may decide: exact count and the oldest _PER_ENTRY."""
    count, first, offset = 0, [], 0
    while True:
        batch = await _rows(db, model, cond, _SCOPED_BATCH, offset=offset)
        for r in batch:
            if _may_decide(user, perms, r):
                count += 1
                if len(first) < _PER_ENTRY:
                    first.append(r)
        if len(batch) < _SCOPED_BATCH:
            return count, first
        offset += _SCOPED_BATCH


async def inbox(db: AsyncSession, user) -> dict:
    """What this user may decide now: per type a count, the oldest items and the screen to decide on."""
    groups, total = [], 0
    for key, label, path, col, values, perms, link in ENTRIES:
        access = _access(user, perms)
        if access is None:
            continue
        model = _model(path)
        cond = _waiting(key, model, col, values)
        if key in _NOT_OWN:
            cond = and_(cond, or_(model.created_by_id.is_(None), model.created_by_id != user.id),
                        or_(model.discount_changed_by_id.is_(None), model.discount_changed_by_id != user.id))
        if key == "quote_discount":          # approved one CPQ level already: the next level is someone else's (M48.S01.T021)
            from app.models.cpq import QuoteApproval
            cond = and_(cond, ~exists().where(QuoteApproval.quote_id == model.id, QuoteApproval.approver_id == user.id))
        if access == "all":
            count = (await db.execute(select(func.count()).select_from(model).where(cond))).scalar_one()
            rows = await _rows(db, model, cond, _PER_ENTRY) if count else []
        else:
            count, rows = await _scoped_rows(db, model, cond, user, perms)
        if not count:
            continue
        groups.append({"key": key, "label": label, "count": count, "link": link,
                       "items": [{"id": _pk_value(r), "ref": _ref(r), "since": getattr(r, "created_at", None),
                                  **{k: str(getattr(r, k, "") or "") for k in _CTX.get(key, ())}} for r in rows]})
        total += count
    return {"total": total, "groups": groups}


async def _deciders(db: AsyncSession, perms: tuple[str, ...]):
    """Active users holding a broad or own-scope right for this entry, with roles/permissions/scopes loaded."""
    from sqlalchemy import or_
    from sqlalchemy.orm import selectinload

    from app.models.role import Permission, Role, role_permission
    from app.models.user import User, user_role

    module, action = _scoped(perms)
    broad = [c for p in perms for c in (p, f"{p}_all")]
    ids = (await db.execute(
        select(User.id).distinct()
        .join(user_role, user_role.c.user_id == User.id).join(Role, Role.id == user_role.c.role_id)
        .join(role_permission, role_permission.c.role_id == Role.id).join(Permission, Permission.id == role_permission.c.permission_id)
        .where(User.is_active.is_(True), Role.is_active.is_(True), Permission.is_active.is_(True),
               or_(Permission.code.in_(broad), Permission.code.like(f"{module}.{action}_own%"))))).scalars().all()
    if not ids:
        return []
    opts = [selectinload(User.roles).selectinload(Role.permissions)]
    if hasattr(User, "access_scopes"):
        opts.append(selectinload(User.access_scopes))
    if hasattr(Role, "access_scopes"):
        opts.append(selectinload(User.roles).selectinload(Role.access_scopes))
    return (await db.execute(select(User).where(User.id.in_(ids)).options(*opts))).scalars().unique().all()


def _notice_key(row) -> str:
    """Dedupe key: the record plus its last change, so a record that waits again after a change is sent again."""
    changed = getattr(row, "updated_at", None)
    return f"{_pk_value(row)}@{int(changed.timestamp() * 1000)}" if changed else _pk_value(row)


def _naive_utc(dt):
    from datetime import timezone

    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt is not None and dt.tzinfo else dt


async def notify_new(db: AsyncSession, days: int = 7) -> int:
    """Send each item that became waiting (or waits again after a change, in the last `days`) once to the people
    who may decide it."""
    from app.models.notifications import (Notification, NotificationChannel, NotificationPriority, NotificationStatus,
                                          NotificationType)

    since, sent = datetime.utcnow() - timedelta(days=days), 0
    cache: dict = {}   # deciders per permission set, once per tick
    for key, label, path, col, values, perms, link in ENTRIES:
        model = _model(path)
        ref_type = f"approval:{key}"
        by = "updated_at" if hasattr(model, "updated_at") else "created_at"
        extra = getattr(model, by) >= since if hasattr(model, by) else None
        if perms not in cache:
            cache[perms] = [(u, _access(u, perms)) for u in await _deciders(db, perms)]
        people = cache[perms]
        if not people:   # nobody may decide this type: nothing to send (and no query for its rows)
            continue
        rows = await _rows(db, model, _waiting(key, model, col, values), 200, extra, newest=True, by=by)
        if not rows:
            continue
        keys = {_pk_value(r): _notice_key(r) for r in rows}
        sent_refs = (await db.execute(select(Notification.reference_id, Notification.created_at).where(
            Notification.reference_type == ref_type,
            Notification.reference_id.in_(list(keys.values()) + list(keys))))).all()
        done = {ref for ref, _ in sent_refs}
        legacy = {}   # notices from before versioned keys: plain id, valid if sent after the last change
        for ref, at in sent_refs:
            if "@" not in ref:
                legacy[ref] = max(legacy.get(ref, at), at)
        now = datetime.utcnow()
        for row in rows:
            pk, nkey = _pk_value(row), keys[_pk_value(row)]
            changed = _naive_utc(getattr(row, "updated_at", None))
            if nkey in done or (pk in legacy and (changed is None or legacy[pk] >= changed)):
                continue
            ref = _ref(row)
            for u, access in people:
                if key in _NOT_OWN and u.id in (getattr(row, "created_by_id", None), getattr(row, "discount_changed_by_id", None)):
                    continue
                if access == "all" or (access == "scoped" and _may_decide(u, perms, row)):
                    db.add(Notification(user_id=str(u.id), user_name=u.full_name or u.username,
                                        title=f"Waiting for your approval: {label} {ref}"[:255],
                                        message=f"{label} {ref} is waiting for your decision. Open My Approvals.",
                                        notification_type=NotificationType.APPROVAL_REQUIRED, priority=NotificationPriority.HIGH,
                                        channel=NotificationChannel.IN_APP, reference_type=ref_type, reference_id=nkey,
                                        module="approvals", status=NotificationStatus.SENT, sent_at=now))
                    sent += 1
        await db.commit()
    return sent


async def run_approval_notifier(interval: float = 60.0) -> None:
    """Lifespan task: approvers hear about new waiting items within a minute."""
    from app.db.session import AsyncSessionLocal

    while True:
        try:
            async with AsyncSessionLocal() as db:
                await notify_new(db)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("approval notifier tick failed")
        await asyncio.sleep(interval)
