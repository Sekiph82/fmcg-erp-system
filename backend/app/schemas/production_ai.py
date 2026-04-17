"""
Production AI — Pydantic schemas for all 6 agent outputs.
"""
from __future__ import annotations
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict


# ── Shared ─────────────────────────────────────────────────────────────────────

class AgentOutputBase(BaseModel):
    confidence_score: float
    explanation:      str


# ── Agent 1: Prediction ────────────────────────────────────────────────────────

class PredictionOutput(AgentOutputBase):
    prediction_id:            Optional[str]   = None
    predicted_completion_at:  Optional[str]   = None
    predicted_output_qty:     Optional[float] = None
    predicted_output_uom:     Optional[str]   = None
    delay_risk_pct:           float
    efficiency_forecast_pct:  Optional[float] = None
    historical_sample_size:   int
    risk_level:               str             # GREEN / YELLOW / RED


# ── Agent 2: Anomaly ───────────────────────────────────────────────────────────

class AnomalyOutput(AgentOutputBase):
    anomaly_type:        str
    severity:            str
    affected_area:       Optional[str]   = None
    affected_material:   Optional[str]   = None
    deviation_pct:       Optional[float] = None
    actual_value:        Optional[float] = None
    expected_value:      Optional[float] = None
    baseline_source:     Optional[str]   = None
    production_order_id: Optional[str]   = None
    work_center_id:      Optional[str]   = None


class AnomalyRead(BaseModel):
    """Stored anomaly record from ai_anomalies table."""
    model_config = ConfigDict(from_attributes=True)

    id:                  str
    anomaly_no:          str
    anomaly_type:        str
    severity:            str
    affected_area:       Optional[str]   = None
    affected_material:   Optional[str]   = None
    deviation_pct:       Optional[float] = None
    actual_value:        Optional[float] = None
    expected_value:      Optional[float] = None
    confidence_score:    float
    explanation:         str
    is_resolved:         bool
    resolved_at:         Optional[str]   = None
    resolved_by:         Optional[str]   = None
    production_order_id: Optional[str]   = None
    work_center_id:      Optional[str]   = None
    created_at:          Optional[str]   = None


class ResolveAnomalyRequest(BaseModel):
    resolved_by: str
    notes:       Optional[str] = None


# ── Agent 3/4/5/6: Suggestions ────────────────────────────────────────────────

class SuggestionOutput(AgentOutputBase):
    agent_type:                   str
    suggestion_type:              str
    issue_detected:               str
    suggested_change:             str
    current_value:                Optional[float] = None
    recommended_value:            Optional[float] = None
    value_unit:                   Optional[str]   = None
    expected_efficiency_gain_pct: Optional[float] = None
    expected_cost_reduction_pct:  Optional[float] = None
    expected_quality_improvement: Optional[str]   = None
    estimated_kes_saving:         Optional[float] = None
    product_id:                   Optional[str]   = None
    recipe_id:                    Optional[str]   = None
    work_center_id:               Optional[str]   = None
    # Maintenance-specific extras
    predicted_next_failure:       Optional[str]   = None
    hours_to_failure:             Optional[float] = None
    mtbf_hours:                   Optional[float] = None
    pct_of_mtbf:                  Optional[float] = None


class SuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                           str
    suggestion_no:                str
    agent_type:                   str
    suggestion_type:              str
    issue_detected:               str
    suggested_change:             str
    current_value:                Optional[float] = None
    recommended_value:            Optional[float] = None
    value_unit:                   Optional[str]   = None
    expected_efficiency_gain_pct: Optional[float] = None
    expected_cost_reduction_pct:  Optional[float] = None
    expected_quality_improvement: Optional[str]   = None
    estimated_kes_saving:         Optional[float] = None
    confidence_score:             float
    explanation:                  str
    status:                       str
    actioned_by:                  Optional[str]   = None
    actioned_at:                  Optional[str]   = None
    rejection_reason:             Optional[str]   = None
    product_id:                   Optional[str]   = None
    recipe_id:                    Optional[str]   = None
    work_center_id:               Optional[str]   = None
    created_at:                   Optional[str]   = None


class UpdateSuggestionRequest(BaseModel):
    status:           str   # accepted / rejected / applied
    actioned_by:      Optional[str] = None
    rejection_reason: Optional[str] = None


# ── Agent 1 Prediction Read ────────────────────────────────────────────────────

class PredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                       str
    prediction_no:            str
    production_order_id:      str
    predicted_completion_at:  Optional[str]   = None
    predicted_output_qty:     Optional[float] = None
    predicted_output_uom:     Optional[str]   = None
    delay_risk_pct:           Optional[float] = None
    efficiency_forecast_pct:  Optional[float] = None
    historical_sample_size:   Optional[int]   = None
    confidence_score:         float
    explanation:              str
    risk_level:               Optional[str]   = None
    actual_completion_at:     Optional[str]   = None
    actual_output_qty:        Optional[float] = None
    was_delayed:              Optional[bool]  = None
    prediction_error_pct:     Optional[float] = None
    created_at:               Optional[str]   = None


# ── Dashboard ──────────────────────────────────────────────────────────────────

class AIDashboard(BaseModel):
    anomalies_7d:    dict
    suggestions:     dict
    predictions_7d:  dict


# ── Run-all output ─────────────────────────────────────────────────────────────

class RunAllOutput(BaseModel):
    prediction:  Optional[PredictionOutput] = None
    anomalies:   List[AnomalyOutput]
    suggestions: List[SuggestionOutput]
    summary:     dict
