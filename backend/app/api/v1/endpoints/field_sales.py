from __future__ import annotations
from datetime import date
from typing import List, Optional
import uuid
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.crud import field_sales as crud
from app.schemas.field_sales import (
    SalesRepCreate, SalesRepUpdate, SalesRepRead,
    SalesRouteCreate, SalesRouteUpdate, SalesRouteRead,
    DailyTargetCreate, DailyTargetRead,
    VisitLogCreate, VisitLogRead,
)


# ── Haversine helper (pure Python, no scipy) ─────────────────────────────────

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

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


# ── Route Optimization ───────────────────────────────────────────────────────

@router.get("/routes/{route_id}/optimize",
            dependencies=[Depends(require_permission("sales", "view"))])
async def optimize_route(route_id: str, db: AsyncSession = Depends(get_db)):
    """
    Nearest-neighbor route optimization.
    Uses customer GPS (or stop lat/lng override) to compute an optimized stop sequence.
    Returns the reordered sequence without modifying the database.
    """
    from app.models.field_sales import SalesRoute, RouteStop
    from app.models.sales import Customer

    r = await db.execute(
        select(SalesRoute)
        .options(selectinload(SalesRoute.stops).selectinload(RouteStop.customer))
        .where(SalesRoute.id == uuid.UUID(route_id))
    )
    route = r.scalar_one_or_none()
    if not route:
        raise HTTPException(404, "Route not found")

    stops = list(route.stops)
    if len(stops) <= 1:
        return {"route_id": route_id, "optimized": False, "reason": "Need ≥2 stops to optimize",
                "sequence": [{"stop_id": str(s.id), "stop_sequence": s.stop_sequence} for s in stops]}

    # Build coordinate list
    def _coords(s: RouteStop):
        lat = float(s.lat_override) if s.lat_override else (float(s.customer.gps_lat) if s.customer and s.customer.gps_lat else None)
        lng = float(s.lng_override) if s.lng_override else (float(s.customer.gps_lng) if s.customer and s.customer.gps_lng else None)
        return lat, lng

    coord_map = {}
    missing = []
    for s in stops:
        lat, lng = _coords(s)
        if lat is None or lng is None:
            missing.append(str(s.id))
        else:
            coord_map[str(s.id)] = (lat, lng)

    if len(coord_map) < 2:
        return {"route_id": route_id, "optimized": False,
                "reason": f"Insufficient GPS data. Missing coords for {len(missing)} stops.",
                "missing_stop_ids": missing,
                "sequence": [{"stop_id": str(s.id), "stop_sequence": s.stop_sequence,
                               "customer_name": s.customer.name if s.customer else None} for s in stops]}

    # Nearest-neighbor algorithm starting from first stop (by current sequence)
    remaining = [s for s in sorted(stops, key=lambda x: x.stop_sequence) if str(s.id) in coord_map]
    uncoord = [s for s in stops if str(s.id) not in coord_map]

    ordered = [remaining.pop(0)]
    while remaining:
        last = ordered[-1]
        last_lat, last_lng = coord_map[str(last.id)]
        nearest = min(remaining, key=lambda s: _haversine_km(last_lat, last_lng, *coord_map[str(s.id)]))
        ordered.append(nearest)
        remaining.remove(nearest)

    # Append stops without coordinates at end
    ordered += uncoord

    # Compute total distance
    total_km = 0.0
    for i in range(1, len(ordered)):
        a, b = str(ordered[i - 1].id), str(ordered[i].id)
        if a in coord_map and b in coord_map:
            total_km += _haversine_km(*coord_map[a], *coord_map[b])

    return {
        "route_id": route_id,
        "optimized": True,
        "total_distance_km": round(total_km, 2),
        "stops_without_gps": missing,
        "sequence": [
            {
                "stop_id": str(s.id),
                "new_sequence": idx + 1,
                "original_sequence": s.stop_sequence,
                "customer_id": str(s.customer_id),
                "customer_name": s.customer.name if s.customer else None,
                "lat": coord_map.get(str(s.id), (None, None))[0],
                "lng": coord_map.get(str(s.id), (None, None))[1],
                "google_maps_link": (
                    f"https://maps.google.com/?q={coord_map[str(s.id)][0]},{coord_map[str(s.id)][1]}"
                    if str(s.id) in coord_map else None
                ),
            }
            for idx, s in enumerate(ordered)
        ],
    }


@router.post("/routes/{route_id}/apply-optimization",
             dependencies=[Depends(require_permission("sales", "edit"))])
async def apply_optimization(route_id: str, stop_order: List[str], db: AsyncSession = Depends(get_db)):
    """
    Apply optimized sequence to route stops.
    stop_order: list of stop UUIDs in desired sequence (index 0 = stop_sequence 1).
    """
    from app.models.field_sales import RouteStop

    for idx, stop_id in enumerate(stop_order):
        r = await db.execute(
            select(RouteStop).where(
                RouteStop.id == uuid.UUID(stop_id),
                RouteStop.route_id == uuid.UUID(route_id),
            )
        )
        stop = r.scalar_one_or_none()
        if stop:
            stop.stop_sequence = idx + 1

    await db.commit()
    return {"route_id": route_id, "stops_updated": len(stop_order), "status": "applied"}


@router.get("/routes/{route_id}/profitability",
            dependencies=[Depends(require_permission("sales", "view"))])
async def route_profitability(
    route_id: str,
    fuel_cost_per_km: float = Query(default=15.0, description="KES per km"),
    db: AsyncSession = Depends(get_db),
):
    """Route profitability: estimated revenue from customers vs fuel cost estimate."""
    from app.models.field_sales import SalesRoute, RouteStop
    from app.models.sales import SalesOrder, SOStatus

    r = await db.execute(
        select(SalesRoute)
        .options(selectinload(SalesRoute.stops).selectinload(RouteStop.customer))
        .where(SalesRoute.id == uuid.UUID(route_id))
    )
    route = r.scalar_one_or_none()
    if not route:
        raise HTTPException(404, "Route not found")

    stops = list(route.stops)
    customer_ids = [s.customer_id for s in stops]

    # Estimate total distance
    def _coords(s: RouteStop):
        lat = float(s.lat_override) if s.lat_override else (float(s.customer.gps_lat) if s.customer and s.customer.gps_lat else None)
        lng = float(s.lng_override) if s.lng_override else (float(s.customer.gps_lng) if s.customer and s.customer.gps_lng else None)
        return lat, lng

    total_km = 0.0
    ordered = sorted(stops, key=lambda s: s.stop_sequence)
    for i in range(1, len(ordered)):
        la, loa = _coords(ordered[i - 1])
        lb, lob = _coords(ordered[i])
        if all(v is not None for v in [la, loa, lb, lob]):
            total_km += _haversine_km(la, loa, lb, lob)

    fuel_cost = total_km * fuel_cost_per_km

    stop_details = []
    for s in ordered:
        stop_details.append({
            "stop_sequence": s.stop_sequence,
            "customer_id": str(s.customer_id),
            "customer_name": s.customer.name if s.customer else None,
        })

    return {
        "route_id": route_id,
        "route_name": route.route_name if hasattr(route, "route_name") else "",
        "stop_count": len(stops),
        "estimated_distance_km": round(total_km, 2),
        "fuel_cost_estimate_kes": round(fuel_cost, 2),
        "fuel_cost_per_km": fuel_cost_per_km,
        "stops": stop_details,
    }
