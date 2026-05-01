"""
Kenya Payroll Calculation Engine.
Implements PAYE (Finance Act 2023/2024), NHIF tiered contributions,
NSSF (Act 2013), and Affordable Housing Levy.
"""
from __future__ import annotations

from datetime import datetime, timezone, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List
import uuid
import json

from fastapi import HTTPException
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.payroll_ke import (
    EmployeePayrollProfile, KeTaxBand, KeStatutoryRate, KeNhifTier,
    PayrollRun, KePayrollLine, Payslip,
    PayFrequency, KeComponentType, PayrollRunStatus,
)
from app.models.hr import Employee
from app.schemas.payroll_ke import (
    PayrollRunCreate, PayrollInsight, SeedResult,
    PayeSummaryRow, NhifSummaryRow, NssfSummaryRow, PayrollSummaryRow,
)

D = Decimal
ZERO = D("0")
CENT = D("0.01")
PERSONAL_RELIEF_MONTHLY = D("2400")   # KES/month — Finance Act 2023


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _round(v: Decimal) -> Decimal:
    return v.quantize(CENT, rounding=ROUND_HALF_UP)


# ── Default Kenya Rate Seeds ──────────────────────────────────────────────────

KE_TAX_BANDS_2024 = [
    (D("0"),      D("24000"),  D("0.10"), "First 24,000"),
    (D("24001"),  D("32333"),  D("0.25"), "Next 8,333"),
    (D("32334"),  D("500000"), D("0.30"), "Next 467,667"),
    (D("500001"), D("800000"), D("0.325"),"Next 300,000"),
    (D("800001"), None,         D("0.35"), "Above 800,000"),
]

KE_NHIF_TIERS_2023 = [
    (D("0"),      D("5999"),  D("150")),
    (D("6000"),   D("7999"),  D("300")),
    (D("8000"),   D("11999"), D("400")),
    (D("12000"),  D("14999"), D("500")),
    (D("15000"),  D("19999"), D("600")),
    (D("20000"),  D("24999"), D("750")),
    (D("25000"),  D("29999"), D("900")),
    (D("30000"),  D("34999"), D("950")),
    (D("35000"),  D("39999"), D("1000")),
    (D("40000"),  D("44999"), D("1100")),
    (D("45000"),  D("49999"), D("1200")),
    (D("50000"),  D("59999"), D("1300")),
    (D("60000"),  D("69999"), D("1400")),
    (D("70000"),  D("79999"), D("1500")),
    (D("80000"),  D("89999"), D("1600")),
    (D("90000"),  D("99999"), D("1700")),
    (D("100000"), None,        D("1700")),
]

KE_STATUTORY_RATES_2024 = [
    # NSSF: 6% of gross, max Tier I (7000 LEL → 420) + Tier II (36000 UEL → 1,740)
    # Simplified: employee contributes 6% up to 36,000 gross
    (KeComponentType.NSSF,           D("0.06"),  True,  D("1080"),   "6% of gross, max KES 1,080 (simplified 2024)"),
    (KeComponentType.HOUSING_LEVY,   D("0.015"), True,  None,        "Affordable Housing Levy 1.5% of gross"),
    (KeComponentType.PERSONAL_RELIEF,D("2400"),  False, None,        "Monthly personal relief — Finance Act 2023"),
]


async def seed_kenya_rates(db: AsyncSession, tax_year: int = 2024) -> SeedResult:
    """Seed Kenya 2024 statutory rates if not already present."""
    bands_seeded = 0
    nhif_seeded = 0
    rates_seeded = 0

    # Tax bands
    for lower, upper, rate, desc in KE_TAX_BANDS_2024:
        existing = await db.execute(
            select(KeTaxBand).where(
                KeTaxBand.tax_year == tax_year,
                KeTaxBand.lower_limit == lower,
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(KeTaxBand(
            tax_year=tax_year, lower_limit=lower, upper_limit=upper,
            rate=rate, description=desc, is_active=True,
        ))
        bands_seeded += 1

    # NHIF tiers
    for g_from, g_to, contrib in KE_NHIF_TIERS_2023:
        existing = await db.execute(
            select(KeNhifTier).where(
                KeNhifTier.rate_year == tax_year,
                KeNhifTier.gross_from == g_from,
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(KeNhifTier(
            rate_year=tax_year, gross_from=g_from, gross_to=g_to,
            contribution=contrib, is_active=True,
        ))
        nhif_seeded += 1

    # Statutory rates
    for component, value, is_pct, max_amt, notes in KE_STATUTORY_RATES_2024:
        existing = await db.execute(
            select(KeStatutoryRate).where(
                KeStatutoryRate.component == component,
                KeStatutoryRate.rate_year == tax_year,
                KeStatutoryRate.is_active == True,  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(KeStatutoryRate(
            component=component, rate_year=tax_year,
            rate_value=value, is_percentage=is_pct,
            max_amount=max_amt, notes=notes, is_active=True,
        ))
        rates_seeded += 1

    await db.flush()
    return SeedResult(
        tax_bands_seeded=bands_seeded,
        nhif_tiers_seeded=nhif_seeded,
        statutory_rates_seeded=rates_seeded,
        message=f"Seeded {bands_seeded} tax bands, {nhif_seeded} NHIF tiers, {rates_seeded} statutory rates for {tax_year}.",
    )


# ── Calculation Engine ────────────────────────────────────────────────────────

async def _get_tax_bands(db: AsyncSession, tax_year: int) -> List[KeTaxBand]:
    r = await db.execute(
        select(KeTaxBand)
        .where(KeTaxBand.tax_year == tax_year, KeTaxBand.is_active == True)  # noqa: E712
        .order_by(KeTaxBand.lower_limit)
    )
    return list(r.scalars().all())


async def _get_nhif_tiers(db: AsyncSession, rate_year: int) -> List[KeNhifTier]:
    r = await db.execute(
        select(KeNhifTier)
        .where(KeNhifTier.rate_year == rate_year, KeNhifTier.is_active == True)  # noqa: E712
        .order_by(KeNhifTier.gross_from)
    )
    return list(r.scalars().all())


async def _get_statutory_rate(
    db: AsyncSession, component: KeComponentType, rate_year: int
) -> Optional[KeStatutoryRate]:
    r = await db.execute(
        select(KeStatutoryRate).where(
            KeStatutoryRate.component == component,
            KeStatutoryRate.rate_year == rate_year,
            KeStatutoryRate.is_active == True,  # noqa: E712
        ).limit(1)
    )
    return r.scalar_one_or_none()


def _calc_paye(taxable_income: Decimal, bands: List[KeTaxBand]) -> Decimal:
    """Apply progressive PAYE tax bands to taxable_income."""
    tax = ZERO
    for band in bands:
        if taxable_income <= ZERO:
            break
        lower = band.lower_limit
        upper = band.upper_limit
        if taxable_income < lower:
            continue
        band_upper = upper if upper else taxable_income
        taxable_in_band = min(taxable_income, band_upper) - lower + 1
        if taxable_in_band <= ZERO:
            continue
        tax += taxable_in_band * band.rate
    return _round(max(tax, ZERO))


def _calc_nhif(gross: Decimal, tiers: List[KeNhifTier]) -> Decimal:
    """Lookup NHIF contribution from tiered table."""
    for tier in sorted(tiers, key=lambda t: t.gross_from):
        if tier.gross_to is None or gross <= tier.gross_to:
            if gross >= tier.gross_from:
                return tier.contribution
    if tiers:
        return sorted(tiers, key=lambda t: t.gross_from)[-1].contribution
    return D("1700")


async def calculate_employee(
    db: AsyncSession,
    profile: EmployeePayrollProfile,
    tax_year: int,
    overtime_pay: Decimal = ZERO,
    other_deductions: Decimal = ZERO,
) -> dict:
    """Calculate Kenya statutory deductions for one employee."""
    bands = await _get_tax_bands(db, tax_year)
    nhif_tiers = await _get_nhif_tiers(db, tax_year)
    nssf_rate = await _get_statutory_rate(db, KeComponentType.NSSF, tax_year)
    ahl_rate = await _get_statutory_rate(db, KeComponentType.HOUSING_LEVY, tax_year)
    relief_rate = await _get_statutory_rate(db, KeComponentType.PERSONAL_RELIEF, tax_year)

    basic = _round(profile.basic_salary)
    housing = _round(profile.housing_allowance)
    transport = _round(profile.transport_allowance)
    other_allow = ZERO
    if profile.other_allowances:
        other_allow = _round(sum(D(str(v)) for v in profile.other_allowances.values()))

    gross = basic + housing + transport + other_allow + _round(overtime_pay)

    # NSSF (employee contribution)
    if nssf_rate:
        if nssf_rate.is_percentage:
            nssf_emp = _round(gross * nssf_rate.rate_value)
            if nssf_rate.max_amount:
                nssf_emp = min(nssf_emp, nssf_rate.max_amount)
        else:
            nssf_emp = _round(nssf_rate.rate_value)
    else:
        nssf_emp = _round(gross * D("0.06"))
        nssf_emp = min(nssf_emp, D("1080"))

    # Taxable income = gross - NSSF
    taxable = max(gross - nssf_emp, ZERO)

    # PAYE
    if bands:
        paye_gross = _calc_paye(taxable, bands)
    else:
        # Fallback built-in 2024 bands
        paye_gross = _calc_paye_builtin(taxable)

    # Personal relief
    if relief_rate and not relief_rate.is_percentage:
        personal_relief = _round(relief_rate.rate_value)
    else:
        personal_relief = PERSONAL_RELIEF_MONTHLY

    paye_net = _round(max(paye_gross - personal_relief, ZERO))

    # NHIF
    nhif = _calc_nhif(gross, nhif_tiers) if nhif_tiers else D("1700")

    # Housing/AHL Levy
    if ahl_rate and ahl_rate.is_percentage:
        ahl = _round(gross * ahl_rate.rate_value)
    else:
        ahl = _round(gross * D("0.015"))

    total_deductions = _round(paye_net + nhif + nssf_emp + ahl + _round(other_deductions))
    net = _round(gross - total_deductions)

    return {
        "basic_salary": basic,
        "housing_allowance": housing,
        "transport_allowance": transport,
        "other_allowances": other_allow,
        "overtime_pay": _round(overtime_pay),
        "gross_salary": gross,
        "nssf_employee": nssf_emp,
        "taxable_income": taxable,
        "paye_before_relief": paye_gross,
        "personal_relief": personal_relief,
        "paye_amount": paye_net,
        "nhif_amount": nhif,
        "housing_levy": ahl,
        "other_deductions": _round(other_deductions),
        "total_deductions": total_deductions,
        "net_salary": net,
        "components_json": {
            "earnings": {
                "Basic Salary": float(basic),
                "Housing Allowance": float(housing),
                "Transport Allowance": float(transport),
                "Other Allowances": float(other_allow),
                "Overtime": float(overtime_pay),
            },
            "deductions": {
                "PAYE": float(paye_net),
                "NHIF": float(nhif),
                "NSSF (Employee)": float(nssf_emp),
                "Housing Levy (AHL)": float(ahl),
                "Other Deductions": float(other_deductions),
            },
        },
    }


def _calc_paye_builtin(taxable: Decimal) -> Decimal:
    """Fallback PAYE using hardcoded 2024 Kenya bands."""
    bands = [
        (D("0"),      D("24000"),  D("0.10")),
        (D("24001"),  D("32333"),  D("0.25")),
        (D("32334"),  D("500000"), D("0.30")),
        (D("500001"), D("800000"), D("0.325")),
        (D("800001"), None,        D("0.35")),
    ]
    tax = ZERO
    for lower, upper, rate in bands:
        if taxable <= ZERO:
            break
        if taxable < lower:
            continue
        band_upper = upper if upper else taxable
        in_band = min(taxable, band_upper) - lower + 1
        if in_band <= ZERO:
            continue
        tax += in_band * rate
    return _round(max(tax, ZERO))


# ── Payroll Run Lifecycle ─────────────────────────────────────────────────────

def _run_no(month: int, year: int) -> str:
    return f"PR-{year}{month:02d}"


async def create_payroll_run(
    db: AsyncSession, data: PayrollRunCreate, user_id: uuid.UUID
) -> PayrollRun:
    existing = await db.execute(
        select(PayrollRun).where(
            PayrollRun.period_month == data.period_month,
            PayrollRun.period_year == data.period_year,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Payroll run for {data.period_month}/{data.period_year} already exists")

    run = PayrollRun(
        run_no=_run_no(data.period_month, data.period_year),
        period_month=data.period_month,
        period_year=data.period_year,
        period_start=data.period_start,
        period_end=data.period_end,
        notes=data.notes,
        created_by=user_id,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return run


async def calculate_payroll_run(
    db: AsyncSession, run: PayrollRun, tax_year: Optional[int] = None
) -> PayrollRun:
    """Calculate all employee lines for this payroll run."""
    if run.status not in (PayrollRunStatus.DRAFT, PayrollRunStatus.CALCULATED):
        raise HTTPException(422, f"Cannot recalculate run in status {run.status}")

    ty = tax_year or run.period_year

    # Delete existing lines
    from sqlalchemy import delete
    await db.execute(delete(KePayrollLine).where(KePayrollLine.run_id == run.id))

    # Load all active profiles
    profiles_q = await db.execute(
        select(EmployeePayrollProfile)
        .where(EmployeePayrollProfile.is_active == True)  # noqa: E712
        .options(selectinload(EmployeePayrollProfile.employee))
    )
    profiles = list(profiles_q.scalars().all())

    totals = {k: ZERO for k in ["gross", "paye", "nhif", "nssf", "housing_levy", "net"]}

    for profile in profiles:
        calc = await calculate_employee(db, profile, ty)
        line = KePayrollLine(
            run_id=run.id,
            employee_id=profile.employee_id,
            **{k: calc[k] for k in [
                "basic_salary", "housing_allowance", "transport_allowance",
                "other_allowances", "overtime_pay", "gross_salary",
                "nssf_employee", "taxable_income", "paye_before_relief",
                "personal_relief", "paye_amount", "nhif_amount",
                "housing_levy", "other_deductions", "total_deductions",
                "net_salary", "components_json",
            ]},
        )
        db.add(line)
        totals["gross"] += calc["gross_salary"]
        totals["paye"] += calc["paye_amount"]
        totals["nhif"] += calc["nhif_amount"]
        totals["nssf"] += calc["nssf_employee"]
        totals["housing_levy"] += calc["housing_levy"]
        totals["net"] += calc["net_salary"]

    run.total_gross = _round(totals["gross"])
    run.total_paye = _round(totals["paye"])
    run.total_nhif = _round(totals["nhif"])
    run.total_nssf = _round(totals["nssf"])
    run.total_housing_levy = _round(totals["housing_levy"])
    run.total_net = _round(totals["net"])
    run.employee_count = len(profiles)
    run.run_date = date.today()
    run.status = PayrollRunStatus.CALCULATED
    await db.flush()
    await db.refresh(run)
    return run


async def approve_payroll_run(
    db: AsyncSession, run: PayrollRun, approver_id: uuid.UUID
) -> PayrollRun:
    if run.status != PayrollRunStatus.CALCULATED:
        raise HTTPException(422, "Only CALCULATED runs can be approved")
    run.status = PayrollRunStatus.APPROVED
    run.approved_by = approver_id
    run.approved_at = _now()
    await db.flush()

    # Generate payslips
    lines_q = await db.execute(
        select(KePayrollLine).where(KePayrollLine.run_id == run.id)
    )
    for line in lines_q.scalars().all():
        existing = await db.execute(
            select(Payslip).where(Payslip.payroll_line_id == line.id)
        )
        if existing.scalar_one_or_none():
            continue
        slip = Payslip(
            payroll_line_id=line.id,
            employee_id=line.employee_id,
            run_id=run.id,
            issue_date=date.today(),
        )
        db.add(slip)
    await db.flush()
    await db.refresh(run)
    return run


# ── Reports ───────────────────────────────────────────────────────────────────

async def paye_report(db: AsyncSession, run_id: uuid.UUID) -> List[PayeSummaryRow]:
    lines_q = await db.execute(
        select(KePayrollLine)
        .where(KePayrollLine.run_id == run_id)
        .options(selectinload(KePayrollLine.employee))
        .order_by(KePayrollLine.employee_id)
    )
    lines = list(lines_q.scalars().all())
    out = []
    for l in lines:
        profile_q = await db.execute(
            select(EmployeePayrollProfile).where(EmployeePayrollProfile.employee_id == l.employee_id)
        )
        profile = profile_q.scalar_one_or_none()
        out.append(PayeSummaryRow(
            employee_name=l.employee.full_name if l.employee else "—",
            employee_code=l.employee.employee_code if l.employee else "—",
            tax_pin=profile.tax_pin if profile else None,
            gross_salary=l.gross_salary,
            taxable_income=l.taxable_income,
            paye_amount=l.paye_amount,
            personal_relief=l.personal_relief,
        ))
    return out


async def nhif_report(db: AsyncSession, run_id: uuid.UUID) -> List[NhifSummaryRow]:
    lines_q = await db.execute(
        select(KePayrollLine)
        .where(KePayrollLine.run_id == run_id)
        .options(selectinload(KePayrollLine.employee))
    )
    lines = list(lines_q.scalars().all())
    out = []
    for l in lines:
        profile_q = await db.execute(
            select(EmployeePayrollProfile).where(EmployeePayrollProfile.employee_id == l.employee_id)
        )
        profile = profile_q.scalar_one_or_none()
        out.append(NhifSummaryRow(
            employee_name=l.employee.full_name if l.employee else "—",
            employee_code=l.employee.employee_code if l.employee else "—",
            nhif_no=profile.nhif_no if profile else None,
            gross_salary=l.gross_salary,
            nhif_amount=l.nhif_amount,
        ))
    return out


async def nssf_report(db: AsyncSession, run_id: uuid.UUID) -> List[NssfSummaryRow]:
    lines_q = await db.execute(
        select(KePayrollLine)
        .where(KePayrollLine.run_id == run_id)
        .options(selectinload(KePayrollLine.employee))
    )
    lines = list(lines_q.scalars().all())
    out = []
    for l in lines:
        profile_q = await db.execute(
            select(EmployeePayrollProfile).where(EmployeePayrollProfile.employee_id == l.employee_id)
        )
        profile = profile_q.scalar_one_or_none()
        out.append(NssfSummaryRow(
            employee_name=l.employee.full_name if l.employee else "—",
            employee_code=l.employee.employee_code if l.employee else "—",
            nssf_no=profile.nssf_no if profile else None,
            gross_salary=l.gross_salary,
            nssf_employee=l.nssf_employee,
        ))
    return out


async def payroll_summary(db: AsyncSession, run_id: uuid.UUID) -> List[PayrollSummaryRow]:
    lines_q = await db.execute(
        select(KePayrollLine)
        .where(KePayrollLine.run_id == run_id)
        .options(selectinload(KePayrollLine.employee))
    )
    lines = list(lines_q.scalars().all())
    return [
        PayrollSummaryRow(
            employee_name=l.employee.full_name if l.employee else "—",
            employee_code=l.employee.employee_code if l.employee else "—",
            department=l.employee.department if l.employee else None,
            gross_salary=l.gross_salary,
            total_deductions=l.total_deductions,
            net_salary=l.net_salary,
            payment_method=l.employee.payment_method.value if l.employee and l.employee.payment_method else None,
        )
        for l in lines
    ]


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def ai_anomaly_detector(db: AsyncSession, run_id: uuid.UUID) -> PayrollInsight:
    lines_q = await db.execute(
        select(KePayrollLine)
        .where(KePayrollLine.run_id == run_id)
        .options(selectinload(KePayrollLine.employee))
    )
    lines = list(lines_q.scalars().all())
    insights = []
    details = []

    if not lines:
        insights.append("No payroll lines calculated yet. Run calculation first.")
        return PayrollInsight(agent="Payroll Anomaly Detector", insights=insights, generated_at=_now().isoformat())

    salaries = [float(l.gross_salary) for l in lines]
    avg = sum(salaries) / len(salaries)
    stddev = (sum((s - avg) ** 2 for s in salaries) / len(salaries)) ** 0.5

    for l in lines:
        gross = float(l.gross_salary)
        net = float(l.net_salary)
        name = l.employee.full_name if l.employee else "Unknown"

        if gross > avg + 3 * stddev:
            insights.append(f"HIGH OUTLIER: {name} — gross KES {gross:,.0f} is >3σ above mean. Verify salary structure.")
            details.append({"employee": name, "issue": "high_outlier", "gross": gross})

        deduction_rate = (gross - net) / gross if gross > 0 else 0
        if deduction_rate > 0.6:
            insights.append(f"HIGH DEDUCTIONS: {name} — {deduction_rate*100:.1f}% of gross deducted. Review for data errors.")
            details.append({"employee": name, "issue": "high_deduction_rate", "rate_pct": round(deduction_rate * 100, 1)})

        if float(l.paye_amount) == 0 and gross > 24000:
            insights.append(f"ZERO PAYE: {name} — earns KES {gross:,.0f} but PAYE is zero. Check tax relief or calculation.")
            details.append({"employee": name, "issue": "zero_paye", "gross": gross})

    if not insights:
        insights.append("No anomalies detected. All salary calculations appear within normal range.")

    return PayrollInsight(agent="Payroll Anomaly Detector", insights=insights, details=details, generated_at=_now().isoformat())


async def ai_compliance_monitor(db: AsyncSession) -> PayrollInsight:
    profiles_q = await db.execute(
        select(EmployeePayrollProfile)
        .where(EmployeePayrollProfile.is_active == True)  # noqa: E712
        .options(selectinload(EmployeePayrollProfile.employee))
    )
    profiles = list(profiles_q.scalars().all())

    insights = []
    details = []
    missing_pin = [p for p in profiles if not p.tax_pin]
    missing_nhif = [p for p in profiles if not p.nhif_no]
    missing_nssf = [p for p in profiles if not p.nssf_no]

    if missing_pin:
        names = ", ".join(p.employee.full_name for p in missing_pin[:5] if p.employee)
        insights.append(f"MISSING KRA PIN: {len(missing_pin)} employee(s) — {names}{'…' if len(missing_pin) > 5 else ''}. Required for PAYE filing with KRA.")
        details.append({"issue": "missing_kra_pin", "count": len(missing_pin)})

    if missing_nhif:
        insights.append(f"MISSING NHIF NO: {len(missing_nhif)} employee(s) without NHIF numbers. Required for NHIF statutory returns.")
        details.append({"issue": "missing_nhif_no", "count": len(missing_nhif)})

    if missing_nssf:
        insights.append(f"MISSING NSSF NO: {len(missing_nssf)} employee(s) without NSSF numbers. Required for NSSF Act 2013 compliance.")
        details.append({"issue": "missing_nssf_no", "count": len(missing_nssf)})

    no_profile_q = await db.execute(
        select(func.count())
        .select_from(Employee)
        .where(
            ~Employee.id.in_(
                select(EmployeePayrollProfile.employee_id)
            )
        )
    )
    no_profile_count = no_profile_q.scalar() or 0
    if no_profile_count > 0:
        insights.append(f"NO PAYROLL PROFILE: {no_profile_count} active employee(s) have no Kenya payroll profile. They will be excluded from payroll runs.")
        details.append({"issue": "no_payroll_profile", "count": no_profile_count})

    if not insights:
        insights.append("All employees have complete statutory data (KRA PIN, NHIF, NSSF). Compliance status: OK.")

    return PayrollInsight(agent="Compliance Monitor", insights=insights, details=details, generated_at=_now().isoformat())
