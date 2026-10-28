from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.crud import master as crud
from app.schemas.master import MaterialCreate, MaterialUpdate, MaterialRead, MasterMergeRequest, MasterMergeResult
from app.api.v1.endpoints.master_lifecycle import deactivate_master, merge_master
from app.services.master_stewardship import record_master_data_change, snapshot_master_data
from fastapi import Response

router = APIRouter()


@router.get("/", response_model=List[MaterialRead])
async def list_materials(skip: int = 0, limit: int = 50, include_inactive: bool = Query(False), db: AsyncSession = Depends(get_db),
                         _=Depends(get_current_user)):
    return await crud.list_materials(db, skip=skip, limit=limit, include_inactive=include_inactive)


@router.post("/", response_model=MaterialRead, status_code=201)
async def create_material(data: MaterialCreate, db: AsyncSession = Depends(get_db),
                          current_user=Depends(require_permission("materials", "create"))):
    obj = await crud.create_material(db, data)
    await record_master_data_change(db, record=obj, actor=current_user, action="CREATE", permission="materials.create")
    await db.commit()
    return obj


@router.get("/{material_id}", response_model=MaterialRead)
async def get_material(material_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                       _=Depends(get_current_user)):
    obj = await crud.get_material(db, material_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Material not found")
    return obj


@router.patch("/{material_id}", response_model=MaterialRead)
async def update_material(material_id: uuid.UUID, data: MaterialUpdate,
                          db: AsyncSession = Depends(get_db), current_user=Depends(require_permission("materials", "edit"))):
    if "is_active" in data.model_fields_set:
        raise HTTPException(422, "Use the governed deactivation action to change material activity.")
    obj = await crud.get_material(db, material_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Material not found")
    before = snapshot_master_data(obj)
    obj = await crud.update_material(db, obj, data)
    await record_master_data_change(db, record=obj, actor=current_user, action="UPDATE", permission="materials.edit", before=before)
    await db.commit()
    return obj


@router.delete("/{material_id}", status_code=204)
async def delete_material(material_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                          current_user=Depends(require_permission("materials", "delete"))):
    obj = await crud.get_material(db, material_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Material not found")
    await deactivate_master(db, crud.Material, "material", material_id, current_user.id)
    return Response(status_code=204)


@router.post("/{material_id}/deactivate", response_model=MaterialRead)
async def deactivate_material(material_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                              current_user=Depends(require_permission("materials", "delete"))):
    return await deactivate_master(db, crud.Material, "material", material_id, current_user.id)


@router.post("/{material_id}/merge", response_model=MasterMergeResult)
async def merge_material(material_id: uuid.UUID, body: MasterMergeRequest,
                         db: AsyncSession = Depends(get_db), current_user=Depends(require_permission("materials", "delete"))):
    return await merge_master(db, crud.Material, "material", material_id, body.survivor_id, current_user.id)
