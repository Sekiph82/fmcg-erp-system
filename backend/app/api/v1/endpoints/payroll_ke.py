from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.models.payroll_ke import (
    EmployeePayrollProfile, KeTaxBand, KeStatutoryRate, KeNhifTier,
    PayrollRun, KePayrollLine, Payslip, PayrollRunStatus,
)
from app.schemas.payroll_ke import (
    PayrollProfileCreate, PayrollProfileUpdate, PayrollProfileRead,
    TaxBandCreate, TaxBandRead,
    StatutoryRateCreate, StatutoryRateRead,
    PayrollRunCreate, PayrollRunRead,
    KePayrollLineRead, PayslipRead,
    PayeSummaryRow, NhifSummaryRow, NssfSummaryRow, PayrollSummaryRow,
    PayrollInsight, SeedResult,
)
from app.services import payroll_ke_service as svc

router = APIRouter(dependencies=[Depends(require_permission("payroll_ke", "view"))])


# ── Payroll Profiles ──────────────────────────────────────────────────────────

@router.get("/profiles", response_model=List[PayrollProfileRead])
async def list_profiles(
    skip: int = 0, limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = (
        select(EmployeePayrollProfile)
        .options(selectinload(EmployeePayrollProfile.employee))
        .order_by(EmployeePayrollProfile.created_at.desc())
        .offset(skip).limit(limit)
    )
    result = await db.execute(q)
    profiles = list(result.scalars().all())
    out = []
    for p in profiles:
        r = PayrollProfileRead.model_validate(p)
        if p.employee:
            r.employee_name = p.employee.full_name
            r.employee_code = p.employee.employee_code
        out.append(r)
    return out


@router.get("/profiles/{profile_id}", response_model=PayrollProfileRead)
async def get_profile(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(
        select(EmployeePayrollProfile)
        .where(EmployeePayrollProfile.id == profile_id)
        .options(selectinload(EmployeePayrollProfile.employee))
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Profile not found")
    r = PayrollProfileRead.model_validate(p)
    if p.employee:
        r.employee_name = p.employee.full_name
        r.employee_code = p.employee.employee_code
    return r


@router.post("/profiles", response_model=PayrollProfileRead, status_code=201,
             dependencies=[Depends(require_permission("payroll_ke", "create"))])
async def create_profile(
    data: PayrollProfileCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    existing = await db.execute(
        select(EmployeePayrollProfile).where(EmployeePayrollProfile.employee_id == data.employee_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Payroll profile already exists for this employee")
    obj = EmployeePayrollProfile(**data.model_dump())
    db.add(obj)
    await db.commit()
    result = await db.execute(
        select(EmployeePayrollProfile)
        .where(EmployeePayrollProfile.id == obj.id)
        .options(selectinload(EmployeePayrollProfile.employee))
    )
    p = result.scalar_one()
    r = PayrollProfileRead.model_validate(p)
    if p.employee:
        r.employee_name = p.employee.full_name
        r.employee_code = p.employee.employee_code
    return r


@router.patch("/profiles/{profile_id}", response_model=PayrollProfileRead,
              dependencies=[Depends(require_permission("payroll_ke", "create"))])
async def update_profile(
    profile_id: uuid.UUID,
    data: PayrollProfileUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(
        select(EmployeePayrollProfile)
        .where(EmployeePayrollProfile.id == profile_id)
        .options(selectinload(EmployeePayrollProfile.employee))
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Profile not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    await db.commit()
    await db.refresh(p)
    r = PayrollProfileRead.model_validate(p)
    if p.employee:
        r.employee_name = p.employee.full_name
        r.employee_code = p.employee.employee_code
    return r


# ── Tax Bands ─────────────────────────────────────────────────────────────────

@router.get("/tax-bands", response_model=List[TaxBandRead])
async def list_tax_bands(
    tax_year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(KeTaxBand).order_by(KeTaxBand.tax_year.desc(), KeTaxBand.lower_limit)
    if tax_year:
        q = q.where(KeTaxBand.tax_year == tax_year)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post("/tax-bands", response_model=TaxBandRead, status_code=201,
             dependencies=[Depends(require_permission("payroll_ke", "create"))])
async def create_tax_band(
    data: TaxBandCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = KeTaxBand(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return TaxBandRead.model_validate(obj)


# ── Statutory Rates ───────────────────────────────────────────────────────────

@router.get("/statutory-rates", response_model=List[StatutoryRateRead])
async def list_statutory_rates(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(
        select(KeStatutoryRate).order_by(KeStatutoryRate.rate_year.desc())
    )
    return list(result.scalars().all())


@router.post("/statutory-rates", response_model=StatutoryRateRead, status_code=201,
             dependencies=[Depends(require_permission("payroll_ke", "create"))])
async def create_statutory_rate(
    data: StatutoryRateCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = KeStatutoryRate(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return StatutoryRateRead.model_validate(obj)


# ── Seed Rates ────────────────────────────────────────────────────────────────

@router.post("/seed-rates", response_model=SeedResult,
             dependencies=[Depends(require_permission("payroll_ke", "create"))])
async def seed_rates(
    tax_year: int = Query(2024),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await svc.seed_kenya_rates(db, tax_year)
    await db.commit()
    return result


# ── Payroll Runs ──────────────────────────────────────────────────────────────

@router.get("/runs", response_model=List[PayrollRunRead])
async def list_runs(
    skip: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = select(PayrollRun).order_by(PayrollRun.period_year.desc(), PayrollRun.period_month.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return [PayrollRunRead.model_validate(r) for r in result.scalars().all()]


@router.post("/runs", response_model=PayrollRunRead, status_code=201,
             dependencies=[Depends(require_permission("payroll_ke", "create"))])
async def create_run(
    data: PayrollRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    run = await svc.create_payroll_run(db, data, current_user.id)
    await db.commit()
    await db.refresh(run)
    return PayrollRunRead.model_validate(run)


@router.get("/runs/{run_id}", response_model=PayrollRunRead)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(PayrollRun).where(PayrollRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Payroll run not found")
    return PayrollRunRead.model_validate(run)


@router.post("/runs/{run_id}/calculate", response_model=PayrollRunRead,
             dependencies=[Depends(require_permission("payroll_ke", "create"))])
async def calculate_run(
    run_id: uuid.UUID,
    tax_year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(PayrollRun).where(PayrollRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    run = await svc.calculate_payroll_run(db, run, tax_year)
    await db.commit()
    return PayrollRunRead.model_validate(run)


@router.post("/runs/{run_id}/approve", response_model=PayrollRunRead,
             dependencies=[Depends(require_permission("payroll_ke", "approve"))])
async def approve_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(PayrollRun).where(PayrollRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    run = await svc.approve_payroll_run(db, run, current_user.id)
    await db.commit()
    return PayrollRunRead.model_validate(run)


@router.get("/runs/{run_id}/lines", response_model=List[KePayrollLineRead])
async def get_run_lines(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = (
        select(KePayrollLine)
        .where(KePayrollLine.run_id == run_id)
        .options(selectinload(KePayrollLine.employee))
        .order_by(KePayrollLine.employee_id)
    )
    result = await db.execute(q)
    lines = list(result.scalars().all())
    out = []
    for l in lines:
        r = KePayrollLineRead.model_validate(l)
        if l.employee:
            r.employee_name = l.employee.full_name
            r.employee_code = l.employee.employee_code
        out.append(r)
    return out


# ── Payslips ──────────────────────────────────────────────────────────────────

@router.get("/runs/{run_id}/payslips", response_model=List[PayslipRead])
async def get_run_payslips(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    q = (
        select(Payslip)
        .where(Payslip.run_id == run_id)
        .options(
            selectinload(Payslip.employee),
            selectinload(Payslip.payroll_line),
            selectinload(Payslip.run),
        )
    )
    result = await db.execute(q)
    slips = list(result.scalars().all())
    out = []
    for s in slips:
        r = PayslipRead.model_validate(s)
        if s.employee:
            r.employee_name = s.employee.full_name
            r.employee_code = s.employee.employee_code
            r.department = s.employee.department
        if s.run:
            r.period_month = s.run.period_month
            r.period_year = s.run.period_year
        if s.payroll_line:
            r.gross_salary = s.payroll_line.gross_salary
            r.net_salary = s.payroll_line.net_salary
            r.paye_amount = s.payroll_line.paye_amount
            r.nhif_amount = s.payroll_line.nhif_amount
            r.nssf_employee = s.payroll_line.nssf_employee
            r.housing_levy = s.payroll_line.housing_levy
            r.components_json = s.payroll_line.components_json
        out.append(r)
    return out


@router.get("/payslips/{payslip_id}", response_model=PayslipRead)
async def get_payslip(
    payslip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(
        select(Payslip)
        .where(Payslip.id == payslip_id)
        .options(
            selectinload(Payslip.employee),
            selectinload(Payslip.payroll_line),
            selectinload(Payslip.run),
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Payslip not found")
    r = PayslipRead.model_validate(s)
    if s.employee:
        r.employee_name = s.employee.full_name
        r.employee_code = s.employee.employee_code
        r.department = s.employee.department
    if s.run:
        r.period_month = s.run.period_month
        r.period_year = s.run.period_year
    if s.payroll_line:
        r.gross_salary = s.payroll_line.gross_salary
        r.net_salary = s.payroll_line.net_salary
        r.paye_amount = s.payroll_line.paye_amount
        r.nhif_amount = s.payroll_line.nhif_amount
        r.nssf_employee = s.payroll_line.nssf_employee
        r.housing_levy = s.payroll_line.housing_levy
        r.components_json = s.payroll_line.components_json
    return r


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/runs/{run_id}/reports/paye", response_model=List[PayeSummaryRow])
async def paye_report(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.paye_report(db, run_id)


@router.get("/runs/{run_id}/reports/nhif", response_model=List[NhifSummaryRow])
async def nhif_report(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.nhif_report(db, run_id)


@router.get("/runs/{run_id}/reports/nssf", response_model=List[NssfSummaryRow])
async def nssf_report(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.nssf_report(db, run_id)


@router.get("/runs/{run_id}/reports/summary", response_model=List[PayrollSummaryRow])
async def payroll_summary(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.payroll_summary(db, run_id)


# ── AI Agents ─────────────────────────────────────────────────────────────────

@router.get("/runs/{run_id}/ai/anomaly", response_model=PayrollInsight)
async def ai_anomaly(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.ai_anomaly_detector(db, run_id)


@router.get("/ai/compliance", response_model=PayrollInsight)
async def ai_compliance(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    return await svc.ai_compliance_monitor(db)


# ── Gap 60: Kenya eTIMS + SHIF ────────────────────────────────────────────────

from datetime import date as _date, datetime as _dt
from pydantic import BaseModel as _BM


class eTIMSSubmitIn(_BM):
    invoice_id: str
    invoice_type: str = "SALES"
    invoice_date: _date
    customer_pin: Optional[str] = None
    supplier_pin: Optional[str] = None
    taxable_amount: float
    vat_amount: float
    total_amount: float


@router.post("/etims/submit", status_code=201,
             dependencies=[Depends(get_current_user)])
async def etims_submit(payload: eTIMSSubmitIn, db: AsyncSession = Depends(get_db)):
    """
    Stub: submit invoice to KRA eTIMS.
    In production: integrate with KRA eTIMS API (https://etims.kra.go.ke/).
    """
    from app.models.payroll_ke import eTIMSInvoiceRecord, eTIMSInvoiceStatus
    record = eTIMSInvoiceRecord(
        invoice_id=payload.invoice_id,
        invoice_type=payload.invoice_type,
        invoice_date=payload.invoice_date,
        customer_pin=payload.customer_pin,
        supplier_pin=payload.supplier_pin,
        taxable_amount=payload.taxable_amount,
        vat_amount=payload.vat_amount,
        total_amount=payload.total_amount,
        etims_status=eTIMSInvoiceStatus.PENDING,
        submission_payload=payload.model_dump(),
        submitted_at=_dt.utcnow(),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {
        "id": str(record.id),
        "invoice_id": record.invoice_id,
        "status": record.etims_status,
        "note": "Stub — wire KRA eTIMS API for live submission. VAT 16% applies.",
    }


@router.get("/etims/records",
            dependencies=[Depends(get_current_user)])
async def list_etims_records(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    from app.models.payroll_ke import eTIMSInvoiceRecord
    from sqlalchemy import desc as _d
    q = select(eTIMSInvoiceRecord)
    if status:
        q = q.where(eTIMSInvoiceRecord.etims_status == status)
    q = q.order_by(_d(eTIMSInvoiceRecord.created_at)).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {"id": str(r.id), "invoice_id": r.invoice_id, "invoice_type": r.invoice_type,
         "invoice_date": str(r.invoice_date) if r.invoice_date else None,
         "total_amount": float(r.total_amount) if r.total_amount else None,
         "vat_amount": float(r.vat_amount) if r.vat_amount else None,
         "status": r.etims_status, "etims_ref": r.etims_ref,
         "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None}
        for r in rows
    ]


class SHIFTierIn(_BM):
    tier_name: str
    gross_min: Optional[float] = None
    gross_max: Optional[float] = None
    contribution_rate_pct: float = 2.75
    min_contribution: Optional[float] = None
    max_contribution: Optional[float] = None
    effective_date: Optional[_date] = None
    notes: Optional[str] = None


@router.post("/shif-tiers", status_code=201,
             dependencies=[Depends(get_current_user)])
async def create_shif_tier(payload: SHIFTierIn, db: AsyncSession = Depends(get_db)):
    from app.models.payroll_ke import SHIFTier
    tier = SHIFTier(**payload.model_dump())
    db.add(tier)
    await db.commit()
    await db.refresh(tier)
    return {"id": str(tier.id), "tier_name": tier.tier_name,
            "contribution_rate_pct": float(tier.contribution_rate_pct)}


@router.get("/shif-tiers",
            dependencies=[Depends(get_current_user)])
async def list_shif_tiers(db: AsyncSession = Depends(get_db)):
    from app.models.payroll_ke import SHIFTier
    rows = (await db.execute(select(SHIFTier).where(SHIFTier.is_active == True)
                             .order_by(SHIFTier.gross_min))).scalars().all()
    return [
        {"id": str(r.id), "tier_name": r.tier_name,
         "gross_min": float(r.gross_min) if r.gross_min else None,
         "gross_max": float(r.gross_max) if r.gross_max else None,
         "contribution_rate_pct": float(r.contribution_rate_pct),
         "effective_date": str(r.effective_date) if r.effective_date else None}
        for r in rows
    ]


@router.post("/shif-tiers/seed-defaults",
             dependencies=[Depends(get_current_user)])
async def seed_shif_defaults(db: AsyncSession = Depends(get_db)):
    """Seed SHIF 2.75% flat-rate tiers per Kenya Finance Act 2023."""
    from app.models.payroll_ke import SHIFTier
    from datetime import date
    existing = (await db.execute(select(SHIFTier))).scalars().first()
    if existing:
        return {"message": "SHIF tiers already seeded", "count": 0}
    tiers = [
        SHIFTier(tier_name="SHIF Standard Rate", contribution_rate_pct=2.75,
                 min_contribution=300, effective_date=date(2023, 10, 1),
                 notes="SHIF 2.75% of gross salary. Min KES 300/month. Replaces NHIF flat rates."),
    ]
    for t in tiers:
        db.add(t)
    await db.commit()
    return {"message": "SHIF tiers seeded", "count": len(tiers)}
