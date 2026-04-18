"""
Utility KPI Center — FastAPI router.
Prefixed at /kpi by the main router.

All KPI computation lives in utility_kpi_service; this file is thin.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.utility_kpi import (
    BoilerDashboardKPIs,
    ChemicalDashboardKPIs,
    CompressorDashboardKPIs,
    DailyTrendPoint,
    ElectricityDashboardKPIs,
    MachineDashboardKPIs,
    MainDashboardKPIs,
    SoftWaterDashboardKPIs,
    SolarDashboardKPIs,
    TopConsumers,
    UtilityCostDashboardKPIs,
    WastewaterDashboardKPIs,
    WaterDashboardKPIs,
)
from app.services.utility_kpi_service import (
    get_boiler_kpis,
    get_chemical_kpis,
    get_compressor_kpis,
    get_daily_trend,
    get_electricity_kpis,
    get_machine_kpis,
    get_main_dashboard_kpis,
    get_soft_water_kpis,
    get_solar_kpis,
    get_top_consumers,
    get_utility_cost_kpis,
    get_wastewater_kpis,
    get_water_kpis,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _default_range() -> tuple[date, date]:
    today = date.today()
    return today, today


# ── Main dashboard ─────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=MainDashboardKPIs)
async def main_dashboard(
    report_date:     Optional[date]  = Query(default_factory=date.today),
    production_tons: Optional[float] = Query(None, description="Production tonnes for /ton KPIs"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await get_main_dashboard_kpis(
        db, report_date=report_date or date.today(),
        production_tons=production_tons,
    )


# ── Top consumers ─────────────────────────────────────────────────────────────

@router.get("/top-consumers", response_model=TopConsumers)
async def top_consumers(
    dimension:    str           = Query("department"),
    utility_type: Optional[str] = Query(None),
    date_from:    Optional[date] = Query(None),
    date_to:      Optional[date] = Query(None),
    top_n:        int           = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    today = date.today()
    return await get_top_consumers(
        db,
        dimension=dimension,
        utility_type=utility_type,
        date_from=date_from or today.replace(day=1),
        date_to=date_to or today,
        top_n=top_n,
    )


# ── Daily multi-utility trend ─────────────────────────────────────────────────

@router.get("/trend", response_model=List[DailyTrendPoint])
async def daily_trend(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    today = date.today()
    return await get_daily_trend(
        db,
        date_from=date_from or (today - timedelta(days=29)),
        date_to=date_to or today,
    )


# ── Per-utility sub-dashboards ────────────────────────────────────────────────

@router.get("/electricity", response_model=ElectricityDashboardKPIs)
async def electricity_kpis(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    today = date.today()
    return await get_electricity_kpis(
        db,
        date_from=date_from or today.replace(day=1),
        date_to=date_to or today,
    )


@router.get("/water", response_model=WaterDashboardKPIs)
async def water_kpis(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    today = date.today()
    return await get_water_kpis(
        db,
        date_from=date_from or today.replace(day=1),
        date_to=date_to or today,
    )


@router.get("/boiler", response_model=BoilerDashboardKPIs)
async def boiler_kpis(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    today = date.today()
    return await get_boiler_kpis(
        db,
        date_from=date_from or today.replace(day=1),
        date_to=date_to or today,
    )


@router.get("/compressor", response_model=CompressorDashboardKPIs)
async def compressor_kpis(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    today = date.today()
    return await get_compressor_kpis(
        db,
        date_from=date_from or today.replace(day=1),
        date_to=date_to or today,
    )


@router.get("/soft-water", response_model=SoftWaterDashboardKPIs)
async def soft_water_kpis(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    today = date.today()
    return await get_soft_water_kpis(
        db,
        date_from=date_from or today.replace(day=1),
        date_to=date_to or today,
    )


@router.get("/solar", response_model=SolarDashboardKPIs)
async def solar_kpis(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    today = date.today()
    return await get_solar_kpis(
        db,
        date_from=date_from or today.replace(day=1),
        date_to=date_to or today,
    )


@router.get("/chemicals", response_model=ChemicalDashboardKPIs)
async def chemicals_kpis(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    today = date.today()
    return await get_chemical_kpis(
        db,
        date_from=date_from or today.replace(day=1),
        date_to=date_to or today,
    )


@router.get("/wastewater", response_model=WastewaterDashboardKPIs)
async def wastewater_kpis(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    today = date.today()
    return await get_wastewater_kpis(
        db,
        date_from=date_from or today.replace(day=1),
        date_to=date_to or today,
    )


@router.get("/machine-utility", response_model=MachineDashboardKPIs)
async def machine_utility_kpis(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    today = date.today()
    return await get_machine_kpis(
        db,
        date_from=date_from or today.replace(day=1),
        date_to=date_to or today,
    )


@router.get("/utility-cost", response_model=UtilityCostDashboardKPIs)
async def utility_cost_kpis(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    today = date.today()
    return await get_utility_cost_kpis(
        db,
        date_from=date_from or today.replace(day=1),
        date_to=date_to or today,
    )
