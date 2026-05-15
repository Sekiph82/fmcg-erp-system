from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from app.models.report_builder import (
    ReportVisibility, AggregationType, FilterOperator, LogicalOperator,
    SortDirection, ChartType, ScheduleFrequency, ExportFormat,
    RBAIAgentType, RBAIRecStatus,
)


# ── Field / Filter ────────────────────────────────────────────────────────────

class ReportFieldCreate(BaseModel):
    field_path: str
    alias: Optional[str] = None
    data_type: str = "string"
    aggregation: AggregationType = AggregationType.NONE
    is_group_by: bool = False
    sort_direction: Optional[SortDirection] = None
    sort_order: Optional[int] = None
    position: int = 0
    visible: bool = True


class ReportFieldOut(BaseModel):
    report_field_id: UUID
    report_id: UUID
    field_path: str
    alias: Optional[str]
    data_type: str
    aggregation: AggregationType
    is_group_by: bool
    sort_direction: Optional[SortDirection]
    sort_order: Optional[int]
    position: int
    visible: bool

    class Config:
        from_attributes = True


class ReportFilterCreate(BaseModel):
    field_path: str
    operator: FilterOperator
    value: Optional[str] = None
    value_to: Optional[str] = None
    logical_op: LogicalOperator = LogicalOperator.AND
    position: int = 0


class ReportFilterOut(BaseModel):
    filter_id: UUID
    report_id: UUID
    field_path: str
    operator: FilterOperator
    value: Optional[str]
    value_to: Optional[str]
    logical_op: LogicalOperator
    position: int

    class Config:
        from_attributes = True


class CalcFieldCreate(BaseModel):
    expression: str
    alias: str
    data_type: str = "number"
    description: Optional[str] = None


class CalcFieldOut(BaseModel):
    calc_id: UUID
    report_id: UUID
    expression: str
    alias: str
    data_type: str
    description: Optional[str]

    class Config:
        from_attributes = True


# ── Schedule ──────────────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    frequency: ScheduleFrequency
    run_time: Optional[str] = "08:00"
    recipients: Optional[str] = None
    export_format: ExportFormat = ExportFormat.CSV


class ScheduleOut(BaseModel):
    schedule_id: UUID
    report_id: UUID
    frequency: ScheduleFrequency
    run_time: Optional[str]
    recipients: Optional[str]
    export_format: ExportFormat
    active_flag: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Report ────────────────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    report_code: str
    report_name: str
    description: Optional[str] = None
    owner_user_id: Optional[str] = None
    owner_name: Optional[str] = None
    visibility: ReportVisibility = ReportVisibility.PRIVATE
    data_source: str
    fields: List[ReportFieldCreate] = []
    filters: List[ReportFilterCreate] = []
    calculated_fields: List[CalcFieldCreate] = []
    query_definition: Optional[Dict[str, Any]] = None


class ReportUpdate(BaseModel):
    report_name: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[ReportVisibility] = None
    data_source: Optional[str] = None
    query_definition: Optional[Dict[str, Any]] = None
    active_flag: Optional[bool] = None


class ReportOut(BaseModel):
    report_id: UUID
    report_code: str
    report_name: str
    description: Optional[str]
    owner_user_id: Optional[str]
    owner_name: Optional[str]
    visibility: ReportVisibility
    data_source: str
    query_definition: Optional[Dict[str, Any]]
    active_flag: bool
    is_template: bool
    run_count: int
    last_run_at: Optional[datetime]
    created_at: datetime
    fields: List[ReportFieldOut] = []
    filters: List[ReportFilterOut] = []
    calculated_fields: List[CalcFieldOut] = []
    schedules: List[ScheduleOut] = []

    class Config:
        from_attributes = True


class RunRequest(BaseModel):
    limit: int = 100
    offset: int = 0
    runtime_filters: Optional[Dict[str, str]] = None


class RunResult(BaseModel):
    report_id: UUID
    report_name: str
    data_source: str
    columns: List[Dict[str, str]]
    rows: List[Dict[str, Any]]
    total_count: int
    execution_ms: int
    page: int
    page_size: int


# ── Dashboard ─────────────────────────────────────────────────────────────────

class WidgetCreate(BaseModel):
    report_id: Optional[UUID] = None
    widget_title: Optional[str] = None
    chart_type: ChartType = ChartType.TABLE
    position: int = 0
    width: int = 6
    height: int = 4
    x_axis_field: Optional[str] = None
    y_axis_field: Optional[str] = None
    color_field: Optional[str] = None
    refresh_interval: Optional[int] = None
    config: Optional[Dict[str, Any]] = None


class WidgetOut(BaseModel):
    widget_id: UUID
    dashboard_id: UUID
    report_id: Optional[UUID]
    widget_title: Optional[str]
    chart_type: ChartType
    position: int
    width: int
    height: int
    x_axis_field: Optional[str]
    y_axis_field: Optional[str]
    color_field: Optional[str]
    refresh_interval: Optional[int]
    config: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardCreate(BaseModel):
    dashboard_code: str
    dashboard_name: str
    description: Optional[str] = None
    owner_user_id: Optional[str] = None
    visibility: ReportVisibility = ReportVisibility.TEAM


class DashboardOut(BaseModel):
    dashboard_id: UUID
    dashboard_code: str
    dashboard_name: str
    description: Optional[str]
    owner_user_id: Optional[str]
    visibility: ReportVisibility
    active_flag: bool
    created_at: datetime
    widgets: List[WidgetOut] = []

    class Config:
        from_attributes = True


# ── AI ────────────────────────────────────────────────────────────────────────

class RBAIRecOut(BaseModel):
    rec_id: UUID
    agent_type: RBAIAgentType
    status: RBAIRecStatus
    title: str
    body: str
    report_id: Optional[UUID]
    score: Optional[int]
    actioned_by: Optional[str]
    actioned_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class RBAIRecAck(BaseModel):
    status: RBAIRecStatus
    actioned_by: Optional[str] = None


class ScheduleRunLogRead(BaseModel):
    run_id: UUID
    schedule_id: UUID
    report_id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    row_count: Optional[int] = None
    export_format: Optional[str] = None
    recipients_sent: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


ReportOut.model_rebuild()
DashboardOut.model_rebuild()
