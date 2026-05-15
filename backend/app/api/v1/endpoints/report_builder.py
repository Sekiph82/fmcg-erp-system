from typing import List, Optional
from uuid import UUID
import uuid as _uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import io
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.schemas.report_builder import (
    ReportCreate, ReportUpdate, ReportOut, RunRequest, RunResult,
    ScheduleCreate, ScheduleOut,
    DashboardCreate, DashboardOut, WidgetCreate, WidgetOut,
    RBAIRecOut, RBAIRecAck,
)
from app.models.report_builder import RLSPolicy, RLSPolicyScope, FilterOperator
import app.services.report_builder_service as svc

router = APIRouter()


# ── Metadata ──────────────────────────────────────────────────────────────────

@router.get("/catalog", dependencies=[Depends(require_permission("reports", "view"))])
async def get_catalog():
    return {
        k: {
            "label": v["label"],
            "module": v["module"],
            "field_count": len(v["fields"]),
            "fields": v["fields"],
        }
        for k, v in svc.DATA_SOURCES.items()
    }


@router.get("/catalog/{data_source}", dependencies=[Depends(require_permission("reports", "view"))])
async def get_data_source(data_source: str):
    ds = svc.DATA_SOURCES.get(data_source)
    if not ds:
        raise HTTPException(404, f"Data source '{data_source}' not found")
    return ds


# ── Reports ───────────────────────────────────────────────────────────────────

@router.post("/reports", response_model=ReportOut, status_code=201,
             dependencies=[Depends(require_permission("reports", "create"))])
async def create_report(data: ReportCreate, db: AsyncSession = Depends(get_db)):
    if data.data_source not in svc.DATA_SOURCES:
        raise HTTPException(400, f"Unknown data source: {data.data_source}")
    return await svc.create_report(db, data)


@router.get("/reports", response_model=List[ReportOut],
            dependencies=[Depends(require_permission("reports", "view"))])
async def list_reports(
    data_source: Optional[str] = None,
    owner: Optional[str] = None,
    template_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_reports(db, data_source, owner, template_only)


@router.get("/reports/{report_id}", response_model=ReportOut,
            dependencies=[Depends(require_permission("reports", "view"))])
async def get_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_report(db, report_id)
    if not obj:
        raise HTTPException(404, "Report not found")
    return obj


@router.patch("/reports/{report_id}", response_model=ReportOut,
              dependencies=[Depends(require_permission("reports", "edit"))])
async def update_report(report_id: UUID, data: ReportUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_report(db, report_id, data)
    if not obj:
        raise HTTPException(404, "Report not found")
    return obj


@router.delete("/reports/{report_id}", status_code=204,
               dependencies=[Depends(require_permission("reports", "admin"))])
async def delete_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.delete_report(db, report_id)
    if not ok:
        raise HTTPException(404, "Report not found")


@router.post("/reports/{report_id}/clone", response_model=ReportOut, status_code=201,
             dependencies=[Depends(require_permission("reports", "create"))])
async def clone_report(
    report_id: UUID,
    new_code: str = Query(...),
    new_name: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    obj = await svc.clone_report(db, report_id, new_code, new_name)
    if not obj:
        raise HTTPException(404, "Report not found")
    return obj


@router.post("/reports/seed-templates",
             dependencies=[Depends(require_permission("reports", "admin"))])
async def seed_templates(db: AsyncSession = Depends(get_db)):
    count = await svc.seed_templates(db)
    return {"created": count}


# ── Run ───────────────────────────────────────────────────────────────────────

@router.post("/reports/{report_id}/run", response_model=RunResult,
             dependencies=[Depends(require_permission("reports", "run"))])
async def run_report(report_id: UUID, req: RunRequest, db: AsyncSession = Depends(get_db)):
    return await svc.run_report(db, report_id, req)


@router.get("/reports/{report_id}/export",
            dependencies=[Depends(require_permission("reports", "export"))])
async def export_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    csv_data = await svc.export_report_csv(db, report_id)
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="report_{report_id}.csv"'},
    )


# ── Preview ───────────────────────────────────────────────────────────────────

@router.post("/preview", dependencies=[Depends(require_permission("reports", "run"))])
async def preview_query(
    data_source: str,
    fields: Optional[List[str]] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    if data_source not in svc.DATA_SOURCES:
        raise HTTPException(400, f"Unknown data source: {data_source}")
    ds = svc.DATA_SOURCES[data_source]
    field_metas = [{"path": f["path"]} for f in ds["fields"][:5]]
    result = await svc._execute_query(db, data_source, field_metas, [], limit, 0)
    return result


# ── Schedules ─────────────────────────────────────────────────────────────────

@router.post("/reports/{report_id}/schedule", response_model=ScheduleOut, status_code=201,
             dependencies=[Depends(require_permission("reports", "create"))])
async def create_schedule(report_id: UUID, data: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_schedule(db, report_id, data)


@router.get("/schedules", response_model=List[ScheduleOut],
            dependencies=[Depends(require_permission("reports", "view"))])
async def list_schedules(report_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_schedules(db, report_id)


@router.delete("/schedules/{schedule_id}", status_code=204,
               dependencies=[Depends(require_permission("reports", "admin"))])
async def deactivate_schedule(schedule_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.deactivate_schedule(db, schedule_id)
    if not ok:
        raise HTTPException(404, "Schedule not found")


# ── Dashboards ────────────────────────────────────────────────────────────────

@router.post("/dashboards", response_model=DashboardOut, status_code=201,
             dependencies=[Depends(require_permission("reports", "create"))])
async def create_dashboard(data: DashboardCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_dashboard(db, data)


@router.get("/dashboards", response_model=List[DashboardOut],
            dependencies=[Depends(require_permission("reports", "view"))])
async def list_dashboards(db: AsyncSession = Depends(get_db)):
    return await svc.list_dashboards(db)


@router.get("/dashboards/{dashboard_id}", response_model=DashboardOut,
            dependencies=[Depends(require_permission("reports", "view"))])
async def get_dashboard(dashboard_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_dashboard(db, dashboard_id)
    if not obj:
        raise HTTPException(404, "Dashboard not found")
    return obj


@router.post("/dashboards/{dashboard_id}/widgets", response_model=WidgetOut, status_code=201,
             dependencies=[Depends(require_permission("reports", "edit"))])
async def add_widget(dashboard_id: UUID, data: WidgetCreate, db: AsyncSession = Depends(get_db)):
    return await svc.add_widget(db, dashboard_id, data)


@router.delete("/widgets/{widget_id}", status_code=204,
               dependencies=[Depends(require_permission("reports", "admin"))])
async def delete_widget(widget_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.delete_widget(db, widget_id)
    if not ok:
        raise HTTPException(404, "Widget not found")


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run-builder-assistant", response_model=List[RBAIRecOut],
             dependencies=[Depends(require_permission("reports", "admin"))])
async def run_builder_assistant(db: AsyncSession = Depends(get_db)):
    return await svc.run_builder_assistant(db)


@router.post("/ai/run-insight-generator", response_model=List[RBAIRecOut],
             dependencies=[Depends(require_permission("reports", "admin"))])
async def run_insight_generator(db: AsyncSession = Depends(get_db)):
    return await svc.run_insight_generator(db)


@router.post("/ai/run-performance-optimizer", response_model=List[RBAIRecOut],
             dependencies=[Depends(require_permission("reports", "admin"))])
async def run_performance_optimizer(db: AsyncSession = Depends(get_db)):
    return await svc.run_performance_optimizer(db)


@router.get("/ai/recommendations", response_model=List[RBAIRecOut],
            dependencies=[Depends(require_permission("reports", "view"))])
async def list_ai_recs(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_ai_recs(db, status)


@router.patch("/ai/recommendations/{rec_id}", response_model=RBAIRecOut,
              dependencies=[Depends(require_permission("reports", "view"))])
async def ack_ai_rec(rec_id: UUID, data: RBAIRecAck, db: AsyncSession = Depends(get_db)):
    obj = await svc.ack_ai_rec(db, rec_id, data)
    if not obj:
        raise HTTPException(404, "Recommendation not found")
    return obj


# ── Cross-Module Executive Summary ────────────────────────────────────────────

@router.get("/executive-summary",
            dependencies=[Depends(require_permission("reports", "admin"))])
async def executive_summary(db: AsyncSession = Depends(get_db)):
    """
    Single-call cross-module KPI summary for executive dashboard.
    Queries Sales, Production, Procurement, Inventory, Approvals, Helpdesk.
    """
    from app.models.sales import SalesOrder, SOStatus
    from app.models.procurement import PurchaseOrder, POStatus
    from app.models.production import ProductionOrder, ProductionOrderStatus
    from app.models.inventory import Stock
    from app.models.workflow import ApprovalRequest, ApprovalStatus
    from app.models.helpdesk import HelpdeskTicket, TicketStatus
    from app.models.master import Product, Material
    from datetime import datetime, timedelta

    today = datetime.utcnow().date()
    month_start = today.replace(day=1)

    # ── Sales Orders ──
    so_r = await db.execute(
        select(SalesOrder.status, func.count().label("cnt"))
        .group_by(SalesOrder.status)
    )
    so_by_status = {r.status: r.cnt for r in so_r.all()}
    open_so = sum(v for k, v in so_by_status.items() if k not in (SOStatus.SHIPPED, "CANCELLED", "DELIVERED"))
    so_this_month = await db.execute(
        select(func.count()).select_from(SalesOrder).where(
            func.date(SalesOrder.created_at) >= month_start
        )
    )
    so_month_count = so_this_month.scalar() or 0

    # ── Purchase Orders ──
    po_r = await db.execute(
        select(PurchaseOrder.status, func.count().label("cnt"))
        .group_by(PurchaseOrder.status)
    )
    po_by_status = {r.status: r.cnt for r in po_r.all()}
    open_po = sum(v for k, v in po_by_status.items() if k in (POStatus.APPROVED, POStatus.ORDERED, POStatus.PARTIALLY_RECEIVED))

    # ── Production Orders ──
    prod_r = await db.execute(
        select(ProductionOrder.status, func.count().label("cnt"))
        .group_by(ProductionOrder.status)
    )
    prod_by_status = {r.status: r.cnt for r in prod_r.all()}
    in_progress_prod = prod_by_status.get(ProductionOrderStatus.IN_PROGRESS, 0) + prod_by_status.get(ProductionOrderStatus.RELEASED, 0)
    planned_prod = prod_by_status.get(ProductionOrderStatus.PLANNED, 0)

    # ── Inventory ──
    stock_r = await db.execute(
        select(func.count()).select_from(Stock).where(Stock.quantity_on_hand <= 0)
    )
    zero_stock = stock_r.scalar() or 0

    low_stock_r = await db.execute(
        select(func.count()).select_from(Stock)
        .join(Product, Stock.product_id == Product.id, isouter=True)
        .where(
            Stock.product_id.isnot(None),
            Stock.quantity_on_hand > 0,
            Stock.quantity_on_hand <= Product.reorder_point,
        )
    )
    low_stock = low_stock_r.scalar() or 0

    # ── Approvals ──
    appr_r = await db.execute(
        select(func.count()).select_from(ApprovalRequest).where(
            ApprovalRequest.status == ApprovalStatus.PENDING
        )
    )
    pending_approvals = appr_r.scalar() or 0

    # ── Helpdesk ──
    ticket_r = await db.execute(
        select(func.count()).select_from(HelpdeskTicket).where(
            HelpdeskTicket.status == TicketStatus.OPEN
        )
    )
    open_tickets = ticket_r.scalar() or 0

    # ── Report counts ──
    from app.models.report_builder import ReportDefinition, ReportSchedule
    report_count_r = await db.execute(select(func.count()).select_from(ReportDefinition).where(ReportDefinition.active_flag == True))
    scheduled_count_r = await db.execute(select(func.count()).select_from(ReportSchedule).where(ReportSchedule.active_flag == True))
    total_reports = report_count_r.scalar() or 0
    scheduled_reports = scheduled_count_r.scalar() or 0

    return {
        "as_of": today.isoformat(),
        "sales": {
            "open_orders": open_so,
            "orders_this_month": so_month_count,
            "by_status": {k.value if hasattr(k, "value") else k: v for k, v in so_by_status.items()},
        },
        "procurement": {
            "open_purchase_orders": open_po,
            "by_status": {k.value if hasattr(k, "value") else k: v for k, v in po_by_status.items()},
        },
        "production": {
            "in_progress": in_progress_prod,
            "planned": planned_prod,
            "by_status": {k.value if hasattr(k, "value") else k: v for k, v in prod_by_status.items()},
        },
        "inventory": {
            "zero_stock_items": zero_stock,
            "low_stock_items": low_stock,
        },
        "approvals": {
            "pending": pending_approvals,
        },
        "helpdesk": {
            "open_tickets": open_tickets,
        },
        "reports": {
            "total_active": total_reports,
            "scheduled": scheduled_reports,
        },
    }


# ── Row-Level Security (RLS) ──────────────────────────────────────────────────

class RLSPolicyIn(BaseModel):
    policy_name: str
    data_source: str
    scope: RLSPolicyScope = RLSPolicyScope.USER
    principal: str
    filter_field: str
    operator: FilterOperator = FilterOperator.EQ
    filter_value: str
    description: Optional[str] = None


class RLSPolicyOut(BaseModel):
    policy_id: str
    policy_name: str
    data_source: str
    scope: str
    principal: str
    filter_field: str
    operator: str
    filter_value: str
    active_flag: bool
    description: Optional[str]
    created_by: Optional[str]
    created_at: str

    @classmethod
    def from_orm(cls, p: RLSPolicy) -> "RLSPolicyOut":
        return cls(
            policy_id=str(p.policy_id),
            policy_name=p.policy_name,
            data_source=p.data_source,
            scope=p.scope,
            principal=p.principal,
            filter_field=p.filter_field,
            operator=p.operator,
            filter_value=p.filter_value,
            active_flag=p.active_flag,
            description=p.description,
            created_by=p.created_by,
            created_at=p.created_at.isoformat() if p.created_at else "",
        )


@router.post("/rls", response_model=RLSPolicyOut, status_code=201,
             dependencies=[Depends(require_permission("reports", "admin"))])
async def create_rls_policy(
    payload: RLSPolicyIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a row-level security policy for a report data source."""
    policy = RLSPolicy(
        policy_name=payload.policy_name,
        data_source=payload.data_source,
        scope=payload.scope,
        principal=payload.principal,
        filter_field=payload.filter_field,
        operator=payload.operator,
        filter_value=payload.filter_value,
        description=payload.description,
        created_by=getattr(current_user, "username", None) or str(current_user.id),
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return RLSPolicyOut.from_orm(policy)


@router.get("/rls", response_model=List[RLSPolicyOut],
            dependencies=[Depends(require_permission("reports", "admin"))])
async def list_rls_policies(
    data_source: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """List row-level security policies."""
    q = select(RLSPolicy)
    if data_source:
        q = q.where(RLSPolicy.data_source == data_source)
    if active_only:
        q = q.where(RLSPolicy.active_flag == True)
    q = q.order_by(RLSPolicy.data_source, RLSPolicy.policy_name)
    r = await db.execute(q)
    return [RLSPolicyOut.from_orm(p) for p in r.scalars().all()]


@router.patch("/rls/{policy_id}",
              dependencies=[Depends(require_permission("reports", "admin"))])
async def update_rls_policy(
    policy_id: str,
    active_flag: Optional[bool] = None,
    policy_name: Optional[str] = None,
    filter_value: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Toggle active flag or update a RLS policy."""
    r = await db.execute(select(RLSPolicy).where(RLSPolicy.policy_id == _uuid.UUID(policy_id)))
    policy = r.scalar_one_or_none()
    if not policy:
        raise HTTPException(404, "RLS policy not found")
    if active_flag is not None:
        policy.active_flag = active_flag
    if policy_name is not None:
        policy.policy_name = policy_name
    if filter_value is not None:
        policy.filter_value = filter_value
    await db.commit()
    return RLSPolicyOut.from_orm(policy)


@router.delete("/rls/{policy_id}", status_code=204,
               dependencies=[Depends(require_permission("reports", "admin"))])
async def delete_rls_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Delete a RLS policy."""
    r = await db.execute(select(RLSPolicy).where(RLSPolicy.policy_id == _uuid.UUID(policy_id)))
    policy = r.scalar_one_or_none()
    if not policy:
        raise HTTPException(404, "RLS policy not found")
    await db.delete(policy)
    await db.commit()
