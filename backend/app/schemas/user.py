from pydantic import BaseModel, EmailStr, field_validator, computed_field
from typing import Optional, List
import uuid

from app.schemas.role import RoleRead, RoleReadShort


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None
    role_ids: Optional[List[uuid.UUID]] = None


class UserRead(UserBase):
    id: uuid.UUID
    roles: List[RoleRead] = []

    @computed_field
    @property
    def permission_codes(self) -> List[str]:
        codes: set[str] = set()
        for role in self.roles:
            if role.is_active:
                for perm in role.permissions:
                    codes.add(perm.code)
        return sorted(codes)

    model_config = {"from_attributes": True}


class UserReadShort(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    full_name: str
    is_active: bool
    is_superuser: bool
    roles: List[RoleReadShort] = []

    model_config = {"from_attributes": True}


class PasswordReset(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class RoleAssign(BaseModel):
    role_ids: List[uuid.UUID]
