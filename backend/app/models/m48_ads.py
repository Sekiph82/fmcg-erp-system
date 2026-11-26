"""M48.S01.T001–T004 ad mutation tables: campaign tree mirror, approvals bound to a budget version + payload hash,
the provider mutation ledger and per-account controls (admin activation, spend caps, credential-scoped members).

Separate from the M44 reporting tables in crm.py (ads_accounts, ads_campaign_days, ads_drafts), which stay unchanged.
"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class AdAccountControl(Base):
    """Fail-closed controls per ad account. No row = not activated, no caps, no members → no provider mutation."""
    __tablename__ = "ads_account_controls"

    account_id   = Column(UUID(as_uuid=True), ForeignKey("ads_accounts.id", ondelete="CASCADE"), primary_key=True)
    activated    = Column(Boolean, nullable=False, default=False)      # admin switch for LIVE mutations
    activated_by = Column(String(100), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    daily_cap    = Column(Numeric(14, 2), nullable=True)               # account currency, sum of daily budgets
    monthly_cap  = Column(Numeric(14, 2), nullable=True)               # account currency, daily sum × days in month
    members      = Column(JSON, nullable=False, default=list)          # usernames allowed to act on this account
    updated_at   = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class AdCampaignNode(Base):
    """One object of a campaign tree mirrored from (or to be created on) the provider.

    Levels per provider: meta CAMPAIGN→ADSET→CREATIVE→AD; google BUDGET→CAMPAIGN→ADSET(ad group)→AD(ad group ad);
    linkedin CAMPAIGN(campaign group)→ADSET(campaign)→AD(creative); tiktok CAMPAIGN→ADSET(ad group)→AD.
    The root row (root_id NULL) carries the tree state, budget and version; children carry their provider object."""
    __tablename__ = "ads_campaign_nodes"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id      = Column(UUID(as_uuid=True), ForeignKey("ads_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    root_id         = Column(UUID(as_uuid=True), ForeignKey("ads_campaign_nodes.id", ondelete="CASCADE"), nullable=True, index=True)
    parent_id       = Column(UUID(as_uuid=True), ForeignKey("ads_campaign_nodes.id", ondelete="CASCADE"), nullable=True)
    level           = Column(String(10), nullable=False)       # BUDGET | CAMPAIGN | ADSET | CREATIVE | AD
    position        = Column(Integer, nullable=False, default=0)
    idempotency_key = Column(String(64), nullable=True, unique=True)   # root only: wizard create key
    name            = Column(String(200), nullable=False)
    objective       = Column(String(40), nullable=True)
    spec            = Column(JSON, nullable=False, default=dict)
    daily_budget    = Column(Numeric(14, 2), nullable=True)    # root only, account currency
    budget_version  = Column(Integer, nullable=False, default=1)
    budget_pushed   = Column(Integer, nullable=False, default=0)   # last budget version sent to the provider
    op_seq          = Column(Integer, nullable=False, default=0)   # root: pause/resume counter for ledger keys
    status          = Column(String(20), nullable=False, default="DRAFT")
    mode            = Column(String(10), nullable=False, default="SIMULATED")   # SIMULATED | LIVE
    provider_id     = Column(String(160), nullable=True)
    provider_status = Column(String(60), nullable=True)        # as read back from the provider
    last_read_at    = Column(DateTime(timezone=True), nullable=True)
    last_error      = Column(String(500), nullable=True)
    validation      = Column(JSON, nullable=True)              # root: last validate result
    created_by      = Column(String(100), nullable=False)
    created_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class AdApproval(Base):
    """Second-person approval of one action on a tree, bound to the budget version and payload hash it was asked for.
    action: SUBMIT (create on provider) | BUDGET (push a new budget version) | RESUME (go live).
    status: PENDING | APPROVED | REJECTED | SUPERSEDED | USED."""
    __tablename__ = "ads_approvals"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    root_id        = Column(UUID(as_uuid=True), ForeignKey("ads_campaign_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    action         = Column(String(10), nullable=False)
    budget_version = Column(Integer, nullable=False)
    daily_budget   = Column(Numeric(14, 2), nullable=False)
    payload_hash   = Column(String(64), nullable=False)
    status         = Column(String(12), nullable=False, default="PENDING")
    requested_by   = Column(String(100), nullable=False)
    decided_by     = Column(String(100), nullable=True)
    decided_at     = Column(DateTime(timezone=True), nullable=True)
    created_at     = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AdMutation(Base):
    """Provider mutation ledger. The row is claimed (PENDING, committed) before the external call; an UNKNOWN outcome
    (timeout / 5xx after sending) is reconciled by read-back, never re-sent blindly.
    state: PENDING | SUCCEEDED | FAILED | UNKNOWN."""
    __tablename__ = "ads_mutations"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id      = Column(UUID(as_uuid=True), ForeignKey("ads_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id         = Column(UUID(as_uuid=True), ForeignKey("ads_campaign_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    operation       = Column(String(20), nullable=False)       # CREATE | STATUS | BUDGET
    idempotency_key = Column(String(160), nullable=False, unique=True)
    request_hash    = Column(String(64), nullable=False)
    mode            = Column(String(10), nullable=False)
    state           = Column(String(10), nullable=False, default="PENDING")
    provider_id     = Column(String(160), nullable=True)
    request         = Column(JSON, nullable=True)              # payload without credentials
    response        = Column(JSON, nullable=True)
    error           = Column(String(500), nullable=True)
    attempts        = Column(Integer, nullable=False, default=1)
    created_by      = Column(String(100), nullable=False)
    created_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
