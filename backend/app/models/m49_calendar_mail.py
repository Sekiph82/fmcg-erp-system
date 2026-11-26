"""M49.S01.T001-T003 tables: recurring meeting series, calendar change subscriptions, shared / delegated mailboxes.

Occurrences of a series are ordinary meeting_records rows (so double-booking checks, busy time, reminders and the
meeting list keep working); meeting_series_occurrences ties each one to its series and original date.
Secrets (channel tokens / clientState) are stored only as SHA-256 digests.
"""
import uuid

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base, TimestampMixin


class MeetingSeries(Base, TimestampMixin):
    __tablename__ = "meeting_series"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(300), nullable=False)
    platform = Column(String(30), nullable=False, default="jitsi")
    meeting_url = Column(String(500), nullable=True)
    time_zone = Column(String(64), nullable=False)
    start_local = Column(DateTime, nullable=False)          # wall time of the first occurrence in time_zone (naive)
    duration_minutes = Column(Integer, nullable=False, default=60)
    rrule = Column(String(500), nullable=False)             # validated subset, UNTIL stored as naive local YYYYMMDDTHHMMSS
    agenda = Column(Text, nullable=True)
    attendees = Column(JSON, nullable=False, default=list)  # [{name, email, response}]
    status = Column(String(20), nullable=False, default="ACTIVE")       # ACTIVE | CANCELLED
    sequence = Column(Integer, nullable=False, default=0, server_default="0")        # iCalendar SEQUENCE of the series
    invited_sequence = Column(Integer, nullable=True)       # sequence last e-mailed: one invitation per change


class MeetingSeriesOccurrence(Base):
    __tablename__ = "meeting_series_occurrences"
    __table_args__ = (UniqueConstraint("series_id", "occ_date", name="uq_series_occ_date"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    series_id = Column(UUID(as_uuid=True), ForeignKey("meeting_series.id", ondelete="CASCADE"), nullable=False, index=True)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey("meeting_records.id", ondelete="CASCADE"), nullable=False, unique=True)
    occ_date = Column(String(10), nullable=False)           # local date this occurrence originally fell on (RECURRENCE-ID)
    is_exception = Column(Boolean, nullable=False, default=False)      # edited / moved / cancelled on its own
    exc_pushed_sequence = Column(Integer, nullable=True)    # meeting.sequence last written to the provider as an exception


class MeetingSeriesCalendarLink(Base):
    __tablename__ = "meeting_series_calendar_links"
    __table_args__ = (UniqueConstraint("series_id", "connection_id", name="uq_series_conn"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    series_id = Column(UUID(as_uuid=True), ForeignKey("meeting_series.id", ondelete="CASCADE"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="CASCADE"), nullable=False)
    external_event_id = Column(String(1024), nullable=True)
    pushed_sequence = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CalendarSubscription(Base, TimestampMixin):
    """Google events.watch channel or Microsoft Graph subscription for one connected calendar."""
    __tablename__ = "calendar_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(20), nullable=False)           # google | microsoft
    channel_id = Column(String(256), nullable=False, unique=True)      # Google channel id / Graph subscription id
    resource_id = Column(String(256), nullable=True)        # Google resourceId (needed to stop the channel)
    token_hash = Column(String(64), nullable=False)         # SHA-256 of the channel token / clientState
    notification_url = Column(String(500), nullable=False)
    lifecycle_url = Column(String(500), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")      # ACTIVE | EXPIRED | FAILED | STOPPED
    environment = Column(String(12), nullable=False, default="SIMULATED")   # SIMULATED (local simulator) | LIVE
    last_message_number = Column(BigInteger, nullable=True)
    last_notification_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(String(500), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)


class CalendarWebhookReceipt(Base):
    """Replay guard: one row per notification already processed."""
    __tablename__ = "calendar_webhook_receipts"
    __table_args__ = (UniqueConstraint("subscription_id", "dedupe_key", name="uq_cal_receipt"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("calendar_subscriptions.id", ondelete="CASCADE"), nullable=False)
    dedupe_key = Column(String(64), nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SharedMailbox(Base, TimestampMixin):
    __tablename__ = "shared_mailboxes"
    __table_args__ = (UniqueConstraint("provider", "address", name="uq_shared_mailbox_addr"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(20), nullable=False)           # google | microsoft
    address = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    kind = Column(String(12), nullable=False, default="shared")       # shared | delegated
    status = Column(String(20), nullable=False, default="ACTIVE")     # ACTIVE | REVOKED | ACCESS_LOST
    connection_id = Column(UUID(as_uuid=True), ForeignKey("oauth_connections.id", ondelete="SET NULL"), nullable=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("email_accounts.id", ondelete="SET NULL"), nullable=True)
    sync_cursor = Column(JSONB, nullable=True)              # own cursor: never the registrant's personal cursor
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(String(500), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class SharedMailboxMember(Base):
    __tablename__ = "shared_mailbox_members"
    __table_args__ = (UniqueConstraint("mailbox_id", "user_id", name="uq_shared_mailbox_member"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mailbox_id = Column(UUID(as_uuid=True), ForeignKey("shared_mailboxes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    can_send = Column(Boolean, nullable=False, default=False)
    send_mode = Column(String(20), nullable=False, default="send_as")      # send_as | on_behalf
    granted_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    granted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
