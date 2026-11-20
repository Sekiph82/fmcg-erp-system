from __future__ import annotations
import uuid
import enum
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, Text, Date, DateTime,
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


# ── M36.S01.T002 sales sequences ──────────────────────────────────────────────

class CRMSequence(Base, TimestampMixin):
    __tablename__ = "crm_sequences"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(150), nullable=False, unique=True)
    active_flag = Column(Boolean, nullable=False, default=True)
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
