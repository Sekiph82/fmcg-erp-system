from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.crud import master as crud
from app.schemas.master import WarehouseCreate, WarehouseUpdate, WarehouseRead, MasterMergeRequest, MasterMergeResult
from app.api.v1.endpoints.master_lifecycle import deactivate_master, merge_master
from app.services.master_stewardship import record_master_data_change, snapshot_master_data
from fastapi import Response

router = APIRouter()


@router.get("/", response_model=List[WarehouseRead])
async def list_warehouses(skip: int = 0, limit: int = 50, include_inactive: bool = Query(False), db: AsyncSession = Depends(get_db),
                          _=Depends(get_current_user)):
    return await crud.list_warehouses(db, skip=skip, limit=limit, include_inactive=include_inactive)


@router.post("/", response_model=WarehouseRead, status_code=201)
async def create_warehouse(data: WarehouseCreate, db: AsyncSession = Depends(get_db),
                           current_user=Depends(require_permission("warehouses", "create"))):
    obj = await crud.create_warehouse(db, data)
    await record_master_data_change(db, record=obj, actor=current_user, action="CREATE", permission="warehouses.create")
    await db.commit()
    return obj


@router.get("/{warehouse_id}", response_model=WarehouseRead)
async def get_warehouse(warehouse_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                        _=Depends(get_current_user)):
    obj = await crud.get_warehouse(db, warehouse_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return obj


@router.patch("/{warehouse_id}", response_model=WarehouseRead)
async def update_warehouse(warehouse_id: uuid.UUID, data: WarehouseUpdate,
                           db: AsyncSession = Depends(get_db), current_user=Depends(require_permission("warehouses", "edit"))):
    if "is_active" in data.model_fields_set:
        raise HTTPException(422, "Use the governed deactivation action to change warehouse activity.")
    obj = await crud.get_warehouse(db, warehouse_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    before = snapshot_master_data(obj)
    obj = await crud.update_warehouse(db, obj, data)
    await record_master_data_change(db, record=obj, actor=current_user, action="UPDATE", permission="warehouses.edit", before=before)
    await db.commit()
    return obj


@router.delete("/{warehouse_id}", status_code=204)
async def delete_warehouse(warehouse_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                           current_user=Depends(require_permission("warehouses", "delete"))):
    obj = await crud.get_warehouse(db, warehouse_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    await deactivate_master(db, crud.Warehouse, "warehouse", warehouse_id, current_user.id)
    return Response(status_code=204)


@router.post("/{warehouse_id}/deactivate", response_model=WarehouseRead)
async def deactivate_warehouse(warehouse_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                               current_user=Depends(require_permission("warehouses", "delete"))):
    return await deactivate_master(db, crud.Warehouse, "warehouse", warehouse_id, current_user.id)


@router.post("/{warehouse_id}/merge", response_model=MasterMergeResult)
async def merge_warehouse(warehouse_id: uuid.UUID, body: MasterMergeRequest,
                          db: AsyncSession = Depends(get_db), current_user=Depends(require_permission("warehouses", "delete"))):
    source = await db.get(crud.Warehouse, warehouse_id)
    survivor = await db.get(crud.Warehouse, body.survivor_id)
    if not source or not survivor:
        raise HTTPException(404, "Warehouse or survivor not found")
    if (source.company_id, source.branch_id) != (survivor.company_id, survivor.branch_id):
        raise HTTPException(409, detail={"code": "warehouse_scope_mismatch", "message": "Warehouses in different company or branch scopes cannot be merged."})
    return await merge_master(db, crud.Warehouse, "warehouse", warehouse_id, body.survivor_id, current_user.id)
