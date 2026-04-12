import uuid
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, Table
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
    # code format: "{module}.{action}"  e.g. "inventory.view", "mpesa.initiate_payment"
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    module = Column(String(100), nullable=False)   # e.g. "inventory", "finance", "mpesa"
    action = Column(String(100), nullable=False)   # view | create | edit | delete | approve | export | …
    is_mobile_visible = Column(Boolean, default=True, nullable=False)

    roles = relationship("Role", secondary=role_permission, back_populates="permissions")


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    permissions = relationship("Permission", secondary=role_permission, back_populates="roles")
    users = relationship("User", secondary="user_role", back_populates="roles")
