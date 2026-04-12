from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user
from app.crud import master as crud
from app.schemas.master import SupplierCreate, SupplierUpdate, SupplierRead
from fastapi import Response

router = APIRouter()


@router.get("/", response_model=List[SupplierRead])
async def list_suppliers(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db),
                         _=Depends(get_current_user)):
    return await crud.list_suppliers(db, skip=skip, limit=limit)


@router.post("/", response_model=SupplierRead, status_code=201)
async def create_supplier(data: SupplierCreate, db: AsyncSession = Depends(get_db),
                          _=Depends(get_current_user)):
    obj = await crud.create_supplier(db, data)
    await db.commit()
    return obj


@router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(supplier_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                       _=Depends(get_current_user)):
    obj = await crud.get_supplier(db, supplier_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return obj


@router.patch("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(supplier_id: uuid.UUID, data: SupplierUpdate,
                          db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_supplier(db, supplier_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Supplier not found")
    obj = await crud.update_supplier(db, obj, data)
    await db.commit()
    return obj


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(supplier_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                          _=Depends(get_current_user)):
    obj = await crud.get_supplier(db, supplier_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Supplier not found")
    await crud.delete_supplier(db, obj)
    await db.commit()
    return Response(status_code=204)
