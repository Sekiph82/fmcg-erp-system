import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.crud import master as crud
from app.schemas.master import ProductCreate, ProductUpdate, ProductRead, MasterMergeRequest, MasterMergeResult
from app.api.v1.endpoints.master_lifecycle import deactivate_master, merge_master
from app.services.master_stewardship import record_master_data_change, snapshot_master_data
from fastapi import Response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[ProductRead])
async def list_products(skip: int = 0, limit: int = 50, include_inactive: bool = Query(False), db: AsyncSession = Depends(get_db),
                        _=Depends(get_current_user)):
    return await crud.list_products(db, skip=skip, limit=limit, include_inactive=include_inactive)


@router.post("/", response_model=ProductRead, status_code=201)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db),
                         current_user=Depends(require_permission("products", "create"))):
    obj = await crud.create_product(db, data)
    await record_master_data_change(db, record=obj, actor=current_user, action="CREATE", permission="products.create")
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
                         db: AsyncSession = Depends(get_db), current_user=Depends(require_permission("products", "edit"))):
    if "is_active" in data.model_fields_set:
        raise HTTPException(422, "Use the governed deactivation action to change product activity.")
    obj = await crud.get_product(db, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    before = snapshot_master_data(obj)
    obj = await crud.update_product(db, obj, data)
    await record_master_data_change(db, record=obj, actor=current_user, action="UPDATE", permission="products.edit", before=before)
    await db.commit()
    return obj


@router.patch("/{product_id}/archive", response_model=ProductRead)
async def archive_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("products", "delete")),
):
    """Deactivate (archive) a product without deleting it."""
    obj = await crud.get_product(db, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    obj = await deactivate_master(db, crud.Product, "product", product_id, current_user.id)
    logger.info("Product %s archived by user %s", product_id, current_user.id)
    return obj


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("products", "delete")),
):
    """Deactivate a product while preserving its existing operational history."""
    obj = await crud.get_product(db, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")

    await deactivate_master(db, crud.Product, "product", product_id, current_user.id)
    logger.info("Product %s deactivated by user %s", product_id, current_user.id)
    return Response(status_code=204)


@router.post("/{product_id}/deactivate", response_model=ProductRead)
async def deactivate_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("products", "delete")),
):
    return await deactivate_master(db, crud.Product, "product", product_id, current_user.id)


@router.post("/{product_id}/merge", response_model=MasterMergeResult)
async def merge_product(
    product_id: uuid.UUID,
    body: MasterMergeRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("products", "delete")),
):
    return await merge_master(
        db, crud.Product, "product", product_id, body.survivor_id, current_user.id
    )
