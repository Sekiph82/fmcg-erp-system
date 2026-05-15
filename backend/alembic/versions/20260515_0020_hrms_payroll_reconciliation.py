"""hrms payroll reconciliation

Revision ID: 20260515_0020
Revises: 20260515_0010
Create Date: 2026-05-15 10:25:00.000000
"""
from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260515_0020"
down_revision = "20260515_0010"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    if context.is_offline_mode():
        return True
    return table_name in _inspector().get_table_names()


def _columns(table_name: str) -> set[str]:
    if context.is_offline_mode() or not _has_table(table_name):
        return set()
    return {column["name"] for column in _inspector().get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    if context.is_offline_mode() or not _has_table(table_name):
        return set()
    return {index["name"] for index in _inspector().get_indexes(table_name)}


def _foreign_keys(table_name: str) -> set[str]:
    if context.is_offline_mode() or not _has_table(table_name):
        return set()
    return {fk["name"] for fk in _inspector().get_foreign_keys(table_name) if fk.get("name")}


def _add_column_once(table_name: str, column: sa.Column) -> None:
    if context.is_offline_mode() or (_has_table(table_name) and column.name not in _columns(table_name)):
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _has_table(table_name) and column_name in _columns(table_name):
        op.drop_column(table_name, column_name)


def _create_index_once(name: str, table_name: str, columns: list[str], **kwargs) -> None:
    if context.is_offline_mode() or (_has_table(table_name) and name not in _indexes(table_name)):
        op.create_index(name, table_name, columns, **kwargs)


def _drop_index_if_exists(name: str, table_name: str) -> None:
    if _has_table(table_name) and name in _indexes(table_name):
        op.drop_index(name, table_name=table_name)


def _create_fk_once(
    name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    **kwargs,
) -> None:
    if context.is_offline_mode() or (_has_table(source_table) and name not in _foreign_keys(source_table)):
        op.create_foreign_key(name, source_table, referent_table, local_cols, remote_cols, **kwargs)


def _drop_fk_if_exists(name: str, table_name: str) -> None:
    if _has_table(table_name) and name in _foreign_keys(table_name):
        op.drop_constraint(name, table_name, type_="foreignkey")


def _create_enum(name: str, *values: str) -> None:
    enum = postgresql.ENUM(*values, name=name)
    enum.create(op.get_bind(), checkfirst=True)


def _enum(name: str, *values: str):
    return postgresql.ENUM(*values, name=name, create_type=False)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    ]


def _create_core_hr_tables_if_missing() -> None:
    _create_enum("employeestatus", "ACTIVE", "INACTIVE", "ON_LEAVE", "TERMINATED")
    _create_enum("hr_attendancestatus", "PRESENT", "ABSENT", "LATE", "LEAVE", "HALF_DAY")
    _create_enum("leavetype", "ANNUAL", "SICK", "MATERNITY", "PATERNITY", "UNPAID", "COMPASSIONATE", "OTHER")
    _create_enum("hr_approvalstatus", "PENDING", "APPROVED", "REJECTED", "CANCELLED")
    _create_enum("hr_paymentmethod", "MPESA", "BANK", "CASH")
    _create_enum("payrollstatus", "DRAFT", "APPROVED", "PAID", "CANCELLED")

    if context.is_offline_mode() or not _has_table("hr_employees"):
        op.create_table(
            "hr_employees",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("employee_code", sa.String(50), nullable=False),
            sa.Column("full_name", sa.String(255), nullable=False),
            sa.Column("department", sa.String(100), nullable=False),
            sa.Column("role", sa.String(100), nullable=False),
            sa.Column("phone", sa.String(30), nullable=True),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("hire_date", sa.Date(), nullable=False),
            sa.Column("status", _enum("employeestatus", "ACTIVE", "INACTIVE", "ON_LEAVE", "TERMINATED"), nullable=False),
            sa.Column("user_id", UUID, nullable=True),
            sa.Column("payment_method", _enum("hr_paymentmethod", "MPESA", "BANK", "CASH"), nullable=True),
            sa.Column("mpesa_number", sa.String(20), nullable=True),
            sa.Column("bank_account", sa.String(50), nullable=True),
            sa.Column("salary_grade", sa.String(30), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("employee_code", name="uq_hr_employees_employee_code"),
        )
        op.create_index("ix_hr_employees_employee_code", "hr_employees", ["employee_code"])
        op.create_index("ix_hr_employees_email", "hr_employees", ["email"])
        op.create_index("ix_hr_employees_user_id", "hr_employees", ["user_id"])

    if context.is_offline_mode() or not _has_table("hr_shift_templates"):
        op.create_table(
            "hr_shift_templates",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("start_time", sa.Time(), nullable=False),
            sa.Column("end_time", sa.Time(), nullable=False),
            sa.Column("department", sa.String(100), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            *_timestamps(),
            sa.UniqueConstraint("name", name="uq_hr_shift_templates_name"),
        )

    if context.is_offline_mode() or not _has_table("hr_shift_assignments"):
        op.create_table(
            "hr_shift_assignments",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("employee_id", UUID, nullable=False),
            sa.Column("shift_template_id", UUID, nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=False),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("supervisor_id", UUID, nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["shift_template_id"], ["hr_shift_templates.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["supervisor_id"], ["hr_employees.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_hr_shift_assignments_employee_id", "hr_shift_assignments", ["employee_id"])

    if context.is_offline_mode() or not _has_table("hr_attendance"):
        op.create_table(
            "hr_attendance",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("employee_id", UUID, nullable=False),
            sa.Column("attendance_date", sa.Date(), nullable=False),
            sa.Column("status", _enum("hr_attendancestatus", "PRESENT", "ABSENT", "LATE", "LEAVE", "HALF_DAY"), nullable=False),
            sa.Column("clock_in", sa.Time(), nullable=True),
            sa.Column("clock_out", sa.Time(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("recorded_by_id", UUID, nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["recorded_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("employee_id", "attendance_date", name="uq_hr_attendance_employee_date"),
        )
        op.create_index("ix_hr_attendance_employee_id", "hr_attendance", ["employee_id"])
        op.create_index("ix_hr_attendance_attendance_date", "hr_attendance", ["attendance_date"])

    if context.is_offline_mode() or not _has_table("hr_leave_requests"):
        op.create_table(
            "hr_leave_requests",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("employee_id", UUID, nullable=False),
            sa.Column("leave_type", _enum("leavetype", "ANNUAL", "SICK", "MATERNITY", "PATERNITY", "UNPAID", "COMPASSIONATE", "OTHER"), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("days_requested", sa.Integer(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("approval_status", _enum("hr_approvalstatus", "PENDING", "APPROVED", "REJECTED", "CANCELLED"), nullable=False, server_default="PENDING"),
            sa.Column("reviewed_by_id", UUID, nullable=True),
            sa.Column("review_note", sa.Text(), nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_hr_leave_requests_employee_id", "hr_leave_requests", ["employee_id"])

    if context.is_offline_mode() or not _has_table("hr_leave_balances"):
        op.create_table(
            "hr_leave_balances",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("employee_id", UUID, nullable=False),
            sa.Column("leave_type", _enum("leavetype", "ANNUAL", "SICK", "MATERNITY", "PATERNITY", "UNPAID", "COMPASSIONATE", "OTHER"), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("entitled_days", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("used_days", sa.Integer(), nullable=False, server_default="0"),
            *_timestamps(),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("employee_id", "leave_type", "year", name="uq_hr_leave_balance"),
        )
        op.create_index("ix_hr_leave_balances_employee_id", "hr_leave_balances", ["employee_id"])

    if context.is_offline_mode() or not _has_table("hr_payroll_periods"):
        op.create_table(
            "hr_payroll_periods",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("period_month", sa.Integer(), nullable=False),
            sa.Column("period_year", sa.Integer(), nullable=False),
            sa.Column("status", _enum("payrollstatus", "DRAFT", "APPROVED", "PAID", "CANCELLED"), nullable=False, server_default="DRAFT"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("approved_by_id", UUID, nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("period_month", "period_year", name="uq_hr_payroll_period"),
        )

    if context.is_offline_mode() or not _has_table("hr_payroll_lines"):
        op.create_table(
            "hr_payroll_lines",
            sa.Column("id", UUID, primary_key=True),
            sa.Column("period_id", UUID, nullable=False),
            sa.Column("employee_id", UUID, nullable=False),
            sa.Column("salary_components", JSONB, nullable=True),
            sa.Column("gross_pay", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("net_pay", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("payment_method", _enum("hr_paymentmethod", "MPESA", "BANK", "CASH"), nullable=True),
            sa.Column("payment_reference", sa.String(100), nullable=True),
            sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("paid_by_id", UUID, nullable=True),
            *_timestamps(),
            sa.ForeignKeyConstraint(["period_id"], ["hr_payroll_periods.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["employee_id"], ["hr_employees.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["paid_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("period_id", "employee_id", name="uq_hr_payroll_line"),
        )
        op.create_index("ix_hr_payroll_lines_period_id", "hr_payroll_lines", ["period_id"])
        op.create_index("ix_hr_payroll_lines_employee_id", "hr_payroll_lines", ["employee_id"])


def _add_scope_columns(table_name: str, include_department: bool = True, include_cost_center: bool = True) -> None:
    if not context.is_offline_mode() and not _has_table(table_name):
        return

    _add_column_once(table_name, sa.Column("company_id", UUID, nullable=True))
    _add_column_once(table_name, sa.Column("branch_id", UUID, nullable=True))
    if include_department:
        _add_column_once(table_name, sa.Column("department_id", sa.String(100), nullable=True))
    if include_cost_center:
        _add_column_once(table_name, sa.Column("cost_center_id", UUID, nullable=True))

    _create_fk_once(f"fk_{table_name}_company_id", table_name, "companies", ["company_id"], ["id"], ondelete="SET NULL")
    _create_fk_once(f"fk_{table_name}_branch_id", table_name, "branches", ["branch_id"], ["id"], ondelete="SET NULL")
    if include_cost_center:
        _create_fk_once(f"fk_{table_name}_cost_center_id", table_name, "cost_centers", ["cost_center_id"], ["id"], ondelete="SET NULL")

    _create_index_once(f"ix_{table_name}_company_id", table_name, ["company_id"])
    _create_index_once(f"ix_{table_name}_branch_id", table_name, ["branch_id"])
    if include_department:
        _create_index_once(f"ix_{table_name}_department_id", table_name, ["department_id"])
    if include_cost_center:
        _create_index_once(f"ix_{table_name}_cost_center_id", table_name, ["cost_center_id"])


def _add_employee_master_extensions() -> None:
    if not context.is_offline_mode() and not _has_table("hr_employees"):
        return

    _add_scope_columns("hr_employees")
    _add_column_once("hr_employees", sa.Column("manager_employee_id", UUID, nullable=True))
    _add_column_once("hr_employees", sa.Column("terminated_at", sa.Date(), nullable=True))
    _add_column_once("hr_employees", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_once("hr_employees", sa.Column("archived_by_id", UUID, nullable=True))
    _create_fk_once("fk_hr_employees_manager_employee_id", "hr_employees", "hr_employees", ["manager_employee_id"], ["id"], ondelete="SET NULL")
    _create_fk_once("fk_hr_employees_archived_by_id", "hr_employees", "users", ["archived_by_id"], ["id"], ondelete="SET NULL")
    _create_index_once("ix_hr_employees_manager_employee_id", "hr_employees", ["manager_employee_id"])
    _create_index_once("ix_hr_employees_archived_by_id", "hr_employees", ["archived_by_id"])
    _create_index_once("ix_hr_employees_status", "hr_employees", ["status"])


def _add_core_hr_scope_extensions() -> None:
    for table_name in (
        "hr_shift_templates",
        "hr_shift_assignments",
        "hr_attendance",
        "hr_leave_requests",
        "hr_leave_balances",
        "hr_payroll_periods",
        "hr_payroll_lines",
    ):
        _add_scope_columns(table_name)


def _add_payroll_ke_extensions() -> None:
    for table_name in ("ke_payroll_profiles", "ke_payroll_lines"):
        _add_scope_columns(table_name)

    _add_scope_columns("ke_payroll_runs")
    _add_column_once("ke_payroll_runs", sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_once("ke_payroll_runs", sa.Column("locked_by_id", UUID, nullable=True))
    _create_fk_once("fk_ke_payroll_runs_locked_by_id", "ke_payroll_runs", "users", ["locked_by_id"], ["id"], ondelete="SET NULL")
    _create_index_once("ix_ke_payroll_runs_locked_by_id", "ke_payroll_runs", ["locked_by_id"])
    _create_index_once("ix_ke_payroll_runs_status", "ke_payroll_runs", ["status"])

    _add_scope_columns("ke_payslips", include_cost_center=False)
    _add_column_once("ke_payslips", sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_once("ke_payslips", sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_once("ke_payslips", sa.Column("sent_by_id", UUID, nullable=True))
    _create_fk_once("fk_ke_payslips_sent_by_id", "ke_payslips", "users", ["sent_by_id"], ["id"], ondelete="SET NULL")
    _create_index_once("ix_ke_payslips_sent_by_id", "ke_payslips", ["sent_by_id"])

    for table_name in ("ke_tax_bands", "ke_statutory_rates", "ke_nhif_tiers"):
        if context.is_offline_mode() or _has_table(table_name):
            _add_column_once(table_name, sa.Column("effective_from", sa.Date(), nullable=True))
            _add_column_once(table_name, sa.Column("effective_to", sa.Date(), nullable=True))
            _create_index_once(f"ix_{table_name}_effective_from", table_name, ["effective_from"])
            _create_index_once(f"ix_{table_name}_effective_to", table_name, ["effective_to"])

    if context.is_offline_mode() or _has_table("ke_shif_tiers"):
        _add_column_once("ke_shif_tiers", sa.Column("effective_to", sa.Date(), nullable=True))
        _create_index_once("ix_ke_shif_tiers_effective_to", "ke_shif_tiers", ["effective_to"])


def _add_timesheet_extensions() -> None:
    if not context.is_offline_mode() and not _has_table("timesheet_headers"):
        return

    _add_column_once("timesheet_headers", sa.Column("hr_employee_id", UUID, nullable=True))
    _add_column_once("timesheet_headers", sa.Column("company_id", UUID, nullable=True))
    _add_column_once("timesheet_headers", sa.Column("branch_id", UUID, nullable=True))
    _add_column_once("timesheet_headers", sa.Column("manager_employee_id", UUID, nullable=True))
    _add_column_once("timesheet_headers", sa.Column("payroll_run_id", UUID, nullable=True))
    _add_column_once("timesheet_headers", sa.Column("finalized_by_id", UUID, nullable=True))
    _create_fk_once("fk_timesheet_headers_hr_employee_id", "timesheet_headers", "hr_employees", ["hr_employee_id"], ["id"], ondelete="SET NULL")
    _create_fk_once("fk_timesheet_headers_company_id", "timesheet_headers", "companies", ["company_id"], ["id"], ondelete="SET NULL")
    _create_fk_once("fk_timesheet_headers_branch_id", "timesheet_headers", "branches", ["branch_id"], ["id"], ondelete="SET NULL")
    _create_fk_once("fk_timesheet_headers_manager_employee_id", "timesheet_headers", "hr_employees", ["manager_employee_id"], ["id"], ondelete="SET NULL")
    _create_fk_once("fk_timesheet_headers_payroll_run_id", "timesheet_headers", "ke_payroll_runs", ["payroll_run_id"], ["id"], ondelete="SET NULL")
    _create_fk_once("fk_timesheet_headers_finalized_by_id", "timesheet_headers", "users", ["finalized_by_id"], ["id"], ondelete="SET NULL")
    for column_name in ("hr_employee_id", "company_id", "branch_id", "manager_employee_id", "payroll_run_id", "finalized_by_id"):
        _create_index_once(f"ix_timesheet_headers_{column_name}", "timesheet_headers", [column_name])


def _add_ess_extensions() -> None:
    if context.is_offline_mode() or _has_table("ess_accounts"):
        _add_column_once("ess_accounts", sa.Column("user_id", UUID, nullable=True))
        _add_column_once("ess_accounts", sa.Column("hr_employee_id", UUID, nullable=True))
        _create_fk_once("fk_ess_accounts_user_id", "ess_accounts", "users", ["user_id"], ["id"], ondelete="SET NULL")
        _create_fk_once("fk_ess_accounts_hr_employee_id", "ess_accounts", "hr_employees", ["hr_employee_id"], ["id"], ondelete="SET NULL")
        _create_index_once("ix_ess_accounts_user_id", "ess_accounts", ["user_id"])
        _create_index_once("ix_ess_accounts_hr_employee_id", "ess_accounts", ["hr_employee_id"])

    if context.is_offline_mode() or _has_table("ess_employee_profiles"):
        _add_column_once("ess_employee_profiles", sa.Column("hr_employee_id", UUID, nullable=True))
        _create_fk_once("fk_ess_employee_profiles_hr_employee_id", "ess_employee_profiles", "hr_employees", ["hr_employee_id"], ["id"], ondelete="SET NULL")
        _create_index_once("ix_ess_employee_profiles_hr_employee_id", "ess_employee_profiles", ["hr_employee_id"])


def upgrade() -> None:
    _create_core_hr_tables_if_missing()
    _add_employee_master_extensions()
    _add_core_hr_scope_extensions()
    _add_payroll_ke_extensions()
    _add_timesheet_extensions()
    _add_ess_extensions()


def downgrade() -> None:
    for table_name, columns in {
        "ess_employee_profiles": ("hr_employee_id",),
        "ess_accounts": ("hr_employee_id", "user_id"),
        "timesheet_headers": (
            "finalized_by_id",
            "payroll_run_id",
            "manager_employee_id",
            "branch_id",
            "company_id",
            "hr_employee_id",
        ),
        "ke_shif_tiers": ("effective_to",),
        "ke_nhif_tiers": ("effective_to", "effective_from"),
        "ke_statutory_rates": ("effective_to", "effective_from"),
        "ke_tax_bands": ("effective_to", "effective_from"),
        "ke_payslips": ("sent_by_id", "sent_at", "viewed_at", "department_id", "branch_id", "company_id"),
        "ke_payroll_runs": (
            "locked_by_id",
            "locked_at",
            "cost_center_id",
            "department_id",
            "branch_id",
            "company_id",
        ),
        "ke_payroll_lines": ("cost_center_id", "department_id", "branch_id", "company_id"),
        "ke_payroll_profiles": ("cost_center_id", "department_id", "branch_id", "company_id"),
        "hr_payroll_lines": ("cost_center_id", "department_id", "branch_id", "company_id"),
        "hr_payroll_periods": ("cost_center_id", "department_id", "branch_id", "company_id"),
        "hr_leave_balances": ("cost_center_id", "department_id", "branch_id", "company_id"),
        "hr_leave_requests": ("cost_center_id", "department_id", "branch_id", "company_id"),
        "hr_attendance": ("cost_center_id", "department_id", "branch_id", "company_id"),
        "hr_shift_assignments": ("cost_center_id", "department_id", "branch_id", "company_id"),
        "hr_shift_templates": ("cost_center_id", "department_id", "branch_id", "company_id"),
        "hr_employees": (
            "archived_by_id",
            "archived_at",
            "terminated_at",
            "manager_employee_id",
            "cost_center_id",
            "department_id",
            "branch_id",
            "company_id",
        ),
    }.items():
        if not _has_table(table_name):
            continue
        for column_name in columns:
            _drop_column_if_exists(table_name, column_name)
