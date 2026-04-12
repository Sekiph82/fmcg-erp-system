from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user
from app.crud import master as crud
from app.schemas.master import WarehouseCreate, WarehouseUpdate, WarehouseRead
from fastapi import Response

router = APIRouter()


@router.get("/", response_model=List[WarehouseRead])
async def list_warehouses(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db),
                          _=Depends(get_current_user)):
    return await crud.list_warehouses(db, skip=skip, limit=limit)


@router.post("/", response_model=WarehouseRead, status_code=201)
async def create_warehouse(data: WarehouseCreate, db: AsyncSession = Depends(get_db),
                           _=Depends(get_current_user)):
    obj = await crud.create_warehouse(db, data)
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
                           db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_warehouse(db, warehouse_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    obj = await crud.update_warehouse(db, obj, data)
    await db.commit()
    return obj


@router.delete("/{warehouse_id}", status_code=204)
async def delete_warehouse(warehouse_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                           _=Depends(get_current_user)):
    obj = await crud.get_warehouse(db, warehouse_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    await crud.delete_warehouse(db, obj)
    await db.commit()
    return Response(status_code=204)
