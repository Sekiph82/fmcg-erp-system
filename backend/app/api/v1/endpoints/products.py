from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user
from app.crud import master as crud
from app.schemas.master import ProductCreate, ProductUpdate, ProductRead
from fastapi import Response

router = APIRouter()


@router.get("/", response_model=List[ProductRead])
async def list_products(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db),
                        _=Depends(get_current_user)):
    return await crud.list_products(db, skip=skip, limit=limit)


@router.post("/", response_model=ProductRead, status_code=201)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db),
                         _=Depends(get_current_user)):
    obj = await crud.create_product(db, data)
    await db.commit()
    return obj


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                      _=Depends(get_current_user)):
    obj = await crud.get_product(db, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    return obj


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(product_id: uuid.UUID, data: ProductUpdate,
                         db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_product(db, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    obj = await crud.update_product(db, obj, data)
    await db.commit()
    return obj


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                         _=Depends(get_current_user)):
    obj = await crud.get_product(db, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    await crud.delete_product(db, obj)
    await db.commit()
    return Response(status_code=204)
