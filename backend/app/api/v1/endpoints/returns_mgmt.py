from __future__ import annotations
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.crud import returns_mgmt as crud
from app.models.returns_mgmt import ReturnStatus
from app.schemas.returns_mgmt import (
    ReturnOrderCreate, ReturnOrderUpdate, ReturnOrderRead,
)

router = APIRouter()


@router.get("/", response_model=List[ReturnOrderRead],
            dependencies=[Depends(require_permission("sales", "view"))])
async def list_returns(
    customer_id: Optional[uuid.UUID] = Query(None),
    status: Optional[ReturnStatus] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    returns = await crud.list_returns(db, customer_id=customer_id, status=status, limit=limit)
    result = []
    for r in returns:
        rd = ReturnOrderRead.model_validate(r)
        if r.customer:
            rd.customer_name = r.customer.name
        rd.line_count = len(r.lines)
        result.append(rd)
    return result


@router.post("/", response_model=ReturnOrderRead, status_code=201,
             dependencies=[Depends(require_permission("sales", "create"))])
async def create_return(
    data: ReturnOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ret = await crud.create_return(db, data, current_user.id)
    await db.commit()
    return ret


@router.get("/{return_id}", response_model=ReturnOrderRead,
            dependencies=[Depends(require_permission("sales", "view"))])
async def get_return(return_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    ret = await crud.get_return(db, return_id)
    if not ret:
        raise HTTPException(status_code=404, detail="Return order not found")
    rd = ReturnOrderRead.model_validate(ret)
    if ret.customer:
        rd.customer_name = ret.customer.name
    rd.line_count = len(ret.lines)
    return rd


@router.patch("/{return_id}", response_model=ReturnOrderRead,
              dependencies=[Depends(require_permission("sales", "edit"))])
async def update_return(
    return_id: uuid.UUID,
    data: ReturnOrderUpdate,
    db: AsyncSession = Depends(get_db),
):
    ret = await crud.get_return(db, return_id)
    if not ret:
        raise HTTPException(status_code=404, detail="Return order not found")
    ret = await crud.update_return(db, ret, data)
    await db.commit()
    return ret


@router.post("/{return_id}/approve",
             dependencies=[Depends(require_permission("sales", "approve"))])
async def approve_return(
    return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ret = await crud.get_return(db, return_id)
    if not ret:
        raise HTTPException(status_code=404, detail="Return order not found")
    if ret.status != ReturnStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Return must be SUBMITTED to approve")
    ret.status = ReturnStatus.APPROVED
    ret.approved_by_id = current_user.id
    ret.approved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "APPROVED"}
