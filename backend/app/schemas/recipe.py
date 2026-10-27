from pydantic import BaseModel, Field, field_validator, model_validator
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
    version: str = Field(min_length=1, max_length=20)
    name: str
    description: Optional[str] = None
    is_active: bool = True
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None

    @field_validator("version")
    @classmethod
    def version_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Recipe version must not be blank.")
        return value

    @model_validator(mode="after")
    def effective_window_must_be_ordered(self):
        validate_recipe_effective_window(self.valid_from, self.valid_to)
        return self


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None

    @model_validator(mode="after")
    def supplied_effective_window_must_be_ordered(self):
        if self.valid_from is not None and self.valid_to is not None:
            validate_recipe_effective_window(self.valid_from, self.valid_to)
        return self


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
    new_version: str = Field(min_length=1, max_length=20)
    new_name: Optional[str] = None

    @field_validator("new_version")
    @classmethod
    def version_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Recipe version must not be blank.")
        return value


def validate_recipe_effective_window(valid_from: Optional[date], valid_to: Optional[date]) -> None:
    """Validate an inclusive recipe date window; a missing endpoint is unbounded."""
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        raise ValueError("Recipe valid_to must be on or after valid_from.")


def validate_recipe_update_window(
    current_valid_from: Optional[date],
    current_valid_to: Optional[date],
    changes: dict,
) -> None:
    """Validate the resulting window for a partial update, including explicit nulls."""
    validate_recipe_effective_window(
        changes.get("valid_from", current_valid_from),
        changes.get("valid_to", current_valid_to),
    )
