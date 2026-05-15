from pydantic import BaseModel
from typing import Optional, List, Any
from decimal import Decimal
from datetime import datetime, date
import uuid

from app.models.payroll_ke import PayFrequency, KeComponentType, PayrollRunStatus


# ── Payroll Profile ───────────────────────────────────────────────────────────

class PayrollScopeFields(BaseModel):
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    department_id: Optional[str] = None
    cost_center_id: Optional[uuid.UUID] = None


class PayrollProfileCreate(PayrollScopeFields):
    employee_id: uuid.UUID
    basic_salary: Decimal
    pay_frequency: PayFrequency = PayFrequency.MONTHLY
    housing_allowance: Decimal = Decimal("0")
    transport_allowance: Decimal = Decimal("0")
    other_allowances: Optional[dict] = None
    tax_pin: Optional[str] = None
    nhif_no: Optional[str] = None
    nssf_no: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_no: Optional[str] = None
    bank_branch: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None


class PayrollProfileUpdate(PayrollScopeFields):
    basic_salary: Optional[Decimal] = None
    housing_allowance: Optional[Decimal] = None
    transport_allowance: Optional[Decimal] = None
    other_allowances: Optional[dict] = None
    tax_pin: Optional[str] = None
    nhif_no: Optional[str] = None
    nssf_no: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_no: Optional[str] = None
    bank_branch: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class PayrollProfileRead(PayrollProfileCreate):
    id: uuid.UUID
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Tax Bands ─────────────────────────────────────────────────────────────────

class TaxBandCreate(BaseModel):
    tax_year: int
    lower_limit: Decimal
    upper_limit: Optional[Decimal] = None
    rate: Decimal
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    description: Optional[str] = None
    is_active: bool = True


class TaxBandRead(TaxBandCreate):
    id: uuid.UUID
    model_config = {"from_attributes": True}


# ── Statutory Rates ───────────────────────────────────────────────────────────

class StatutoryRateCreate(BaseModel):
    component: KeComponentType
    rate_year: int
    rate_value: Decimal
    is_percentage: bool = True
    max_amount: Optional[Decimal] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    notes: Optional[str] = None
    is_active: bool = True


class StatutoryRateRead(StatutoryRateCreate):
    id: uuid.UUID
    model_config = {"from_attributes": True}


# ── Payroll Run ───────────────────────────────────────────────────────────────

class PayrollRunCreate(PayrollScopeFields):
    period_month: int
    period_year: int
    period_start: date
    period_end: date
    notes: Optional[str] = None


class PayrollRunRead(BaseModel):
    id: uuid.UUID
    run_no: str
    period_month: int
    period_year: int
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    department_id: Optional[str] = None
    cost_center_id: Optional[uuid.UUID] = None
    period_start: date
    period_end: date
    run_date: Optional[date] = None
    status: PayrollRunStatus
    total_gross: Decimal
    total_paye: Decimal
    total_nhif: Decimal
    total_nssf: Decimal
    total_housing_levy: Decimal
    total_net: Decimal
    employee_count: int
    notes: Optional[str] = None
    locked_at: Optional[datetime] = None
    locked_by_id: Optional[uuid.UUID] = None
    model_config = {"from_attributes": True}


# ── Payroll Lines ─────────────────────────────────────────────────────────────

class KePayrollLineRead(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    employee_id: uuid.UUID
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    department_id: Optional[str] = None
    cost_center_id: Optional[uuid.UUID] = None
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    tax_pin: Optional[str] = None
    nhif_no: Optional[str] = None
    nssf_no: Optional[str] = None
    basic_salary: Decimal
    housing_allowance: Decimal
    transport_allowance: Decimal
    other_allowances: Decimal
    overtime_pay: Decimal
    gross_salary: Decimal
    nssf_employee: Decimal
    taxable_income: Decimal
    paye_before_relief: Decimal
    personal_relief: Decimal
    paye_amount: Decimal
    nhif_amount: Decimal
    housing_levy: Decimal
    other_deductions: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    notes: Optional[str] = None
    components_json: Optional[dict] = None
    model_config = {"from_attributes": True}


# ── Payslip ───────────────────────────────────────────────────────────────────

class PayslipRead(BaseModel):
    id: uuid.UUID
    payroll_line_id: uuid.UUID
    employee_id: uuid.UUID
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    department_id: Optional[str] = None
    run_id: uuid.UUID
    issue_date: date
    is_sent: bool
    viewed_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    sent_by_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    department: Optional[str] = None
    period_month: Optional[int] = None
    period_year: Optional[int] = None
    gross_salary: Optional[Decimal] = None
    net_salary: Optional[Decimal] = None
    paye_amount: Optional[Decimal] = None
    nhif_amount: Optional[Decimal] = None
    nssf_employee: Optional[Decimal] = None
    housing_levy: Optional[Decimal] = None
    components_json: Optional[dict] = None
    model_config = {"from_attributes": True}


# ── Reports ───────────────────────────────────────────────────────────────────

class PayeSummaryRow(BaseModel):
    employee_name: str
    employee_code: str
    tax_pin: Optional[str] = None
    gross_salary: Decimal
    taxable_income: Decimal
    paye_amount: Decimal
    personal_relief: Decimal


class NhifSummaryRow(BaseModel):
    employee_name: str
    employee_code: str
    nhif_no: Optional[str] = None
    gross_salary: Decimal
    nhif_amount: Decimal


class NssfSummaryRow(BaseModel):
    employee_name: str
    employee_code: str
    nssf_no: Optional[str] = None
    gross_salary: Decimal
    nssf_employee: Decimal


class PayrollSummaryRow(BaseModel):
    employee_name: str
    employee_code: str
    department: Optional[str] = None
    gross_salary: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    payment_method: Optional[str] = None


# ── AI ────────────────────────────────────────────────────────────────────────

class PayrollInsight(BaseModel):
    agent: str
    insights: List[str]
    details: Optional[List[dict]] = None
    generated_at: str


# ── Seed result ───────────────────────────────────────────────────────────────

class SeedResult(BaseModel):
    tax_bands_seeded: int
    nhif_tiers_seeded: int
    statutory_rates_seeded: int
    message: str
