"""Brand Asset / Label Design Management (DAM) models."""
from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class AssetType(str, PyEnum):
    LABEL = "LABEL"
    ARTWORK = "ARTWORK"
    PACKAGING_DESIGN = "PACKAGING_DESIGN"
    LOGO = "LOGO"
    BRAND_GUIDELINE = "BRAND_GUIDELINE"
    PRODUCT_PHOTO = "PRODUCT_PHOTO"
    MARKETING_MATERIAL = "MARKETING_MATERIAL"


class AssetStatus(str, PyEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"
    PRINT_READY = "PRINT_READY"


class ApprovalStageStatus(str, PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


# Approval workflow: R&D → Regulatory → Marketing → Print
APPROVAL_STAGES = ["R&D", "Regulatory", "Marketing", "Print"]


class BrandAsset(Base):
    """Digital asset — label, artwork, packaging design with version control."""
    __tablename__ = "brand_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_ref = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(300), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False, default=AssetType.LABEL)
    brand = Column(String(200), nullable=True)
    product_name = Column(String(300), nullable=True)
    product_sku = Column(String(100), nullable=True, index=True)

    # Version control
    version = Column(Integer, nullable=False, default=1)
    is_latest = Column(Boolean, default=True, nullable=False)
    previous_version_id = Column(UUID(as_uuid=True), ForeignKey("brand_assets.id", ondelete="SET NULL"), nullable=True)
    change_notes = Column(Text, nullable=True)

    # Linked to BOM/recipe
    bom_version = Column(String(100), nullable=True)
    bom_id = Column(String(100), nullable=True)                  # soft link
    bom_change_flag = Column(Boolean, default=False, nullable=False)  # BOM changed, label needs update

    # File info
    file_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    file_format = Column(String(50), nullable=True)              # PDF | AI | PSD | PNG
    file_size_kb = Column(Integer, nullable=True)

    # Compliance checklist
    compliance_checklist = Column(JSONB, nullable=True)          # {allergen_declared: bool, nutrition_label: bool, ...}

    status = Column(Enum(AssetStatus), nullable=False, default=AssetStatus.DRAFT)
    created_by = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    approval_stages = relationship("AssetApprovalStage", back_populates="asset", cascade="all, delete-orphan",
                                   order_by="AssetApprovalStage.stage_order")
    previous_version = relationship("BrandAsset", remote_side="BrandAsset.id", foreign_keys=[previous_version_id])


class AssetApprovalStage(Base):
    """Per-stage approval gate in the R&D → Regulatory → Marketing → Print workflow."""
    __tablename__ = "asset_approval_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("brand_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_name = Column(String(100), nullable=False)             # R&D | Regulatory | Marketing | Print
    stage_order = Column(Integer, nullable=False)
    status = Column(Enum(ApprovalStageStatus), nullable=False, default=ApprovalStageStatus.PENDING)
    approved_by = Column(String(200), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    asset = relationship("BrandAsset", back_populates="approval_stages")
