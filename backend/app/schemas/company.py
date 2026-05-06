from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.company import CompanyUserRole


class BranchCreate(BaseModel):
    name:        str
    branch_code: str
    branch_type: Optional[str] = None
    address:     Optional[str] = None
    city:        Optional[str] = None
    phone:       Optional[str] = None
    is_default:  bool = False


class BranchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:          uuid.UUID
    company_id:  uuid.UUID
    name:        str
    branch_code: str
    branch_type: Optional[str]
    address:     Optional[str]
    city:        Optional[str]
    phone:       Optional[str]
    is_active:   bool
    is_default:  bool
    created_at:  datetime


class CompanyCreate(BaseModel):
    name:            str
    short_code:      str
    registration_no: Optional[str] = None
    tax_pin:         Optional[str] = None
    country:         str = "Kenya"
    base_currency:   str = "KES"
    address:         Optional[str] = None
    phone:           Optional[str] = None
    email:           Optional[str] = None
    website:         Optional[str] = None


class CompanyUpdate(BaseModel):
    name:            Optional[str] = None
    registration_no: Optional[str] = None
    tax_pin:         Optional[str] = None
    address:         Optional[str] = None
    phone:           Optional[str] = None
    email:           Optional[str] = None
    website:         Optional[str] = None
    logo_url:        Optional[str] = None
    is_active:       Optional[bool] = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              uuid.UUID
    name:            str
    short_code:      str
    registration_no: Optional[str]
    tax_pin:         Optional[str]
    country:         str
    base_currency:   str
    address:         Optional[str]
    phone:           Optional[str]
    email:           Optional[str]
    website:         Optional[str]
    logo_url:        Optional[str]
    is_active:       bool
    is_default:      bool
    created_at:      datetime
    branch_count:    int = 0
    user_count:      int = 0


class GrantUserAccess(BaseModel):
    user_id:    uuid.UUID
    role:       CompanyUserRole = CompanyUserRole.USER
    is_default: bool = False


class UserAccessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:         uuid.UUID
    user_id:    uuid.UUID
    company_id: uuid.UUID
    role:       CompanyUserRole
    is_default: bool
    username:   Optional[str] = None
    full_name:  Optional[str] = None
    created_at: datetime


class CompanySummary(BaseModel):
    company_id:       uuid.UUID
    company_name:     str
    short_code:       str
    base_currency:    str
    branch_count:     int
    user_count:       int
    # Financial snapshots (best-effort from available data)
    total_budgeted:   Decimal = Decimal("0")
    open_po_count:    int = 0
    open_so_count:    int = 0
    product_count:    int = 0
    warehouse_count:  int = 0
