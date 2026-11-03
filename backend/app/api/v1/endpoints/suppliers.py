from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid
from datetime import date, datetime, timezone

from app.db.session import get_db
from app.core.deps import require_permission
from app.crud import master as crud
from app.schemas.master import (
    SupplierCreate,
    SupplierUpdate,
    SupplierRead,
    SupplierQualificationDecision,
    SupplierPreferenceDecision,
    MasterMergeRequest,
    MasterMergeResult,
)
from app.models.master import SupplierQualificationStatus
from app.api.v1.endpoints.master_lifecycle import deactivate_master, merge_master
from app.services.master_stewardship import (
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
    if data.qualification_status not in (None, SupplierQualificationStatus.PENDING) or data.approved_from or data.approved_until:
        raise HTTPException(422, "New suppliers start as PENDING; use the governed qualification decision to approve them.")
    obj = await crud.create_supplier(db, data)
    obj.qualification_status = SupplierQualificationStatus.PENDING
    obj.is_preferred = False
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
    if {"qualification_status", "approved_from", "approved_until"}.intersection(data.model_fields_set):
        raise HTTPException(422, "Use the governed supplier qualification decision to change qualification or approval dates.")
    obj = await crud.get_supplier(db, supplier_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Supplier not found")
    before = snapshot_master_data(obj)
    obj = await crud.update_supplier(db, obj, data)
    await record_master_data_change(db, record=obj, actor=current_user, action="UPDATE", permission="suppliers.edit", before=before)
    await db.commit()
    return obj


@router.post("/{supplier_id}/qualification", response_model=SupplierRead)
async def decide_supplier_qualification(
    supplier_id: uuid.UUID,
    body: SupplierQualificationDecision,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("procurement", "approve")),
):
    obj = await crud.get_supplier(db, supplier_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if (
        body.qualification_status == SupplierQualificationStatus.APPROVED
        and body.approved_until
        and body.approved_until < (body.approved_from or date.today())
    ):
        raise HTTPException(422, "Approval end date must be on or after the effective start date.")
    before = snapshot_master_data(obj)
    obj.qualification_status = body.qualification_status
    if body.qualification_status == SupplierQualificationStatus.APPROVED:
        obj.approved_from = body.approved_from or date.today()
        obj.approved_until = body.approved_until
        obj.approved_by_id = current_user.id
        obj.approved_at = datetime.now(timezone.utc)
    else:
        obj.approved_from = None
        obj.approved_until = None
        obj.approved_by_id = None
        obj.approved_at = None
        obj.is_preferred = False
    await db.flush()
    await record_master_data_change(
        db,
        record=obj,
        actor=current_user,
        action="UPDATE",
        permission="procurement.approve",
        before=before,
        audit_context={
            "workflow": "SUPPLIER_QUALIFICATION_DECISION",
            "approval_required": True,
            "required_permission": "procurement.approve",
            "decision": body.qualification_status.value,
            "reason": body.reason,
        },
        force_event=True,
    )
    await db.commit()
    return obj


@router.post("/{supplier_id}/preference", response_model=SupplierRead)
async def decide_supplier_preference(
    supplier_id: uuid.UUID,
    body: SupplierPreferenceDecision,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("procurement", "approve")),
):
    obj = await crud.get_supplier(db, supplier_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if body.is_preferred:
        today = date.today()
        status_value = getattr(obj.qualification_status, "value", obj.qualification_status)
        if not obj.is_active or status_value != SupplierQualificationStatus.APPROVED.value:
            raise HTTPException(409, "Only an active, APPROVED supplier can be marked preferred.")
        if (obj.approved_from and obj.approved_from > today) or (obj.approved_until and obj.approved_until < today):
            raise HTTPException(409, "Supplier approval is outside its effective date window.")
    if obj.is_preferred == body.is_preferred:
        raise HTTPException(409, "Supplier already has the requested preference state.")
    before = snapshot_master_data(obj)
    obj.is_preferred = body.is_preferred
    await db.flush()
    await record_master_data_change(
        db,
        record=obj,
        actor=current_user,
        action="UPDATE",
        permission="procurement.approve",
        before=before,
        audit_context={
            "workflow": "SUPPLIER_PREFERENCE_DECISION",
            "approval_required": True,
            "required_permission": "procurement.approve",
            "decision": "PREFERRED" if body.is_preferred else "NOT_PREFERRED",
            "reason": body.reason,
        },
    )
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
