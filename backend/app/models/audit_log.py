import uuid
from sqlalchemy import Column, String, Text, ForeignKey, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    """Immutable audit trail for security-sensitive events."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Who did it (nullable for unauthenticated events like LOGIN_FAILED)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_email = Column(String(255), nullable=True)  # denormalized
    actor_name = Column(String(255), nullable=True)   # denormalized full name

    # Session context
    session_id = Column(String(100), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)

    # What happened
    event_type = Column(String(100), nullable=False, index=True)  # e.g. LOGIN_SUCCESS
    module = Column(String(100), nullable=True, index=True)       # inventory | sales | finance …

    # What was affected
    target_type = Column(String(50), nullable=True)   # user | role | permission | mpesa_payment
    target_id = Column(String(100), nullable=True)    # UUID str of the affected object
    target_name = Column(String(255), nullable=True)  # human-readable name

    # Before / after value tracking
    before_value = Column(JSONB, nullable=True)   # state before change
    after_value = Column(JSONB, nullable=True)    # state after change

    # Extra context
    details = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Tamper detection — SHA-256 of (id + event_type + actor_email + created_at + before + after)
    row_hash = Column(String(64), nullable=True)


class AuditRetentionPolicy(Base):
    """Configurable retention rules per module. Older logs auto-purged."""
    __tablename__ = "audit_retention_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module = Column(String(100), nullable=False, unique=True)
    retain_days = Column(Integer, nullable=False, default=365)
    active_flag = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)


# ── Event type constants ───────────────────────────────────────────────────────
class AuditEvent:
    # Auth
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"

    # User lifecycle
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_ACTIVATED = "USER_ACTIVATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    PASSWORD_RESET = "PASSWORD_RESET"

    # Role assignment on user
    USER_ROLE_ASSIGNED = "USER_ROLE_ASSIGNED"
    USER_ROLE_REMOVED = "USER_ROLE_REMOVED"

    # Role lifecycle
    ROLE_CREATED = "ROLE_CREATED"
    ROLE_UPDATED = "ROLE_UPDATED"
    ROLE_ACTIVATED = "ROLE_ACTIVATED"
    ROLE_DEACTIVATED = "ROLE_DEACTIVATED"

    # Permissions on role
    ROLE_PERMISSION_ASSIGNED = "ROLE_PERMISSION_ASSIGNED"
    ROLE_PERMISSION_REMOVED = "ROLE_PERMISSION_REMOVED"

    # M-Pesa
    MPESA_PAYMENT_INITIATED = "MPESA_PAYMENT_INITIATED"
    MPESA_PAYMENT_RETRIED = "MPESA_PAYMENT_RETRIED"
    MPESA_PAYMENT_CANCELLED = "MPESA_PAYMENT_CANCELLED"
    MPESA_PAYMENT_RECONCILED = "MPESA_PAYMENT_RECONCILED"
    MPESA_PAYMENT_VIEWED = "MPESA_PAYMENT_VIEWED"

    # Inventory
    STOCK_RECEIVED = "STOCK_RECEIVED"
    STOCK_ISSUED = "STOCK_ISSUED"
    STOCK_TRANSFERRED = "STOCK_TRANSFERRED"
    STOCK_ADJUSTED = "STOCK_ADJUSTED"
    STOCK_COUNT_COMPLETED = "STOCK_COUNT_COMPLETED"

    # Production
    PRODUCTION_ORDER_CREATED = "PRODUCTION_ORDER_CREATED"
    PRODUCTION_ORDER_STARTED = "PRODUCTION_ORDER_STARTED"
    PRODUCTION_ORDER_COMPLETED = "PRODUCTION_ORDER_COMPLETED"
    PRODUCTION_ORDER_CANCELLED = "PRODUCTION_ORDER_CANCELLED"
    MATERIAL_CONSUMED = "MATERIAL_CONSUMED"
    FINISHED_GOODS_RECEIVED = "FINISHED_GOODS_RECEIVED"

    # Sales & Finance
    INVOICE_CREATED = "INVOICE_CREATED"
    INVOICE_APPROVED = "INVOICE_APPROVED"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    JOURNAL_ENTRY_POSTED = "JOURNAL_ENTRY_POSTED"
    BUDGET_APPROVED = "BUDGET_APPROVED"

    # Procurement
    PO_CREATED = "PO_CREATED"
    PO_APPROVED = "PO_APPROVED"
    GRN_POSTED = "GRN_POSTED"

    # Shipment
    SHIPMENT_DISPATCHED = "SHIPMENT_DISPATCHED"
    SHIPMENT_DELIVERED = "SHIPMENT_DELIVERED"
    SHIPMENT_RETURNED = "SHIPMENT_RETURNED"

    # Security events
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_POLICY_VIOLATION = "PASSWORD_POLICY_VIOLATION"
    AI_INJECTION_DETECTED = "AI_INJECTION_DETECTED"
    AI_RECOMMENDATION_ACTIONED = "AI_RECOMMENDATION_ACTIONED"
    AI_RECOMMENDATION_DISMISSED = "AI_RECOMMENDATION_DISMISSED"

    # Business logic guards triggered
    MARGIN_FLOOR_OVERRIDE = "MARGIN_FLOOR_OVERRIDE"
    DUPLICATE_PAYMENT_BLOCKED = "DUPLICATE_PAYMENT_BLOCKED"
    STOCK_NEGATIVE_FLAGGED = "STOCK_NEGATIVE_FLAGGED"

    # Approvals
    EXPENSE_APPROVED = "EXPENSE_APPROVED"
    EXPENSE_REJECTED = "EXPENSE_REJECTED"
    CONTRACT_APPROVED = "CONTRACT_APPROVED"
    PRICE_OVERRIDE_APPROVED = "PRICE_OVERRIDE_APPROVED"
    PAYROLL_APPROVED = "PAYROLL_APPROVED"

    # 2FA
    TWO_FA_ENABLED = "TWO_FA_ENABLED"
    TWO_FA_DISABLED = "TWO_FA_DISABLED"
    TWO_FA_CHALLENGE_SENT = "TWO_FA_CHALLENGE_SENT"
    TWO_FA_SUCCESS = "TWO_FA_SUCCESS"
    TWO_FA_FAILED = "TWO_FA_FAILED"
    TWO_FA_STEPUP_SUCCESS = "TWO_FA_STEPUP_SUCCESS"
    TWO_FA_STEPUP_FAILED = "TWO_FA_STEPUP_FAILED"
    TWO_FA_RECOVERY_USED = "TWO_FA_RECOVERY_USED"
    TWO_FA_RECOVERY_FAILED = "TWO_FA_RECOVERY_FAILED"
    TWO_FA_RECOVERY_REGENERATED = "TWO_FA_RECOVERY_REGENERATED"
