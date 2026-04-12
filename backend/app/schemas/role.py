from pydantic import BaseModel
from typing import Optional, List
import uuid


class PermissionBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    module: str
    action: str
    is_mobile_visible: bool = True


class PermissionCreate(PermissionBase):
    pass


class PermissionRead(PermissionBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permission_ids: List[uuid.UUID] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permission_ids: Optional[List[uuid.UUID]] = None


class RoleRead(RoleBase):
    id: uuid.UUID
    is_active: bool
    permissions: List[PermissionRead] = []

    model_config = {"from_attributes": True}


class RoleReadShort(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool

    model_config = {"from_attributes": True}


class PermissionAssign(BaseModel):
    permission_ids: List[uuid.UUID]
