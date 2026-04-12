from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user
from app.crud import master as crud
from app.schemas.master import MaterialCreate, MaterialUpdate, MaterialRead

router = APIRouter()


@router.get("/", response_model=List[MaterialRead])
async def list_materials(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db),
                         _=Depends(get_current_user)):
    return await crud.list_materials(db, skip=skip, limit=limit)


@router.post("/", response_model=MaterialRead, status_code=201)
async def create_material(data: MaterialCreate, db: AsyncSession = Depends(get_db),
                          _=Depends(get_current_user)):
    obj = await crud.create_material(db, data)
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
                          db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    obj = await crud.get_material(db, material_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Material not found")
    obj = await crud.update_material(db, obj, data)
    await db.commit()
    return obj
