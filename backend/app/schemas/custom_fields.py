from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel
from app.models.custom_fields import (
    FieldType, EntityType, ValidationRuleType,
    CFAIAgentType, CFAIRecStatus,
)


class FieldOptionOut(BaseModel):
    option_id: str
    custom_field_id: str
    option_value: str
    option_label: str
    display_order: int
    active_flag: bool
    model_config = {"from_attributes": True}


class FieldOptionCreate(BaseModel):
    option_value: str
    option_label: str
    display_order: int = 0
    active_flag: bool = True


class ValidationRuleOut(BaseModel):
    validation_rule_id: str
    custom_field_id: str
    rule_type: ValidationRuleType
    rule_value: Optional[str] = None
    error_message: Optional[str] = None
    active_flag: bool
    model_config = {"from_attributes": True}


class ValidationRuleCreate(BaseModel):
    rule_type: ValidationRuleType
    rule_value: Optional[str] = None
    error_message: Optional[str] = None
    active_flag: bool = True


class CustomFieldOut(BaseModel):
    custom_field_id: str
    field_code: str
    field_label: str
    entity_type: EntityType
    field_type: FieldType
    help_text: Optional[str] = None
    placeholder: Optional[str] = None
    default_value: Optional[str] = None
    required_flag: bool
    unique_flag: bool
    searchable_flag: bool
    filterable_flag: bool
    reportable_flag: bool
    importable_flag: bool
    exportable_flag: bool
    sensitive_flag: bool
    active_flag: bool
    display_order: int
    section_label: Optional[str] = None
    reference_entity: Optional[str] = None
    formula: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    options: List[FieldOptionOut] = []
    validation_rules: List[ValidationRuleOut] = []
    model_config = {"from_attributes": True}


class CustomFieldCreate(BaseModel):
    field_code: str
    field_label: str
    entity_type: EntityType
    field_type: FieldType
    help_text: Optional[str] = None
    placeholder: Optional[str] = None
    default_value: Optional[str] = None
    required_flag: bool = False
    unique_flag: bool = False
    searchable_flag: bool = True
    filterable_flag: bool = True
    reportable_flag: bool = True
    importable_flag: bool = True
    exportable_flag: bool = True
    sensitive_flag: bool = False
    active_flag: bool = True
    display_order: int = 0
    section_label: Optional[str] = None
    reference_entity: Optional[str] = None
    formula: Optional[str] = None
    created_by: Optional[str] = None
    notes: Optional[str] = None
    options: List[FieldOptionCreate] = []
    validation_rules: List[ValidationRuleCreate] = []


class CustomFieldUpdate(BaseModel):
    field_label: Optional[str] = None
    help_text: Optional[str] = None
    placeholder: Optional[str] = None
    default_value: Optional[str] = None
    required_flag: Optional[bool] = None
    unique_flag: Optional[bool] = None
    searchable_flag: Optional[bool] = None
    filterable_flag: Optional[bool] = None
    reportable_flag: Optional[bool] = None
    importable_flag: Optional[bool] = None
    exportable_flag: Optional[bool] = None
    sensitive_flag: Optional[bool] = None
    active_flag: Optional[bool] = None
    display_order: Optional[int] = None
    section_label: Optional[str] = None
    formula: Optional[str] = None
    notes: Optional[str] = None


class FieldValueOut(BaseModel):
    custom_field_id: str
    field_code: str
    field_label: str
    field_type: FieldType
    value: Optional[Any] = None
    display_value: Optional[str] = None
    required_flag: bool = False
    sensitive_flag: bool = False


class FieldValuesSet(BaseModel):
    values: Dict[str, Any]
    updated_by: Optional[str] = "system"


class ValidationError(BaseModel):
    field_code: str
    field_label: str
    errors: List[str]


class ValidationResult(BaseModel):
    valid: bool
    errors: List[ValidationError] = []


class UsageStat(BaseModel):
    custom_field_id: str
    field_code: str
    field_label: str
    entity_type: str
    value_count: int


class CFAIRecOut(BaseModel):
    rec_id: str
    agent_type: CFAIAgentType
    entity_type: Optional[str] = None
    title: str
    body: str
    score: Optional[float] = None
    status: CFAIRecStatus
    rec_metadata: dict = {}
    created_at: datetime
    model_config = {"from_attributes": True}


class CFAIRecAck(BaseModel):
    status: CFAIRecStatus


CustomFieldOut.model_rebuild()
