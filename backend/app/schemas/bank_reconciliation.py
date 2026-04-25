"""Bank Reconciliation — Pydantic v2 Schemas"""
from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.bank_reconciliation import (
    BRAccountType, BRImportSource, BRStatementStatus, BRLineMatchStatus,
    BRMatchMethod, BRERPTransactionType, BRAdjustmentType, BRRuleConditionType,
    BRAIAgentType, BRAIRecStatus,
)


# ─── Bank Account ─────────────────────────────────────────────────────────────

class BRBankAccountCreate(BaseModel):
    bank_name:                str
    branch_name:              Optional[str]  = None
    account_name:             str
    account_number_masked:    Optional[str]  = None
    currency:                 str            = "KES"
    country:                  str            = "KE"
    account_type:             BRAccountType  = BRAccountType.CURRENT
    reconciliation_enabled:   bool           = True
    mobile_money_flag:        bool           = False
    mpesa_till_or_paybill_no: Optional[str]  = None
    gl_account_id:            Optional[UUID] = None
    cash_account_id:          Optional[UUID] = None
    active:                   bool           = True
    notes:                    Optional[str]  = None

class BRBankAccountUpdate(BaseModel):
    bank_name:                Optional[str]          = None
    branch_name:              Optional[str]          = None
    account_name:             Optional[str]          = None
    account_number_masked:    Optional[str]          = None
    reconciliation_enabled:   Optional[bool]         = None
    mobile_money_flag:        Optional[bool]         = None
    mpesa_till_or_paybill_no: Optional[str]          = None
    gl_account_id:            Optional[UUID]         = None
    cash_account_id:          Optional[UUID]         = None
    active:                   Optional[bool]         = None
    notes:                    Optional[str]          = None

class BRBankAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                       UUID
    bank_name:                str
    branch_name:              Optional[str]
    account_name:             str
    account_number_masked:    Optional[str]
    currency:                 str
    country:                  str
    account_type:             BRAccountType
    reconciliation_enabled:   bool
    mobile_money_flag:        bool
    mpesa_till_or_paybill_no: Optional[str]
    gl_account_id:            Optional[UUID]
    cash_account_id:          Optional[UUID]
    active:                   bool
    notes:                    Optional[str]
    created_at:               datetime


# ─── Statement ────────────────────────────────────────────────────────────────

class BRStatementCreate(BaseModel):
    bank_account_id:    UUID
    statement_date:     date
    period_start_date:  date
    period_end_date:    date
    opening_balance:    float = 0.0
    closing_balance:    float = 0.0
    statement_currency: str   = "KES"
    import_source:      BRImportSource = BRImportSource.MANUAL
    import_file_name:   Optional[str]  = None
    notes:              Optional[str]  = None
    imported_by:        Optional[str]  = None

class BRStatementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                 UUID
    statement_no:       str
    bank_account_id:    UUID
    statement_date:     date
    period_start_date:  date
    period_end_date:    date
    opening_balance:    float
    closing_balance:    float
    statement_currency: str
    import_source:      BRImportSource
    import_file_name:   Optional[str]
    status:             BRStatementStatus
    imported_by:        Optional[str]
    imported_at:        Optional[datetime]
    closed_by:          Optional[str]
    closed_at:          Optional[datetime]
    notes:              Optional[str]
    total_credits:      float
    total_debits:       float
    total_lines:        int
    created_at:         datetime


# ─── Statement Line ───────────────────────────────────────────────────────────

class BRStatementLineCreate(BaseModel):
    transaction_date:      date
    value_date:            Optional[date]  = None
    external_reference:    Optional[str]   = None
    bank_reference:        Optional[str]   = None
    narration:             Optional[str]   = None
    counterparty_name:     Optional[str]   = None
    amount:                float
    debit_credit_indicator: str            = "C"
    running_balance:       Optional[float] = None

class BRStatementLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                      UUID
    statement_id:            UUID
    line_no:                 int
    transaction_date:        date
    value_date:              Optional[date]
    external_reference:      Optional[str]
    bank_reference:          Optional[str]
    narration:               Optional[str]
    counterparty_name:       Optional[str]
    amount:                  float
    debit_credit_indicator:  str
    running_balance:         Optional[float]
    normalized_reference:    Optional[str]
    normalized_narration:    Optional[str]
    match_status:            BRLineMatchStatus
    matched_amount:          float
    unmatched_amount:        float
    reconciliation_notes:    Optional[str]
    is_duplicate_suspected:  bool
    created_at:              datetime


# ─── Match ────────────────────────────────────────────────────────────────────

class BRMatchCreate(BaseModel):
    statement_line_id:    UUID
    erp_transaction_type: BRERPTransactionType
    erp_transaction_id:   Optional[UUID] = None
    erp_reference:        Optional[str]  = None
    erp_transaction_date: Optional[date] = None
    erp_amount:           Optional[float] = None
    erp_description:      Optional[str]  = None
    matched_amount:       float
    match_method:         BRMatchMethod  = BRMatchMethod.MANUAL
    confidence_score:     Optional[float] = None
    notes:                Optional[str]  = None
    created_by:           Optional[str]  = None

class BRMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                    UUID
    statement_line_id:     UUID
    erp_transaction_type:  BRERPTransactionType
    erp_transaction_id:    Optional[UUID]
    erp_reference:         Optional[str]
    erp_transaction_date:  Optional[date]
    erp_amount:            Optional[float]
    erp_description:       Optional[str]
    matched_amount:        float
    match_method:          BRMatchMethod
    confidence_score:      Optional[float]
    is_active:             bool
    created_by:            Optional[str]
    approved_by:           Optional[str]
    approved_at:           Optional[datetime]
    notes:                 Optional[str]
    created_at:            datetime


# ─── Rule ─────────────────────────────────────────────────────────────────────

class BRRuleCreate(BaseModel):
    bank_account_id:         Optional[UUID] = None
    rule_name:               str
    condition_type:          BRRuleConditionType
    condition_value:         str
    target_transaction_type: BRERPTransactionType
    auto_apply:              bool  = True
    confidence_weight:       float = 0.8
    priority:                int   = 100
    active:                  bool  = True
    notes:                   Optional[str] = None

class BRRuleUpdate(BaseModel):
    rule_name:               Optional[str]                  = None
    condition_value:         Optional[str]                  = None
    target_transaction_type: Optional[BRERPTransactionType] = None
    auto_apply:              Optional[bool]                 = None
    confidence_weight:       Optional[float]                = None
    priority:                Optional[int]                  = None
    active:                  Optional[bool]                 = None
    notes:                   Optional[str]                  = None

class BRRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                      UUID
    bank_account_id:         Optional[UUID]
    rule_name:               str
    condition_type:          BRRuleConditionType
    condition_value:         str
    target_transaction_type: BRERPTransactionType
    auto_apply:              bool
    confidence_weight:       float
    priority:                int
    active:                  bool
    notes:                   Optional[str]
    created_at:              datetime


# ─── Adjustment ───────────────────────────────────────────────────────────────

class BRAdjustmentCreate(BaseModel):
    statement_id:      UUID
    statement_line_id: Optional[UUID]       = None
    adjustment_type:   BRAdjustmentType
    amount:            float
    description:       str
    gl_account_id:     Optional[UUID]       = None
    created_by:        Optional[str]        = None

class BRAdjustmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                UUID
    statement_id:      UUID
    statement_line_id: Optional[UUID]
    adjustment_type:   BRAdjustmentType
    amount:            float
    description:       str
    gl_account_id:     Optional[UUID]
    auto_created:      bool
    posted:            bool
    posted_by:         Optional[str]
    posted_at:         Optional[datetime]
    created_by:        Optional[str]
    created_at:        datetime


# ─── AI Recommendation ────────────────────────────────────────────────────────

class BRAIRecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               UUID
    statement_id:     Optional[UUID]
    statement_line_id: Optional[UUID]
    agent_type:       BRAIAgentType
    title:            str
    explanation:      Optional[str]
    impact_summary:   Optional[str]
    suggested_action: Optional[str]
    priority:         str
    confidence_score: Optional[float]
    status:           BRAIRecStatus
    actioned_by:      Optional[str]
    actioned_at:      Optional[datetime]
    created_at:       datetime


# ─── Import / CSV ─────────────────────────────────────────────────────────────

class CSVImportRequest(BaseModel):
    bank_account_id:    UUID
    statement_date:     date
    period_start_date:  date
    period_end_date:    date
    opening_balance:    float
    closing_balance:    float
    statement_currency: str  = "KES"
    import_source:      BRImportSource = BRImportSource.CSV
    imported_by:        Optional[str]  = None
    lines:              List[BRStatementLineCreate]


# ─── Match requests ───────────────────────────────────────────────────────────

class ManualMatchRequest(BaseModel):
    erp_transaction_type: BRERPTransactionType
    erp_transaction_id:   Optional[UUID] = None
    erp_reference:        Optional[str]  = None
    erp_transaction_date: Optional[date] = None
    erp_amount:           Optional[float] = None
    erp_description:      Optional[str]  = None
    matched_amount:       float
    notes:                Optional[str]  = None
    created_by:           Optional[str]  = None

class SplitMatchRequest(BaseModel):
    matches: List[ManualMatchRequest]

class AutoMatchResult(BaseModel):
    line_id:         UUID
    candidates:      List[Dict[str, Any]]
    best_confidence: float
    auto_applied:    bool


# ─── Dashboard / Reports ──────────────────────────────────────────────────────

class BRDashboard(BaseModel):
    total_accounts:          int
    active_statements:       int
    unmatched_items:         int
    partially_matched_items: int
    total_unmatched_amount:  float
    statements_in_recon:     int
    statements_locked:       int
    pending_ai_recs:         int
    recent_statements:       List[BRStatementOut] = Field(default_factory=list)

class BROpenItemRow(BaseModel):
    line_id:             UUID
    statement_no:        str
    bank_account_name:   str
    transaction_date:    date
    amount:              float
    debit_credit:        str
    unmatched_amount:    float
    match_status:        BRLineMatchStatus
    narration:           Optional[str]
    days_outstanding:    int

class BRBalanceSummaryRow(BaseModel):
    bank_account_id:   UUID
    bank_account_name: str
    currency:          str
    last_statement_no: Optional[str]
    statement_closing: float
    erp_book_balance:  float
    variance:          float
    status:            str
