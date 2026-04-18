"""
Utility Alarm & Anomaly Detection — Pydantic v2 Schemas
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ── Alarm Rule schemas ─────────────────────────────────────────────────────────

class AlarmRuleBase(BaseModel):
    rule_code: str
    name: str
    description: Optional[str] = None
    utility_type: str
    device_id: Optional[UUID] = None
    asset_id: Optional[UUID] = None
    alarm_type: Optional[str] = None
    source_module: Optional[str] = None
    alarm_category: str = "GENERAL"
    detection_type: str = "THRESHOLD"
    parameter: str
    operator: str
    threshold_value: float
    threshold_unit: Optional[str] = None
    rolling_window_hours: Optional[int] = None
    delta_pct_threshold: Optional[float] = None
    standard_value: Optional[float] = None
    comparison_asset_id: Optional[UUID] = None
    severity: str = "WARNING"
    cooldown_minutes: int = 15
    evaluation_frequency_min: int = 60
    is_active: bool = True
    notification_emails: Optional[str] = None
    notification_channel: Optional[str] = None
    notes: Optional[str] = None


class AlarmRuleCreate(AlarmRuleBase):
    pass


class AlarmRuleUpdate(BaseModel):
    rule_code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    utility_type: Optional[str] = None
    device_id: Optional[UUID] = None
    asset_id: Optional[UUID] = None
    alarm_type: Optional[str] = None
    source_module: Optional[str] = None
    alarm_category: Optional[str] = None
    detection_type: Optional[str] = None
    parameter: Optional[str] = None
    operator: Optional[str] = None
    threshold_value: Optional[float] = None
    threshold_unit: Optional[str] = None
    rolling_window_hours: Optional[int] = None
    delta_pct_threshold: Optional[float] = None
    standard_value: Optional[float] = None
    comparison_asset_id: Optional[UUID] = None
    severity: Optional[str] = None
    cooldown_minutes: Optional[int] = None
    evaluation_frequency_min: Optional[int] = None
    is_active: Optional[bool] = None
    notification_emails: Optional[str] = None
    notification_channel: Optional[str] = None
    notes: Optional[str] = None


class AlarmRuleRead(AlarmRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_name: Optional[str] = None
    device_name: Optional[str] = None
    asset_name: Optional[str] = None
    event_count: int = 0


# ── Alarm Event schemas ────────────────────────────────────────────────────────

class AlarmEventBase(BaseModel):
    rule_id: UUID
    device_id: Optional[UUID] = None
    asset_id: Optional[UUID] = None
    triggered_at: datetime
    status: str
    severity: str
    alarm_type: Optional[str] = None
    source_module: Optional[str] = None
    detection_type: Optional[str] = None
    parameter: Optional[str] = None
    triggered_value: Optional[float] = None
    expected_value: Optional[float] = None
    threshold_value: Optional[float] = None
    threshold_unit: Optional[str] = None
    deviation_pct: Optional[float] = None
    notes: Optional[str] = None


class AlarmEventRead(AlarmEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_no: str
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    created_at: datetime
    rule_code: Optional[str] = None
    rule_name: Optional[str] = None
    device_name: Optional[str] = None
    asset_name: Optional[str] = None
    assigned_to_name: Optional[str] = None
    acknowledged_by_name: Optional[str] = None
    resolved_by_name: Optional[str] = None


# ── Action schemas ─────────────────────────────────────────────────────────────

class AlarmEventAcknowledge(BaseModel):
    notes: Optional[str] = None


class AlarmEventAssign(BaseModel):
    assigned_to_id: UUID


class AlarmEventResolve(BaseModel):
    root_cause: str
    corrective_action: str
    notes: Optional[str] = None


# ── Summary schema ─────────────────────────────────────────────────────────────

class AlarmSummary(BaseModel):
    total_active: int
    total_acknowledged: int
    critical_count: int
    alert_count: int
    warning_count: int
    info_count: int
    by_utility_type: Dict[str, int]
    by_category: Dict[str, int]


# ── Template schema ────────────────────────────────────────────────────────────

class AlarmRuleTemplate(BaseModel):
    template_key: str
    name: str
    description: str
    alarm_type: str
    source_module: str
    utility_type: str
    alarm_category: str
    detection_type: str
    parameter: str
    operator: str
    threshold_value: float
    threshold_unit: str
    severity: str
    rolling_window_hours: Optional[int] = None
    delta_pct_threshold: Optional[float] = None
    standard_value: Optional[float] = None
