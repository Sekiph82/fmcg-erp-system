import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, Date, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base, TimestampMixin


class RecipeStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    OBSOLETE = "OBSOLETE"


class Recipe(Base, TimestampMixin):
    __tablename__ = "recipes"
    __table_args__ = (
        UniqueConstraint("product_id", "version", name="uq_recipe_product_version"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    version = Column(String(20), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(RecipeStatus), nullable=False, default=RecipeStatus.DRAFT)
    is_active = Column(Boolean, default=True, nullable=False)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    product = relationship("Product", foreign_keys=[product_id])
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    items = relationship(
        "RecipeItem",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeItem.line_no",
    )
    process_parameters = relationship(
        "ProcessParameter",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="ProcessParameter.step_no",
    )


class RecipeItem(Base, TimestampMixin):
    __tablename__ = "recipe_items"
    __table_args__ = (
        UniqueConstraint("recipe_id", "line_no", name="uq_recipe_item_line"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id", ondelete="RESTRICT"), nullable=False, index=True)
    line_no = Column(Integer, nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    unit = Column(String(20), nullable=False)
    loss_percentage = Column(Numeric(5, 2), default=0, nullable=False)
    is_optional = Column(Boolean, default=False, nullable=False)
    alternative_group = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)

    recipe = relationship("Recipe", back_populates="items")
    material = relationship("Material")


class ProcessParameter(Base, TimestampMixin):
    __tablename__ = "process_parameters"
    __table_args__ = (
        UniqueConstraint("recipe_id", "step_no", name="uq_process_param_step"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    step_no = Column(Integer, nullable=False)
    step_name = Column(String(255), nullable=False)
    target_temperature = Column(Numeric(7, 2), nullable=True)
    target_ph = Column(Numeric(5, 2), nullable=True)
    target_viscosity = Column(Numeric(10, 2), nullable=True)
    mixing_time_minutes = Column(Integer, nullable=True)
    rpm = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    recipe = relationship("Recipe", back_populates="process_parameters")
