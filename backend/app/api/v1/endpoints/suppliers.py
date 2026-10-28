from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.db.session import get_db
from app.core.deps import require_permission
from app.crud import master as crud
from app.schemas.master import SupplierCreate, SupplierUpdate, SupplierRead, MasterMergeRequest, MasterMergeResult
from app.models.master import SupplierQualificationStatus
from app.api.v1.endpoints.master_lifecycle import deactivate_master, merge_master
from app.services.master_stewardship import (
    apply_supplier_qualification_actor,
    record_master_data_change,
    snapshot_master_data,
)
from fastapi import Response

router = APIRouter()


@router.get("/", response_model=List[SupplierRead])
async def list_suppliers(skip: int = 0, limit: int = 50, include_inactive: bool = Query(False), db: AsyncSession = Depends(get_db),
                         _=Depends(require_permission("suppliers", "view"))):
    return await crud.list_suppliers(db, skip=skip, limit=limit, include_inactive=include_inactive)


@router.post("/", response_model=SupplierRead, status_code=201)
async def create_supplier(data: SupplierCreate, db: AsyncSession = Depends(get_db),
                          current_user=Depends(require_permission("suppliers", "create"))):
    obj = await crud.create_supplier(db, data)
    if obj.qualification_status == SupplierQualificationStatus.APPROVED:
        apply_supplier_qualification_actor(obj, current_user)
        await db.flush()
    await record_master_data_change(db, record=obj, actor=current_user, action="CREATE", permission="suppliers.create")
    await db.commit()
    return obj


@router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(supplier_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                       _=Depends(require_permission("suppliers", "view"))):
    obj = await crud.get_supplier(db, supplier_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return obj


@router.patch("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(supplier_id: uuid.UUID, data: SupplierUpdate,
                          db: AsyncSession = Depends(get_db), current_user=Depends(require_permission("suppliers", "edit"))):
    if "is_active" in data.model_fields_set:
        raise HTTPException(422, "Use the governed deactivation action to change supplier activity.")
    obj = await crud.get_supplier(db, supplier_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Supplier not found")
    before = snapshot_master_data(obj)
    obj = await crud.update_supplier(db, obj, data)
    if "qualification_status" in data.model_fields_set:
        previous_status = before.get("qualification_status")
        apply_supplier_qualification_actor(
            obj,
            current_user,
            previous_status=previous_status,
        )
        if getattr(obj.qualification_status, "value", obj.qualification_status) != previous_status:
            await db.flush()
    await record_master_data_change(db, record=obj, actor=current_user, action="UPDATE", permission="suppliers.edit", before=before)
    await db.commit()
    return obj


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(supplier_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                          current_user=Depends(require_permission("suppliers", "delete"))):
    obj = await crud.get_supplier(db, supplier_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Supplier not found")
    await deactivate_master(db, crud.Supplier, "supplier", supplier_id, current_user.id)
    return Response(status_code=204)


@router.post("/{supplier_id}/deactivate", response_model=SupplierRead)
async def deactivate_supplier(supplier_id: uuid.UUID, db: AsyncSession = Depends(get_db),
                              current_user=Depends(require_permission("suppliers", "delete"))):
    return await deactivate_master(db, crud.Supplier, "supplier", supplier_id, current_user.id)


@router.post("/{supplier_id}/merge", response_model=MasterMergeResult)
async def merge_supplier(supplier_id: uuid.UUID, body: MasterMergeRequest,
                         db: AsyncSession = Depends(get_db), current_user=Depends(require_permission("suppliers", "delete"))):
    return await merge_master(db, crud.Supplier, "supplier", supplier_id, body.survivor_id, current_user.id)
