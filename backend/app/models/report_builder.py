from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, Enum,
    UniqueConstraint, ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class ReportVisibility(str, PyEnum):
    PRIVATE = "private"
    TEAM = "team"
    GLOBAL = "global"


class AggregationType(str, PyEnum):
    NONE = "none"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"


class FilterOperator(str, PyEnum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    BETWEEN = "between"
    IN = "in"
    LIKE = "like"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class LogicalOperator(str, PyEnum):
    AND = "and"
    OR = "or"


class SortDirection(str, PyEnum):
    ASC = "asc"
    DESC = "desc"


class ChartType(str, PyEnum):
    TABLE = "table"
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    KPI = "kpi"
    AREA = "area"
    SCATTER = "scatter"


class ScheduleFrequency(str, PyEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ExportFormat(str, PyEnum):
    CSV = "csv"
    XLSX = "xlsx"
    JSON = "json"


class RBAIAgentType(str, PyEnum):
    BUILDER_ASSISTANT = "builder_assistant"
    INSIGHT_GENERATOR = "insight_generator"
    PERFORMANCE_OPTIMIZER = "performance_optimizer"


class RBAIRecStatus(str, PyEnum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"


class ReportDefinition(Base):
    __tablename__ = "rb_report_definitions"

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_code = Column(String(50), unique=True, nullable=False)
    report_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    owner_user_id = Column(String(100), nullable=True)
    owner_name = Column(String(200), nullable=True)
    visibility = Column(Enum(ReportVisibility), default=ReportVisibility.PRIVATE, nullable=False)
    data_source = Column(String(100), nullable=False)
    query_definition = Column(JSONB, nullable=True)
    active_flag = Column(Boolean, default=True)
    is_template = Column(Boolean, default=False)
    run_count = Column(Integer, default=0)
    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fields = relationship("ReportField", back_populates="report", cascade="all, delete-orphan",
                          order_by="ReportField.position")
    filters = relationship("ReportFilter", back_populates="report", cascade="all, delete-orphan",
                           order_by="ReportFilter.position")
    calculated_fields = relationship("ReportCalculatedField", back_populates="report", cascade="all, delete-orphan")
    schedules = relationship("ReportSchedule", back_populates="report", cascade="all, delete-orphan")
    widgets = relationship("DashboardWidget", back_populates="report", lazy="dynamic")


class ReportField(Base):
    __tablename__ = "rb_report_fields"

    report_field_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("rb_report_definitions.report_id", ondelete="CASCADE"), nullable=False)
    field_path = Column(String(200), nullable=False)
    alias = Column(String(200), nullable=True)
    data_type = Column(String(50), default="string")
    aggregation = Column(Enum(AggregationType), default=AggregationType.NONE)
    is_group_by = Column(Boolean, default=False)
    sort_direction = Column(Enum(SortDirection), nullable=True)
    sort_order = Column(Integer, nullable=True)
    position = Column(Integer, default=0)
    visible = Column(Boolean, default=True)

    report = relationship("ReportDefinition", back_populates="fields")


class ReportFilter(Base):
    __tablename__ = "rb_report_filters"

    filter_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("rb_report_definitions.report_id", ondelete="CASCADE"), nullable=False)
    field_path = Column(String(200), nullable=False)
    operator = Column(Enum(FilterOperator), nullable=False)
    value = Column(Text, nullable=True)
    value_to = Column(Text, nullable=True)
    logical_op = Column(Enum(LogicalOperator), default=LogicalOperator.AND)
    position = Column(Integer, default=0)

    report = relationship("ReportDefinition", back_populates="filters")


class ReportCalculatedField(Base):
    __tablename__ = "rb_calculated_fields"

    calc_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("rb_report_definitions.report_id", ondelete="CASCADE"), nullable=False)
    expression = Column(Text, nullable=False)
    alias = Column(String(200), nullable=False)
    data_type = Column(String(50), default="number")
    description = Column(Text, nullable=True)

    report = relationship("ReportDefinition", back_populates="calculated_fields")


class ReportSchedule(Base):
    __tablename__ = "rb_report_schedules"

    schedule_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("rb_report_definitions.report_id", ondelete="CASCADE"), nullable=False)
    frequency = Column(Enum(ScheduleFrequency), nullable=False)
    run_time = Column(String(10), nullable=True)
    recipients = Column(Text, nullable=True)
    export_format = Column(Enum(ExportFormat), default=ExportFormat.CSV)
    active_flag = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("ReportDefinition", back_populates="schedules")
    run_logs = relationship("ScheduleRunLog", back_populates="schedule", cascade="all, delete-orphan",
                            foreign_keys="ScheduleRunLog.schedule_id")


class ReportDashboard(Base):
    __tablename__ = "rb_dashboards"

    dashboard_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_code = Column(String(50), unique=True, nullable=False)
    dashboard_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    owner_user_id = Column(String(100), nullable=True)
    visibility = Column(Enum(ReportVisibility), default=ReportVisibility.TEAM)
    active_flag = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    widgets = relationship("DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan",
                           order_by="DashboardWidget.position")


class DashboardWidget(Base):
    __tablename__ = "rb_dashboard_widgets"

    widget_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_id = Column(UUID(as_uuid=True), ForeignKey("rb_dashboards.dashboard_id", ondelete="CASCADE"), nullable=False)
    report_id = Column(UUID(as_uuid=True), ForeignKey("rb_report_definitions.report_id", ondelete="SET NULL"), nullable=True)
    widget_title = Column(String(200), nullable=True)
    chart_type = Column(Enum(ChartType), default=ChartType.TABLE)
    position = Column(Integer, default=0)
    width = Column(Integer, default=6)
    height = Column(Integer, default=4)
    x_axis_field = Column(String(200), nullable=True)
    y_axis_field = Column(String(200), nullable=True)
    color_field = Column(String(200), nullable=True)
    refresh_interval = Column(Integer, nullable=True)
    config = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    dashboard = relationship("ReportDashboard", back_populates="widgets")
    report = relationship("ReportDefinition", back_populates="widgets", foreign_keys=[report_id])


class RBAIRecommendation(Base):
    __tablename__ = "rb_ai_recommendations"

    rec_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(Enum(RBAIAgentType), nullable=False)
    status = Column(Enum(RBAIRecStatus), default=RBAIRecStatus.PENDING, nullable=False)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    report_id = Column(UUID(as_uuid=True), nullable=True)
    score = Column(Integer, nullable=True)
    actioned_by = Column(String(200), nullable=True)
    actioned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScheduleRunStatus(str, PyEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ScheduleRunLog(Base):
    """Execution history for scheduled report runs."""
    __tablename__ = "rb_schedule_run_log"

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rb_report_schedules.schedule_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rb_report_definitions.report_id", ondelete="CASCADE"),
        nullable=False,
    )
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(ScheduleRunStatus), nullable=False, default=ScheduleRunStatus.RUNNING)
    row_count = Column(Integer, nullable=True)
    export_format = Column(String(10), nullable=True)
    recipients_sent = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    schedule = relationship("ReportSchedule", back_populates="run_logs", foreign_keys=[schedule_id])
    report = relationship("ReportDefinition", foreign_keys=[report_id])


class RLSPolicyScope(str, PyEnum):
    USER = "user"
    ROLE = "role"


class RLSPolicy(Base):
    """Row-Level Security policy — restricts data visible in a report by user/role."""
    __tablename__ = "rb_rls_policies"

    policy_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_name = Column(String(200), nullable=False)
    data_source = Column(String(100), nullable=False)
    scope = Column(Enum(RLSPolicyScope), nullable=False, default=RLSPolicyScope.USER)
    principal = Column(String(200), nullable=False)   # user_id or role name
    filter_field = Column(String(200), nullable=False)
    operator = Column(Enum(FilterOperator), nullable=False, default=FilterOperator.EQ)
    filter_value = Column(Text, nullable=False)
    active_flag = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
