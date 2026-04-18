"""
Utility KPI Service — centralised KPI computation for all utility systems.

All KPI formulas live here; endpoints are thin wrappers that call these
functions. Each function is independently queryable so the frontend can
request only what it needs.

KPI formula reference
---------------------
  electricity_kwh_per_ton      = SUM(elec_kwh) / production_tons
  water_m3_per_ton             = SUM(water_m3) / production_tons
  gas_nm3_per_ton              = SUM(gas_nm3) / production_tons
  gas_per_ton_steam            = SUM(fuel_consumed) / (SUM(steam_generated_kg)/1000)
  condensate_recovery_pct      = SUM(condensate_returned_m3) /
                                 (SUM(steam_generated_kg)/1000) * 100
  blowdown_loss_pct            = SUM(blowdown_volume_litres)/1000 /
                                 SUM(feedwater_consumed_m3) * 100
  air_kwh_per_nm3              = SUM(electricity_used_kwh) / SUM(air_generated_nm3)
  soft_water_conversion_pct    = SUM(volume_treated_m3) / SUM(raw_water_input_m3) * 100
  salt_per_m3_soft             = SUM(salt_consumed_kg) / SUM(volume_treated_m3)
  solar_contribution_pct       = SUM(solar_kwh) / SUM(total_elec_kwh) * 100
  cod_removal_pct              = (1 - AVG(effluent_cod) / AVG(influent_cod)) * 100
  machine_standby_pct          = SUM(standby_cons) / SUM(total_cons) * 100
  utility_cost_per_ton         = SUM(total_cost) / production_tons
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import Integer, and_, cast, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.utility_management import (
    AlarmSeverity,
    AlarmStatus,
    BillStatus,
    BoilerSteamRecord,
    CompressorRecord,
    ComplianceStatus,
    MachineConsumptionRecord,
    SoftWaterRecord,
    SolarRecord,
    TreatmentChemicalRecord,
    UtilityAlarmEvent,
    UtilityBill,
    UtilityCostAllocation,
    UtilityTransaction,
    UtilityType,
    WastewaterRecord,
)
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
    TopConsumerRow,
    TopConsumers,
    UtilityCostDashboardKPIs,
    WastewaterDashboardKPIs,
    WaterDashboardKPIs,
)

logger = logging.getLogger(__name__)

_D  = lambda v: Decimal(str(v)) if v is not None else Decimal("0")
_DN = lambda v: Decimal(str(v)) if v is not None else None
_R  = lambda v, dp=2: Decimal(str(round(float(v), dp))) if v is not None else None
_safe_div = lambda a, b: _R(_D(a) / _D(b)) if b and float(b) != 0.0 else None


# ── Helper: date clause builder ───────────────────────────────────────────────

def _dt_clause(col, d_from: date, d_to: date):
    """Returns a WHERE clause for a Date column."""
    return and_(col >= d_from, col <= d_to)


def _dtime_date_clause(col, d_from: date, d_to: date):
    """Cast DateTime column to Date for range filter."""
    from sqlalchemy import func as sqlfunc
    return and_(sqlfunc.date(col) >= d_from, sqlfunc.date(col) <= d_to)


# ── Main dashboard KPIs ───────────────────────────────────────────────────────

async def get_main_dashboard_kpis(
    db: AsyncSession,
    *,
    report_date: date,
    production_tons: Optional[float] = None,
) -> MainDashboardKPIs:
    d_from = d_to = report_date

    # ── Utility transactions (electricity, water, gas) ────────────────────────
    tx_agg = list((await db.execute(
        select(
            UtilityTransaction.utility_type.label("utype"),
            func.sum(UtilityTransaction.quantity).label("qty"),
            func.max(UtilityTransaction.unit_of_measure).label("unit"),
            func.sum(UtilityTransaction.total_cost).label("cost"),
            func.sum(cast(UtilityTransaction.is_estimated, Integer)).label("est_cnt"),
            func.count().label("cnt"),
        )
        .where(_dt_clause(UtilityTransaction.transaction_date, d_from, d_to))
        .group_by(UtilityTransaction.utility_type)
    )).all())

    tx_by_type: dict = {r.utype.value if hasattr(r.utype, "value") else str(r.utype): r for r in tx_agg}

    def _tx_qty(utype: str) -> Optional[Decimal]:
        r = tx_by_type.get(utype)
        return _DN(r.qty) if r else None

    def _tx_cost(utype: str) -> Optional[Decimal]:
        r = tx_by_type.get(utype)
        return _DN(r.cost) if r else None

    elec_kwh   = _tx_qty("ELECTRICITY")
    water_m3   = _tx_qty("WATER")
    gas_nm3    = _tx_qty("NATURAL_GAS")
    has_est    = any(r.est_cnt and r.est_cnt > 0 for r in tx_agg)
    total_tx_cost = sum((_D(r.cost) for r in tx_agg if r.cost), Decimal("0"))

    # ── Electricity MTD ───────────────────────────────────────────────────────
    mtd_start = report_date.replace(day=1)
    elec_mtd_agg = (await db.execute(
        select(func.sum(UtilityTransaction.quantity))
        .where(and_(
            UtilityTransaction.utility_type == UtilityType.ELECTRICITY,
            _dt_clause(UtilityTransaction.transaction_date, mtd_start, d_to),
        ))
    )).scalar()
    elec_kwh_mtd = _DN(elec_mtd_agg)

    # ── Boiler / Steam ────────────────────────────────────────────────────────
    boiler_agg = (await db.execute(
        select(
            func.sum(BoilerSteamRecord.steam_generated_kg).label("steam_kg"),
            func.sum(BoilerSteamRecord.fuel_consumption).label("fuel"),
            func.max(BoilerSteamRecord.fuel_unit).label("fuel_unit"),
            func.avg(BoilerSteamRecord.boiler_efficiency_pct).label("eff"),
            func.sum(BoilerSteamRecord.condensate_returned_m3).label("condensate"),
            func.sum(BoilerSteamRecord.feedwater_consumed_m3).label("feedwater"),
            func.sum(BoilerSteamRecord.blowdown_volume_litres).label("blowdown_l"),
        )
        .where(_dtime_date_clause(BoilerSteamRecord.record_datetime, d_from, d_to))
    )).one()

    steam_ton = _R(_D(boiler_agg.steam_kg) / 1000, 3) if boiler_agg.steam_kg else None
    gas_per_ton_steam = (
        _safe_div(boiler_agg.fuel, _D(boiler_agg.steam_kg) / 1000)
        if boiler_agg.fuel and boiler_agg.steam_kg else None
    )
    condensate_pct = (
        _R(_D(boiler_agg.condensate) / (_D(boiler_agg.steam_kg) / 1000) * 100, 1)
        if boiler_agg.condensate and boiler_agg.steam_kg else None
    )
    blowdown_pct = (
        _R(_D(boiler_agg.blowdown_l) / 1000 / _D(boiler_agg.feedwater) * 100, 1)
        if boiler_agg.blowdown_l and boiler_agg.feedwater else None
    )

    # ── Compressor / Air ──────────────────────────────────────────────────────
    comp_agg = (await db.execute(
        select(
            func.sum(CompressorRecord.air_generated_nm3).label("air"),
            func.sum(CompressorRecord.electricity_used_kwh).label("elec"),
            func.avg(CompressorRecord.specific_energy_kwh_m3).label("spec"),
            func.avg(CompressorRecord.leak_estimation_pct).label("leak"),
            func.avg(CompressorRecord.load_pct).label("load"),
        )
        .where(_dtime_date_clause(CompressorRecord.record_datetime, d_from, d_to))
    )).one()

    air_kwh_per_nm3 = (
        _safe_div(comp_agg.elec, comp_agg.air)
        if comp_agg.elec and comp_agg.air else _DN(comp_agg.spec)
    )
    air_nm3_today = _DN(comp_agg.air)

    # ── Soft Water ────────────────────────────────────────────────────────────
    sw_agg = (await db.execute(
        select(
            func.sum(SoftWaterRecord.volume_treated_m3).label("sw"),
            func.sum(SoftWaterRecord.raw_water_input_m3).label("raw"),
            func.sum(SoftWaterRecord.salt_consumed_kg).label("salt"),
            func.avg(SoftWaterRecord.efficiency_pct).label("eff"),
        )
        .where(_dtime_date_clause(SoftWaterRecord.record_datetime, d_from, d_to))
    )).one()

    sw_eff = (
        _R(_D(sw_agg.sw) / _D(sw_agg.raw) * 100, 1)
        if sw_agg.sw and sw_agg.raw else _DN(sw_agg.eff)
    )
    salt_per_m3 = _safe_div(sw_agg.salt, sw_agg.sw) if sw_agg.salt and sw_agg.sw else None

    # ── Solar ─────────────────────────────────────────────────────────────────
    solar_agg = (await db.execute(
        select(
            func.sum(SolarRecord.energy_generated_kwh).label("kwh"),
            func.avg(SolarRecord.pr_ratio).label("pr"),
            func.avg(SolarRecord.capacity_factor_pct).label("cf"),
        )
        .where(_dtime_date_clause(SolarRecord.record_datetime, d_from, d_to))
    )).one()

    solar_kwh = _DN(solar_agg.kwh)
    total_elec = (_D(elec_kwh) + _D(solar_kwh)) if elec_kwh or solar_kwh else None
    solar_contribution = (
        _R(_D(solar_kwh) / total_elec * 100, 1)
        if solar_kwh and total_elec and float(total_elec) > 0 else None
    )

    # ── Wastewater ────────────────────────────────────────────────────────────
    ww_agg = (await db.execute(
        select(
            func.avg(WastewaterRecord.influent_cod_mgl).label("in_cod"),
            func.avg(WastewaterRecord.effluent_cod_mgl).label("out_cod"),
            func.avg(WastewaterRecord.effluent_flow_m3h).label("eff_flow"),
            func.sum(WastewaterRecord.power_consumed_kwh).label("power"),
            func.max(WastewaterRecord.compliance_status).label("compliance"),
        )
        .where(_dtime_date_clause(WastewaterRecord.record_datetime, d_from, d_to))
    )).one()

    cod_removal = (
        _R((1 - _D(ww_agg.out_cod) / _D(ww_agg.in_cod)) * 100, 1)
        if ww_agg.in_cod and ww_agg.out_cod and float(ww_agg.in_cod) > 0 else None
    )
    compliance_str = (
        ww_agg.compliance.value if hasattr(ww_agg.compliance, "value") else str(ww_agg.compliance)
        if ww_agg.compliance else None
    )
    ww_cost_per_m3 = (
        _safe_div(total_tx_cost, _D(ww_agg.eff_flow) * 24)
        if ww_agg.eff_flow else None
    )

    # ── Treatment chemicals cost ───────────────────────────────────────────────
    chem_cost = (await db.execute(
        select(func.sum(TreatmentChemicalRecord.consumed_qty * TreatmentChemicalRecord.unit_cost))
        .where(TreatmentChemicalRecord.date == report_date)
    )).scalar()

    # ── Utility cost (MTD from transactions) ──────────────────────────────────
    cost_mtd_agg = (await db.execute(
        select(func.sum(UtilityTransaction.total_cost))
        .where(_dt_clause(UtilityTransaction.transaction_date, mtd_start, d_to))
    )).scalar()

    # ── Cost from bills (MTD allocations) ────────────────────────────────────
    alloc_mtd = (await db.execute(
        select(
            func.sum(UtilityCostAllocation.allocated_cost).label("cost"),
            func.sum(UtilityCostAllocation.production_volume_kg).label("kg"),
            func.count(distinct(UtilityCostAllocation.batch_no)).label("batches"),
        )
        .where(
            and_(
                UtilityCostAllocation.allocation_date >= mtd_start,
                UtilityCostAllocation.allocation_date <= d_to,
            )
        )
    )).one()

    prod_tons = Decimal(str(production_tons)) if production_tons else (
        _D(alloc_mtd.kg) / 1000 if alloc_mtd.kg else None
    )
    batch_count = int(alloc_mtd.batches or 0)
    alloc_cost  = _DN(alloc_mtd.cost)
    cost_today  = _DN(total_tx_cost) if float(total_tx_cost) > 0 else None
    cost_mtd    = _DN(cost_mtd_agg)

    cost_per_ton = (
        _safe_div(alloc_cost, prod_tons) if alloc_cost and prod_tons else
        _safe_div(cost_mtd, prod_tons) if cost_mtd and prod_tons else None
    )
    cost_per_batch = (
        _R(_D(alloc_cost) / batch_count, 4) if alloc_cost and batch_count > 0 else None
    )

    # ── Machine standby ───────────────────────────────────────────────────────
    mach_agg = (await db.execute(
        select(
            func.sum(MachineConsumptionRecord.actual_consumption).label("total"),
            func.sum(
                MachineConsumptionRecord.actual_consumption
                * cast(MachineConsumptionRecord.is_standby, Integer)
            ).label("standby"),
        )
        .where(MachineConsumptionRecord.record_date == report_date)
    )).one()

    standby_pct = (
        _R(_D(mach_agg.standby) / _D(mach_agg.total) * 100, 1)
        if mach_agg.standby and mach_agg.total and float(mach_agg.total) > 0 else None
    )

    # ── Active alarms ─────────────────────────────────────────────────────────
    alarm_agg = list((await db.execute(
        select(
            UtilityAlarmEvent.severity.label("sev"),
            func.count().label("cnt"),
        )
        .join(
            UtilityAlarmEvent.__table__.c,
            isouter=False,
        )
        .where(UtilityAlarmEvent.status == AlarmStatus.ACTIVE)
        .group_by(UtilityAlarmEvent.severity)
    )).all())

    # Fallback: simple count query if join fails
    try:
        crit_cnt = sum(r.cnt for r in alarm_agg if hasattr(r.sev, "value") and r.sev.value == "CRITICAL")
        warn_cnt = sum(r.cnt for r in alarm_agg if hasattr(r.sev, "value") and r.sev.value in ("WARNING", "ALERT"))
    except Exception:
        crit_cnt = warn_cnt = 0

    # ── KPIs per ton ─────────────────────────────────────────────────────────
    elec_per_ton  = _safe_div(elec_kwh, prod_tons) if elec_kwh and prod_tons else None
    water_per_ton = _safe_div(water_m3, prod_tons) if water_m3 and prod_tons else None
    gas_per_ton   = _safe_div(gas_nm3, prod_tons) if gas_nm3 and prod_tons else None

    return MainDashboardKPIs(
        report_date=str(report_date),
        electricity_kwh_today=_R(elec_kwh, 1),
        electricity_kwh_mtd=_R(elec_kwh_mtd, 1),
        electricity_kwh_per_ton=_R(elec_per_ton, 2),
        water_m3_today=_R(water_m3, 2),
        water_m3_per_ton=_R(water_per_ton, 3),
        gas_nm3_today=_R(gas_nm3, 1),
        gas_nm3_per_ton=_R(gas_per_ton, 2),
        steam_ton_today=steam_ton,
        gas_per_ton_steam=_R(gas_per_ton_steam, 3),
        condensate_recovery_pct=condensate_pct,
        blowdown_loss_pct=blowdown_pct,
        boiler_efficiency_pct=_R(boiler_agg.eff, 1),
        air_nm3_today=_R(air_nm3_today, 1),
        air_kwh_per_nm3=_R(air_kwh_per_nm3, 4),
        leak_estimate_pct=_R(comp_agg.leak, 1),
        compressor_efficiency_pct=_R(comp_agg.load, 1),
        soft_water_m3_today=_R(sw_agg.sw, 2),
        soft_water_conversion_pct=sw_eff,
        salt_per_m3_soft=_R(salt_per_m3, 3),
        solar_kwh_today=_R(solar_kwh, 1),
        solar_contribution_pct=solar_contribution,
        wastewater_cost_per_m3=_R(ww_cost_per_m3, 4),
        cod_removal_pct=cod_removal,
        wastewater_compliance=compliance_str,
        chemical_cost_today=_R(chem_cost, 2),
        utility_cost_today=_R(cost_today, 2),
        utility_cost_mtd=_R(cost_mtd, 2),
        utility_cost_per_ton=_R(cost_per_ton, 4),
        utility_cost_per_batch=_R(cost_per_batch, 4),
        machine_standby_pct=standby_pct,
        production_tons_today=_R(prod_tons, 2) if prod_tons else None,
        critical_alarm_count=crit_cnt,
        warning_alarm_count=warn_cnt,
        has_estimated_data=has_est,
    )


# ── Top consumers ─────────────────────────────────────────────────────────────

async def get_top_consumers(
    db: AsyncSession,
    *,
    dimension: str = "department",
    utility_type: Optional[str] = None,
    date_from: date,
    date_to: date,
    top_n: int = 10,
) -> TopConsumers:
    _DIM = {
        "department":     UtilityTransaction.department,
        "production_line": UtilityTransaction.production_line,
        "machine_ref":    UtilityTransaction.machine_ref,
    }
    dim_col = _DIM.get(dimension, UtilityTransaction.department)

    clauses = [_dt_clause(UtilityTransaction.transaction_date, date_from, date_to)]
    if utility_type:
        try:
            clauses.append(UtilityTransaction.utility_type == UtilityType(utility_type))
        except ValueError:
            pass

    rows_raw = list((await db.execute(
        select(
            dim_col.label("grp"),
            func.sum(UtilityTransaction.quantity).label("qty"),
            func.max(UtilityTransaction.unit_of_measure).label("unit"),
            func.sum(UtilityTransaction.total_cost).label("cost"),
            func.count().label("cnt"),
        )
        .where(and_(*clauses))
        .group_by(dim_col)
        .order_by(func.sum(UtilityTransaction.quantity).desc())
        .limit(top_n)
    )).all())

    grand = sum(_D(r.qty) for r in rows_raw) or Decimal("1")
    rows = [
        TopConsumerRow(
            label=str(r.grp) if r.grp else f"(no {dimension})",
            consumption=_D(r.qty),
            unit=r.unit or "",
            cost=_DN(r.cost),
            pct_of_total=_R(_D(r.qty) / grand * 100, 1),
            record_count=int(r.cnt or 0),
        )
        for r in rows_raw
    ]
    return TopConsumers(
        dimension=dimension,
        utility_type=utility_type,
        date_from=str(date_from),
        date_to=str(date_to),
        rows=rows,
        grand_total=grand,
    )


# ── Daily multi-utility trend ─────────────────────────────────────────────────

async def get_daily_trend(
    db: AsyncSession,
    *,
    date_from: date,
    date_to: date,
) -> List[DailyTrendPoint]:
    rows_raw = list((await db.execute(
        select(
            UtilityTransaction.transaction_date.label("day"),
            UtilityTransaction.utility_type.label("utype"),
            func.sum(UtilityTransaction.quantity).label("qty"),
            func.sum(UtilityTransaction.total_cost).label("cost"),
            func.sum(cast(UtilityTransaction.is_estimated, Integer)).label("est"),
        )
        .where(_dt_clause(UtilityTransaction.transaction_date, date_from, date_to))
        .group_by(UtilityTransaction.transaction_date, UtilityTransaction.utility_type)
        .order_by(UtilityTransaction.transaction_date)
    )).all())

    # Pivot into date-keyed dict
    by_date: dict = {}
    for r in rows_raw:
        d = str(r.day)
        if d not in by_date:
            by_date[d] = DailyTrendPoint(date=d)
        utype = r.utype.value if hasattr(r.utype, "value") else str(r.utype)
        qty = _D(r.qty)
        cost = _D(r.cost)
        pt = by_date[d]
        if utype == "ELECTRICITY":
            pt.electricity_kwh = (pt.electricity_kwh or Decimal("0")) + qty
        elif utype in ("WATER", "PROCESS_WATER"):
            pt.water_m3 = (pt.water_m3 or Decimal("0")) + qty
        elif utype == "NATURAL_GAS":
            pt.gas_nm3 = (pt.gas_nm3 or Decimal("0")) + qty
        elif utype == "STEAM":
            pt.steam_ton = (pt.steam_ton or Decimal("0")) + qty
        elif utype == "COMPRESSED_AIR":
            pt.compressed_air_nm3 = (pt.compressed_air_nm3 or Decimal("0")) + qty
        pt.total_cost = (pt.total_cost or Decimal("0")) + cost
        if r.est:
            pt.is_estimated = True

    # Merge solar into daily trend
    solar_rows = list((await db.execute(
        select(
            func.date(SolarRecord.record_datetime).label("day"),
            func.sum(SolarRecord.energy_generated_kwh).label("kwh"),
        )
        .where(_dtime_date_clause(SolarRecord.record_datetime, date_from, date_to))
        .group_by(func.date(SolarRecord.record_datetime))
    )).all())
    for r in solar_rows:
        d = str(r.day)
        if d not in by_date:
            by_date[d] = DailyTrendPoint(date=d)
        by_date[d].solar_kwh = _DN(r.kwh)

    return sorted(by_date.values(), key=lambda x: x.date)


# ── Per-utility sub-dashboard KPIs ────────────────────────────────────────────

async def get_electricity_kpis(
    db: AsyncSession, *, date_from: date, date_to: date,
) -> ElectricityDashboardKPIs:
    agg = (await db.execute(
        select(
            func.sum(UtilityTransaction.quantity).label("kwh"),
            func.sum(UtilityTransaction.total_cost).label("cost"),
            func.sum(cast(UtilityTransaction.is_estimated, Integer)).label("est"),
            func.count().label("cnt"),
            func.sum(cast(UtilityTransaction.is_anomaly, Integer)).label("anom"),
        )
        .where(and_(
            UtilityTransaction.utility_type == UtilityType.ELECTRICITY,
            _dt_clause(UtilityTransaction.transaction_date, date_from, date_to),
        ))
    )).one()

    solar_kwh = (await db.execute(
        select(func.sum(SolarRecord.energy_generated_kwh))
        .where(_dtime_date_clause(SolarRecord.record_datetime, date_from, date_to))
    )).scalar()

    kwh = _D(agg.kwh)
    total_elec = kwh + _D(solar_kwh)
    solar_contrib = _R(_D(solar_kwh) / total_elec * 100, 1) if solar_kwh and float(total_elec) > 0 else None
    est_pct = _R(_D(agg.est) / _D(agg.cnt) * 100, 1) if agg.cnt else None

    return ElectricityDashboardKPIs(
        date_from=str(date_from), date_to=str(date_to),
        kwh_total=_R(kwh, 1),
        solar_offset_kwh=_DN(solar_kwh),
        solar_contribution_pct=solar_contrib,
        total_cost=_DN(agg.cost),
        cost_per_kwh=_safe_div(agg.cost, agg.kwh),
        estimated_pct=est_pct,
        anomaly_count=int(agg.anom or 0),
    )


async def get_water_kpis(
    db: AsyncSession, *, date_from: date, date_to: date,
) -> WaterDashboardKPIs:
    agg = (await db.execute(
        select(
            UtilityTransaction.utility_type.label("utype"),
            func.sum(UtilityTransaction.quantity).label("qty"),
            func.sum(UtilityTransaction.total_cost).label("cost"),
            func.sum(cast(UtilityTransaction.is_estimated, Integer)).label("est"),
            func.count().label("cnt"),
            func.sum(cast(UtilityTransaction.is_anomaly, Integer)).label("anom"),
        )
        .where(and_(
            UtilityTransaction.utility_type.in_([UtilityType.WATER, UtilityType.PROCESS_WATER]),
            _dt_clause(UtilityTransaction.transaction_date, date_from, date_to),
        ))
        .group_by(UtilityTransaction.utility_type)
    )).all()

    water_m3 = sum(_D(r.qty) for r in agg if r.utype == UtilityType.WATER)
    proc_m3  = sum(_D(r.qty) for r in agg if r.utype == UtilityType.PROCESS_WATER)
    total_m3 = water_m3 + proc_m3
    total_cost = sum(_D(r.cost) for r in agg if r.cost)
    total_cnt  = sum(int(r.cnt or 0) for r in agg)
    est_cnt    = sum(int(r.est or 0) for r in agg)
    anom_cnt   = sum(int(r.anom or 0) for r in agg)

    return WaterDashboardKPIs(
        date_from=str(date_from), date_to=str(date_to),
        water_m3_total=_R(total_m3, 2),
        process_water_m3=_R(proc_m3, 2) if proc_m3 else None,
        total_cost=_R(total_cost, 2) if total_cost else None,
        cost_per_m3=_safe_div(total_cost, total_m3) if total_m3 else None,
        estimated_pct=_R(_D(est_cnt) / _D(total_cnt) * 100, 1) if total_cnt else None,
        anomaly_count=anom_cnt,
    )


async def get_boiler_kpis(
    db: AsyncSession, *, date_from: date, date_to: date,
) -> BoilerDashboardKPIs:
    agg = (await db.execute(
        select(
            func.sum(BoilerSteamRecord.steam_generated_kg).label("steam_kg"),
            func.sum(BoilerSteamRecord.fuel_consumption).label("fuel"),
            func.max(BoilerSteamRecord.fuel_unit).label("fuel_unit"),
            func.avg(BoilerSteamRecord.boiler_efficiency_pct).label("eff"),
            func.sum(BoilerSteamRecord.condensate_returned_m3).label("condensate"),
            func.sum(BoilerSteamRecord.feedwater_consumed_m3).label("feedwater"),
            func.sum(BoilerSteamRecord.blowdown_volume_litres).label("blowdown_l"),
            func.sum(BoilerSteamRecord.burner_runtime_hours).label("runtime"),
            func.avg(BoilerSteamRecord.boiler_load_pct).label("load"),
            func.sum(cast(BoilerSteamRecord.is_anomaly, Integer)).label("anom"),
        )
        .where(_dtime_date_clause(BoilerSteamRecord.record_datetime, date_from, date_to))
    )).one()

    steam_ton = _R(_D(agg.steam_kg) / 1000, 3) if agg.steam_kg else None
    g_per_t   = _safe_div(agg.fuel, _D(agg.steam_kg) / 1000) if agg.fuel and agg.steam_kg else None
    cond_pct  = (
        _R(_D(agg.condensate) / (_D(agg.steam_kg) / 1000) * 100, 1)
        if agg.condensate and agg.steam_kg else None
    )
    blow_pct  = (
        _R(_D(agg.blowdown_l) / 1000 / _D(agg.feedwater) * 100, 1)
        if agg.blowdown_l and agg.feedwater else None
    )

    return BoilerDashboardKPIs(
        date_from=str(date_from), date_to=str(date_to),
        steam_ton_total=steam_ton,
        fuel_consumed_total=_DN(agg.fuel),
        fuel_unit=agg.fuel_unit,
        gas_per_ton_steam=_R(g_per_t, 3),
        boiler_efficiency_pct=_R(agg.eff, 1),
        condensate_recovery_pct=cond_pct,
        blowdown_loss_pct=blow_pct,
        feedwater_m3_total=_DN(agg.feedwater),
        burner_runtime_hours=_DN(agg.runtime),
        avg_boiler_load_pct=_R(agg.load, 1),
        anomaly_count=int(agg.anom or 0),
    )


async def get_compressor_kpis(
    db: AsyncSession, *, date_from: date, date_to: date,
) -> CompressorDashboardKPIs:
    agg = (await db.execute(
        select(
            func.sum(CompressorRecord.air_generated_nm3).label("air"),
            func.sum(CompressorRecord.electricity_used_kwh).label("elec"),
            func.avg(CompressorRecord.specific_energy_kwh_m3).label("spec"),
            func.avg(CompressorRecord.leak_estimation_pct).label("leak"),
            func.avg(CompressorRecord.load_pct).label("load"),
            func.sum(CompressorRecord.night_idle_kwh).label("night"),
            func.sum(CompressorRecord.runtime_hours).label("runtime"),
            func.sum(cast(CompressorRecord.is_anomaly, Integer)).label("anom"),
        )
        .where(_dtime_date_clause(CompressorRecord.record_datetime, date_from, date_to))
    )).one()

    kwh_per_nm3 = _safe_div(agg.elec, agg.air) if agg.elec and agg.air else _DN(agg.spec)

    return CompressorDashboardKPIs(
        date_from=str(date_from), date_to=str(date_to),
        air_nm3_total=_DN(agg.air),
        electricity_kwh_total=_DN(agg.elec),
        air_kwh_per_nm3=_R(kwh_per_nm3, 4),
        leak_estimate_pct=_R(agg.leak, 1),
        night_idle_kwh=_DN(agg.night),
        avg_load_pct=_R(agg.load, 1),
        runtime_hours=_DN(agg.runtime),
        anomaly_count=int(agg.anom or 0),
    )


async def get_soft_water_kpis(
    db: AsyncSession, *, date_from: date, date_to: date,
) -> SoftWaterDashboardKPIs:
    agg = (await db.execute(
        select(
            func.sum(SoftWaterRecord.volume_treated_m3).label("sw"),
            func.sum(SoftWaterRecord.raw_water_input_m3).label("raw"),
            func.sum(SoftWaterRecord.salt_consumed_kg).label("salt"),
            func.avg(SoftWaterRecord.efficiency_pct).label("eff"),
            func.avg(SoftWaterRecord.product_water_hardness_ppm).label("hardness"),
            func.sum(SoftWaterRecord.regeneration_count).label("regen"),
            func.sum(cast(SoftWaterRecord.is_anomaly, Integer)).label("anom"),
        )
        .where(_dtime_date_clause(SoftWaterRecord.record_datetime, date_from, date_to))
    )).one()

    eff = (
        _R(_D(agg.sw) / _D(agg.raw) * 100, 1)
        if agg.sw and agg.raw else _DN(agg.eff)
    )
    salt_per = _safe_div(agg.salt, agg.sw) if agg.salt and agg.sw else None

    return SoftWaterDashboardKPIs(
        date_from=str(date_from), date_to=str(date_to),
        sw_volume_m3=_DN(agg.sw),
        raw_input_m3=_DN(agg.raw),
        conversion_efficiency_pct=eff,
        salt_consumed_kg=_DN(agg.salt),
        salt_per_m3=_R(salt_per, 3),
        avg_product_hardness=_R(agg.hardness, 2),
        regen_count=int(agg.regen or 0),
        anomaly_count=int(agg.anom or 0),
    )


async def get_solar_kpis(
    db: AsyncSession, *, date_from: date, date_to: date,
) -> SolarDashboardKPIs:
    agg = (await db.execute(
        select(
            func.sum(SolarRecord.energy_generated_kwh).label("kwh"),
            func.sum(SolarRecord.self_consumption_kwh).label("self"),
            func.sum(SolarRecord.grid_export_kwh).label("export"),
            func.avg(SolarRecord.pr_ratio).label("pr"),
            func.avg(SolarRecord.capacity_factor_pct).label("cf"),
            func.avg(SolarRecord.inverter_efficiency_pct).label("inv_eff"),
            func.sum(cast(SolarRecord.is_anomaly, Integer)).label("anom"),
        )
        .where(_dtime_date_clause(SolarRecord.record_datetime, date_from, date_to))
    )).one()

    # Solar contribution vs total electricity grid usage
    total_elec = (await db.execute(
        select(func.sum(UtilityTransaction.quantity))
        .where(and_(
            UtilityTransaction.utility_type == UtilityType.ELECTRICITY,
            _dt_clause(UtilityTransaction.transaction_date, date_from, date_to),
        ))
    )).scalar()

    contrib_pct = None
    if agg.kwh and total_elec:
        total_e = _D(agg.kwh) + _D(total_elec)
        contrib_pct = _R(_D(agg.kwh) / total_e * 100, 1) if float(total_e) > 0 else None

    return SolarDashboardKPIs(
        date_from=str(date_from), date_to=str(date_to),
        kwh_generated=_DN(agg.kwh),
        kwh_self_consumed=_DN(agg.self),
        kwh_exported=_DN(agg.export),
        solar_contribution_pct=contrib_pct,
        avg_pr_ratio=_R(agg.pr, 3),
        avg_capacity_factor=_R(agg.cf, 1),
        avg_inverter_efficiency=_R(agg.inv_eff, 1),
        anomaly_count=int(agg.anom or 0),
    )


async def get_chemical_kpis(
    db: AsyncSession, *, date_from: date, date_to: date,
) -> ChemicalDashboardKPIs:
    from app.models.utility_management import ChemicalCategory

    agg = (await db.execute(
        select(
            func.sum(TreatmentChemicalRecord.consumed_qty * TreatmentChemicalRecord.unit_cost).label("cost"),
            func.sum(TreatmentChemicalRecord.consumed_qty).label("qty"),
            func.count(distinct(TreatmentChemicalRecord.chemical_id)).label("chems"),
        )
        .where(and_(
            TreatmentChemicalRecord.date >= date_from,
            TreatmentChemicalRecord.date <= date_to,
        ))
    )).one()

    days = max((date_to - date_from).days + 1, 1)

    return ChemicalDashboardKPIs(
        date_from=str(date_from), date_to=str(date_to),
        total_cost=_R(agg.cost, 2),
        total_consumed_kg=_R(agg.qty, 2),
        cost_per_day=_R(_D(agg.cost) / days, 2) if agg.cost else None,
        distinct_chemicals=int(agg.chems or 0),
    )


async def get_wastewater_kpis(
    db: AsyncSession, *, date_from: date, date_to: date,
) -> WastewaterDashboardKPIs:
    agg = (await db.execute(
        select(
            func.avg(WastewaterRecord.influent_cod_mgl).label("in_cod"),
            func.avg(WastewaterRecord.effluent_cod_mgl).label("out_cod"),
            func.avg(WastewaterRecord.influent_bod_mgl).label("in_bod"),
            func.avg(WastewaterRecord.effluent_bod_mgl).label("out_bod"),
            func.avg(WastewaterRecord.do_mgl).label("do"),
            func.avg(WastewaterRecord.effluent_ph).label("ph"),
            func.sum(WastewaterRecord.sludge_produced_kg).label("sludge"),
            func.sum(WastewaterRecord.power_consumed_kwh).label("power"),
            func.avg(WastewaterRecord.effluent_flow_m3h).label("flow"),
            func.count().label("cnt"),
            func.sum(
                cast(WastewaterRecord.compliance_status == ComplianceStatus.NON_COMPLIANT, Integer)
            ).label("non_comp"),
            func.sum(
                cast(WastewaterRecord.compliance_status == ComplianceStatus.COMPLIANT, Integer)
            ).label("comp"),
            func.sum(cast(WastewaterRecord.is_anomaly, Integer)).label("anom"),
        )
        .where(_dtime_date_clause(WastewaterRecord.record_datetime, date_from, date_to))
    )).one()

    cod_rem = (
        _R((1 - _D(agg.out_cod) / _D(agg.in_cod)) * 100, 1)
        if agg.in_cod and agg.out_cod and float(agg.in_cod) > 0 else None
    )
    bod_rem = (
        _R((1 - _D(agg.out_bod) / _D(agg.in_bod)) * 100, 1)
        if agg.in_bod and agg.out_bod and float(agg.in_bod) > 0 else None
    )
    power_per_m3 = (
        _safe_div(agg.power, _D(agg.flow) * 24 * ((date_to - date_from).days + 1))
        if agg.power and agg.flow else None
    )
    total_cnt   = int(agg.cnt or 0)
    comp_cnt    = int(agg.comp or 0)
    non_comp    = int(agg.non_comp or 0)
    comp_pct    = _R(_D(comp_cnt) / _D(total_cnt) * 100, 1) if total_cnt > 0 else None

    return WastewaterDashboardKPIs(
        date_from=str(date_from), date_to=str(date_to),
        cod_removal_pct=cod_rem,
        bod_removal_pct=bod_rem,
        avg_do_mgl=_R(agg.do, 2),
        avg_effluent_ph=_R(agg.ph, 2),
        sludge_kg_total=_DN(agg.sludge),
        power_kwh_total=_DN(agg.power),
        power_per_m3=_R(power_per_m3, 4),
        compliant_pct=comp_pct,
        non_compliant_count=non_comp,
        anomaly_count=int(agg.anom or 0),
    )


async def get_machine_kpis(
    db: AsyncSession, *, date_from: date, date_to: date,
) -> MachineDashboardKPIs:
    # Reuse existing machine utility service logic
    from app.services.machine_utility_service import get_machine_utility_kpis
    kpis = await get_machine_utility_kpis(db, date_from=date_from, date_to=date_to)
    return MachineDashboardKPIs(
        date_from=str(date_from), date_to=str(date_to),
        total_consumption=kpis.total_consumption,
        consumption_unit=kpis.consumption_unit,
        electricity_per_runtime_h=kpis.electricity_per_runtime_h,
        water_per_batch=kpis.water_per_batch,
        air_per_batch=kpis.air_per_batch,
        standby_pct=kpis.standby_pct,
        cost_per_batch=kpis.cost_per_batch,
        avg_variance_pct=kpis.avg_variance_pct,
        anomaly_count=kpis.anomaly_count,
        flag_high_variance=kpis.flag_high_variance,
        flag_standby_waste=kpis.flag_standby_waste,
    )


async def get_utility_cost_kpis(
    db: AsyncSession, *, date_from: date, date_to: date,
) -> UtilityCostDashboardKPIs:
    # Cost from transactions (actual spend)
    tx_agg = list((await db.execute(
        select(
            UtilityTransaction.utility_type.label("utype"),
            func.sum(UtilityTransaction.total_cost).label("cost"),
        )
        .where(_dt_clause(UtilityTransaction.transaction_date, date_from, date_to))
        .group_by(UtilityTransaction.utility_type)
    )).all())

    def _by_type(t: str) -> Decimal:
        for r in tx_agg:
            k = r.utype.value if hasattr(r.utype, "value") else str(r.utype)
            if k == t:
                return _D(r.cost)
        return Decimal("0")

    total_cost = sum(_D(r.cost) for r in tx_agg if r.cost)

    # Bill stats
    bill_agg = (await db.execute(
        select(
            func.count().label("cnt"),
            func.sum(UtilityBill.total_amount).filter(
                UtilityBill.status.in_([BillStatus.RECEIVED, BillStatus.OVERDUE])
            ).label("unpaid"),
        )
        .where(and_(
            UtilityBill.billing_period_from >= date_from,
            UtilityBill.billing_period_to <= date_to,
        ))
    )).one()

    # Cost per ton/batch from allocations
    alloc = (await db.execute(
        select(
            func.sum(UtilityCostAllocation.allocated_cost).label("cost"),
            func.sum(UtilityCostAllocation.production_volume_kg).label("kg"),
            func.count(distinct(UtilityCostAllocation.batch_no)).label("batches"),
        )
        .where(and_(
            UtilityCostAllocation.allocation_date >= date_from,
            UtilityCostAllocation.allocation_date <= date_to,
        ))
    )).one()

    prod_tons   = _D(alloc.kg) / 1000 if alloc.kg else None
    batch_cnt   = int(alloc.batches or 0)
    alloc_cost  = _D(alloc.cost) if alloc.cost else total_cost
    cost_per_ton   = _safe_div(alloc_cost, prod_tons) if prod_tons else None
    cost_per_batch = _R(alloc_cost / batch_cnt, 4) if alloc_cost and batch_cnt > 0 else None

    return UtilityCostDashboardKPIs(
        date_from=str(date_from), date_to=str(date_to),
        total_cost=_R(total_cost, 2),
        electricity_cost=_R(_by_type("ELECTRICITY"), 2),
        water_cost=_R(_by_type("WATER") + _by_type("PROCESS_WATER"), 2),
        gas_cost=_R(_by_type("NATURAL_GAS"), 2),
        steam_cost=_R(_by_type("STEAM"), 2),
        other_cost=_R(
            sum(_D(r.cost) for r in tx_agg
                if r.utype not in (UtilityType.ELECTRICITY, UtilityType.WATER,
                                   UtilityType.PROCESS_WATER, UtilityType.NATURAL_GAS,
                                   UtilityType.STEAM) and r.cost), 2
        ),
        cost_per_ton=_R(cost_per_ton, 4),
        cost_per_batch=cost_per_batch,
        total_bills=int(bill_agg.cnt or 0),
        unpaid_amount=_DN(bill_agg.unpaid),
    )
