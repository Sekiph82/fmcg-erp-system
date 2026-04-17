from pydantic import BaseModel, field_validator
from typing import Optional
from decimal import Decimal
import uuid

from app.models.utilities import ConfigCategory


# ── SystemConfig ───────────────────────────────────────────────────────────────

class SystemConfigBase(BaseModel):
    key: str
    value: Optional[str] = None
    description: Optional[str] = None
    category: ConfigCategory = ConfigCategory.SYSTEM
    is_editable: bool = True


class SystemConfigCreate(SystemConfigBase):
    pass


class SystemConfigUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ConfigCategory] = None
    is_editable: Optional[bool] = None


class SystemConfigRead(SystemConfigBase):
    id: uuid.UUID
    updated_by_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


# ── UomConversion ──────────────────────────────────────────────────────────────

class UomConversionBase(BaseModel):
    from_uom: str
    to_uom: str
    factor: Decimal
    is_active: bool = True

    @field_validator("factor")
    @classmethod
    def factor_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Conversion factor must be positive")
        return v


class UomConversionCreate(UomConversionBase):
    pass


class UomConversionUpdate(BaseModel):
    factor: Optional[Decimal] = None
    is_active: Optional[bool] = None


class UomConversionRead(UomConversionBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}


# ── NumberSeries ───────────────────────────────────────────────────────────────

class NumberSeriesBase(BaseModel):
    module: str
    label: str
    prefix: str
    suffix: Optional[str] = None
    current_number: int = 0
    padding: int = 4
    is_active: bool = True


class NumberSeriesCreate(NumberSeriesBase):
    pass


class NumberSeriesUpdate(BaseModel):
    label: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    current_number: Optional[int] = None
    padding: Optional[int] = None
    is_active: Optional[bool] = None


class NumberSeriesRead(NumberSeriesBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class NextNumberResponse(BaseModel):
    module: str
    number: str
    sequence: int


# ── Currency ───────────────────────────────────────────────────────────────────

class CurrencyBase(BaseModel):
    code: str
    name: str
    symbol: str
    exchange_rate: Decimal = Decimal("1")
    is_base: bool = False
    is_active: bool = True


class CurrencyCreate(CurrencyBase):
    pass


class CurrencyUpdate(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    exchange_rate: Optional[Decimal] = None
    is_base: Optional[bool] = None
    is_active: Optional[bool] = None


class CurrencyRead(CurrencyBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}
