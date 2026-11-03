from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional
from decimal import Decimal
from datetime import date, datetime
import uuid

from app.models.master import (
    UnitOfMeasure,
    ProductCategory,
    MaterialType,
    WarehouseType,
    SupplierPaymentMethod,
    SupplierQualificationStatus,
    SupplierRiskLevel,
)


class MasterMergeRequest(BaseModel):
    survivor_id: uuid.UUID


class MasterMergeResult(BaseModel):
    entity_type: str
    source_id: uuid.UUID
    survivor_id: uuid.UUID
    source_is_active: bool
    lifecycle_event_id: uuid.UUID


# ── Supplier ──────────────────────────────────────────────────────────────────

class SupplierBase(BaseModel):
    code: str
    name: str
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms_days: int = 30
    is_active: bool = True
    preferred_payment_method: Optional[SupplierPaymentMethod] = None
    mpesa_phone_number: Optional[str] = None
    supplier_category: Optional[str] = None
    qualification_status: Optional[SupplierQualificationStatus] = None
    risk_level: Optional[SupplierRiskLevel] = None
    approved_from: Optional[date] = None
    approved_until: Optional[date] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierImportCreate(BaseModel):
    code: str
    name: str
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms_days: int = 30
    is_active: bool = True
    preferred_payment_method: Optional[SupplierPaymentMethod] = None
    mpesa_phone_number: Optional[str] = None
    supplier_category: Optional[str] = None
    risk_level: Optional[SupplierRiskLevel] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms_days: Optional[int] = None
    is_active: Optional[bool] = None
    preferred_payment_method: Optional[SupplierPaymentMethod] = None
    mpesa_phone_number: Optional[str] = None
    supplier_category: Optional[str] = None
    qualification_status: Optional[SupplierQualificationStatus] = None
    risk_level: Optional[SupplierRiskLevel] = None
    approved_from: Optional[date] = None
    approved_until: Optional[date] = None


class SupplierQualificationDecision(BaseModel):
    qualification_status: SupplierQualificationStatus
    approved_from: Optional[date] = None
    approved_until: Optional[date] = None
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_approval_window(self):
        if self.qualification_status == SupplierQualificationStatus.APPROVED:
            if self.approved_until and self.approved_from and self.approved_until < self.approved_from:
                raise ValueError("approved_until must be on or after approved_from")
        elif self.approved_from is not None or self.approved_until is not None:
            raise ValueError("Approval dates may only be set when approving a supplier")
        return self


class SupplierPreferenceDecision(BaseModel):
    is_preferred: bool
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value):
        return value.strip() if isinstance(value, str) else value


class SupplierRead(SupplierBase):
    id: uuid.UUID
    is_preferred: bool = False
    approved_by_id: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ── Product ───────────────────────────────────────────────────────────────────

class ProductBase(BaseModel):
    sku: str
    barcode: Optional[str] = None
    name: str
    description: Optional[str] = None
    category: ProductCategory
    uom: UnitOfMeasure = UnitOfMeasure.PCS
    units_per_carton: int = 1
    weight_kg: Optional[Decimal] = None
    shelf_life_days: Optional[int] = None
    reorder_point: Decimal = Decimal("0")
    minimum_run_qty: Optional[Decimal] = Field(default=None, gt=0)
    standard_cost: Optional[Decimal] = None
    standard_cost_currency: Optional[str] = Field(default=None, pattern=r"^[A-Z]{3}$")
    selling_price: Optional[Decimal] = None
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ProductCategory] = None
    uom: Optional[UnitOfMeasure] = None
    units_per_carton: Optional[int] = None
    weight_kg: Optional[Decimal] = None
    shelf_life_days: Optional[int] = None
    reorder_point: Optional[Decimal] = None
    minimum_run_qty: Optional[Decimal] = Field(default=None, gt=0)
    standard_cost: Optional[Decimal] = None
    standard_cost_currency: Optional[str] = Field(default=None, pattern=r"^[A-Z]{3}$")
    selling_price: Optional[Decimal] = None
    is_active: Optional[bool] = None


class ProductRead(ProductBase):
    id: uuid.UUID
    model_config = {"from_attributes": True}


# ── Material ──────────────────────────────────────────────────────────────────

class MaterialBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    material_type: MaterialType
    uom: UnitOfMeasure = UnitOfMeasure.KG
    weight_kg: Optional[Decimal] = None
    reorder_point: Decimal = Decimal("0")
    standard_cost: Optional[Decimal] = None
    lead_time_days: int = 0
    is_active: bool = True
    supplier_id: Optional[uuid.UUID] = None


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    material_type: Optional[MaterialType] = None
    uom: Optional[UnitOfMeasure] = None
    weight_kg: Optional[Decimal] = None
    reorder_point: Optional[Decimal] = None
    standard_cost: Optional[Decimal] = None
    lead_time_days: Optional[int] = None
    is_active: Optional[bool] = None
    supplier_id: Optional[uuid.UUID] = None


class MaterialRead(MaterialBase):
    id: uuid.UUID
    model_config = {"from_attributes": True}


# ── Warehouse ─────────────────────────────────────────────────────────────────

class WarehouseBase(BaseModel):
    code: str
    name: str
    warehouse_type: WarehouseType
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    capacity_sqm: Optional[Decimal] = None
    is_active: bool = True
    company_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    warehouse_type: Optional[WarehouseType] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    capacity_sqm: Optional[Decimal] = None
    is_active: Optional[bool] = None


class WarehouseRead(WarehouseBase):
    id: uuid.UUID
    model_config = {"from_attributes": True}
