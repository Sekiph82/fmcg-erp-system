"""M50.S01.T007/T008/T012 tables: agent approval gates and reusable templates, atomic budget ledger and measured usage
log, AI evaluation runs. Evidence tables (gates, reservations, usage log, eval runs/results) need archive-on-downgrade."""
import uuid

from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class AIAgentGate(Base):
    """A human approval step of an agent run: the run is parked (job WAITING) with its state until a second person decides."""
    __tablename__ = "ai_agent_gates"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id       = Column(UUID(as_uuid=True), ForeignKey("ai_agent_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id      = Column(String(20), nullable=False)
    message      = Column(String(500), nullable=True)
    state        = Column(JSON, nullable=False)               # json-safe run context to resume from
    status       = Column(String(10), nullable=False, default="PENDING")   # PENDING | APPROVED | DENIED
    requested_by = Column(String(100), nullable=True)
    decided_by   = Column(String(100), nullable=True)
    decided_at   = Column(DateTime(timezone=True), nullable=True)
    resumed_at   = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AIAgentTemplate(Base):
    """A reusable, company-saved agent definition (the built-in templates stay in code)."""
    __tablename__ = "ai_agent_templates"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name            = Column(String(120), nullable=False, unique=True)
    description     = Column(String(500), nullable=True)
    definition      = Column(JSON, nullable=False)
    source_agent_id = Column(UUID(as_uuid=True), nullable=True)
    created_by      = Column(String(100), nullable=True)
    created_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AIBudgetCounter(Base):
    """Per scope and day: the cap and what is reserved (in flight) and spent. Reservations are conditional UPDATEs on this
    row, so concurrent workers serialize on the row lock and can never reserve past the cap."""
    __tablename__ = "ai_budget_counters"

    scope_type      = Column(String(10), primary_key=True)    # COMPANY | USER | AGENT
    scope_id        = Column(String(40), primary_key=True)
    day             = Column(Date, primary_key=True)
    cap_cost        = Column(Numeric(14, 6), nullable=False)
    reserved_cost   = Column(Numeric(14, 6), nullable=False, default=0)
    spent_cost      = Column(Numeric(14, 6), nullable=False, default=0)
    reserved_tokens = Column(Integer, nullable=False, default=0)
    spent_tokens    = Column(Integer, nullable=False, default=0)


class AIBudgetReservation(Base):
    __tablename__ = "ai_budget_reservations"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key = Column(String(150), nullable=False, unique=True)
    job_id          = Column(UUID(as_uuid=True), nullable=True, index=True)
    agent_id        = Column(String(40), nullable=False)
    user_id         = Column(String(40), nullable=True)
    day             = Column(Date, nullable=False)
    reserved_cost   = Column(Numeric(14, 6), nullable=False)
    reserved_tokens = Column(Integer, nullable=False)
    actual_cost     = Column(Numeric(14, 6), nullable=False, default=0)
    actual_tokens   = Column(Integer, nullable=False, default=0)
    status          = Column(String(10), nullable=False, default="RESERVED", index=True)  # RESERVED | SETTLED | RELEASED | EXPIRED
    worker_id       = Column(String(60), nullable=True)
    expires_at      = Column(DateTime(timezone=True), nullable=False)     # lease: past it the owner is presumed crashed
    settled_at      = Column(DateTime(timezone=True), nullable=True)
    note            = Column(String(300), nullable=True)
    created_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AIUsageLog(Base):
    """One row per model call attempt. source PROVIDER = tokens reported by the provider; ESTIMATE = text/4 estimate
    (deterministic template path, nothing was billed); SIMULATOR = local test simulator."""
    __tablename__ = "ai_usage_log"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id            = Column(UUID(as_uuid=True), nullable=True, index=True)
    reservation_id    = Column(UUID(as_uuid=True), nullable=True)
    agent_id          = Column(String(40), nullable=True)
    provider          = Column(String(30), nullable=False)
    model             = Column(String(80), nullable=False)
    source            = Column(String(10), nullable=False)
    prompt_tokens     = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    cost              = Column(Numeric(14, 6), nullable=False, default=0)
    latency_ms        = Column(Integer, nullable=False, default=0)
    outcome           = Column(String(20), nullable=False, default="OK")    # OK | RATE_LIMITED | ERROR
    retry_after_s     = Column(Numeric(10, 2), nullable=True)
    attempt           = Column(Integer, nullable=False, default=1)
    created_at        = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AIEvalRun(Base):
    __tablename__ = "ai_eval_runs"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    corpus_id      = Column(String(40), nullable=False, index=True)
    corpus_version = Column(String(20), nullable=False)
    corpus_sha256  = Column(String(64), nullable=False)
    adapter        = Column(String(40), nullable=False)
    model_id       = Column(String(80), nullable=False)
    provider       = Column(String(30), nullable=False)
    config         = Column(JSON, nullable=False)
    config_hash    = Column(String(64), nullable=False, index=True)
    data_kind      = Column(String(20), nullable=False, default="SYNTHETIC")   # SYNTHETIC now; REAL_CALIBRATION reserved
    real_calibration = Column(JSON, nullable=True)       # reserved for future real-world calibration, never set from synthetic runs
    status         = Column(String(12), nullable=False, default="DONE")        # DONE | UNAVAILABLE | FAILED
    total          = Column(Integer, nullable=False, default=0)
    passed         = Column(Integer, nullable=False, default=0)
    summary        = Column(JSON, nullable=True)         # per-scorer pass counts
    note           = Column(String(300), nullable=True)
    review_status  = Column(String(12), nullable=False, default="UNREVIEWED")  # UNREVIEWED | ACCEPTED | REJECTED
    reviewed_by    = Column(String(100), nullable=True)
    review_note    = Column(String(500), nullable=True)
    created_by     = Column(String(100), nullable=True)
    created_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AIEvalCaseResult(Base):
    __tablename__ = "ai_eval_case_results"
    __table_args__ = (UniqueConstraint("run_id", "case_id", name="uq_ai_eval_case"),)

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id     = Column(UUID(as_uuid=True), ForeignKey("ai_eval_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id    = Column(String(60), nullable=False)
    passed     = Column(Boolean, nullable=False)
    scores     = Column(JSON, nullable=False)      # {scorer: {"passed", "score", "detail"}}
    expected   = Column(JSON, nullable=True)
    actual     = Column(JSON, nullable=True)
    latency_ms = Column(Integer, nullable=False, default=0)
    tokens     = Column(Integer, nullable=False, default=0)
    cost       = Column(Numeric(14, 6), nullable=False, default=0)
    error      = Column(String(500), nullable=True)
