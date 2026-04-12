from __future__ import annotations
from datetime import date
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.crud import field_sales as crud
from app.schemas.field_sales import (
    SalesRepCreate, SalesRepUpdate, SalesRepRead,
    SalesRouteCreate, SalesRouteUpdate, SalesRouteRead,
    DailyTargetCreate, DailyTargetRead,
    VisitLogCreate, VisitLogRead,
)

router = APIRouter()


# ── Sales Reps ────────────────────────────────────────────────────────────────

@router.get("/reps", response_model=List[SalesRepRead],
            dependencies=[Depends(require_permission("sales", "view"))])
async def list_reps(
    region: Optional[str] = Query(None),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_reps(db, region=region, active_only=active_only)


@router.post("/reps", response_model=SalesRepRead, status_code=201,
             dependencies=[Depends(require_permission("sales", "create"))])
async def create_rep(data: SalesRepCreate, db: AsyncSession = Depends(get_db)):
    rep = await crud.create_rep(db, data)
    await db.commit()
    return rep


@router.get("/reps/{rep_id}", response_model=SalesRepRead,
            dependencies=[Depends(require_permission("sales", "view"))])
async def get_rep(rep_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rep = await crud.get_rep(db, rep_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Sales rep not found")
    return rep


@router.patch("/reps/{rep_id}", response_model=SalesRepRead,
              dependencies=[Depends(require_permission("sales", "edit"))])
async def update_rep(rep_id: uuid.UUID, data: SalesRepUpdate, db: AsyncSession = Depends(get_db)):
    rep = await crud.get_rep(db, rep_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Sales rep not found")
    rep = await crud.update_rep(db, rep, data)
    await db.commit()
    return rep


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/routes", response_model=List[SalesRouteRead],
            dependencies=[Depends(require_permission("sales", "view"))])
async def list_routes(
    region: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    routes = await crud.list_routes(db, region=region)
    result = []
    for r in routes:
        rd = SalesRouteRead.model_validate(r)
        if r.assigned_rep:
            rd.rep_name = r.assigned_rep.name
        rd.stop_count = len(r.stops)
        for stop in r.stops:
            if stop.customer:
                stop_rd = rd.stops[r.stops.index(stop)] if rd.stops else None
                if stop_rd:
                    stop_rd.customer_name = stop.customer.name
        result.append(rd)
    return result


@router.post("/routes", response_model=SalesRouteRead, status_code=201,
             dependencies=[Depends(require_permission("sales", "create"))])
async def create_route(data: SalesRouteCreate, db: AsyncSession = Depends(get_db)):
    route = await crud.create_route(db, data)
    await db.commit()
    return route


@router.get("/routes/{route_id}", response_model=SalesRouteRead,
            dependencies=[Depends(require_permission("sales", "view"))])
async def get_route(route_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    route = await crud.get_route(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    rd = SalesRouteRead.model_validate(route)
    if route.assigned_rep:
        rd.rep_name = route.assigned_rep.name
    rd.stop_count = len(route.stops)
    return rd


@router.patch("/routes/{route_id}", response_model=SalesRouteRead,
              dependencies=[Depends(require_permission("sales", "edit"))])
async def update_route(route_id: uuid.UUID, data: SalesRouteUpdate, db: AsyncSession = Depends(get_db)):
    route = await crud.get_route(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    route = await crud.update_route(db, route, data)
    await db.commit()
    return route


# ── Daily Targets ─────────────────────────────────────────────────────────────

@router.get("/targets", response_model=List[DailyTargetRead],
            dependencies=[Depends(require_permission("sales", "view"))])
async def list_targets(
    rep_id: Optional[uuid.UUID] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    targets = await crud.list_targets(db, rep_id=rep_id, from_date=from_date, to_date=to_date)
    result = []
    for t in targets:
        td = DailyTargetRead.model_validate(t)
        if t.rep:
            td.rep_name = t.rep.name
        if t.route:
            td.route_name = t.route.name
        result.append(td)
    return result


@router.post("/targets", response_model=DailyTargetRead, status_code=201,
             dependencies=[Depends(require_permission("sales", "create"))])
async def upsert_target(data: DailyTargetCreate, db: AsyncSession = Depends(get_db)):
    target = await crud.upsert_daily_target(db, data)
    await db.commit()
    return target


# ── Visit Logs ────────────────────────────────────────────────────────────────

@router.get("/visits", response_model=List[VisitLogRead],
            dependencies=[Depends(require_permission("sales", "view"))])
async def list_visits(
    rep_id: Optional[uuid.UUID] = Query(None),
    visit_date: Optional[date] = Query(None),
    route_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    logs = await crud.list_visit_logs(db, rep_id=rep_id, visit_date=visit_date,
                                       route_id=route_id, limit=limit)
    result = []
    for log in logs:
        vl = VisitLogRead.model_validate(log)
        if log.rep:
            vl.rep_name = log.rep.name
        if log.customer:
            vl.customer_name = log.customer.name
        result.append(vl)
    return result


@router.post("/visits", response_model=VisitLogRead, status_code=201,
             dependencies=[Depends(require_permission("sales", "create"))])
async def log_visit(data: VisitLogCreate, db: AsyncSession = Depends(get_db)):
    log = await crud.create_visit_log(db, data)
    await db.commit()
    return log
