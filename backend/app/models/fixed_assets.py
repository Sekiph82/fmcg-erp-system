"""Fixed Asset Accounting + Depreciation models."""
import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Integer,
    ForeignKey, Enum, DateTime, Date, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base, TimestampMixin


# ── Enums ──────────────────────────────────────────────────────────────────────

class DepreciationMethod(str, enum.Enum):
    STRAIGHT_LINE        = "STRAIGHT_LINE"
    DECLINING_BALANCE    = "DECLINING_BALANCE"
    UNITS_OF_PRODUCTION  = "UNITS_OF_PRODUCTION"
    MANUAL               = "MANUAL"


class DepreciationFrequency(str, enum.Enum):
    MONTHLY   = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY    = "YEARLY"


class DepreciationStartRule(str, enum.Enum):
    CAPITALIZATION_DATE   = "CAPITALIZATION_DATE"
    IN_SERVICE_DATE       = "IN_SERVICE_DATE"
    FIRST_OF_NEXT_MONTH   = "FIRST_OF_NEXT_MONTH"


class FAAssetStatus(str, enum.Enum):
    DRAFT    = "DRAFT"
    ACTIVE   = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    IMPAIRED  = "IMPAIRED"
    DISPOSED  = "DISPOSED"
    RETIRED   = "RETIRED"
    ARCHIVED  = "ARCHIVED"


class ScheduleStatus(str, enum.Enum):
    PLANNED  = "PLANNED"
    POSTED   = "POSTED"
    REVERSED = "REVERSED"
    ADJUSTED = "ADJUSTED"


class AssetEventType(str, enum.Enum):
    ACQUISITION          = "ACQUISITION"
    CAPITALIZATION       = "CAPITALIZATION"
    TRANSFER             = "TRANSFER"
    REVALUATION          = "REVALUATION"
    IMPAIRMENT           = "IMPAIRMENT"
    REPAIR_CAPITALIZATION = "REPAIR_CAPITALIZATION"
    DEPRECIATION         = "DEPRECIATION"
    DISPOSAL             = "DISPOSAL"
    WRITEOFF             = "WRITEOFF"
    RETIREMENT           = "RETIREMENT"
    SUSPENSION           = "SUSPENSION"
    REACTIVATION         = "REACTIVATION"
    LEGACY_IMPORT        = "LEGACY_IMPORT"


class DisposalMethod(str, enum.Enum):
    SALE       = "SALE"
    RETIREMENT = "RETIREMENT"
    SCRAP      = "SCRAP"
    WRITEOFF   = "WRITEOFF"


class FAIAgentType(str, enum.Enum):
    RISK_MONITOR             = "RISK_MONITOR"
    DEPRECIATION_REVIEW      = "DEPRECIATION_REVIEW"
    CAPITALIZATION_CHECKER   = "CAPITALIZATION_CHECKER"


class FAIRecStatus(str, enum.Enum):
    PENDING      = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACTIONED     = "ACTIONED"
    DISMISSED    = "DISMISSED"


# ── Asset Category ─────────────────────────────────────────────────────────────

class FAAssetCategory(Base, TimestampMixin):
    __tablename__ = "fa_asset_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_code = Column(String(30), unique=True, nullable=False, index=True)
    category_name = Column(String(200), nullable=False)
    default_depreciation_method = Column(Enum(DepreciationMethod), nullable=False, default=DepreciationMethod.STRAIGHT_LINE)
    default_useful_life_months  = Column(Integer, nullable=True)
    default_salvage_value_pct   = Column(Numeric(8, 4), nullable=True, default=0)
    capitalization_threshold    = Column(Numeric(18, 4), nullable=True)
    depreciation_start_rule     = Column(Enum(DepreciationStartRule), nullable=False, default=DepreciationStartRule.FIRST_OF_NEXT_MONTH)
    # GL accounts (free-text codes — foreign key to ChartOfAccount optional)
    asset_account               = Column(String(30), nullable=True)
    accum_depreciation_account  = Column(String(30), nullable=True)
    depreciation_expense_account= Column(String(30), nullable=True)
    disposal_gain_account       = Column(String(30), nullable=True)
    disposal_loss_account       = Column(String(30), nullable=True)
    impairment_account          = Column(String(30), nullable=True)
    revaluation_reserve_account = Column(String(30), nullable=True)
    maintenance_integration     = Column(Boolean, default=False)
    is_active                   = Column(Boolean, default=True)
    notes                       = Column(Text, nullable=True)

    assets = relationship("FAFixedAsset", back_populates="category")


# ── Fixed Asset Master ─────────────────────────────────────────────────────────

class FAFixedAsset(Base, TimestampMixin):
    __tablename__ = "fa_fixed_assets"
    __table_args__ = (UniqueConstraint("asset_code", name="uq_fa_asset_code"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_code      = Column(String(50), nullable=False, index=True)
    asset_name      = Column(String(255), nullable=False)
    asset_category_id = Column(UUID(as_uuid=True), ForeignKey("fa_asset_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    asset_type      = Column(String(100), nullable=True)
    serial_no       = Column(String(100), nullable=True)
    asset_tag_no    = Column(String(100), nullable=True)
    # Links
    physical_asset_id     = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    procurement_reference_type = Column(String(50), nullable=True)
    procurement_reference_id   = Column(UUID(as_uuid=True), nullable=True)
    supplier_id     = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    # Dates
    acquisition_date     = Column(Date, nullable=True)
    in_service_date      = Column(Date, nullable=True)
    capitalization_date  = Column(Date, nullable=True)
    depreciation_start_date = Column(Date, nullable=True)
    depreciation_end_date   = Column(Date, nullable=True)
    # Cost
    original_cost     = Column(Numeric(18, 4), nullable=False)
    currency          = Column(String(3), nullable=False, default="KES")
    exchange_rate     = Column(Numeric(12, 6), nullable=False, default=1)
    local_currency_cost = Column(Numeric(18, 4), nullable=False)
    salvage_value     = Column(Numeric(18, 4), nullable=False, default=0)
    depreciable_base  = Column(Numeric(18, 4), nullable=False)   # cost - salvage
    # Depreciation parameters
    useful_life_months        = Column(Integer, nullable=True)
    depreciation_method       = Column(Enum(DepreciationMethod), nullable=False, default=DepreciationMethod.STRAIGHT_LINE)
    depreciation_frequency    = Column(Enum(DepreciationFrequency), nullable=False, default=DepreciationFrequency.MONTHLY)
    declining_balance_rate    = Column(Numeric(8, 4), nullable=True)  # for DB method
    total_production_units    = Column(Numeric(18, 4), nullable=True)  # for UoP method
    # NBV tracking
    accumulated_depreciation  = Column(Numeric(18, 4), nullable=False, default=0)
    net_book_value            = Column(Numeric(18, 4), nullable=False)
    last_depreciation_date    = Column(Date, nullable=True)
    # Status / location
    status          = Column(Enum(FAAssetStatus), nullable=False, default=FAAssetStatus.DRAFT, index=True)
    location        = Column(String(200), nullable=True)
    warehouse_id    = Column(UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    plant           = Column(String(100), nullable=True)
    department      = Column(String(100), nullable=True)
    cost_center     = Column(String(100), nullable=True)
    custodian_employee_id = Column(UUID(as_uuid=True), ForeignKey("hr_employees.id", ondelete="SET NULL"), nullable=True)
    condition_status = Column(String(50), nullable=True)
    is_legacy_import = Column(Boolean, default=False)
    legacy_accumulated_depreciation = Column(Numeric(18, 4), nullable=True)
    notes           = Column(Text, nullable=True)

    category      = relationship("FAAssetCategory", back_populates="assets")
    physical_asset = relationship("Asset", foreign_keys=[physical_asset_id])
    supplier      = relationship("Supplier", foreign_keys=[supplier_id])
    warehouse     = relationship("Warehouse", foreign_keys=[warehouse_id])
    custodian     = relationship("Employee", foreign_keys=[custodian_employee_id])
    schedule_lines = relationship("FADepreciationSchedule", back_populates="asset", cascade="all, delete-orphan", order_by="FADepreciationSchedule.period_start")
    events        = relationship("FAAssetEvent", back_populates="asset", cascade="all, delete-orphan", order_by="FAAssetEvent.event_date")
    components    = relationship("FAAssetComponent", back_populates="parent_asset", cascade="all, delete-orphan")
    ai_recs       = relationship("FAAIRecommendation", back_populates="asset", cascade="all, delete-orphan")


# ── Depreciation Schedule ──────────────────────────────────────────────────────

class FADepreciationSchedule(Base, TimestampMixin):
    __tablename__ = "fa_depreciation_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id         = Column(UUID(as_uuid=True), ForeignKey("fa_fixed_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    period_start     = Column(Date, nullable=False)
    period_end       = Column(Date, nullable=False)
    scheduled_amount = Column(Numeric(18, 4), nullable=False)
    posted_amount    = Column(Numeric(18, 4), nullable=True)
    posting_date     = Column(Date, nullable=True)
    journal_entry_id = Column(UUID(as_uuid=True), nullable=True)
    schedule_status  = Column(Enum(ScheduleStatus, name="assets_schedulestatus"), nullable=False, default=ScheduleStatus.PLANNED, index=True)
    opening_nbv      = Column(Numeric(18, 4), nullable=False)
    closing_nbv      = Column(Numeric(18, 4), nullable=False)
    actual_production_units = Column(Numeric(18, 4), nullable=True)
    notes            = Column(Text, nullable=True)

    asset = relationship("FAFixedAsset", back_populates="schedule_lines")


# ── Asset Events / History ─────────────────────────────────────────────────────

class FAAssetEvent(Base, TimestampMixin):
    __tablename__ = "fa_asset_events"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id       = Column(UUID(as_uuid=True), ForeignKey("fa_fixed_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type     = Column(Enum(AssetEventType), nullable=False, index=True)
    event_date     = Column(Date, nullable=False)
    reference_type = Column(String(50), nullable=True)
    reference_id   = Column(UUID(as_uuid=True), nullable=True)
    amount         = Column(Numeric(18, 4), nullable=True)
    nbv_before     = Column(Numeric(18, 4), nullable=True)
    nbv_after      = Column(Numeric(18, 4), nullable=True)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason         = Column(String(500), nullable=True)
    notes          = Column(Text, nullable=True)

    asset       = relationship("FAFixedAsset", back_populates="events")
    user        = relationship("User", foreign_keys=[user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])


# ── Asset Disposal Record ──────────────────────────────────────────────────────

class FAAssetDisposal(Base, TimestampMixin):
    __tablename__ = "fa_asset_disposals"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id         = Column(UUID(as_uuid=True), ForeignKey("fa_fixed_assets.id", ondelete="RESTRICT"), nullable=False, unique=True)
    disposal_method  = Column(Enum(DisposalMethod), nullable=False)
    disposal_date    = Column(Date, nullable=False)
    sale_proceeds    = Column(Numeric(18, 4), nullable=True, default=0)
    nbv_at_disposal  = Column(Numeric(18, 4), nullable=False)
    cost_at_disposal = Column(Numeric(18, 4), nullable=False)
    accum_depr_at_disposal = Column(Numeric(18, 4), nullable=False)
    gain_loss        = Column(Numeric(18, 4), nullable=False)
    journal_entry_id = Column(UUID(as_uuid=True), nullable=True)
    buyer_name       = Column(String(255), nullable=True)
    reason           = Column(String(500), nullable=True)
    approved_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes            = Column(Text, nullable=True)

    asset       = relationship("FAFixedAsset")
    approved_by = relationship("User", foreign_keys=[approved_by_id])


# ── Asset Components ───────────────────────────────────────────────────────────

class FAAssetComponent(Base, TimestampMixin):
    __tablename__ = "fa_asset_components"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_asset_id       = Column(UUID(as_uuid=True), ForeignKey("fa_fixed_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    component_name        = Column(String(255), nullable=False)
    component_cost        = Column(Numeric(18, 4), nullable=False)
    salvage_value         = Column(Numeric(18, 4), nullable=False, default=0)
    useful_life_months    = Column(Integer, nullable=True)
    depreciation_method   = Column(Enum(DepreciationMethod), nullable=False, default=DepreciationMethod.STRAIGHT_LINE)
    in_service_date       = Column(Date, nullable=True)
    accumulated_depreciation = Column(Numeric(18, 4), nullable=False, default=0)
    net_book_value        = Column(Numeric(18, 4), nullable=False)
    is_active             = Column(Boolean, default=True)
    notes                 = Column(Text, nullable=True)

    parent_asset = relationship("FAFixedAsset", back_populates="components")


# ── AI Recommendations ─────────────────────────────────────────────────────────

class FAAIRecommendation(Base, TimestampMixin):
    __tablename__ = "fa_ai_recommendations"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id    = Column(UUID(as_uuid=True), ForeignKey("fa_fixed_assets.id", ondelete="CASCADE"), nullable=True, index=True)
    agent_type  = Column(Enum(FAIAgentType), nullable=False, index=True)
    status      = Column(Enum(FAIRecStatus), nullable=False, default=FAIRecStatus.PENDING, index=True)
    title       = Column(String(300), nullable=False)
    detail      = Column(Text, nullable=False)
    severity    = Column(String(20), nullable=True)  # info / warning / critical
    action_taken= Column(Text, nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    asset = relationship("FAFixedAsset", back_populates="ai_recs")
