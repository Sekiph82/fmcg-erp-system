from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import io
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.report_builder import (
    ReportCreate, ReportUpdate, ReportOut, RunRequest, RunResult,
    ScheduleCreate, ScheduleOut,
    DashboardCreate, DashboardOut, WidgetCreate, WidgetOut,
    RBAIRecOut, RBAIRecAck,
)
import app.services.report_builder_service as svc

router = APIRouter()


# ── Metadata ──────────────────────────────────────────────────────────────────

@router.get("/catalog")
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


@router.get("/catalog/{data_source}")
async def get_data_source(data_source: str):
    ds = svc.DATA_SOURCES.get(data_source)
    if not ds:
        raise HTTPException(404, f"Data source '{data_source}' not found")
    return ds


# ── Reports ───────────────────────────────────────────────────────────────────

@router.post("/reports", response_model=ReportOut, status_code=201)
async def create_report(data: ReportCreate, db: AsyncSession = Depends(get_db)):
    if data.data_source not in svc.DATA_SOURCES:
        raise HTTPException(400, f"Unknown data source: {data.data_source}")
    return await svc.create_report(db, data)


@router.get("/reports", response_model=List[ReportOut])
async def list_reports(
    data_source: Optional[str] = None,
    owner: Optional[str] = None,
    template_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_reports(db, data_source, owner, template_only)


@router.get("/reports/{report_id}", response_model=ReportOut)
async def get_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_report(db, report_id)
    if not obj:
        raise HTTPException(404, "Report not found")
    return obj


@router.patch("/reports/{report_id}", response_model=ReportOut)
async def update_report(report_id: UUID, data: ReportUpdate, db: AsyncSession = Depends(get_db)):
    obj = await svc.update_report(db, report_id, data)
    if not obj:
        raise HTTPException(404, "Report not found")
    return obj


@router.delete("/reports/{report_id}", status_code=204)
async def delete_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.delete_report(db, report_id)
    if not ok:
        raise HTTPException(404, "Report not found")


@router.post("/reports/{report_id}/clone", response_model=ReportOut, status_code=201)
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


@router.post("/reports/seed-templates")
async def seed_templates(db: AsyncSession = Depends(get_db)):
    count = await svc.seed_templates(db)
    return {"created": count}


# ── Run ───────────────────────────────────────────────────────────────────────

@router.post("/reports/{report_id}/run", response_model=RunResult)
async def run_report(report_id: UUID, req: RunRequest, db: AsyncSession = Depends(get_db)):
    return await svc.run_report(db, report_id, req)


@router.get("/reports/{report_id}/export")
async def export_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    csv_data = await svc.export_report_csv(db, report_id)
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="report_{report_id}.csv"'},
    )


# ── Preview ───────────────────────────────────────────────────────────────────

@router.post("/preview")
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

@router.post("/reports/{report_id}/schedule", response_model=ScheduleOut, status_code=201)
async def create_schedule(report_id: UUID, data: ScheduleCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_schedule(db, report_id, data)


@router.get("/schedules", response_model=List[ScheduleOut])
async def list_schedules(report_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_schedules(db, report_id)


@router.delete("/schedules/{schedule_id}", status_code=204)
async def deactivate_schedule(schedule_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.deactivate_schedule(db, schedule_id)
    if not ok:
        raise HTTPException(404, "Schedule not found")


# ── Dashboards ────────────────────────────────────────────────────────────────

@router.post("/dashboards", response_model=DashboardOut, status_code=201)
async def create_dashboard(data: DashboardCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_dashboard(db, data)


@router.get("/dashboards", response_model=List[DashboardOut])
async def list_dashboards(db: AsyncSession = Depends(get_db)):
    return await svc.list_dashboards(db)


@router.get("/dashboards/{dashboard_id}", response_model=DashboardOut)
async def get_dashboard(dashboard_id: UUID, db: AsyncSession = Depends(get_db)):
    obj = await svc.get_dashboard(db, dashboard_id)
    if not obj:
        raise HTTPException(404, "Dashboard not found")
    return obj


@router.post("/dashboards/{dashboard_id}/widgets", response_model=WidgetOut, status_code=201)
async def add_widget(dashboard_id: UUID, data: WidgetCreate, db: AsyncSession = Depends(get_db)):
    return await svc.add_widget(db, dashboard_id, data)


@router.delete("/widgets/{widget_id}", status_code=204)
async def delete_widget(widget_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await svc.delete_widget(db, widget_id)
    if not ok:
        raise HTTPException(404, "Widget not found")


# ── AI ────────────────────────────────────────────────────────────────────────

@router.post("/ai/run-builder-assistant", response_model=List[RBAIRecOut])
async def run_builder_assistant(db: AsyncSession = Depends(get_db)):
    return await svc.run_builder_assistant(db)


@router.post("/ai/run-insight-generator", response_model=List[RBAIRecOut])
async def run_insight_generator(db: AsyncSession = Depends(get_db)):
    return await svc.run_insight_generator(db)


@router.post("/ai/run-performance-optimizer", response_model=List[RBAIRecOut])
async def run_performance_optimizer(db: AsyncSession = Depends(get_db)):
    return await svc.run_performance_optimizer(db)


@router.get("/ai/recommendations", response_model=List[RBAIRecOut])
async def list_ai_recs(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await svc.list_ai_recs(db, status)


@router.patch("/ai/recommendations/{rec_id}", response_model=RBAIRecOut)
async def ack_ai_rec(rec_id: UUID, data: RBAIRecAck, db: AsyncSession = Depends(get_db)):
    obj = await svc.ack_ai_rec(db, rec_id, data)
    if not obj:
        raise HTTPException(404, "Recommendation not found")
    return obj
