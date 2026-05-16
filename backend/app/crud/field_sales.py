from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Optional, List
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.field_sales import SalesRep, SalesRoute, RouteStop, DailyTarget, VisitLog
from app.models.sales import SalesOrder
from app.schemas.field_sales import (
    SalesRepCreate, SalesRepUpdate, SalesRouteCreate, SalesRouteUpdate,
    DailyTargetCreate, VisitLogCreate, RepPerformance,
)


# ── Sales Reps ────────────────────────────────────────────────────────────────

async def list_reps(db: AsyncSession, *, region: Optional[str] = None, active_only: bool = False, limit: int = 200, offset: int = 0) -> List[SalesRep]:
    q = select(SalesRep)
    if region:
        q = q.where(SalesRep.region == region)
    if active_only:
        q = q.where(SalesRep.is_active == True)  # noqa
    result = await db.execute(q.order_by(SalesRep.name).offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_rep(db: AsyncSession, rep_id: uuid.UUID) -> Optional[SalesRep]:
    result = await db.execute(
        select(SalesRep)
        .options(selectinload(SalesRep.routes), selectinload(SalesRep.daily_targets))
        .where(SalesRep.id == rep_id)
    )
    return result.scalar_one_or_none()


async def create_rep(db: AsyncSession, data: SalesRepCreate) -> SalesRep:
    rep = SalesRep(**data.model_dump())
    db.add(rep)
    await db.flush()
    await db.refresh(rep)
    return rep


async def update_rep(db: AsyncSession, rep: SalesRep, data: SalesRepUpdate) -> SalesRep:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(rep, k, v)
    await db.flush()
    await db.refresh(rep)
    return rep


# ── Routes ────────────────────────────────────────────────────────────────────

async def list_routes(db: AsyncSession, *, region: Optional[str] = None, limit: int = 200, offset: int = 0) -> List[SalesRoute]:
    q = select(SalesRoute).options(
        selectinload(SalesRoute.stops).selectinload(RouteStop.customer),
        selectinload(SalesRoute.assigned_rep),
    )
    if region:
        q = q.where(SalesRoute.region == region)
    result = await db.execute(q.order_by(SalesRoute.name).offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_route(db: AsyncSession, route_id: uuid.UUID) -> Optional[SalesRoute]:
    result = await db.execute(
        select(SalesRoute)
        .options(
            selectinload(SalesRoute.stops).selectinload(RouteStop.customer),
            selectinload(SalesRoute.assigned_rep),
        )
        .where(SalesRoute.id == route_id)
    )
    return result.scalar_one_or_none()


async def create_route(db: AsyncSession, data: SalesRouteCreate) -> SalesRoute:
    stops_data = data.stops
    route = SalesRoute(**data.model_dump(exclude={"stops"}))
    db.add(route)
    await db.flush()
    for s in stops_data:
        db.add(RouteStop(route_id=route.id, **s.model_dump()))
    await db.flush()
    await db.refresh(route)
    return route


async def update_route(db: AsyncSession, route: SalesRoute, data: SalesRouteUpdate) -> SalesRoute:
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(route, k, v)
    await db.flush()
    await db.refresh(route)
    return route


# ── Daily Targets ─────────────────────────────────────────────────────────────

async def upsert_daily_target(db: AsyncSession, data: DailyTargetCreate) -> DailyTarget:
    result = await db.execute(
        select(DailyTarget).where(
            and_(DailyTarget.rep_id == data.rep_id, DailyTarget.target_date == data.target_date)
        )
    )
    target = result.scalar_one_or_none()
    if target:
        for k, v in data.model_dump(exclude={"rep_id", "target_date"}).items():
            if v is not None:
                setattr(target, k, v)
    else:
        target = DailyTarget(**data.model_dump())
        db.add(target)
    await db.flush()
    await db.refresh(target)
    return target


async def list_targets(
    db: AsyncSession,
    *,
    rep_id: Optional[uuid.UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit: int = 200,
    offset: int = 0,
) -> List[DailyTarget]:
    q = select(DailyTarget).options(
        selectinload(DailyTarget.rep),
        selectinload(DailyTarget.route),
    )
    if rep_id:
        q = q.where(DailyTarget.rep_id == rep_id)
    if from_date:
        q = q.where(DailyTarget.target_date >= from_date)
    if to_date:
        q = q.where(DailyTarget.target_date <= to_date)
    result = await db.execute(q.order_by(DailyTarget.target_date.desc()).offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


# ── Visit Logs ────────────────────────────────────────────────────────────────

async def create_visit_log(db: AsyncSession, data: VisitLogCreate) -> VisitLog:
    log = VisitLog(**data.model_dump())
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def list_visit_logs(
    db: AsyncSession,
    *,
    rep_id: Optional[uuid.UUID] = None,
    visit_date: Optional[date] = None,
    route_id: Optional[uuid.UUID] = None,
    limit: int = 100,
) -> List[VisitLog]:
    q = select(VisitLog).options(
        selectinload(VisitLog.rep),
        selectinload(VisitLog.customer),
    )
    if rep_id:
        q = q.where(VisitLog.rep_id == rep_id)
    if visit_date:
        q = q.where(VisitLog.visit_date == visit_date)
    if route_id:
        q = q.where(VisitLog.route_id == route_id)
    result = await db.execute(q.order_by(VisitLog.visited_at.desc()).limit(limit))
    return list(result.scalars().all())
