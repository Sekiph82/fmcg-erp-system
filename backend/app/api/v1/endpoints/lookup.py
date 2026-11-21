"""Record lookup for pickers (M40.S02.T001): search a record by its number/code/name and get its id, so screens link
records instead of asking people to paste UUIDs. Returns only id + a short label; each kind needs the owning
module's view right. Customers, sales orders and invoices use their own scoped list endpoints instead."""
from __future__ import annotations

import importlib
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db

router = APIRouter()

# kind: (model, label columns, sub columns, any-of view permissions)
KINDS: dict[str, tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    "purchase_order": ("app.models.procurement:PurchaseOrder", ("po_no",), ("status", "order_date"), ("procurement.view", "inventory.view", "finance.view")),
    "goods_receipt": ("app.models.procurement:GoodsReceipt", ("grn_no",), ("status", "received_date"), ("procurement.view", "inventory.view", "quality.view")),
    "shipment": ("app.models.sales:Shipment", ("shipment_no",), ("status", "scheduled_date"), ("sales.view", "logistics.view", "inventory.view")),
    "qc_inspection": ("app.models.quality:QCInspection", ("inspection_no",), ("status", "lot_number"), ("quality.view",)),
    "asset": ("app.models.maintenance:Asset", ("name", "asset_no"), ("asset_no", "status"), ("maintenance.view",)),
    "campaign": ("app.models.marketing:Campaign", ("campaign_name", "campaign_code"), ("campaign_code", "status"), ("marketing.view", "crm.view")),
    "promotion": ("app.models.marketing:MarketingPromotion", ("promotion_name", "promotion_code"), ("promotion_code", "status"), ("marketing.view", "sales.view")),
    "influencer": ("app.models.marketing:Influencer", ("influencer_name",), ("status",), ("marketing.view",)),
    "delivery_trip": ("app.models.delivery:DeliveryTrip", ("trip_no",), ("driver_name", "trip_date"), ("logistics.view", "delivery.view", "sales.view")),
    "work_center": ("app.models.production_advanced:WorkCenter", ("name",), ("status",), ("production.view",)),
    "machine": ("app.models.machine_operator:Machine", ("machine_name", "machine_code"), ("machine_code", "status"), ("production.view", "maintenance.view")),
    "flow_txn": ("app.models.material_flow:MaterialFlowTransaction", ("flow_no",), ("status", "transaction_datetime"), ("inventory.view", "production.view")),
    "candidate": ("app.models.recruitment:Candidate", ("full_name", "candidate_code"), ("candidate_code", "current_title"), ("recruitment.view", "hr.view")),
    "requisition": ("app.models.recruitment:JobRequisition", ("job_title", "requisition_code"), ("requisition_code", "status"), ("recruitment.view", "hr.view")),
    "sales_rep": ("app.models.field_sales:SalesRep", ("name", "code"), ("code",), ("sales.view", "crm.view")),
    "production_plan": ("app.models.production:ProductionPlan", ("plan_no", "name"), ("name", "status"), ("production.view", "planning.view")),
    "mrp_run": ("app.models.mrp:MRPRun", ("run_no",), ("run_date", "status"), ("production.view", "mrp.view", "planning.view")),
    "lot": ("app.models.inventory:Lot", ("lot_number",), ("batch_number", "expiry_date"), ("inventory.view", "quality.view", "production.view")),
    "location": ("app.models.wms:StorageLocation", ("code", "name"), ("name", "barcode"), ("inventory.view", "wms.view")),
    "contract": ("app.models.contracts:Contract", ("contract_name", "contract_code"), ("contract_code", "status"), ("contracts.view", "sales.view", "procurement.view")),
    "crm_record": ("app.models.crm:CRMRecord", ("company_name", "lead_code", "opportunity_code"), ("contact_person_name", "status"), ("crm.view",)),
    "expense": ("app.models.expenses:ExpenseClaim", ("claim_no",), ("status", "period_start"), ("finance.view", "hr.view")),  # others see only own claims
    "bom": ("app.models.bom:AdvancedBOM", ("bom_name", "bom_code"), ("bom_code", "product_name", "version_no"), ("bom.view", "production.view")),
    "mpesa_transaction": ("app.models.sales:MpesaTransaction", ("mpesa_reference", "phone_number"), ("status",), ("finance.view", "sales.view")),
    "cash_transaction": ("app.models.finance:CashTransaction", ("reference", "source_ref"), ("mpesa_name", "status"), ("finance.view",)),
    "count_task": ("app.models.cycle_count:CycleCountTask", ("task_no",), ("status", "scheduled_date"), ("inventory.view", "cycle_count.view")),
    "operator": ("app.models.machine_operator:OperatorProfile", ("full_name", "operator_code"), ("operator_code", "department"), ("production.view", "hr.view")),
    "work_order": ("app.models.production_advanced:WorkOrder", ("work_order_id", "operation"), ("operation", "status"), ("production.view",)),
    "purchase_invoice": ("app.models.finance:PurchaseInvoice", ("invoice_no",), ("status", "invoice_date"), ("finance.view", "procurement.view")),
    "segment": ("app.models.marketing:CustomerSegment", ("segment_name",), ("segment_type", "region"), ("marketing.view", "crm.view")),
    "gl_account": ("app.models.finance:ChartOfAccount", ("code", "name"), ("name", "account_type"), ("finance.view", "accounting.view")),
    "utility_asset": ("app.models.utility_management:UtilityAsset", ("name", "asset_no"), ("asset_no", "utility_type"), ("utility.view", "utility_management.view", "maintenance.view")),
    "payroll_period": ("app.models.hr:PayrollPeriod", ("period_year", "period_month"), ("status",), ("payroll.view", "hr.view", "finance.view")),
}


def _model(kind: str):
    spec = KINDS.get(kind)
    if spec is None:
        raise HTTPException(404, "Unknown record type.")
    mod, cls = spec[0].split(":")
    return getattr(importlib.import_module(mod), cls), spec


def _allowed(user, perms) -> bool:
    return getattr(user, "is_superuser", False) or has_any_permission(user, perms)


def _pk(m) -> str:
    from sqlalchemy import inspect as _inspect
    return str(getattr(m, _inspect(type(m)).primary_key[0].key))


def _row(m, label_cols, sub_cols) -> dict:
    label = " · ".join(str(getattr(m, c)) for c in label_cols[:1] if getattr(m, c, None) is not None)
    extra = [str(getattr(m, c)) for c in (label_cols[1:] + sub_cols) if getattr(m, c, None) not in (None, "")]
    status = lambda v: getattr(v, "value", v)  # noqa: E731
    return {"id": _pk(m), "label": label or _pk(m)[:8], "sub": " · ".join(str(status(x)) for x in dict.fromkeys(extra))}


@router.get("/{kind}")
async def search(kind: str, search: Optional[str] = Query(None, max_length=100), limit: int = Query(20, ge=1, le=50),
                 db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    model, (_, label_cols, sub_cols, perms) = _model(kind)
    if not _allowed(current_user, perms):
        raise HTTPException(403, "Required permission is missing.")
    q = select(model)
    if search and search.strip():
        term = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{term}%"
        q = q.where(or_(*[cast(getattr(model, c), String).ilike(like, escape="\\") for c in label_cols]))
    order = getattr(model, "updated_at", None) or getattr(model, "created_at", None)
    if order is not None:
        q = q.order_by(order.desc())
    rows = (await db.execute(q.limit(limit))).scalars().all()
    return [_row(m, label_cols, sub_cols) for m in rows]


@router.get("/{kind}/{record_id}")
async def one(kind: str, record_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    model, (_, label_cols, sub_cols, perms) = _model(kind)
    if not _allowed(current_user, perms):
        raise HTTPException(403, "Required permission is missing.")
    m = await db.get(model, record_id)
    if m is None:
        raise HTTPException(404, "Not found.")
    return _row(m, label_cols, sub_cols)
