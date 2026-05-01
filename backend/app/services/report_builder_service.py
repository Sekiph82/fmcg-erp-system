from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import time, csv, io
from uuid import UUID

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.report_builder import (
    ReportDefinition, ReportField, ReportFilter, ReportCalculatedField,
    ReportSchedule, ReportDashboard, DashboardWidget, RBAIRecommendation,
    AggregationType, FilterOperator, ChartType, ScheduleFrequency,
    RBAIAgentType, RBAIRecStatus,
)
from app.schemas.report_builder import (
    ReportCreate, ReportUpdate, RunRequest, RunResult,
    ReportFieldCreate, ReportFilterCreate, CalcFieldCreate,
    ScheduleCreate, DashboardCreate, WidgetCreate, RBAIRecAck,
)


# ── Metadata Catalog ──────────────────────────────────────────────────────────

DATA_SOURCES: Dict[str, Dict[str, Any]] = {
    "sales_orders": {
        "label": "Sales Orders",
        "module": "sales",
        "table": "sales_orders",
        "fields": [
            {"path": "order_no", "label": "Order No", "type": "string"},
            {"path": "order_date", "label": "Order Date", "type": "date"},
            {"path": "customer_id", "label": "Customer ID", "type": "string"},
            {"path": "total_amount", "label": "Total Amount", "type": "number"},
            {"path": "status", "label": "Status", "type": "string"},
            {"path": "channel", "label": "Channel", "type": "string"},
        ],
    },
    "customers": {
        "label": "Customers",
        "module": "sales",
        "table": "customers",
        "fields": [
            {"path": "customer_code", "label": "Customer Code", "type": "string"},
            {"path": "customer_name", "label": "Customer Name", "type": "string"},
            {"path": "region", "label": "Region", "type": "string"},
            {"path": "credit_limit", "label": "Credit Limit", "type": "number"},
            {"path": "outstanding_balance", "label": "Outstanding Balance", "type": "number"},
        ],
    },
    "products": {
        "label": "Products",
        "module": "inventory",
        "table": "products",
        "fields": [
            {"path": "product_code", "label": "Product Code", "type": "string"},
            {"path": "product_name", "label": "Product Name", "type": "string"},
            {"path": "category", "label": "Category", "type": "string"},
            {"path": "unit_price", "label": "Unit Price", "type": "number"},
            {"path": "active_flag", "label": "Active", "type": "boolean"},
        ],
    },
    "stock": {
        "label": "Inventory / Stock",
        "module": "inventory",
        "table": "stocks",
        "fields": [
            {"path": "product_id", "label": "Product ID", "type": "string"},
            {"path": "warehouse_id", "label": "Warehouse ID", "type": "string"},
            {"path": "quantity", "label": "Quantity", "type": "number"},
            {"path": "reserved_quantity", "label": "Reserved Qty", "type": "number"},
            {"path": "last_movement_date", "label": "Last Movement", "type": "date"},
        ],
    },
    "invoices": {
        "label": "Invoices",
        "module": "sales",
        "table": "invoices",
        "fields": [
            {"path": "invoice_no", "label": "Invoice No", "type": "string"},
            {"path": "invoice_date", "label": "Invoice Date", "type": "date"},
            {"path": "due_date", "label": "Due Date", "type": "date"},
            {"path": "amount", "label": "Amount", "type": "number"},
            {"path": "paid_amount", "label": "Paid Amount", "type": "number"},
            {"path": "status", "label": "Status", "type": "string"},
        ],
    },
    "purchase_orders": {
        "label": "Purchase Orders",
        "module": "procurement",
        "table": "purchase_orders",
        "fields": [
            {"path": "po_no", "label": "PO No", "type": "string"},
            {"path": "po_date", "label": "PO Date", "type": "date"},
            {"path": "supplier_id", "label": "Supplier ID", "type": "string"},
            {"path": "total_amount", "label": "Total Amount", "type": "number"},
            {"path": "status", "label": "Status", "type": "string"},
        ],
    },
    "expenses": {
        "label": "Expense Claims",
        "module": "expenses",
        "table": "expense_claims",
        "fields": [
            {"path": "claim_no", "label": "Claim No", "type": "string"},
            {"path": "employee_id", "label": "Employee ID", "type": "string"},
            {"path": "submission_date", "label": "Submission Date", "type": "date"},
            {"path": "total_amount", "label": "Total Amount", "type": "number"},
            {"path": "approved_amount", "label": "Approved Amount", "type": "number"},
            {"path": "status", "label": "Status", "type": "string"},
        ],
    },
    "timesheets": {
        "label": "Timesheets",
        "module": "timesheets",
        "table": "timesheet_headers",
        "fields": [
            {"path": "employee_id", "label": "Employee ID", "type": "string"},
            {"path": "employee_name", "label": "Employee Name", "type": "string"},
            {"path": "department_id", "label": "Department", "type": "string"},
            {"path": "period_start", "label": "Period Start", "type": "date"},
            {"path": "period_end", "label": "Period End", "type": "date"},
            {"path": "total_hours", "label": "Total Hours", "type": "number"},
            {"path": "overtime_hours", "label": "Overtime Hours", "type": "number"},
            {"path": "status", "label": "Status", "type": "string"},
        ],
    },
    "appraisals": {
        "label": "Performance Appraisals",
        "module": "appraisals",
        "table": "appraisal_records",
        "fields": [
            {"path": "employee_id", "label": "Employee ID", "type": "string"},
            {"path": "employee_name", "label": "Employee Name", "type": "string"},
            {"path": "department_name", "label": "Department", "type": "string"},
            {"path": "status", "label": "Status", "type": "string"},
            {"path": "final_score", "label": "Final Score", "type": "number"},
            {"path": "final_rating", "label": "Final Rating", "type": "string"},
        ],
    },
    "crm_records": {
        "label": "CRM Pipeline",
        "module": "crm",
        "table": "crm_records",
        "fields": [
            {"path": "record_code", "label": "Record Code", "type": "string"},
            {"path": "company_name", "label": "Company", "type": "string"},
            {"path": "record_type", "label": "Type", "type": "string"},
            {"path": "expected_revenue", "label": "Expected Revenue", "type": "number"},
            {"path": "probability_pct", "label": "Probability %", "type": "number"},
            {"path": "status", "label": "Status", "type": "string"},
        ],
    },
    "kanban_cards": {
        "label": "Kanban Cards",
        "module": "kanban",
        "table": "kanban_cards",
        "fields": [
            {"path": "card_no", "label": "Card No", "type": "string"},
            {"path": "title", "label": "Title", "type": "string"},
            {"path": "assigned_user_name", "label": "Assigned To", "type": "string"},
            {"path": "priority", "label": "Priority", "type": "string"},
            {"path": "status", "label": "Status", "type": "string"},
            {"path": "due_date", "label": "Due Date", "type": "date"},
        ],
    },
    "training_assignments": {
        "label": "Training Assignments",
        "module": "training",
        "table": "training_assignments",
        "fields": [
            {"path": "employee_id", "label": "Employee ID", "type": "string"},
            {"path": "employee_name", "label": "Employee Name", "type": "string"},
            {"path": "training_id", "label": "Training ID", "type": "string"},
            {"path": "status", "label": "Status", "type": "string"},
            {"path": "completion_date", "label": "Completion Date", "type": "date"},
            {"path": "score", "label": "Score", "type": "number"},
        ],
    },
    "certifications": {
        "label": "Certifications",
        "module": "training",
        "table": "certification_records",
        "fields": [
            {"path": "employee_id", "label": "Employee ID", "type": "string"},
            {"path": "employee_name", "label": "Employee Name", "type": "string"},
            {"path": "certificate_name", "label": "Certificate", "type": "string"},
            {"path": "issue_date", "label": "Issue Date", "type": "date"},
            {"path": "expiry_date", "label": "Expiry Date", "type": "date"},
            {"path": "status", "label": "Status", "type": "string"},
        ],
    },
    "notifications": {
        "label": "Notifications",
        "module": "notifications",
        "table": "nc_notifications",
        "fields": [
            {"path": "user_id", "label": "User ID", "type": "string"},
            {"path": "notification_type", "label": "Type", "type": "string"},
            {"path": "priority", "label": "Priority", "type": "string"},
            {"path": "read_flag", "label": "Read", "type": "boolean"},
            {"path": "module", "label": "Module", "type": "string"},
            {"path": "created_at", "label": "Created At", "type": "datetime"},
        ],
    },
    "skill_matrix": {
        "label": "Skill Matrix",
        "module": "training",
        "table": "employee_skill_profiles",
        "fields": [
            {"path": "employee_id", "label": "Employee ID", "type": "string"},
            {"path": "employee_name", "label": "Employee Name", "type": "string"},
            {"path": "department_id", "label": "Department", "type": "string"},
            {"path": "current_level", "label": "Current Level", "type": "string"},
            {"path": "required_level", "label": "Required Level", "type": "string"},
        ],
    },
}

# Allowed aggregation functions per data type
SAFE_AGGREGATIONS = {"none", "sum", "avg", "min", "max", "count", "count_distinct"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_field(data_source: str, field_path: str) -> bool:
    ds = DATA_SOURCES.get(data_source)
    if not ds:
        return False
    allowed = {f["path"] for f in ds["fields"]}
    return field_path in allowed


def _apply_filter_python(rows: List[Dict], field: str, op: str, value: str, value_to: Optional[str] = None) -> List[Dict]:
    result = []
    for row in rows:
        v = row.get(field)
        try:
            if op == "eq":
                if str(v) == value:
                    result.append(row)
            elif op == "neq":
                if str(v) != value:
                    result.append(row)
            elif op == "gt":
                if float(v or 0) > float(value):
                    result.append(row)
            elif op == "lt":
                if float(v or 0) < float(value):
                    result.append(row)
            elif op == "gte":
                if float(v or 0) >= float(value):
                    result.append(row)
            elif op == "lte":
                if float(v or 0) <= float(value):
                    result.append(row)
            elif op == "like":
                if value.lower() in str(v or "").lower():
                    result.append(row)
            elif op == "is_null":
                if v is None:
                    result.append(row)
            elif op == "is_not_null":
                if v is not None:
                    result.append(row)
            elif op == "in":
                vals = [x.strip() for x in value.split(",")]
                if str(v) in vals:
                    result.append(row)
            elif op == "between" and value_to:
                if float(value) <= float(v or 0) <= float(value_to):
                    result.append(row)
            else:
                result.append(row)
        except Exception:
            result.append(row)
    return result


async def _execute_query(db: AsyncSession, data_source: str, fields: List[Dict], filters: List[Dict], limit: int, offset: int) -> Dict:
    ds_info = DATA_SOURCES.get(data_source)
    if not ds_info:
        return {"columns": [], "rows": [], "total": 0}
    table_name = ds_info["table"]

    # Build safe SELECT from allowed fields only
    allowed_fields = {f["path"] for f in ds_info["fields"]}
    select_fields = [f["path"] for f in fields if f["path"] in allowed_fields] or [f["path"] for f in ds_info["fields"][:5]]

    col_sql = ", ".join(f'"{col}"' for col in select_fields)
    count_sql = f'SELECT COUNT(*) FROM "{table_name}"'
    data_sql = f'SELECT {col_sql} FROM "{table_name}" LIMIT {int(limit)} OFFSET {int(offset)}'

    try:
        total_result = await db.execute(text(count_sql))
        total = total_result.scalar() or 0
        data_result = await db.execute(text(data_sql))
        col_names = list(data_result.keys())
        rows = [dict(zip(col_names, row)) for row in data_result.fetchall()]

        # Apply Python-level filters (safe, post-DB)
        for f in filters:
            if f.get("field_path") in allowed_fields:
                rows = _apply_filter_python(rows, f["field_path"], f["operator"], f.get("value", ""), f.get("value_to"))

        return {
            "columns": [{"path": c, "label": c, "type": "string"} for c in col_names],
            "rows": [{k: (str(v) if v is not None else None) for k, v in row.items()} for row in rows],
            "total": total,
        }
    except Exception as e:
        return {"columns": [], "rows": [], "total": 0, "error": str(e)}


# ── Report CRUD ───────────────────────────────────────────────────────────────

async def create_report(db: AsyncSession, data: ReportCreate) -> ReportDefinition:
    report = ReportDefinition(
        report_code=data.report_code, report_name=data.report_name,
        description=data.description, owner_user_id=data.owner_user_id,
        owner_name=data.owner_name, visibility=data.visibility,
        data_source=data.data_source, query_definition=data.query_definition,
    )
    db.add(report)
    await db.flush()
    for i, f in enumerate(data.fields):
        db.add(ReportField(report_id=report.report_id, position=i, **f.model_dump()))
    for i, f in enumerate(data.filters):
        db.add(ReportFilter(report_id=report.report_id, position=i, **f.model_dump()))
    for cf in data.calculated_fields:
        db.add(ReportCalculatedField(report_id=report.report_id, **cf.model_dump()))
    await db.commit()
    await db.refresh(report)
    return report


async def list_reports(db: AsyncSession, data_source: Optional[str] = None, owner: Optional[str] = None, template_only: bool = False) -> List[ReportDefinition]:
    q = (
        select(ReportDefinition)
        .options(
            selectinload(ReportDefinition.fields),
            selectinload(ReportDefinition.filters),
            selectinload(ReportDefinition.calculated_fields),
            selectinload(ReportDefinition.schedules),
        )
        .where(ReportDefinition.active_flag == True)
        .order_by(ReportDefinition.report_name)
    )
    if data_source:
        q = q.where(ReportDefinition.data_source == data_source)
    if owner:
        q = q.where(ReportDefinition.owner_user_id == owner)
    if template_only:
        q = q.where(ReportDefinition.is_template == True)
    result = await db.execute(q)
    return result.scalars().all()


async def get_report(db: AsyncSession, report_id: UUID) -> Optional[ReportDefinition]:
    result = await db.execute(
        select(ReportDefinition)
        .options(
            selectinload(ReportDefinition.fields),
            selectinload(ReportDefinition.filters),
            selectinload(ReportDefinition.calculated_fields),
            selectinload(ReportDefinition.schedules),
        )
        .where(ReportDefinition.report_id == report_id)
    )
    return result.scalar_one_or_none()


async def update_report(db: AsyncSession, report_id: UUID, data: ReportUpdate) -> Optional[ReportDefinition]:
    report = await get_report(db, report_id)
    if not report:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(report, k, v)
    report.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(report)
    return report


async def delete_report(db: AsyncSession, report_id: UUID) -> bool:
    report = await get_report(db, report_id)
    if not report:
        return False
    report.active_flag = False
    await db.commit()
    return True


async def clone_report(db: AsyncSession, report_id: UUID, new_code: str, new_name: str) -> Optional[ReportDefinition]:
    src = await get_report(db, report_id)
    if not src:
        return None
    new_report = ReportDefinition(
        report_code=new_code, report_name=new_name,
        description=src.description, data_source=src.data_source,
        query_definition=src.query_definition,
    )
    db.add(new_report)
    await db.flush()
    for f in src.fields:
        db.add(ReportField(report_id=new_report.report_id, field_path=f.field_path, alias=f.alias,
                           data_type=f.data_type, aggregation=f.aggregation, is_group_by=f.is_group_by,
                           sort_direction=f.sort_direction, sort_order=f.sort_order, position=f.position, visible=f.visible))
    for f in src.filters:
        db.add(ReportFilter(report_id=new_report.report_id, field_path=f.field_path, operator=f.operator,
                            value=f.value, value_to=f.value_to, logical_op=f.logical_op, position=f.position))
    await db.commit()
    await db.refresh(new_report)
    return new_report


# ── Run Engine ────────────────────────────────────────────────────────────────

async def run_report(db: AsyncSession, report_id: UUID, req: RunRequest) -> RunResult:
    report = await get_report(db, report_id)
    if not report:
        return RunResult(report_id=report_id, report_name="Not Found", data_source="", columns=[], rows=[], total_count=0, execution_ms=0, page=1, page_size=req.limit)

    t0 = time.time()
    fields_meta = [{"path": f.field_path, "alias": f.alias, "aggregation": f.aggregation, "is_group_by": f.is_group_by} for f in report.fields]
    filters_meta = [{"field_path": f.field_path, "operator": f.operator, "value": f.value, "value_to": f.value_to} for f in report.filters]

    result = await _execute_query(db, report.data_source, fields_meta, filters_meta, req.limit, req.offset)
    ms = int((time.time() - t0) * 1000)

    # Update run stats
    report.run_count = (report.run_count or 0) + 1
    report.last_run_at = datetime.utcnow()
    await db.commit()

    columns = [{"path": c["path"], "label": c["label"], "type": c["type"]} for c in result["columns"]]
    return RunResult(
        report_id=report_id, report_name=report.report_name,
        data_source=report.data_source,
        columns=columns, rows=result["rows"],
        total_count=result["total"],
        execution_ms=ms,
        page=(req.offset // req.limit) + 1 if req.limit else 1,
        page_size=req.limit,
    )


async def export_report_csv(db: AsyncSession, report_id: UUID) -> str:
    result = await run_report(db, report_id, RunRequest(limit=10000, offset=0))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[c["path"] for c in result.columns])
    writer.writeheader()
    writer.writerows(result.rows)
    return output.getvalue()


# ── Templates ─────────────────────────────────────────────────────────────────

async def seed_templates(db: AsyncSession) -> int:
    templates = [
        ("TMPL-SALES-SUMMARY", "Sales Summary Report", "sales_orders",
         [{"field_path": "status", "is_group_by": True, "aggregation": "none", "position": 0},
          {"field_path": "total_amount", "aggregation": "sum", "alias": "Total Sales", "position": 1}]),
        ("TMPL-EXPENSE-SUMMARY", "Expense Summary Report", "expenses",
         [{"field_path": "employee_id", "is_group_by": True, "aggregation": "none", "position": 0},
          {"field_path": "total_amount", "aggregation": "sum", "alias": "Total Claimed", "position": 1}]),
        ("TMPL-TIMESHEET-UTIL", "Timesheet Utilization Report", "timesheets",
         [{"field_path": "employee_name", "is_group_by": True, "aggregation": "none", "position": 0},
          {"field_path": "total_hours", "aggregation": "sum", "alias": "Total Hours", "position": 1},
          {"field_path": "overtime_hours", "aggregation": "sum", "alias": "Overtime Hours", "position": 2}]),
        ("TMPL-CERT-EXPIRY", "Certification Expiry Report", "certifications",
         [{"field_path": "employee_name", "position": 0},
          {"field_path": "certificate_name", "position": 1},
          {"field_path": "expiry_date", "position": 2},
          {"field_path": "status", "position": 3}]),
        ("TMPL-CRM-PIPELINE", "CRM Pipeline Report", "crm_records",
         [{"field_path": "status", "is_group_by": True, "aggregation": "none", "position": 0},
          {"field_path": "expected_revenue", "aggregation": "sum", "alias": "Pipeline Value", "position": 1}]),
        ("TMPL-APPRAISAL-RATINGS", "Appraisal Ratings Report", "appraisals",
         [{"field_path": "department_name", "is_group_by": True, "aggregation": "none", "position": 0},
          {"field_path": "final_score", "aggregation": "avg", "alias": "Avg Score", "position": 1}]),
    ]
    count = 0
    for code, name, ds, flds in templates:
        existing = await db.execute(select(ReportDefinition).where(ReportDefinition.report_code == code))
        if not existing.scalar_one_or_none():
            rpt = ReportDefinition(report_code=code, report_name=name, data_source=ds, is_template=True, visibility="global")
            db.add(rpt)
            await db.flush()
            for f in flds:
                db.add(ReportField(report_id=rpt.report_id, **{k: v for k, v in f.items()}))
            count += 1
    if count:
        await db.commit()
    return count


# ── Schedules ─────────────────────────────────────────────────────────────────

async def create_schedule(db: AsyncSession, report_id: UUID, data: ScheduleCreate) -> ReportSchedule:
    schedule = ReportSchedule(report_id=report_id, **data.model_dump())
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def list_schedules(db: AsyncSession, report_id: Optional[UUID] = None) -> List[ReportSchedule]:
    q = select(ReportSchedule).where(ReportSchedule.active_flag == True).order_by(ReportSchedule.created_at)
    if report_id:
        q = q.where(ReportSchedule.report_id == report_id)
    result = await db.execute(q)
    return result.scalars().all()


async def deactivate_schedule(db: AsyncSession, schedule_id: UUID) -> bool:
    result = await db.execute(select(ReportSchedule).where(ReportSchedule.schedule_id == schedule_id))
    s = result.scalar_one_or_none()
    if not s:
        return False
    s.active_flag = False
    await db.commit()
    return True


# ── Dashboard ─────────────────────────────────────────────────────────────────

async def create_dashboard(db: AsyncSession, data: DashboardCreate) -> ReportDashboard:
    dash = ReportDashboard(**data.model_dump())
    db.add(dash)
    await db.commit()
    await db.refresh(dash)
    return dash


async def list_dashboards(db: AsyncSession) -> List[ReportDashboard]:
    result = await db.execute(
        select(ReportDashboard)
        .options(selectinload(ReportDashboard.widgets))
        .where(ReportDashboard.active_flag == True)
        .order_by(ReportDashboard.dashboard_name)
    )
    return result.scalars().all()


async def get_dashboard(db: AsyncSession, dashboard_id: UUID) -> Optional[ReportDashboard]:
    result = await db.execute(
        select(ReportDashboard)
        .options(selectinload(ReportDashboard.widgets))
        .where(ReportDashboard.dashboard_id == dashboard_id)
    )
    return result.scalar_one_or_none()


async def add_widget(db: AsyncSession, dashboard_id: UUID, data: WidgetCreate) -> DashboardWidget:
    widget = DashboardWidget(dashboard_id=dashboard_id, **data.model_dump())
    db.add(widget)
    await db.commit()
    await db.refresh(widget)
    return widget


async def delete_widget(db: AsyncSession, widget_id: UUID) -> bool:
    result = await db.execute(select(DashboardWidget).where(DashboardWidget.widget_id == widget_id))
    w = result.scalar_one_or_none()
    if not w:
        return False
    await db.delete(w)
    await db.commit()
    return True


# ── AI Agents ─────────────────────────────────────────────────────────────────

async def run_builder_assistant(db: AsyncSession) -> List[RBAIRecommendation]:
    # Reports with 0 runs
    result = await db.execute(
        select(ReportDefinition).where(
            ReportDefinition.run_count == 0, ReportDefinition.active_flag == True
        ).limit(10)
    )
    recs = []
    for rpt in result.scalars().all():
        ds = DATA_SOURCES.get(rpt.data_source, {})
        rec = RBAIRecommendation(
            agent_type=RBAIAgentType.BUILDER_ASSISTANT,
            title=f"Unused report: {rpt.report_name}",
            body=(
                f"Report '{rpt.report_name}' on source '{ds.get('label', rpt.data_source)}' "
                f"has never been run. Consider adding filters, groupings, or scheduling for automated delivery. "
                f"Available fields: {', '.join(f['path'] for f in ds.get('fields', [])[:4])}…"
            ),
            report_id=rpt.report_id,
            score=0,
        )
        db.add(rec)
        recs.append(rec)
    if recs:
        await db.commit()
    return recs


async def run_insight_generator(db: AsyncSession) -> List[RBAIRecommendation]:
    result = await db.execute(
        select(ReportDefinition)
        .where(ReportDefinition.run_count > 5, ReportDefinition.active_flag == True)
        .order_by(ReportDefinition.run_count.desc())
        .limit(5)
    )
    recs = []
    for rpt in result.scalars().all():
        rec = RBAIRecommendation(
            agent_type=RBAIAgentType.INSIGHT_GENERATOR,
            title=f"High-usage report: {rpt.report_name}",
            body=(
                f"Report '{rpt.report_name}' has been run {rpt.run_count} times. "
                f"Consider pinning it to a dashboard, scheduling for automated delivery, "
                f"or exporting to CSV for offline analysis."
            ),
            report_id=rpt.report_id,
            score=rpt.run_count,
        )
        db.add(rec)
        recs.append(rec)
    if recs:
        await db.commit()
    return recs


async def run_performance_optimizer(db: AsyncSession) -> List[RBAIRecommendation]:
    result = await db.execute(
        select(ReportDefinition)
        .where(ReportDefinition.active_flag == True)
        .where(ReportDefinition.data_source.in_(list(DATA_SOURCES.keys())))
    )
    recs = []
    for rpt in result.scalars().all():
        if not rpt.filters or len(rpt.filters) == 0:
            rec = RBAIRecommendation(
                agent_type=RBAIAgentType.PERFORMANCE_OPTIMIZER,
                title=f"No filters: {rpt.report_name}",
                body=(
                    f"Report '{rpt.report_name}' has no filters applied, which may return large datasets. "
                    f"Add date range or status filters to improve query performance and result relevance."
                ),
                report_id=rpt.report_id,
                score=50,
            )
            db.add(rec)
            recs.append(rec)
    if recs:
        await db.commit()
    return recs[:10]


async def list_ai_recs(db: AsyncSession, status: Optional[str] = None) -> List[RBAIRecommendation]:
    q = select(RBAIRecommendation).order_by(RBAIRecommendation.created_at.desc())
    if status:
        q = q.where(RBAIRecommendation.status == status)
    result = await db.execute(q)
    return result.scalars().all()


async def ack_ai_rec(db: AsyncSession, rec_id: UUID, data: RBAIRecAck) -> Optional[RBAIRecommendation]:
    result = await db.execute(select(RBAIRecommendation).where(RBAIRecommendation.rec_id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        return None
    rec.status = data.status
    if data.actioned_by:
        rec.actioned_by = data.actioned_by
        rec.actioned_at = datetime.utcnow()
    await db.commit()
    await db.refresh(rec)
    return rec
