from pydantic import BaseModel, EmailStr
from typing import Optional
from decimal import Decimal
import uuid

from app.models.master import UnitOfMeasure, ProductCategory, MaterialType, WarehouseType, SupplierPaymentMethod


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


class SupplierCreate(SupplierBase):
    pass


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


class SupplierRead(SupplierBase):
    id: uuid.UUID
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
    standard_cost: Optional[Decimal] = None
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
    standard_cost: Optional[Decimal] = None
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
