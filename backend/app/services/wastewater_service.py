"""
Biological / Wastewater Treatment Service
──────────────────────────────────────────
Aggregation queries over wastewater_records for KPI reporting, trend charts,
stage analysis, compliance summary, and alarm evaluation.

KPI thresholds (default values; should become configurable per asset):
  EFFLUENT_PH_LOW      = 6.0
  EFFLUENT_PH_HIGH     = 9.0
  COD_LIMIT_MGL        = 150.0    (effluent COD)
  DO_LOW_MGL           = 1.5      (dissolved oxygen)
  OVERFLOW_FLOW_M3H    = 500.0    (influent flow alarm threshold)
  NON_COMPLIANCE_RISK_WINDOW = 7  (days — if any NC in last N days → risk flag)
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import Integer, cast, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.utility_management import (
    ComplianceStatus,
    WastewaterProcess,
    WastewaterRecord,
)
from app.schemas.wastewater import (
    WastewaterAlarm,
    WastewaterComplianceSummary,
    WastewaterKPIs,
    WastewaterStagePoint,
    WastewaterTrendPoint,
)

logger = logging.getLogger(__name__)

# ── Alarm thresholds ──────────────────────────────────────────────────────────
EFFLUENT_PH_LOW            = Decimal("6.0")
EFFLUENT_PH_HIGH           = Decimal("9.0")
COD_LIMIT_MGL              = Decimal("150.0")
DO_LOW_MGL                 = Decimal("1.5")
OVERFLOW_FLOW_M3H          = Decimal("500.0")
NON_COMPLIANCE_RISK_DAYS   = 7


# ── Helpers ───────────────────────────────────────────────────────────────────

def _d(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _d_opt(v) -> Optional[Decimal]:
    return Decimal(str(v)) if v is not None else None


def _rnd(v, dp: int = 2) -> Optional[Decimal]:
    return Decimal(str(round(float(v), dp))) if v is not None else None


def _clauses(
    *,
    asset_id:          Optional[UUID],
    date_from:         Optional[date],
    date_to:           Optional[date],
    process_stage:     Optional[str]  = None,
    compliance_status: Optional[str]  = None,
    shift_ref:         Optional[str]  = None,
) -> list:
    c = []
    if asset_id:
        c.append(WastewaterRecord.asset_id == asset_id)
    if shift_ref:
        c.append(WastewaterRecord.shift_ref == shift_ref)
    if date_from:
        c.append(WastewaterRecord.record_datetime >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        c.append(WastewaterRecord.record_datetime <= datetime.combine(date_to, datetime.max.time()))
    if process_stage:
        try:
            c.append(WastewaterRecord.process_stage == WastewaterProcess(process_stage))
        except ValueError:
            pass
    if compliance_status:
        try:
            c.append(WastewaterRecord.compliance_status == ComplianceStatus(compliance_status))
        except ValueError:
            pass
    return c


def _removal_pct(influent: Optional[Decimal], effluent: Optional[Decimal]) -> Optional[Decimal]:
    """Compute (influent − effluent) / influent × 100, guarded against None/zero."""
    if influent is None or effluent is None or influent == 0:
        return None
    removal = (influent - effluent) / influent * 100
    return _rnd(removal, 1)


# ── Public API ────────────────────────────────────────────────────────────────

async def get_wastewater_kpis(
    db: AsyncSession,
    *,
    asset_id:          Optional[UUID]    = None,
    date_from:         Optional[date]    = None,
    date_to:           Optional[date]    = None,
    process_stage:     Optional[str]     = None,
    shift_ref:         Optional[str]     = None,
    treatment_cost_total: Optional[Decimal] = None,
) -> WastewaterKPIs:
    clauses = _clauses(
        asset_id=asset_id, date_from=date_from, date_to=date_to,
        process_stage=process_stage, shift_ref=shift_ref,
    )
    where = and_(*clauses) if clauses else True

    agg = (await db.execute(
        select(
            func.sum(WastewaterRecord.influent_flow_m3h).label("inf_flow"),
            func.sum(WastewaterRecord.effluent_flow_m3h).label("eff_flow"),
            func.avg(WastewaterRecord.influent_flow_m3h).label("avg_inf_flow"),
            func.avg(WastewaterRecord.effluent_flow_m3h).label("avg_eff_flow"),

            func.avg(WastewaterRecord.influent_cod_mgl).label("avg_inf_cod"),
            func.avg(WastewaterRecord.effluent_cod_mgl).label("avg_eff_cod"),
            func.avg(WastewaterRecord.influent_bod_mgl).label("avg_inf_bod"),
            func.avg(WastewaterRecord.effluent_bod_mgl).label("avg_eff_bod"),
            func.avg(WastewaterRecord.influent_tss_mgl).label("avg_inf_tss"),
            func.avg(WastewaterRecord.effluent_tss_mgl).label("avg_eff_tss"),

            func.avg(WastewaterRecord.influent_ph).label("avg_inf_ph"),
            func.avg(WastewaterRecord.effluent_ph).label("avg_eff_ph"),

            func.avg(WastewaterRecord.do_mgl).label("avg_do"),
            func.avg(WastewaterRecord.mlss_mgl).label("avg_mlss"),
            func.avg(WastewaterRecord.svi).label("avg_svi"),

            func.avg(WastewaterRecord.conductivity_us_cm).label("avg_conductivity"),
            func.avg(WastewaterRecord.temperature_c).label("avg_temp"),

            func.sum(WastewaterRecord.power_consumed_kwh).label("total_power"),
            func.sum(WastewaterRecord.aeration_runtime_hours).label("total_aeration"),
            func.sum(WastewaterRecord.blower_power_kw).label("total_blower_power"),

            func.sum(WastewaterRecord.nutrient_dose_kg).label("total_nutrient"),
            func.sum(WastewaterRecord.antifoam_dose_kg).label("total_antifoam"),

            func.sum(WastewaterRecord.sludge_produced_kg).label("total_sludge_kg"),
            func.sum(WastewaterRecord.sludge_volume_m3).label("total_sludge_m3"),
            func.sum(WastewaterRecord.sludge_disposal_qty_kg).label("total_disposal"),

            func.sum(cast(
                WastewaterRecord.compliance_status == ComplianceStatus.COMPLIANT, Integer
            )).label("compliant_cnt"),
            func.sum(cast(
                WastewaterRecord.compliance_status == ComplianceStatus.NON_COMPLIANT, Integer
            )).label("non_compliant_cnt"),
            func.sum(cast(
                WastewaterRecord.compliance_status == ComplianceStatus.BORDERLINE, Integer
            )).label("borderline_cnt"),

            func.count().label("cnt"),
            func.sum(cast(WastewaterRecord.is_anomaly, Integer)).label("anomaly_cnt"),

            # Alarm helpers
            func.min(WastewaterRecord.effluent_ph).label("min_eff_ph"),
            func.max(WastewaterRecord.effluent_ph).label("max_eff_ph"),
            func.max(WastewaterRecord.influent_flow_m3h).label("max_inf_flow"),
            func.sum(cast(
                WastewaterRecord.aeration_runtime_hours == 0, Integer
            )).label("zero_aeration_cnt"),
        ).where(where)
    )).one()

    total_inf = _d(agg.inf_flow)
    total_eff = _d(agg.eff_flow)
    avg_inf_cod = _d_opt(agg.avg_inf_cod)
    avg_eff_cod = _d_opt(agg.avg_eff_cod)
    avg_inf_bod = _d_opt(agg.avg_inf_bod)
    avg_eff_bod = _d_opt(agg.avg_eff_bod)
    avg_do      = _d_opt(agg.avg_do)
    avg_eff_ph  = _d_opt(agg.avg_eff_ph)
    total_power = _d(agg.total_power)
    total_blower = _d_opt(agg.total_blower_power)
    total_sludge_kg = _d(agg.total_sludge_kg)
    record_count    = int(agg.cnt or 0)
    compliant_cnt   = int(agg.compliant_cnt or 0)
    non_compliant_cnt = int(agg.non_compliant_cnt or 0)
    borderline_cnt  = int(agg.borderline_cnt or 0)

    # KPI 1 — COD removal efficiency
    cod_removal = _removal_pct(avg_inf_cod, avg_eff_cod)

    # KPI 2 — BOD removal efficiency
    bod_removal = _removal_pct(avg_inf_bod, avg_eff_bod)

    # KPI 3 — compliance %
    compliance_pct = None
    if record_count > 0:
        compliance_pct = _rnd(Decimal(str(compliant_cnt)) / Decimal(str(record_count)) * 100, 1)

    # KPI 5 — blower energy per m³
    blower_energy_per_m3 = None
    if total_blower and total_eff > 0:
        blower_energy_per_m3 = _rnd(total_blower / total_eff, 4)

    # KPI 7 — sludge generation rate (kg / m³ influent)
    sludge_gen_rate = None
    if total_sludge_kg > 0 and total_inf > 0:
        sludge_gen_rate = _rnd(total_sludge_kg / total_inf, 3)

    # KPI 4 — treatment cost per m³
    treatment_cost_per_m3 = None
    if treatment_cost_total and total_eff > 0:
        treatment_cost_per_m3 = _rnd(treatment_cost_total / total_eff, 4)

    # KPI 8 — non-compliance risk (any NC in configured look-back window)
    risk_window_from = (datetime.utcnow() - timedelta(days=NON_COMPLIANCE_RISK_DAYS)).date()
    risk_clauses = [WastewaterRecord.compliance_status == ComplianceStatus.NON_COMPLIANT]
    if asset_id:
        risk_clauses.append(WastewaterRecord.asset_id == asset_id)
    risk_clauses.append(WastewaterRecord.record_datetime >= datetime.combine(risk_window_from, datetime.min.time()))
    risk_count = (await db.execute(
        select(func.count()).where(and_(*risk_clauses))
    )).scalar_one_or_none() or 0
    non_compliance_risk = int(risk_count) > 0

    # ── Alarm flags ───────────────────────────────────────────────────────────
    alarm_ph = False
    if agg.min_eff_ph is not None and agg.max_eff_ph is not None:
        alarm_ph = (
            _d(agg.min_eff_ph) < EFFLUENT_PH_LOW
            or _d(agg.max_eff_ph) > EFFLUENT_PH_HIGH
        )
    alarm_cod = bool(avg_eff_cod is not None and avg_eff_cod > COD_LIMIT_MGL)
    alarm_do  = bool(avg_do is not None and avg_do < DO_LOW_MGL)
    alarm_blower = bool((agg.zero_aeration_cnt or 0) > 0)
    alarm_overflow = bool(
        agg.max_inf_flow is not None and _d(agg.max_inf_flow) > OVERFLOW_FLOW_M3H
    )
    alarm_nc_discharge = non_compliant_cnt > 0

    return WastewaterKPIs(
        date_from=date_from,
        date_to=date_to,

        total_influent_m3=total_inf,
        total_effluent_m3=total_eff,
        avg_influent_flow_m3h=_rnd(agg.avg_inf_flow, 2),
        avg_effluent_flow_m3h=_rnd(agg.avg_eff_flow, 2),

        avg_influent_cod=_rnd(agg.avg_inf_cod, 2),
        avg_effluent_cod=_rnd(agg.avg_eff_cod, 2),
        avg_influent_bod=_rnd(agg.avg_inf_bod, 2),
        avg_effluent_bod=_rnd(agg.avg_eff_bod, 2),
        avg_influent_tss=_rnd(agg.avg_inf_tss, 2),
        avg_effluent_tss=_rnd(agg.avg_eff_tss, 2),

        cod_removal_pct=cod_removal,
        bod_removal_pct=bod_removal,

        avg_influent_ph=_rnd(agg.avg_inf_ph, 2),
        avg_effluent_ph=_rnd(agg.avg_eff_ph, 2),

        avg_do_mgl=_rnd(agg.avg_do, 2),
        avg_mlss_mgl=_rnd(agg.avg_mlss, 2),
        avg_svi=_rnd(agg.avg_svi, 2),

        avg_conductivity_us_cm=_rnd(agg.avg_conductivity, 2),
        avg_temperature_c=_rnd(agg.avg_temp, 1),

        total_power_kwh=total_power,
        total_aeration_hours=_d_opt(agg.total_aeration),
        total_blower_power_kwh=total_blower,
        blower_energy_per_m3=blower_energy_per_m3,

        total_nutrient_dose_kg=_d_opt(agg.total_nutrient),
        total_antifoam_dose_kg=_d_opt(agg.total_antifoam),

        total_sludge_produced_kg=total_sludge_kg,
        total_sludge_volume_m3=_d_opt(agg.total_sludge_m3),
        total_sludge_disposal_kg=_d_opt(agg.total_disposal),
        sludge_gen_rate=sludge_gen_rate,

        compliance_pct=compliance_pct,
        compliant_count=compliant_cnt,
        non_compliant_count=non_compliant_cnt,
        borderline_count=borderline_cnt,

        treatment_cost_total=treatment_cost_total,
        treatment_cost_per_m3=treatment_cost_per_m3,

        record_count=record_count,
        anomaly_count=int(agg.anomaly_cnt or 0),
        non_compliance_risk=non_compliance_risk,

        alarm_ph_out_of_range=alarm_ph,
        alarm_cod_high=alarm_cod,
        alarm_low_do=alarm_do,
        alarm_blower_failure=alarm_blower,
        alarm_overflow_risk=alarm_overflow,
        alarm_non_compliant_discharge=alarm_nc_discharge,
    )


async def get_wastewater_daily_trend(
    db: AsyncSession,
    *,
    asset_id:      Optional[UUID] = None,
    date_from:     Optional[date] = None,
    date_to:       Optional[date] = None,
    process_stage: Optional[str]  = None,
) -> List[WastewaterTrendPoint]:
    clauses = _clauses(asset_id=asset_id, date_from=date_from, date_to=date_to,
                       process_stage=process_stage)
    where = and_(*clauses) if clauses else True

    rows = list((await db.execute(
        select(
            func.date(WastewaterRecord.record_datetime).label("day"),
            func.avg(WastewaterRecord.influent_flow_m3h).label("inf_flow"),
            func.avg(WastewaterRecord.effluent_flow_m3h).label("eff_flow"),
            func.avg(WastewaterRecord.influent_cod_mgl).label("avg_inf_cod"),
            func.avg(WastewaterRecord.effluent_cod_mgl).label("avg_eff_cod"),
            func.avg(WastewaterRecord.influent_bod_mgl).label("avg_inf_bod"),
            func.avg(WastewaterRecord.effluent_bod_mgl).label("avg_eff_bod"),
            func.avg(WastewaterRecord.do_mgl).label("avg_do"),
            func.avg(WastewaterRecord.effluent_ph).label("avg_eff_ph"),
            func.sum(WastewaterRecord.power_consumed_kwh).label("power_kwh"),
            func.sum(WastewaterRecord.sludge_produced_kg).label("sludge_kg"),
            func.sum(cast(
                WastewaterRecord.compliance_status == ComplianceStatus.NON_COMPLIANT, Integer
            )).label("nc_cnt"),
            func.count().label("cnt"),
        )
        .where(where)
        .group_by(func.date(WastewaterRecord.record_datetime))
        .order_by(func.date(WastewaterRecord.record_datetime))
    )).all())

    return [
        WastewaterTrendPoint(
            date=str(r.day),
            influent_flow_m3h=_d(r.inf_flow),
            effluent_flow_m3h=_d(r.eff_flow),
            avg_cod_influent=_rnd(r.avg_inf_cod, 2),
            avg_cod_effluent=_rnd(r.avg_eff_cod, 2),
            avg_bod_influent=_rnd(r.avg_inf_bod, 2),
            avg_bod_effluent=_rnd(r.avg_eff_bod, 2),
            avg_do=_rnd(r.avg_do, 2),
            avg_ph_effluent=_rnd(r.avg_eff_ph, 2),
            power_kwh=_d(r.power_kwh),
            sludge_kg=_d(r.sludge_kg),
            non_compliant_cnt=int(r.nc_cnt or 0),
            record_count=int(r.cnt or 0),
        )
        for r in rows
    ]


async def get_wastewater_stage_analysis(
    db: AsyncSession,
    *,
    asset_id:  Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to:   Optional[date] = None,
) -> List[WastewaterStagePoint]:
    clauses = _clauses(asset_id=asset_id, date_from=date_from, date_to=date_to)
    where = and_(*clauses) if clauses else True

    _STAGE_LABELS = {
        "PRIMARY":        "Primary",
        "SECONDARY":      "Secondary (Biological)",
        "TERTIARY":       "Tertiary / Polishing",
        "SLUDGE_HANDLING": "Sludge Handling",
    }

    rows = list((await db.execute(
        select(
            WastewaterRecord.process_stage.label("stage"),
            func.count().label("cnt"),
            func.avg(WastewaterRecord.do_mgl).label("avg_do"),
            func.sum(cast(
                WastewaterRecord.compliance_status == ComplianceStatus.NON_COMPLIANT, Integer
            )).label("nc_cnt"),
        )
        .where(where)
        .group_by(WastewaterRecord.process_stage)
        .order_by(WastewaterRecord.process_stage)
    )).all())

    result = []
    for r in rows:
        stage_val = r.stage.value if hasattr(r.stage, "value") else str(r.stage)
        result.append(WastewaterStagePoint(
            stage=stage_val,
            label=_STAGE_LABELS.get(stage_val, stage_val),
            record_count=int(r.cnt or 0),
            avg_do=_rnd(r.avg_do, 2),
            non_compliant_cnt=int(r.nc_cnt or 0),
        ))
    return result


async def get_wastewater_compliance_summary(
    db: AsyncSession,
    *,
    asset_id:  Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to:   Optional[date] = None,
) -> WastewaterComplianceSummary:
    clauses = _clauses(asset_id=asset_id, date_from=date_from, date_to=date_to)
    where = and_(*clauses) if clauses else True

    row = (await db.execute(
        select(
            func.count().label("total"),
            func.sum(cast(WastewaterRecord.compliance_status == ComplianceStatus.COMPLIANT, Integer)).label("c"),
            func.sum(cast(WastewaterRecord.compliance_status == ComplianceStatus.NON_COMPLIANT, Integer)).label("nc"),
            func.sum(cast(WastewaterRecord.compliance_status == ComplianceStatus.BORDERLINE, Integer)).label("b"),
            func.sum(cast(WastewaterRecord.compliance_status == ComplianceStatus.NOT_TESTED, Integer)).label("nt"),
        ).where(where)
    )).one()

    total = int(row.total or 0)
    c     = int(row.c  or 0)
    nc    = int(row.nc or 0)
    b     = int(row.b  or 0)
    nt    = int(row.nt or 0)

    pct = _rnd(Decimal(str(c)) / Decimal(str(total)) * 100, 1) if total > 0 else None

    label = "All"
    if date_from and date_to:
        label = f"{date_from} – {date_to}"
    elif date_from:
        label = f"From {date_from}"
    elif date_to:
        label = f"To {date_to}"

    return WastewaterComplianceSummary(
        period_label=label,
        total_records=total,
        compliant=c,
        non_compliant=nc,
        borderline=b,
        not_tested=nt,
        compliance_pct=pct,
    )


def evaluate_alarms(rec: WastewaterRecord) -> List[WastewaterAlarm]:
    """
    Evaluate a freshly created/updated WastewaterRecord against alarm thresholds.
    Returns a list of WastewaterAlarm objects for the caller to persist or dispatch.
    Caller is responsible for checking cooldown windows before saving.
    """
    alarms: List[WastewaterAlarm] = []
    now = datetime.utcnow()

    # pH out of range
    if rec.effluent_ph is not None:
        ph = Decimal(str(rec.effluent_ph))
        if ph < EFFLUENT_PH_LOW or ph > EFFLUENT_PH_HIGH:
            alarms.append(WastewaterAlarm(
                alarm_key="ph_out_of_range",
                severity="ALERT",
                message=f"Effluent pH {ph} is outside permitted range [{EFFLUENT_PH_LOW}–{EFFLUENT_PH_HIGH}].",
                triggered_value=ph,
                threshold_value=EFFLUENT_PH_HIGH if ph > EFFLUENT_PH_HIGH else EFFLUENT_PH_LOW,
                record_id=rec.id,
                triggered_at=now,
            ))

    # COD too high
    if rec.effluent_cod_mgl is not None:
        cod = Decimal(str(rec.effluent_cod_mgl))
        if cod > COD_LIMIT_MGL:
            alarms.append(WastewaterAlarm(
                alarm_key="cod_high",
                severity="CRITICAL",
                message=f"Effluent COD {cod} mg/L exceeds limit {COD_LIMIT_MGL} mg/L.",
                triggered_value=cod,
                threshold_value=COD_LIMIT_MGL,
                record_id=rec.id,
                triggered_at=now,
            ))

    # Low dissolved oxygen
    if rec.do_mgl is not None:
        do_val = Decimal(str(rec.do_mgl))
        if do_val < DO_LOW_MGL:
            alarms.append(WastewaterAlarm(
                alarm_key="low_do",
                severity="WARNING",
                message=f"Dissolved oxygen {do_val} mg/L is below minimum {DO_LOW_MGL} mg/L.",
                triggered_value=do_val,
                threshold_value=DO_LOW_MGL,
                record_id=rec.id,
                triggered_at=now,
            ))

    # Blower failure (zero runtime)
    if rec.aeration_runtime_hours is not None and Decimal(str(rec.aeration_runtime_hours)) == 0:
        alarms.append(WastewaterAlarm(
            alarm_key="blower_failure",
            severity="CRITICAL",
            message="Aeration blower runtime is zero — possible blower failure.",
            triggered_value=Decimal("0"),
            threshold_value=Decimal("0"),
            record_id=rec.id,
            triggered_at=now,
        ))

    # Overflow risk
    if rec.influent_flow_m3h is not None:
        flow = Decimal(str(rec.influent_flow_m3h))
        if flow > OVERFLOW_FLOW_M3H:
            alarms.append(WastewaterAlarm(
                alarm_key="overflow_risk",
                severity="ALERT",
                message=f"Influent flow {flow} m³/h exceeds overflow threshold {OVERFLOW_FLOW_M3H} m³/h.",
                triggered_value=flow,
                threshold_value=OVERFLOW_FLOW_M3H,
                record_id=rec.id,
                triggered_at=now,
            ))

    # Non-compliant discharge
    if rec.compliance_status == ComplianceStatus.NON_COMPLIANT:
        alarms.append(WastewaterAlarm(
            alarm_key="non_compliant_discharge",
            severity="CRITICAL",
            message="Effluent discharge is NON-COMPLIANT with permit limits.",
            record_id=rec.id,
            triggered_at=now,
        ))

    return alarms
