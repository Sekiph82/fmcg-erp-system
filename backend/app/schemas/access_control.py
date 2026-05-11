from typing import Literal, Optional
import uuid

from pydantic import BaseModel, field_validator


SCOPE_ACTION_FIELDS = (
    "can_view",
    "can_create",
    "can_edit",
    "can_delete",
    "can_approve",
    "can_post",
    "can_release",
    "can_cancel",
    "can_export",
    "can_import",
    "can_transfer",
    "can_adjust",
    "can_receive",
    "can_dispatch",
)


class AccessScopeBase(BaseModel):
    scope_type: str
    scope_id: str
    scope_name: Optional[str] = None
    can_view: bool = False
    can_create: bool = False
    can_edit: bool = False
    can_delete: bool = False
    can_approve: bool = False
    can_post: bool = False
    can_release: bool = False
    can_cancel: bool = False
    can_export: bool = False
    can_import: bool = False
    can_transfer: bool = False
    can_adjust: bool = False
    can_receive: bool = False
    can_dispatch: bool = False
    is_active: bool = True

    @field_validator("scope_type")
    @classmethod
    def normalize_scope_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("scope_type is required")
        return normalized

    @field_validator("scope_id")
    @classmethod
    def normalize_scope_id(cls, value: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("scope_id is required")
        return normalized


class AccessScopeCreate(AccessScopeBase):
    user_id: Optional[uuid.UUID] = None
    role_id: Optional[uuid.UUID] = None

    @field_validator("role_id")
    @classmethod
    def require_exactly_one_owner(cls, value: Optional[uuid.UUID], info):
        user_id = info.data.get("user_id")
        if bool(user_id) == bool(value):
            raise ValueError("Exactly one of user_id or role_id is required")
        return value


class AccessScopeUpdate(BaseModel):
    scope_name: Optional[str] = None
    can_view: Optional[bool] = None
    can_create: Optional[bool] = None
    can_edit: Optional[bool] = None
    can_delete: Optional[bool] = None
    can_approve: Optional[bool] = None
    can_post: Optional[bool] = None
    can_release: Optional[bool] = None
    can_cancel: Optional[bool] = None
    can_export: Optional[bool] = None
    can_import: Optional[bool] = None
    can_transfer: Optional[bool] = None
    can_adjust: Optional[bool] = None
    can_receive: Optional[bool] = None
    can_dispatch: Optional[bool] = None
    is_active: Optional[bool] = None


class AccessScopeAssign(AccessScopeBase):
    pass


class AccessScopeAssignList(BaseModel):
    scopes: list[AccessScopeAssign]


class AccessScopeRead(AccessScopeBase):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    role_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class EffectiveAccessScopeRead(AccessScopeBase):
    source: Literal["user", "role"]

    model_config = {"from_attributes": True}
