"""Kenya Payroll Localization — statutory profiles, tax bands, payroll details, payslips."""
import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum as SAEnum, DateTime, Date, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class PayFrequency(str, enum.Enum):
    MONTHLY = "MONTHLY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"


class KeComponentType(str, enum.Enum):
    NHIF = "NHIF"
    NSSF = "NSSF"
    HOUSING_LEVY = "HOUSING_LEVY"
    PERSONAL_RELIEF = "PERSONAL_RELIEF"


class PayrollRunStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CALCULATED = "CALCULATED"
    APPROVED = "APPROVED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class EmployeePayrollProfile(Base, TimestampMixin):
    """Kenya-specific payroll profile per employee — statutory IDs, salary structure."""
    __tablename__ = "ke_payroll_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="CASCADE"),
                         nullable=False, unique=True, index=True)
    basic_salary = Column(Numeric(14, 2), nullable=False)
    pay_frequency = Column(SAEnum(PayFrequency), nullable=False, default=PayFrequency.MONTHLY)
    housing_allowance = Column(Numeric(14, 2), nullable=False, default=0)
    transport_allowance = Column(Numeric(14, 2), nullable=False, default=0)
    other_allowances = Column(JSONB, nullable=True)  # {"Medical": 2000, "Lunch": 1500}
    tax_pin = Column(String(20), nullable=True)
    nhif_no = Column(String(20), nullable=True)
    nssf_no = Column(String(20), nullable=True)
    bank_name = Column(String(100), nullable=True)
    bank_account_no = Column(String(50), nullable=True)
    bank_branch = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    employee = relationship("Employee")


class KeTaxBand(Base, TimestampMixin):
    """Configurable PAYE tax bands — Kenya Finance Act rates."""
    __tablename__ = "ke_tax_bands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tax_year = Column(Integer, nullable=False, index=True)
    lower_limit = Column(Numeric(14, 2), nullable=False)
    upper_limit = Column(Numeric(14, 2), nullable=True)  # NULL = no upper limit
    rate = Column(Numeric(6, 4), nullable=False)  # 0.10 = 10%
    description = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class KeStatutoryRate(Base, TimestampMixin):
    """Configurable statutory rates — NSSF, Housing Levy, Personal Relief."""
    __tablename__ = "ke_statutory_rates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component = Column(SAEnum(KeComponentType), nullable=False)
    rate_year = Column(Integer, nullable=False)
    rate_value = Column(Numeric(10, 6), nullable=False)  # percentage as decimal OR fixed KES
    is_percentage = Column(Boolean, default=True, nullable=False)  # True=%, False=fixed KES
    max_amount = Column(Numeric(14, 2), nullable=True)  # cap
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class KeNhifTier(Base, TimestampMixin):
    """NHIF contribution tiers — gross salary range → fixed contribution."""
    __tablename__ = "ke_nhif_tiers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rate_year = Column(Integer, nullable=False, index=True)
    gross_from = Column(Numeric(14, 2), nullable=False)
    gross_to = Column(Numeric(14, 2), nullable=True)  # NULL = no upper
    contribution = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class PayrollRun(Base, TimestampMixin):
    """Kenya payroll run — period with full statutory calculation."""
    __tablename__ = "ke_payroll_runs"
    __table_args__ = (
        UniqueConstraint("period_month", "period_year", name="uq_ke_payroll_run"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_no = Column(String(30), unique=True, nullable=False, index=True)
    period_month = Column(Integer, nullable=False)
    period_year = Column(Integer, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    run_date = Column(Date, nullable=True)
    status = Column(SAEnum(PayrollRunStatus), nullable=False, default=PayrollRunStatus.DRAFT)
    total_gross = Column(Numeric(18, 2), nullable=False, default=0)
    total_paye = Column(Numeric(18, 2), nullable=False, default=0)
    total_nhif = Column(Numeric(18, 2), nullable=False, default=0)
    total_nssf = Column(Numeric(18, 2), nullable=False, default=0)
    total_housing_levy = Column(Numeric(18, 2), nullable=False, default=0)
    total_net = Column(Numeric(18, 2), nullable=False, default=0)
    employee_count = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    lines = relationship("KePayrollLine", back_populates="run", cascade="all, delete-orphan")


class KePayrollLine(Base, TimestampMixin):
    """Per-employee Kenya payroll line with full statutory breakdown."""
    __tablename__ = "ke_payroll_lines"
    __table_args__ = (
        UniqueConstraint("run_id", "employee_id", name="uq_ke_payroll_line"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("ke_payroll_runs.id", ondelete="CASCADE"),
                    nullable=False, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="RESTRICT"),
                         nullable=False, index=True)
    basic_salary = Column(Numeric(14, 2), nullable=False)
    housing_allowance = Column(Numeric(14, 2), nullable=False, default=0)
    transport_allowance = Column(Numeric(14, 2), nullable=False, default=0)
    other_allowances = Column(Numeric(14, 2), nullable=False, default=0)
    overtime_pay = Column(Numeric(14, 2), nullable=False, default=0)
    gross_salary = Column(Numeric(14, 2), nullable=False)
    nssf_employee = Column(Numeric(14, 2), nullable=False, default=0)
    taxable_income = Column(Numeric(14, 2), nullable=False)
    paye_before_relief = Column(Numeric(14, 2), nullable=False, default=0)
    personal_relief = Column(Numeric(14, 2), nullable=False, default=0)
    paye_amount = Column(Numeric(14, 2), nullable=False, default=0)
    nhif_amount = Column(Numeric(14, 2), nullable=False, default=0)
    housing_levy = Column(Numeric(14, 2), nullable=False, default=0)
    other_deductions = Column(Numeric(14, 2), nullable=False, default=0)
    total_deductions = Column(Numeric(14, 2), nullable=False)
    net_salary = Column(Numeric(14, 2), nullable=False)
    notes = Column(Text, nullable=True)
    components_json = Column(JSONB, nullable=True)  # full breakdown for payslip

    run = relationship("PayrollRun", back_populates="lines")
    employee = relationship("Employee")
    payslip = relationship("Payslip", back_populates="payroll_line", uselist=False)


class Payslip(Base, TimestampMixin):
    """Payslip record — one per payroll line."""
    __tablename__ = "ke_payslips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payroll_line_id = Column(UUID(as_uuid=True), ForeignKey("ke_payroll_lines.id", ondelete="CASCADE"),
                              nullable=False, unique=True, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="RESTRICT"),
                          nullable=False, index=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("ke_payroll_runs.id", ondelete="CASCADE"),
                    nullable=False)
    issue_date = Column(Date, nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    payroll_line = relationship("KePayrollLine", back_populates="payslip")
    employee = relationship("Employee")
    run = relationship("PayrollRun")
