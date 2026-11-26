from __future__ import annotations
import uuid
import enum
from sqlalchemy import Index, func, text  # noqa: E402
from sqlalchemy import (
    Column, String, Integer, BigInteger, Numeric, Boolean, Text, Date, DateTime,
    ForeignKey, Enum, JSON, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


# ── Enums ─────────────────────────────────────────────────────────────────────

class CRMRecordType(str, enum.Enum):
    LEAD        = "LEAD"
    OPPORTUNITY = "OPPORTUNITY"


class CRMAccountType(str, enum.Enum):
    PROSPECT         = "PROSPECT"
    CUSTOMER         = "CUSTOMER"
    DISTRIBUTOR      = "DISTRIBUTOR"
    RETAILER         = "RETAILER"
    MODERN_TRADE     = "MODERN_TRADE"
    INSTITUTIONAL    = "INSTITUTIONAL"
    SUPPLIER_XSELL   = "SUPPLIER_XSELL"
    OTHER            = "OTHER"


class CRMSourceType(str, enum.Enum):
    WEBSITE     = "WEBSITE"
    REFERRAL    = "REFERRAL"
    FIELD_SALES = "FIELD_SALES"
    EVENT       = "EVENT"
    OUTBOUND    = "OUTBOUND"
    INBOUND     = "INBOUND"
    CAMPAIGN    = "CAMPAIGN"
    MANUAL      = "MANUAL"
    IMPORT      = "IMPORT"


class CRMStageType(str, enum.Enum):
    LEAD        = "LEAD"
    OPPORTUNITY = "OPPORTUNITY"
    TERMINAL    = "TERMINAL"
    NURTURING   = "NURTURING"


class CRMTemperature(str, enum.Enum):
    COLD = "COLD"
    WARM = "WARM"
    HOT  = "HOT"


class CRMStatus(str, enum.Enum):
    OPEN     = "OPEN"
    WON      = "WON"
    LOST     = "LOST"
    ON_HOLD  = "ON_HOLD"
    ARCHIVED = "ARCHIVED"


class CRMActivityType(str, enum.Enum):
    CALL              = "CALL"
    EMAIL             = "EMAIL"
    MEETING           = "MEETING"
    WHATSAPP          = "WHATSAPP"
    VISIT             = "VISIT"
    TASK              = "TASK"
    NOTE              = "NOTE"
    DEMO              = "DEMO"
    SAMPLE_SENT       = "SAMPLE_SENT"
    QUOTATION_SENT    = "QUOTATION_SENT"
    NEGOTIATION       = "NEGOTIATION"
    COMPLAINT_FOLLOWUP = "COMPLAINT_FOLLOWUP"
    OTHER             = "OTHER"


class CRMActivityResult(str, enum.Enum):
    PLANNED     = "PLANNED"
    COMPLETED   = "COMPLETED"
    NO_RESPONSE = "NO_RESPONSE"
    RESCHEDULED = "RESCHEDULED"
    CANCELLED   = "CANCELLED"


class CRMLossReason(str, enum.Enum):
    PRICE_TOO_HIGH        = "PRICE_TOO_HIGH"
    COMPETITOR_RELATION   = "COMPETITOR_RELATION"
    PRODUCT_MISMATCH      = "PRODUCT_MISMATCH"
    TIMELINE_ISSUE        = "TIMELINE_ISSUE"
    NO_BUDGET             = "NO_BUDGET"
    NO_RESPONSE           = "NO_RESPONSE"
    COMPETITOR_PROMO      = "COMPETITOR_PROMO"
    DISTRIBUTOR_CONFLICT  = "DISTRIBUTOR_CONFLICT"
    CAPACITY_SUPPLY       = "CAPACITY_SUPPLY"
    INTERNAL_FOLLOWUP     = "INTERNAL_FOLLOWUP"
    OTHER                 = "OTHER"


class CRMWinReason(str, enum.Enum):
    BETTER_PRICE       = "BETTER_PRICE"
    BETTER_PRODUCT_FIT = "BETTER_PRODUCT_FIT"
    FASTER_RESPONSE    = "FASTER_RESPONSE"
    STRONGER_RELATION  = "STRONGER_RELATION"
    AVAILABILITY       = "AVAILABILITY"
    TECHNICAL_SUPPORT  = "TECHNICAL_SUPPORT"
    PROMOTION_SUPPORT  = "PROMOTION_SUPPORT"
    OTHER              = "OTHER"


class CRMAIAgentType(str, enum.Enum):
    LEAD_PRIORITIZATION = "LEAD_PRIORITIZATION"
    PIPELINE_RISK       = "PIPELINE_RISK"
    WIN_LOSS_INSIGHT    = "WIN_LOSS_INSIGHT"


class CRMAIRecStatus(str, enum.Enum):
    PENDING      = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED     = "ACTIONED"
    DISMISSED    = "DISMISSED"


# ── Models ────────────────────────────────────────────────────────────────────

class CRMTerritory(Base, TimestampMixin):
    __tablename__ = "crm_territories"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    territory_code       = Column(String(50), nullable=False, unique=True)
    territory_name       = Column(String(150), nullable=False)
    region               = Column(String(100))
    company_id           = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    branch_id            = Column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    sales_region_id      = Column(String(100), nullable=True, index=True)
    sales_team_id        = Column(String(100), nullable=True, index=True)
    customer_group_id    = Column(String(100), nullable=True, index=True)
    parent_territory_id  = Column(UUID(as_uuid=True), ForeignKey("crm_territories.id"), nullable=True)
    assigned_rep_ids     = Column(String(500))
    active_flag          = Column(Boolean, default=True)
    notes                = Column(Text)

    company = relationship("Company", foreign_keys=[company_id])
    branch = relationship("Branch", foreign_keys=[branch_id])
    records = relationship("CRMRecord", back_populates="territory", foreign_keys="CRMRecord.territory_id")


class CRMPipeline(Base, TimestampMixin):
    """M43.S01.T011: a named pipeline (e.g. distributor onboarding, key-account deals) owning its own stages."""
    __tablename__ = "crm_pipelines"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(120), nullable=False, unique=True)
    record_type = Column(String(20), nullable=True)          # LEAD | OPPORTUNITY | None = any
    company_id  = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    is_default  = Column(Boolean, nullable=False, default=False)
    active_flag = Column(Boolean, nullable=False, default=True)
    sequence_no = Column(Integer, nullable=False, default=0)


class CRMPipelineStage(Base, TimestampMixin):
    __tablename__ = "crm_pipeline_stages"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stage_code            = Column(String(50), nullable=False, unique=True)
    stage_name            = Column(String(100), nullable=False)
    stage_type            = Column(Enum(CRMStageType), nullable=False)
    default_probability   = Column(Numeric(5, 2), default=0)
    sequence_no           = Column(Integer, nullable=False, default=0)
    active_flag           = Column(Boolean, default=True)
    color_code            = Column(String(20))
    notes                 = Column(Text)
    required_fields       = Column(JSON, nullable=True)   # M43.S01.T016: fields needed to ENTER this stage
    pipeline_id           = Column(UUID(as_uuid=True), ForeignKey("crm_pipelines.id", ondelete="RESTRICT"), nullable=True, index=True)

    records = relationship("CRMRecord", back_populates="stage", foreign_keys="CRMRecord.stage_id")


class CRMRecord(Base, TimestampMixin):
    __tablename__ = "crm_records"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_type           = Column(Enum(CRMRecordType), nullable=False, default=CRMRecordType.LEAD)
    lead_code             = Column(String(50), unique=True)
    opportunity_code      = Column(String(50), unique=True)
    account_type          = Column(Enum(CRMAccountType), default=CRMAccountType.PROSPECT)
    company_name          = Column(String(200), nullable=False)
    contact_person_name   = Column(String(200))
    contact_email         = Column(String(200))
    contact_phone         = Column(String(50))
    alternate_contact     = Column(String(200))
    customer_id           = Column(String(50))
    distributor_id        = Column(String(50))
    source_type           = Column(Enum(CRMSourceType), default=CRMSourceType.MANUAL)
    source_detail         = Column(String(200))
    region_id             = Column(String(50))
    company_id            = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    branch_id             = Column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    sales_region_id       = Column(String(100), nullable=True, index=True)
    sales_team_id         = Column(String(100), nullable=True, index=True)
    customer_group_id     = Column(String(100), nullable=True, index=True)
    country_id            = Column(String(50))
    channel_id            = Column(String(50))
    industry_segment      = Column(String(100))
    assigned_rep_id       = Column(String(50))
    assigned_team_id      = Column(String(50))
    stage_id              = Column(UUID(as_uuid=True), ForeignKey("crm_pipeline_stages.id"), nullable=True)
    territory_id          = Column(UUID(as_uuid=True), ForeignKey("crm_territories.id"), nullable=True)
    assigned_customer_id  = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    probability_pct       = Column(Numeric(5, 2), default=0)
    probability_override  = Column(Boolean, default=False)
    expected_close_date   = Column(Date)
    expected_revenue      = Column(Numeric(18, 2), default=0)
    expected_margin       = Column(Numeric(18, 2), default=0)
    currency              = Column(String(10), default="KES")
    lead_score            = Column(Integer, default=0)
    temperature           = Column(Enum(CRMTemperature), default=CRMTemperature.COLD)
    next_action_date      = Column(Date)
    status                = Column(Enum(CRMStatus), default=CRMStatus.OPEN)
    qualified_flag        = Column(Boolean, default=False)
    qualified_date        = Column(Date)
    converted_date        = Column(Date)
    linked_quotation_id   = Column(String(50))
    linked_order_id       = Column(String(50))
    created_by            = Column(String(50))
    updated_by            = Column(String(50))
    notes                 = Column(Text)
    pipeline_id           = Column(UUID(as_uuid=True), ForeignKey("crm_pipelines.id", ondelete="SET NULL"), nullable=True, index=True)  # M43.S01.T011, follows the stage
    forecast_category     = Column(String(10), nullable=True)   # M43.S01.T007 override: PIPELINE|BEST_CASE|COMMIT|OMITTED

    stage         = relationship("CRMPipelineStage", back_populates="records", foreign_keys=[stage_id])
    territory     = relationship("CRMTerritory", back_populates="records", foreign_keys=[territory_id])
    company       = relationship("Company", foreign_keys=[company_id])
    branch        = relationship("Branch", foreign_keys=[branch_id])
    assigned_customer = relationship("Customer", foreign_keys=[assigned_customer_id])
    interest_lines = relationship("CRMInterestLine", back_populates="record", cascade="all, delete-orphan")
    activities    = relationship("CRMActivity", back_populates="record", cascade="all, delete-orphan")
    competitors   = relationship("CRMCompetitor", back_populates="record", cascade="all, delete-orphan")
    win_loss      = relationship("CRMWinLoss", back_populates="record", uselist=False, cascade="all, delete-orphan")


class CRMInterestLine(Base, TimestampMixin):
    __tablename__ = "crm_interest_lines"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id           = Column(UUID(as_uuid=True), ForeignKey("crm_records.id"), nullable=False)
    item_id                 = Column(String(50))
    item_name               = Column(String(200))
    category_id             = Column(String(50))
    brand_id                = Column(String(50))
    expected_qty            = Column(Numeric(18, 3))
    expected_frequency      = Column(String(50))
    expected_value          = Column(Numeric(18, 2))
    competitive_brand       = Column(String(200))
    competitor_price        = Column(Numeric(18, 2))
    notes                   = Column(Text)

    record = relationship("CRMRecord", back_populates="interest_lines")


class CRMActivity(Base, TimestampMixin):
    __tablename__ = "crm_activities"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id       = Column(UUID(as_uuid=True), ForeignKey("crm_records.id"), nullable=False)
    activity_type       = Column(Enum(CRMActivityType), nullable=False)
    subject             = Column(String(300), nullable=False)
    description         = Column(Text)
    activity_datetime   = Column(DateTime)
    due_datetime        = Column(DateTime)
    completed_datetime  = Column(DateTime)
    assigned_to         = Column(String(50))
    created_by          = Column(String(50))
    result_status       = Column(Enum(CRMActivityResult), default=CRMActivityResult.PLANNED)
    outcome_code        = Column(String(100))
    queue                = Column(String(60), nullable=True, index=True)      # M43.S01.T013 task queue
    recurrence_rule      = Column(String(10), nullable=True)                  # DAILY | WEEKLY | MONTHLY
    recurrence_every     = Column(Integer, nullable=True)
    recurrence_until     = Column(Date, nullable=True)
    recurrence_parent_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    next_step           = Column(Text)
    notes               = Column(Text)

    record = relationship("CRMRecord", back_populates="activities")


class CRMCompetitor(Base, TimestampMixin):
    __tablename__ = "crm_competitors"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id        = Column(UUID(as_uuid=True), ForeignKey("crm_records.id"), nullable=False)
    competitor_name      = Column(String(200), nullable=False)
    competitor_product   = Column(String(200))
    offer_type          = Column(String(100))
    competitor_price     = Column(Numeric(18, 2))
    competitor_strength  = Column(Text)
    competitor_weakness  = Column(Text)
    risk_level           = Column(String(20))
    notes                = Column(Text)

    record = relationship("CRMRecord", back_populates="competitors")


class CRMWinLoss(Base, TimestampMixin):
    __tablename__ = "crm_win_loss"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id    = Column(UUID(as_uuid=True), ForeignKey("crm_records.id"), nullable=False, unique=True)
    final_status     = Column(String(10), nullable=False)
    close_date       = Column(Date)
    final_revenue    = Column(Numeric(18, 2))
    final_margin     = Column(Numeric(18, 2))
    loss_reason_code = Column(Enum(CRMLossReason))
    win_reason_code  = Column(Enum(CRMWinReason))
    competitor_name  = Column(String(200))
    narrative        = Column(Text)
    recorded_by      = Column(String(50))
    notes            = Column(Text)

    record = relationship("CRMRecord", back_populates="win_loss")


class CRMAIRecommendation(Base, TimestampMixin):
    __tablename__ = "crm_ai_recommendations"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type     = Column(Enum(CRMAIAgentType), nullable=False)
    crm_record_id  = Column(UUID(as_uuid=True), ForeignKey("crm_records.id"), nullable=True)
    title          = Column(String(300), nullable=False)
    body           = Column(Text, nullable=False)
    priority       = Column(String(20))
    action_label   = Column(String(100))
    status         = Column(Enum(CRMAIRecStatus), default=CRMAIRecStatus.PENDING)
    acknowledged_by = Column(String(50))
    notes          = Column(Text)


# ── M36.S02 sales intelligence ────────────────────────────────────────────────

class CRMScoreRule(Base, TimestampMixin):
    """Configurable lead-score rule: when `field <operator> value` holds, add `points` (fit or engagement)."""
    __tablename__ = "crm_score_rules"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String(150), nullable=False)
    category   = Column(String(20), nullable=False, default="FIT")      # FIT | ENGAGEMENT
    field      = Column(String(50), nullable=False)                     # see crm_intelligence_service.SCORE_FIELDS
    operator   = Column(String(10), nullable=False)                     # eq | in | gte | lte | true
    value      = Column(String(500), nullable=True)
    points     = Column(Integer, nullable=False)
    max_points = Column(Integer, nullable=True)                         # cap for count fields (points per item)
    active_flag = Column(Boolean, default=True, nullable=False)
    sequence_no = Column(Integer, default=0, nullable=False)


class CRMScoreHistory(Base):
    """One row per score change, with the per-rule breakdown that explains it."""
    __tablename__ = "crm_score_history"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id  = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_score = Column(Integer, nullable=True)
    score          = Column(Integer, nullable=False)
    temperature    = Column(String(10), nullable=False)
    breakdown      = Column(Text, nullable=False)                       # JSON list of {rule, points, reason}
    computed_at    = Column(DateTime(timezone=True), nullable=False)
    computed_by    = Column(String(50), nullable=True)


class CRMStageHistory(Base):
    """Stage/status transitions of a CRM record (captured on flush for every write path)."""
    __tablename__ = "crm_stage_history"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="CASCADE"), nullable=False, index=True)
    from_stage_id = Column(UUID(as_uuid=True), nullable=True)
    to_stage_id   = Column(UUID(as_uuid=True), nullable=True)
    from_status   = Column(String(20), nullable=True)
    to_status     = Column(String(20), nullable=True)
    changed_at    = Column(DateTime(timezone=True), nullable=False, index=True)


class CRMForecastSnapshot(Base):
    """Frozen copy of a forecast (filters + rows) for later comparison."""
    __tablename__ = "crm_forecast_snapshots"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label       = Column(String(150), nullable=True)
    filters     = Column(Text, nullable=False)                          # JSON
    rows        = Column(Text, nullable=False)                          # JSON
    taken_at    = Column(DateTime(timezone=True), nullable=False, index=True)
    taken_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


def _capture_stage_changes(session, _flush_context, _instances):
    from datetime import datetime, timezone

    from sqlalchemy import inspect

    now = datetime.now(timezone.utc)
    for obj in list(session.new) + list(session.dirty):
        if not isinstance(obj, CRMRecord):
            continue
        state = inspect(obj)
        stage, status = state.attrs.stage_id.history, state.attrs.status.history
        if obj in session.new:  # creation is an event too (automation "created" trigger)
            from_stage, from_status = None, None
            if obj.status is None:
                obj.status = CRMStatus.OPEN  # column default, applied now so the history row is complete
        elif stage.has_changes() or status.has_changes():
            # a changed attribute with nothing in `deleted` had no previous value (e.g. first stage)
            from_stage = (stage.deleted or [None])[0] if stage.has_changes() else obj.stage_id
            from_status = (status.deleted or [None])[0] if status.has_changes() else obj.status
        else:
            continue
        if obj.id is None:
            obj.id = uuid.uuid4()
        session.add(CRMStageHistory(
            crm_record_id=obj.id, from_stage_id=from_stage, to_stage_id=obj.stage_id,
            from_status=getattr(from_status, "value", from_status), to_status=getattr(obj.status, "value", obj.status),
            changed_at=now))


from sqlalchemy import event as _event  # noqa: E402
from sqlalchemy.orm import Session as _Session  # noqa: E402

_event.listen(_Session, "before_flush", _capture_stage_changes)


# ── M36.S02.T001 website lead capture ─────────────────────────────────────────

class CRMLeadForm(Base, TimestampMixin):
    """Public lead form (hosted at /forms/<slug>, embeddable by iframe). Scope fields are copied to leads."""
    __tablename__ = "crm_lead_forms"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug             = Column(String(80), nullable=False, unique=True, index=True)
    name             = Column(String(150), nullable=False)
    title            = Column(String(200), nullable=False)
    intro            = Column(Text, nullable=True)
    consent_text     = Column(Text, nullable=True)
    require_consent  = Column(Boolean, nullable=False, default=True)
    success_message  = Column(String(300), nullable=True)
    active_flag      = Column(Boolean, nullable=False, default=True)
    assigned_rep_id  = Column(String(50), nullable=True)
    territory_id     = Column(UUID(as_uuid=True), ForeignKey("crm_territories.id"), nullable=True)
    company_id       = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    branch_id        = Column(UUID(as_uuid=True), ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    sales_region_id  = Column(String(100), nullable=True)
    sales_team_id    = Column(String(100), nullable=True)


class CRMLeadSubmission(Base):
    """Every submission, kept for audit and attribution (ACCEPTED / DUPLICATE / SPAM)."""
    __tablename__ = "crm_lead_submissions"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    form_id        = Column(UUID(as_uuid=True), ForeignKey("crm_lead_forms.id", ondelete="CASCADE"), nullable=False, index=True)
    received_at    = Column(DateTime(timezone=True), nullable=False, index=True)
    ip_hash        = Column(String(64), nullable=True, index=True)   # keyed hash; raw IPs are not stored
    status         = Column(String(12), nullable=False)
    crm_record_id  = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="SET NULL"), nullable=True)
    contact_email  = Column(String(200), nullable=True)
    consent_given  = Column(Boolean, nullable=False, default=False)
    consent_text   = Column(Text, nullable=True)                     # text the visitor agreed to
    utm_source     = Column(String(100), nullable=True)
    utm_medium     = Column(String(100), nullable=True)
    utm_campaign   = Column(String(100), nullable=True)
    utm_term       = Column(String(100), nullable=True)
    utm_content    = Column(String(100), nullable=True)
    referrer       = Column(String(500), nullable=True)
    landing_page   = Column(String(500), nullable=True)



# ── M36.S01.T004 CRM automation ───────────────────────────────────────────────

class CRMAutomationRun(Base):
    """One execution of a CRM automation rule for one CRM event; unique per (rule, event) so replays,
    restarts and several API workers never run an action twice. Doubles as the audit trail."""
    __tablename__ = "crm_automation_runs"
    __table_args__ = (UniqueConstraint("rule_id", "event_key", name="uq_crm_automation_rule_event"),)

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id         = Column(String(36), nullable=False, index=True)
    rule_name       = Column(String(200), nullable=True)
    event_key       = Column(String(80), nullable=False)               # "<event>:<stage_history_id>"
    event_type      = Column(String(20), nullable=False)
    crm_record_id   = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="CASCADE"), nullable=False, index=True)
    status          = Column(String(10), nullable=False, default="PENDING", index=True)  # PENDING|DONE|FAILED|SKIPPED
    attempts        = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(timezone=True), nullable=False)
    result          = Column(Text, nullable=True)
    error           = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), nullable=False)
    finished_at     = Column(DateTime(timezone=True), nullable=True)



# ── M36 consent register and outbound e-mail outbox ───────────────────────────

class CRMContactConsent(Base):
    """Marketing permission per e-mail address. UNSUBSCRIBED / BOUNCED / COMPLAINED suppress all
    sequence and campaign mail; the latest event wins."""
    __tablename__ = "crm_contact_consents"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email          = Column(String(254), nullable=False, unique=True, index=True)   # stored lower-case
    status         = Column(String(15), nullable=False)    # SUBSCRIBED | UNSUBSCRIBED | BOUNCED | COMPLAINED
    source         = Column(String(100), nullable=True)    # form:<slug> | unsubscribe-link | manual:<user> ...
    consent_text   = Column(Text, nullable=True)
    updated_at     = Column(DateTime(timezone=True), nullable=False)
    tracking_opt_out = Column(Boolean, nullable=False, default=False, server_default="false")  # M43.S01.T006


class CRMOutboundMessage(Base):
    """Outbox: every CRM e-mail is queued here first. Never marked SENT unless the SMTP server accepted it."""
    __tablename__ = "crm_outbound_messages"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dedupe_key          = Column(String(200), nullable=False, unique=True)   # same key = same message, sent once
    purpose             = Column(String(12), nullable=False)                 # MANUAL | SEQUENCE | CAMPAIGN
    to_email            = Column(String(254), nullable=False, index=True)
    subject             = Column(String(300), nullable=False)
    body_text           = Column(Text, nullable=False)
    crm_record_id       = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id         = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    status              = Column(String(12), nullable=False, index=True)     # QUEUED | SENT | SUPPRESSED | FAILED | CANCELLED
    status_reason       = Column(String(300), nullable=True)
    attempts            = Column(Integer, nullable=False, default=0)
    next_attempt_at     = Column(DateTime(timezone=True), nullable=False)
    provider_message_id = Column(String(300), nullable=True)
    created_by          = Column(String(100), nullable=True)
    created_at          = Column(DateTime(timezone=True), nullable=False)
    sent_at             = Column(DateTime(timezone=True), nullable=True)
    track_engagement    = Column(Boolean, nullable=False, default=False, server_default="false")  # M43.S01.T006 opt-in
    tracked_links       = Column(JSON, nullable=True)       # the only allowed click-redirect targets of this message
    body_html           = Column(Text, nullable=True)       # M44.S01.T001 designed e-mail (text part stays in body_text)
    ab_variant          = Column(String(1), nullable=True)      # M44.S01.T012 A | B


class CRMEmailEvent(Base):
    """M43.S01.T006 open/click events of tracked CRM e-mail; is_machine = proxy, scanner or too fast after send."""
    __tablename__ = "crm_email_events"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id  = Column(UUID(as_uuid=True), ForeignKey("crm_outbound_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    kind        = Column(String(5), nullable=False)          # OPEN | CLICK
    link_index  = Column(Integer, nullable=False, default=0)
    url         = Column(String(2000), nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    is_machine  = Column(Boolean, nullable=False, default=False)
    ua_class    = Column(String(10), nullable=True)          # client | proxy | machine
    ip_hash     = Column(String(64), nullable=True)


# ── M36.S01.T002 sales sequences ──────────────────────────────────────────────

class CRMSequence(Base, TimestampMixin):
    __tablename__ = "crm_sequences"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(150), nullable=False, unique=True)
    active_flag = Column(Boolean, nullable=False, default=True)
    track_engagement = Column(Boolean, nullable=False, default=False, server_default="false")  # M43.S01.T006
    notes       = Column(Text, nullable=True)


class CRMSequenceStep(Base):
    __tablename__ = "crm_sequence_steps"
    __table_args__ = (UniqueConstraint("sequence_id", "step_no", name="uq_crm_sequence_step"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sequence_id = Column(UUID(as_uuid=True), ForeignKey("crm_sequences.id", ondelete="CASCADE"), nullable=False, index=True)
    step_no     = Column(Integer, nullable=False)
    delay_days  = Column(Integer, nullable=False, default=0)        # after enrolment (step 1) or the previous step
    subject     = Column(String(300), nullable=False)
    body        = Column(Text, nullable=False)                       # {contact_name} {company_name} {rep}


class CRMSequenceEnrollment(Base):
    """A CRM record going through a sequence; one active enrolment per (sequence, record)."""
    __tablename__ = "crm_sequence_enrollments"
    __table_args__ = (UniqueConstraint("sequence_id", "crm_record_id", name="uq_crm_sequence_enrollment"),)

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sequence_id   = Column(UUID(as_uuid=True), ForeignKey("crm_sequences.id", ondelete="CASCADE"), nullable=False, index=True)
    crm_record_id = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="CASCADE"), nullable=False, index=True)
    email         = Column(String(254), nullable=False)
    status        = Column(String(10), nullable=False, index=True)     # ACTIVE | COMPLETED | STOPPED
    stop_reason   = Column(String(200), nullable=True)
    next_step_no  = Column(Integer, nullable=False, default=1)
    next_due_at   = Column(DateTime(timezone=True), nullable=False, index=True)
    enrolled_by   = Column(String(100), nullable=True)
    enrolled_at   = Column(DateTime(timezone=True), nullable=False)
    finished_at   = Column(DateTime(timezone=True), nullable=True)


# ── M36.S02.T005 segment e-mail campaigns ─────────────────────────────────────

class CRMEmailCampaign(Base, TimestampMixin):
    """E-mail to a customer segment through the consent-aware outbox (CAMPAIGN purpose)."""
    __tablename__ = "crm_email_campaigns"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name                  = Column(String(150), nullable=False)
    subject               = Column(String(300), nullable=False)
    body                  = Column(Text, nullable=False)                 # {contact_name} {company_name}
    segment_id            = Column(UUID(as_uuid=True), ForeignKey("mkt_customer_segments.id", ondelete="RESTRICT"), nullable=False)
    company_id            = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    marketing_campaign_id = Column(UUID(as_uuid=True), ForeignKey("mkt_campaigns.id", ondelete="SET NULL"), nullable=True)
    track_engagement      = Column(Boolean, nullable=False, default=False, server_default="false")  # M43.S01.T006
    design_id             = Column(UUID(as_uuid=True), ForeignKey("mkt_email_designs.id", ondelete="RESTRICT"), nullable=True)  # M44.S01.T001
    # M44.S01.T012 A/B test, send-time optimisation, approval
    ab_split_pct          = Column(Integer, nullable=False, default=0, server_default="0")    # % of recipients getting B
    variant_b_subject     = Column(String(300), nullable=True)
    variant_b_body        = Column(Text, nullable=True)
    variant_b_design_id   = Column(UUID(as_uuid=True), ForeignKey("mkt_email_designs.id", ondelete="RESTRICT"), nullable=True)
    send_time_optimize    = Column(Boolean, nullable=False, default=False, server_default="false")
    approval_status       = Column(String(10), nullable=False, default="NONE", server_default="NONE")  # NONE|PENDING|APPROVED|REJECTED
    approval_requested_by = Column(String(100), nullable=True)
    approved_by           = Column(String(100), nullable=True)
    approved_at           = Column(DateTime(timezone=True), nullable=True)
    status                = Column(String(10), nullable=False, default="DRAFT")   # DRAFT|SCHEDULED|QUEUED|CANCELLED
    scheduled_at          = Column(DateTime(timezone=True), nullable=True)
    queued_at             = Column(DateTime(timezone=True), nullable=True)
    audience_size         = Column(Integer, nullable=True)
    created_by            = Column(String(100), nullable=True)


# ── M36.S01.T003 unified conversations inbox ───────────────────────────────────

class CRMConversation(Base, TimestampMixin):
    """One row per customer conversation, whatever the channel (e-mail thread, WhatsApp number, support ticket).
    Messages stay in their source tables; this index carries the inbox state (assignee, status, SLA, activity)."""
    __tablename__ = "crm_conversations"
    __table_args__ = (UniqueConstraint("channel", "source_ref", name="uq_crm_conversation_source"),)

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel          = Column(String(10), nullable=False, index=True)        # EMAIL | WHATSAPP | TICKET
    source_ref       = Column(String(120), nullable=False)                   # thread id / "<config>:<phone>" / ticket id
    subject          = Column(String(500), nullable=True)
    contact          = Column(String(255), nullable=True)                    # e-mail address / phone / customer name
    customer_id      = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    company_id       = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    mailbox_owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    assignee_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status           = Column(String(10), nullable=False, default="OPEN", index=True)  # OPEN | PENDING | CLOSED
    last_inbound_at  = Column(DateTime(timezone=True), nullable=True)
    last_outbound_at = Column(DateTime(timezone=True), nullable=True)
    last_message_at  = Column(DateTime(timezone=True), nullable=True, index=True)
    sla_due_at       = Column(DateTime(timezone=True), nullable=True)        # reply due for an unanswered customer message
    closed_at        = Column(DateTime(timezone=True), nullable=True)


class CRMConversationRead(Base):
    """Per user: when they last opened the conversation (unread = a customer message after that)."""
    __tablename__ = "crm_conversation_reads"
    __table_args__ = (UniqueConstraint("conversation_id", "user_id", name="uq_crm_conversation_read"),)

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("crm_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    last_read_at    = Column(DateTime(timezone=True), nullable=False)


# ── M36.S03.T001 sales document engagement ─────────────────────────────────────

class CRMDocumentLink(Base):
    """A share link for one quotation: random token (stored as SHA-256), expiry, revocation, view counters."""
    __tablename__ = "crm_document_links"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quotation_id    = Column(UUID(as_uuid=True), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash      = Column(String(64), nullable=False, unique=True)
    label           = Column(String(150), nullable=True)                   # e.g. who it was sent to
    created_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at      = Column(DateTime(timezone=True), nullable=False)
    expires_at      = Column(DateTime(timezone=True), nullable=False)
    revoked_at      = Column(DateTime(timezone=True), nullable=True)
    view_count      = Column(Integer, nullable=False, default=0)           # distinct visits (30-minute dedupe)
    password_hash   = Column(String(255), nullable=True)                   # optional password (M45.S01.T014)
    first_viewed_at = Column(DateTime(timezone=True), nullable=True)
    last_viewed_at  = Column(DateTime(timezone=True), nullable=True)


class CRMDocumentView(Base):
    """One visit. No IP or user agent is stored: only a keyed hash used to merge repeat views."""
    __tablename__ = "crm_document_views"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    link_id     = Column(UUID(as_uuid=True), ForeignKey("crm_document_links.id", ondelete="CASCADE"), nullable=False, index=True)
    viewer_hash = Column(String(64), nullable=False)
    viewed_at   = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=False)


class CRMQuoteDecision(Base):
    """M36.S04.T003 the customer's signed decision on a shared quotation (one per quotation version).
    document_hash = SHA-256 of the customer-facing content they saw; evidence_hash binds it to the signer,
    the time and the link, so later changes to the quote or the record are detectable."""
    __tablename__ = "crm_quote_decisions"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quotation_id   = Column(UUID(as_uuid=True), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, unique=True)
    link_id        = Column(UUID(as_uuid=True), ForeignKey("crm_document_links.id", ondelete="SET NULL"), nullable=True)
    decision       = Column(String(10), nullable=False)                    # ACCEPTED | DECLINED
    signer_name    = Column(String(150), nullable=False)
    signer_email   = Column(String(254), nullable=False)
    reason         = Column(Text, nullable=True)                           # decline reason
    decided_at     = Column(DateTime(timezone=True), nullable=False)
    document_hash  = Column(String(64), nullable=False)
    evidence_hash  = Column(String(64), nullable=False)
    viewer_hash    = Column(String(64), nullable=True)
    document_snapshot = Column(JSON, nullable=True)                         # exactly what the signer saw
    email_verified_at = Column(DateTime(timezone=True), nullable=True)      # M41: signer proved the e-mail with a code


class CRMQuoteSignerCode(Base):
    """M41.S01.T002 one-time code e-mailed to the signer before they accept or decline a shared quotation.
    Sent only to an e-mail on file for the quoted customer; stored as a keyed hash; 15 minutes, 5 tries, single use."""
    __tablename__ = "crm_quote_signer_codes"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    link_id    = Column(UUID(as_uuid=True), ForeignKey("crm_document_links.id", ondelete="CASCADE"), nullable=False, index=True)
    email      = Column(String(254), nullable=False)                     # lower-case
    code_hash  = Column(String(64), nullable=False)
    attempts   = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at    = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ── M36.S03.T005 website live chat ─────────────────────────────────────────────

class CRMChatSession(Base):
    """A website visitor's chat. The visitor holds a random token (stored as SHA-256) to read and write it."""
    __tablename__ = "crm_chat_sessions"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_hash      = Column(String(64), nullable=False, unique=True)
    visitor_name    = Column(String(120), nullable=True)
    visitor_email   = Column(String(254), nullable=True)
    consent_given   = Column(Boolean, nullable=False, default=False)
    status          = Column(String(10), nullable=False, default="BOT")        # BOT | WAITING (handed off) | CLOSED
    assignee_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    crm_record_id   = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="SET NULL"), nullable=True)
    company_id      = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    ip_hash         = Column(String(64), nullable=True, index=True)
    page_url        = Column(String(500), nullable=True)
    portal_account_id = Column(UUID(as_uuid=True), ForeignKey("portal_accounts.id", ondelete="SET NULL"), nullable=True)  # signed-in portal visitor (M45.S01.T024)
    created_at      = Column(DateTime(timezone=True), nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=False, index=True)
    closed_at       = Column(DateTime(timezone=True), nullable=True)


class CRMChatMessage(Base):
    __tablename__ = "crm_chat_messages"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id  = Column(UUID(as_uuid=True), ForeignKey("crm_chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    sender      = Column(String(8), nullable=False)                           # VISITOR | BOT | AGENT
    body        = Column(Text, nullable=False)
    agent_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, index=True)



# ── M36.S05.T005 account-based marketing ─────────────────────────────────────────

class CRMAccountGroup(Base, TimestampMixin):
    """Target-account list (ERP customers) worked together by sales and marketing."""
    __tablename__ = "crm_account_groups"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name                = Column(String(150), nullable=False, unique=True)
    description         = Column(Text, nullable=True)
    owner_user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    campaign_started_at = Column(DateTime(timezone=True), nullable=True)


class CRMAccountGroupMember(Base):
    __tablename__ = "crm_account_group_members"

    group_id    = Column(UUID(as_uuid=True), ForeignKey("crm_account_groups.id", ondelete="CASCADE"), primary_key=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True)
    tier        = Column(Integer, nullable=False, default=2)        # 1 = strategic, 2 = core, 3 = watch
    added_at    = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CRMAccountContact(Base, TimestampMixin):
    """A person in an account's buying committee."""
    __tablename__ = "crm_account_contacts"
    __table_args__ = (Index("uq_crm_account_contacts_customer_email", "customer_id", text("lower(email)"),
                            unique=True, postgresql_where=text("email IS NOT NULL")),)

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id    = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name      = Column(String(150), nullable=False)
    title          = Column(String(150), nullable=True)
    email          = Column(String(254), nullable=True)
    phone          = Column(String(50), nullable=True)
    committee_role = Column(String(20), nullable=False, default="INFLUENCER")
    contact_id     = Column(UUID(as_uuid=True), ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True)  # M43.S01.T015
    notes          = Column(String(500), nullable=True)



# ── M36.S05.T002 landing pages and A/B tests ─────────────────────────────────────

class CRMLandingPage(Base, TimestampMixin):
    __tablename__ = "crm_landing_pages"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug         = Column(String(80), nullable=False, unique=True, index=True)
    name         = Column(String(150), nullable=False)
    status       = Column(String(8), nullable=False, default="DRAFT")       # DRAFT | LIVE | PAUSED
    lead_form_id = Column(UUID(as_uuid=True), ForeignKey("crm_lead_forms.id", ondelete="RESTRICT"), nullable=False)
    min_sample   = Column(Integer, nullable=False, default=100)              # views per variant before any verdict


class CRMLandingVariant(Base):
    __tablename__ = "crm_landing_variants"
    __table_args__ = (UniqueConstraint("page_id", "key", name="uq_crm_landing_variant_key"),)

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id   = Column(UUID(as_uuid=True), ForeignKey("crm_landing_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    key       = Column(String(4), nullable=False)                            # A = control, B, C …
    headline  = Column(String(200), nullable=False)
    body      = Column(Text, nullable=True)
    cta_label = Column(String(60), nullable=False, default="Send")
    weight    = Column(Integer, nullable=False, default=50)
    is_active = Column(Boolean, nullable=False, default=True)


class CRMLandingEvent(Base):
    __tablename__ = "crm_landing_events"
    __table_args__ = (UniqueConstraint("page_id", "visitor_hash", "kind", name="uq_crm_landing_event_once"),)

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id      = Column(UUID(as_uuid=True), ForeignKey("crm_landing_pages.id", ondelete="CASCADE"), nullable=False)
    variant_id   = Column(UUID(as_uuid=True), ForeignKey("crm_landing_variants.id", ondelete="CASCADE"), nullable=False, index=True)
    visitor_hash = Column(String(64), nullable=False)
    kind         = Column(String(8), nullable=False)                         # VIEW | CONVERT
    ip_hash      = Column(String(64), nullable=True, index=True)             # keyed hash of the connection (rate limit)
    created_at   = Column(DateTime(timezone=True), nullable=False)



# ── M36.S05.T004 conversation intelligence ───────────────────────────────────────

class CRMConversationInsight(Base):
    __tablename__ = "crm_conversation_insights"
    __table_args__ = (UniqueConstraint("source_type", "source_id", name="uq_crm_conversation_insight_source"),)

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type    = Column(String(8), nullable=False)                     # call | chat
    source_id      = Column(UUID(as_uuid=True), nullable=False)
    agent_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    findings       = Column(JSON, nullable=False, default=list)            # [{kind, label, quote, offset}]
    counts         = Column(JSON, nullable=False, default=dict)
    engine         = Column(String(12), nullable=False, default="rules")
    status         = Column(String(16), nullable=False, default="PENDING_REVIEW")   # PENDING_REVIEW | REVIEWED | REJECTED
    coaching_note  = Column(Text, nullable=True)
    analysed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    analysed_at    = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at    = Column(DateTime(timezone=True), nullable=True)



# ── M36.S03.T004 visual workflow designer ────────────────────────────────────────

class CRMWorkflow(Base, TimestampMixin):
    __tablename__ = "crm_workflows"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name                 = Column(String(150), nullable=False, unique=True)
    trigger_event        = Column(String(20), nullable=True)
    published_version_id = Column(UUID(as_uuid=True), nullable=True)
    enqueued_until       = Column(DateTime(timezone=True), nullable=True)
    created_by           = Column(String(100), nullable=True)


class CRMWorkflowVersion(Base):
    __tablename__ = "crm_workflow_versions"
    __table_args__ = (UniqueConstraint("workflow_id", "version_no", name="uq_crm_workflow_version_no"),
                      Index("uq_crm_workflow_one_published", "workflow_id", unique=True, postgresql_where=text("status = 'PUBLISHED'")))

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id     = Column(UUID(as_uuid=True), ForeignKey("crm_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no      = Column(Integer, nullable=False)
    graph           = Column(JSON, nullable=False)
    status          = Column(String(10), nullable=False, default="DRAFT")   # DRAFT | PUBLISHED | ARCHIVED
    created_by      = Column(String(100), nullable=True)
    created_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    published_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at    = Column(DateTime(timezone=True), nullable=True)


class CRMWorkflowRun(Base):
    __tablename__ = "crm_workflow_runs"
    __table_args__ = (UniqueConstraint("version_id", "event_key", name="uq_crm_workflow_run_event"),)

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id    = Column(UUID(as_uuid=True), ForeignKey("crm_workflow_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    crm_record_id = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="CASCADE"), nullable=False)
    event_key     = Column(String(120), nullable=False)
    current_node  = Column(String(40), nullable=True)
    waiting_node  = Column(String(40), nullable=True)
    status        = Column(String(16), nullable=False, default="RUNNING")   # RUNNING | WAITING | WAITING_APPROVAL | DONE | FAILED
    resume_at     = Column(DateTime(timezone=True), nullable=True, index=True)
    log           = Column(JSON, nullable=False, default=list)
    created_at    = Column(DateTime(timezone=True), nullable=False)
    finished_at   = Column(DateTime(timezone=True), nullable=True)


# ── M43.S01.T007 sales quotas and forecast snapshots ─────────────────────────

class SalesQuota(Base, TimestampMixin):
    __tablename__ = "sales_quotas"
    __table_args__ = (UniqueConstraint("scope_type", "scope_ref", "period_start", "period_end", "currency",
                                       name="uq_sales_quota_scope_period_currency"),)

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope_type    = Column(String(10), nullable=False)       # REP | TEAM | TERRITORY | COMPANY
    scope_ref     = Column(String(100), nullable=False)      # user id | sales_team_id | sales_region_id | company id
    scope_label   = Column(String(200), nullable=True)
    period_type   = Column(String(10), nullable=False)       # MONTH | QUARTER | YEAR | CUSTOM
    period_start  = Column(Date, nullable=False)
    period_end    = Column(Date, nullable=False)
    currency      = Column(String(10), nullable=False)
    target_amount = Column(Numeric(18, 2), nullable=False)
    company_id    = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    notes         = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class SalesQuotaSnapshot(Base):
    __tablename__ = "sales_quota_snapshots"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quota_id         = Column(UUID(as_uuid=True), ForeignKey("sales_quotas.id", ondelete="CASCADE"), nullable=False, index=True)
    taken_at         = Column(DateTime(timezone=True), nullable=False)
    actual_amount    = Column(Numeric(18, 2), nullable=False)
    commit_amount    = Column(Numeric(18, 2), nullable=False)
    best_case_amount = Column(Numeric(18, 2), nullable=False)
    pipeline_amount  = Column(Numeric(18, 2), nullable=False)
    projected_amount = Column(Numeric(18, 2), nullable=False)
    assumptions      = Column(JSON, nullable=False)


# ── M43.S01.T010 playbooks and deal plans ─────────────────────────────────────

class CRMPlaybook(Base, TimestampMixin):
    __tablename__ = "crm_playbooks"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id         = Column(UUID(as_uuid=True), nullable=False, index=True, default=uuid.uuid4)  # versions share it
    version           = Column(Integer, nullable=False, default=1)
    name              = Column(String(150), nullable=False)
    purpose           = Column(String(15), nullable=False)     # CALL | VISIT | QUALIFICATION | STAGE
    stage_id          = Column(UUID(as_uuid=True), ForeignKey("crm_pipeline_stages.id", ondelete="SET NULL"), nullable=True)
    guidance          = Column(Text, nullable=True)
    questions         = Column(JSON, nullable=False, default=list)
    blocks_stage_exit = Column(Boolean, nullable=False, default=False)
    status            = Column(String(16), nullable=False, default="DRAFT")   # DRAFT|PENDING_APPROVAL|PUBLISHED|RETIRED
    created_by_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at       = Column(DateTime(timezone=True), nullable=True)


class CRMPlaybookRun(Base):
    __tablename__ = "crm_playbook_runs"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playbook_id   = Column(UUID(as_uuid=True), ForeignKey("crm_playbooks.id", ondelete="RESTRICT"), nullable=False, index=True)
    crm_record_id = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    answers       = Column(JSON, nullable=False, default=dict)
    completed     = Column(Boolean, nullable=False, default=False)
    completed_at  = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False)


class CRMDealPlan(Base, TimestampMixin):
    """Mutual action plan for one deal; optionally shared with the customer contact."""
    __tablename__ = "crm_deal_plans"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id    = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="CASCADE"), nullable=False, unique=True)
    title            = Column(String(200), nullable=False)
    steps            = Column(JSON, nullable=False, default=list)    # [{id, title, owner us|customer, due_date, done}]
    shared           = Column(Boolean, nullable=False, default=False)
    share_token_hash = Column(String(64), nullable=True, unique=True)


# ── M43.S01.T015 standalone contacts, associations, lifecycle ─────────────────

class CRMContact(Base, TimestampMixin):
    __tablename__ = "crm_contacts"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name            = Column(String(200), nullable=False)
    email                = Column(String(254), nullable=True)       # stored lower-case; partial unique index
    phone                = Column(String(50), nullable=True)
    job_title            = Column(String(150), nullable=True)
    lifecycle_stage      = Column(String(12), nullable=True)
    language             = Column(String(8), nullable=True)      # e.g. en, sw (M45.S01.T024 locale blocks)
    lifecycle_changed_at = Column(DateTime(timezone=True), nullable=True)
    owner_user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    company_id           = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    source               = Column(String(60), nullable=True)
    notes                = Column(Text, nullable=True)


class CRMContactAssociation(Base):
    __tablename__ = "crm_contact_associations"
    __table_args__ = (UniqueConstraint("contact_id", "object_type", "object_id", "label", name="uq_contact_assoc"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id  = Column(UUID(as_uuid=True), ForeignKey("crm_contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    object_type = Column(String(20), nullable=False)    # customer | crm_record | ticket | quotation | sales_order
    object_id   = Column(UUID(as_uuid=True), nullable=False)
    label       = Column(String(20), nullable=False, default="primary")
    created_at  = Column(DateTime(timezone=True), nullable=False)


class CRMLifecycleHistory(Base):
    __tablename__ = "crm_lifecycle_history"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id    = Column(UUID(as_uuid=True), ForeignKey("crm_contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    from_stage    = Column(String(12), nullable=True)
    to_stage      = Column(String(12), nullable=False)
    source        = Column(String(60), nullable=False)
    reason        = Column(String(300), nullable=True)
    changed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    changed_at    = Column(DateTime(timezone=True), nullable=False)


# ── M43.S01.T016 teams, tags, saved views ─────────────────────────────────────

class CRMTeam(Base, TimestampMixin):
    __tablename__ = "crm_teams"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code            = Column(String(100), nullable=False, unique=True)    # = sales_team_id stored on records/orders
    name            = Column(String(150), nullable=False)
    parent_id       = Column(UUID(as_uuid=True), ForeignKey("crm_teams.id", ondelete="SET NULL"), nullable=True)
    manager_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    company_id      = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    active_flag     = Column(Boolean, nullable=False, default=True)


class CRMTeamMember(Base):
    __tablename__ = "crm_team_members"

    team_id = Column(UUID(as_uuid=True), ForeignKey("crm_teams.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role    = Column(String(10), nullable=False, default="member")    # member | manager


class CRMTag(Base):
    __tablename__ = "crm_tags"

    id    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name  = Column(String(60), nullable=False, unique=True)
    color = Column(String(20), nullable=True)


class CRMRecordTag(Base):
    __tablename__ = "crm_record_tags"

    crm_record_id = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="CASCADE"), primary_key=True)
    tag_id        = Column(UUID(as_uuid=True), ForeignKey("crm_tags.id", ondelete="CASCADE"), primary_key=True)


class CRMSavedView(Base, TimestampMixin):
    __tablename__ = "crm_saved_views"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name          = Column(String(120), nullable=False)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id       = Column(UUID(as_uuid=True), ForeignKey("crm_teams.id", ondelete="CASCADE"), nullable=True)
    view_type     = Column(String(10), nullable=False, default="list")   # list | board | calendar
    filters       = Column(JSON, nullable=False, default=dict)
    columns       = Column(JSON, nullable=False, default=list)
    calendar_field = Column(String(30), nullable=True)                    # expected_close_date | next_action_date


class CRMDealScoreHistory(Base):
    """M43.S01.T012: daily deal score snapshot (trend)."""
    __tablename__ = "crm_deal_score_history"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="CASCADE"), nullable=False, index=True)
    score         = Column(Integer, nullable=False)
    factors       = Column(JSON, nullable=False)
    computed_at   = Column(DateTime(timezone=True), nullable=False)


# ── M43.S01.T013 snippets and signatures ──────────────────────────────────────

class CRMSnippet(Base, TimestampMixin):
    __tablename__ = "crm_snippets"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name          = Column(String(120), nullable=False)
    shortcut      = Column(String(30), nullable=True)
    body          = Column(Text, nullable=False)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # None = shared


class CRMEmailSignature(Base, TimestampMixin):
    __tablename__ = "crm_email_signatures"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name       = Column(String(80), nullable=False)
    body       = Column(Text, nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)


# ── M43.S01.T014 routing, stage approvals, splits, handoffs ───────────────────

class CRMRoutingRule(Base, TimestampMixin):
    __tablename__ = "crm_routing_rules"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String(120), nullable=False)
    priority   = Column(Integer, nullable=False, default=100)
    active     = Column(Boolean, nullable=False, default=True)
    conditions = Column(JSON, nullable=False, default=dict)
    method     = Column(String(12), nullable=False, default="ROUND_ROBIN")   # ROUND_ROBIN | WEIGHTED | FIXED
    user_ids   = Column(JSON, nullable=False, default=list)
    weights    = Column(JSON, nullable=True)
    state      = Column(JSON, nullable=True)


class CRMStageApprovalRule(Base, TimestampMixin):
    __tablename__ = "crm_stage_approval_rules"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name                 = Column(String(120), nullable=False)
    stage_id             = Column(UUID(as_uuid=True), ForeignKey("crm_pipeline_stages.id", ondelete="CASCADE"), nullable=False)
    min_expected_revenue = Column(Numeric(18, 2), nullable=True)
    active               = Column(Boolean, nullable=False, default=True)


class CRMStageApprovalRequest(Base):
    __tablename__ = "crm_stage_approval_requests"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id   = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_id        = Column(UUID(as_uuid=True), ForeignKey("crm_pipeline_stages.id", ondelete="CASCADE"), nullable=False)
    rule_id         = Column(UUID(as_uuid=True), ForeignKey("crm_stage_approval_rules.id", ondelete="SET NULL"), nullable=True)
    requested_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status          = Column(String(10), nullable=False, default="PENDING")   # PENDING | APPROVED | REJECTED | CONSUMED
    approved_value  = Column(Numeric(18, 2), nullable=True)   # deal value the approval covered
    reason          = Column(String(300), nullable=True)
    decided_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    requested_at    = Column(DateTime(timezone=True), nullable=False)
    decided_at      = Column(DateTime(timezone=True), nullable=True)


class CRMDealSplit(Base):
    __tablename__ = "crm_deal_splits"

    crm_record_id = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="CASCADE"), primary_key=True)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    share_pct     = Column(Numeric(5, 2), nullable=False)


class CRMHandoff(Base):
    __tablename__ = "crm_handoffs"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crm_record_id = Column(UUID(as_uuid=True), ForeignKey("crm_records.id", ondelete="CASCADE"), nullable=False, unique=True)
    brief         = Column(JSON, nullable=False)
    status        = Column(String(12), nullable=False, default="OPEN")     # OPEN | ACKNOWLEDGED
    acknowledged_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=False)


# ── M44.S01.T001 visual e-mail designs ────────────────────────────────────────

class EmailDesign(Base, TimestampMixin):
    __tablename__ = "mkt_email_designs"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id     = Column(UUID(as_uuid=True), nullable=False, index=True, default=uuid.uuid4)
    version       = Column(Integer, nullable=False, default=1)
    name          = Column(String(150), nullable=False)
    preheader     = Column(String(200), nullable=True)
    document      = Column(JSON, nullable=False)                    # {"theme": {...}, "blocks": [...]}
    status        = Column(String(10), nullable=False, default="DRAFT")   # DRAFT | PUBLISHED | RETIRED
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class MailFeedbackEvent(Base):
    """M44.S01.T011 provider delivery/complaint event (verified), stored once per provider event id."""
    __tablename__ = "mail_feedback_events"
    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_mail_feedback_event"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider    = Column(String(20), nullable=False)
    event_id    = Column(String(200), nullable=False)
    kind        = Column(String(15), nullable=False)
    email       = Column(String(254), nullable=True)
    message_id  = Column(String(300), nullable=True)
    outbound_id = Column(UUID(as_uuid=True), ForeignKey("crm_outbound_messages.id", ondelete="SET NULL"), nullable=True)
    applied     = Column(Boolean, nullable=False, default=False)
    received_at = Column(DateTime(timezone=True), nullable=False)


class WebEvent(Base):
    """M44.S01.T009 first-party website event, collected only with analytics consent. The browser's random visitor id
    is stored only as a keyed hash; no IP, no full referrer URL, no query string except UTM fields."""
    __tablename__ = "web_events"
    __table_args__ = (UniqueConstraint("visitor_hash", "event_id", name="uq_web_event_visitor_event"),
                      Index("ix_web_events_time", "occurred_at"), Index("ix_web_events_visitor", "visitor_hash", "occurred_at"))

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_hash  = Column(String(64), nullable=False)
    session_id    = Column(String(64), nullable=False)     # keyed hash of the browser session id
    event_id      = Column(String(64), nullable=False)     # client id: the same event sent twice counts once
    kind          = Column(String(10), nullable=False)     # PAGE | FORM | CTA | CUSTOM
    name          = Column(String(100), nullable=True)
    path          = Column(String(300), nullable=False)
    referrer_host = Column(String(200), nullable=True)
    utm_source    = Column(String(100), nullable=True)
    utm_medium    = Column(String(100), nullable=True)
    utm_campaign  = Column(String(100), nullable=True)
    occurred_at   = Column(DateTime(timezone=True), nullable=False)


class WebIdentity(Base):
    """Visitor ↔ e-mail link, created only when the visitor gave marketing consent and told us the address."""
    __tablename__ = "web_identities"

    visitor_hash = Column(String(64), primary_key=True)
    email        = Column(String(254), nullable=False, index=True)
    linked_at    = Column(DateTime(timezone=True), nullable=False)
    verified_at  = Column(DateTime(timezone=True), nullable=True)   # set only when the visitor proved the address


class WebConsent(Base):
    """Cookie-banner decisions per visitor (append-only audit of what the visitor chose and when)."""
    __tablename__ = "web_consents"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_hash = Column(String(64), nullable=False, index=True)
    analytics    = Column(Boolean, nullable=False)
    marketing    = Column(Boolean, nullable=False)
    decided_at   = Column(DateTime(timezone=True), nullable=False)


class MarketingAudience(Base):
    """M44.S01.T010 rule-based dynamic audience. Membership is recomputed from the rules; only addresses with
    marketing consent become members when require_consent is set (the default)."""
    __tablename__ = "mkt_audiences"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name             = Column(String(150), nullable=False, unique=True)
    rules            = Column(JSON, nullable=False)          # {"all": [...conditions], "exclude": [...conditions]}
    require_consent  = Column(Boolean, nullable=False, default=True)
    member_count     = Column(Integer, nullable=False, default=0)
    blocked_count    = Column(Integer, nullable=False, default=0)   # matched but no consent / no e-mail
    computed_at      = Column(DateTime(timezone=True), nullable=True)
    created_by_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at       = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MarketingAudienceMember(Base):
    __tablename__ = "mkt_audience_members"

    audience_id = Column(UUID(as_uuid=True), ForeignKey("mkt_audiences.id", ondelete="CASCADE"), primary_key=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True)
    email       = Column(String(254), nullable=False)
    added_at    = Column(DateTime(timezone=True), nullable=False)



class AdAccount(Base):
    """M44.S01.T002–T005 an ad account on Meta / Google / LinkedIn / TikTok (reporting; no live writes)."""
    __tablename__ = "ads_accounts"
    __table_args__ = (UniqueConstraint("provider", "external_id", name="uq_ads_account_provider_ext"),)

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider       = Column(String(10), nullable=False)       # meta | google | linkedin | tiktok
    external_id    = Column(String(40), nullable=False)
    name           = Column(String(200), nullable=False)
    currency       = Column(String(3), nullable=False)
    time_zone      = Column(String(64), nullable=True)
    status         = Column(String(15), nullable=False, default="ACTIVE")   # ACTIVE | AUTH_FAILED | NO_ACCESS
    last_sync_at   = Column(DateTime(timezone=True), nullable=True)
    last_error     = Column(String(500), nullable=True)
    created_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AdCampaignDay(Base):
    """Daily campaign metrics from a platform report; re-syncing a day replaces it (idempotent)."""
    __tablename__ = "ads_campaign_days"
    __table_args__ = (UniqueConstraint("account_id", "campaign_id", "day", name="uq_ads_campaign_day"),)

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id    = Column(UUID(as_uuid=True), ForeignKey("ads_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id   = Column(String(40), nullable=False)
    campaign_name = Column(String(300), nullable=False)
    day           = Column(Date, nullable=False)
    impressions   = Column(BigInteger, nullable=False, default=0)
    clicks        = Column(BigInteger, nullable=False, default=0)
    spend         = Column(Numeric(16, 4), nullable=False, default=0)    # account currency
    conversions   = Column(Numeric(14, 2), nullable=False, default=0)


class AdDraft(Base):
    """A campaign draft prepared in the ERP: guardrail-checked, approved by a second editor, validated (validate-only
    on platforms that offer it). Publishing is refused until the owner activates ad accounts."""
    __tablename__ = "ads_drafts"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id      = Column(UUID(as_uuid=True), ForeignKey("ads_accounts.id", ondelete="CASCADE"), nullable=False)
    idempotency_key = Column(String(64), nullable=False, unique=True)
    name            = Column(String(200), nullable=False)
    objective       = Column(String(40), nullable=False)
    daily_budget    = Column(Numeric(14, 2), nullable=False)       # account currency
    start_date      = Column(Date, nullable=True)
    end_date        = Column(Date, nullable=True)
    status          = Column(String(10), nullable=False, default="DRAFT")   # DRAFT|PENDING|APPROVED|REJECTED
    requested_by    = Column(String(100), nullable=True)
    approved_by     = Column(String(100), nullable=True)
    validation      = Column(JSON, nullable=True)
    created_by      = Column(String(100), nullable=False)
    created_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())



class SocialChannel(Base):
    """M44.S01.T006–T008 a social account the company owns (page, profile, organisation)."""
    __tablename__ = "social_channels"
    __table_args__ = (UniqueConstraint("network", "external_id", name="uq_social_channel_network_ext"),)

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    network        = Column(String(12), nullable=False)    # facebook | instagram | linkedin | tiktok | x | youtube
    external_id    = Column(String(64), nullable=False)
    name           = Column(String(200), nullable=False)
    time_zone      = Column(String(64), nullable=False, default="Africa/Nairobi")
    listen_enabled = Column(Boolean, nullable=False, default=False)   # opt-in: only then comments/mentions are stored
    created_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SocialPost(Base):
    """A scheduled post: versioned (an edit after approval needs a new approval), published by the adapter when the
    channel and publishing are enabled, otherwise exported for manual posting. history = publishing log."""
    __tablename__ = "social_posts"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id       = Column(UUID(as_uuid=True), ForeignKey("social_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    idempotency_key  = Column(String(64), nullable=False, unique=True)
    text             = Column(Text, nullable=False)
    media            = Column(JSON, nullable=False, default=list)     # [{"url", "kind": image|video, ...}]
    link             = Column(String(500), nullable=True)
    campaign_tag     = Column(String(100), nullable=True, index=True)
    owner_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    scheduled_at     = Column(DateTime(timezone=True), nullable=True, index=True)
    time_zone        = Column(String(64), nullable=False, default="Africa/Nairobi")
    status           = Column(String(12), nullable=False, default="DRAFT")
    # DRAFT | PENDING | APPROVED | PUBLISHING | PUBLISHED | FAILED | CANCELLED | EXPORTED
    version          = Column(Integer, nullable=False, default=1)
    approved_version = Column(Integer, nullable=True)
    approved_by      = Column(String(100), nullable=True)
    external_post_id = Column(String(120), nullable=True)
    error            = Column(String(500), nullable=True)
    published_at     = Column(DateTime(timezone=True), nullable=True)
    history          = Column(JSON, nullable=False, default=list)
    created_by       = Column(String(100), nullable=False)
    created_at       = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SocialItem(Base):
    """An inbound comment / mention / message from an opted-in channel (webhook) or a manual import."""
    __tablename__ = "social_items"
    __table_args__ = (UniqueConstraint("network", "external_id", name="uq_social_item_network_ext"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id  = Column(UUID(as_uuid=True), ForeignKey("social_channels.id", ondelete="SET NULL"), nullable=True)
    network     = Column(String(12), nullable=False)
    kind        = Column(String(8), nullable=False)        # COMMENT | MENTION | MESSAGE
    external_id = Column(String(120), nullable=False)
    parent_id   = Column(String(120), nullable=True)       # post the comment belongs to
    author      = Column(String(200), nullable=True)
    text        = Column(Text, nullable=True)              # blanked when the author deletes it
    url         = Column(String(500), nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    source      = Column(String(8), nullable=False)        # WEBHOOK | IMPORT
    sentiment   = Column(String(8), nullable=True)         # POSITIVE | NEGATIVE | NEUTRAL
    topics      = Column(JSON, nullable=False, default=list)
    evidence    = Column(JSON, nullable=False, default=dict)   # words that led to the tags
    status      = Column(String(9), nullable=False, default="NEW")   # NEW | ASSIGNED | REPLIED | HIDDEN | DONE | DELETED
    assigned_to = Column(String(100), nullable=True)
    reply_draft = Column(Text, nullable=True)


# ── M44.S01.T013 messaging channels ──────────────────────────────────────────────

class CRMChannelMessage(Base):
    """One message of a Messenger / Instagram DM / custom-channel thread. Threads show in the unified inbox as
    channel + "<account>:<thread>"; external_id dedupes webhook replays and our own echoes."""
    __tablename__ = "crm_channel_messages"
    __table_args__ = (UniqueConstraint("channel", "external_id", name="uq_crm_channel_message_ext"),)

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel     = Column(String(10), nullable=False)          # MESSENGER | INSTAGRAM | CUSTOM
    account_id  = Column(String(64), nullable=False)          # page id / Instagram account id / custom channel key
    thread_id   = Column(String(120), nullable=False)         # PSID / IGSID / the custom channel's thread id
    external_id = Column(String(120), nullable=True)
    direction   = Column(String(3), nullable=False)           # IN | OUT
    sender      = Column(String(200), nullable=True)
    body        = Column(Text, nullable=False)
    status      = Column(String(9), nullable=False, default="RECEIVED")   # RECEIVED | SENT | QUEUED | DELIVERED | FAILED
    error       = Column(String(500), nullable=True)
    agent_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __mapper_args__ = {"eager_defaults": True}


Index("ix_crm_channel_messages_thread", CRMChannelMessage.channel, CRMChannelMessage.account_id, CRMChannelMessage.thread_id)


class CustomChannel(Base):
    """A channel the company connects itself (e.g. a partner app) through the custom channels API; the token is
    shown once and stored as SHA-256."""
    __tablename__ = "crm_custom_channels"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key         = Column(String(40), nullable=False, unique=True)
    name        = Column(String(120), nullable=False)
    token_hash  = Column(String(64), nullable=False)
    active      = Column(Boolean, nullable=False, default=True)
    created_by  = Column(String(100), nullable=False)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SlackDelivery(Base):
    """Each deal / ticket / approval notice goes to Slack once (unique kind + ref); failures retry a few times."""
    __tablename__ = "crm_slack_deliveries"
    __table_args__ = (UniqueConstraint("kind", "ref", name="uq_crm_slack_delivery"),)

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind       = Column(String(10), nullable=False)    # DEAL | TICKET | APPROVAL
    ref        = Column(String(200), nullable=False)
    text       = Column(String(1000), nullable=False)
    status     = Column(String(6), nullable=False, default="QUEUED")   # QUEUED | SENT | FAILED
    attempts   = Column(Integer, nullable=False, default=0)
    error      = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
