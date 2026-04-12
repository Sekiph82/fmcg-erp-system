from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import date
import uuid

from app.models.recipe import RecipeStatus


# ── Recipe Item ───────────────────────────────────────────────────────────────

class RecipeItemBase(BaseModel):
    material_id: uuid.UUID
    line_no: int
    quantity: Decimal
    unit: str
    loss_percentage: Decimal = Decimal("0")
    is_optional: bool = False
    alternative_group: Optional[str] = None
    notes: Optional[str] = None


class RecipeItemCreate(RecipeItemBase):
    pass


class RecipeItemUpdate(BaseModel):
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    loss_percentage: Optional[Decimal] = None
    is_optional: Optional[bool] = None
    alternative_group: Optional[str] = None
    notes: Optional[str] = None


class RecipeItemRead(RecipeItemBase):
    id: uuid.UUID
    recipe_id: uuid.UUID
    material_name: Optional[str] = None
    material_code: Optional[str] = None
    model_config = {"from_attributes": True}


# ── Process Parameter ─────────────────────────────────────────────────────────

class ProcessParameterBase(BaseModel):
    step_no: int
    step_name: str
    target_temperature: Optional[Decimal] = None
    target_ph: Optional[Decimal] = None
    target_viscosity: Optional[Decimal] = None
    mixing_time_minutes: Optional[int] = None
    rpm: Optional[int] = None
    notes: Optional[str] = None


class ProcessParameterCreate(ProcessParameterBase):
    pass


class ProcessParameterUpdate(BaseModel):
    step_name: Optional[str] = None
    target_temperature: Optional[Decimal] = None
    target_ph: Optional[Decimal] = None
    target_viscosity: Optional[Decimal] = None
    mixing_time_minutes: Optional[int] = None
    rpm: Optional[int] = None
    notes: Optional[str] = None


class ProcessParameterRead(ProcessParameterBase):
    id: uuid.UUID
    recipe_id: uuid.UUID
    model_config = {"from_attributes": True}


# ── Recipe Header ─────────────────────────────────────────────────────────────

class RecipeBase(BaseModel):
    product_id: uuid.UUID
    version: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


class RecipeRead(RecipeBase):
    id: uuid.UUID
    status: RecipeStatus
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    model_config = {"from_attributes": True}


class RecipeDetailRead(RecipeRead):
    items: List[RecipeItemRead] = []
    process_parameters: List[ProcessParameterRead] = []


# ── Duplicate Request ─────────────────────────────────────────────────────────

class RecipeDuplicateRequest(BaseModel):
    new_version: str
    new_name: Optional[str] = None
