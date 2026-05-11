import uuid
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin

# Association table: role <-> permission
role_permission = Table(
    "role_permission",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # code format: "{module}.{action}"  e.g. "inventory.view", "inventory.view_all"
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    module = Column(String(100), nullable=False)  # e.g. "inventory", "finance", "mpesa"
    action = Column(String(100), nullable=False)  # view | view_all | edit_own_scope | approve | export
    is_active = Column(Boolean, default=True, nullable=False)
    is_mobile_visible = Column(Boolean, default=True, nullable=False)

    roles = relationship("Role", secondary=role_permission, back_populates="permissions")


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_system_role = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    permissions = relationship("Permission", secondary=role_permission, back_populates="roles")
    users = relationship("User", secondary="user_role", back_populates="roles")
    access_scopes = relationship("AccessScope", back_populates="role", cascade="all, delete-orphan")


class AccessScope(Base, TimestampMixin):
    """Generic role/user access scope for ERP-wide scoped mutation rules."""

    __tablename__ = "access_scopes"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND role_id IS NULL) OR (user_id IS NULL AND role_id IS NOT NULL)",
            name="ck_access_scopes_exactly_one_owner",
        ),
        Index("ix_access_scopes_scope", "scope_type", "scope_id"),
        Index("ix_access_scopes_user_scope_type", "user_id", "scope_type"),
        Index("ix_access_scopes_role_scope_type", "role_id", "scope_type"),
        Index(
            "uq_access_scopes_user_scope",
            "user_id",
            "scope_type",
            "scope_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index(
            "uq_access_scopes_role_scope",
            "role_id",
            "scope_type",
            "scope_id",
            unique=True,
            postgresql_where=text("role_id IS NOT NULL"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=True, index=True)
    scope_type = Column(String(80), nullable=False)
    scope_id = Column(String(120), nullable=False)
    scope_name = Column(String(255), nullable=True)

    can_view = Column(Boolean, default=False, nullable=False)
    can_create = Column(Boolean, default=False, nullable=False)
    can_edit = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)
    can_approve = Column(Boolean, default=False, nullable=False)
    can_post = Column(Boolean, default=False, nullable=False)
    can_release = Column(Boolean, default=False, nullable=False)
    can_cancel = Column(Boolean, default=False, nullable=False)
    can_export = Column(Boolean, default=False, nullable=False)
    can_import = Column(Boolean, default=False, nullable=False)
    can_transfer = Column(Boolean, default=False, nullable=False)
    can_adjust = Column(Boolean, default=False, nullable=False)
    can_receive = Column(Boolean, default=False, nullable=False)
    can_dispatch = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="access_scopes")
    role = relationship("Role", back_populates="access_scopes")
