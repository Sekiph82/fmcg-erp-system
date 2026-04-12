from __future__ import annotations
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.crud import distribution as crud
from app.schemas.distribution import (
    DistributorCreate, DistributorUpdate, DistributorRead,
    DistributorPricingTierCreate, DistributorPricingTierRead,
)

router = APIRouter()


@router.get("/", response_model=List[DistributorRead],
            dependencies=[Depends(require_permission("sales", "view"))])
async def list_distributors(
    region: Optional[str] = Query(None),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_distributors(db, region=region, active_only=active_only)


@router.post("/", response_model=DistributorRead, status_code=201,
             dependencies=[Depends(require_permission("sales", "create"))])
async def create_distributor(data: DistributorCreate, db: AsyncSession = Depends(get_db)):
    existing = await crud.get_distributor_by_code(db, data.code)
    if existing:
        raise HTTPException(status_code=400, detail="Distributor code already exists")
    dist = await crud.create_distributor(db, data)
    await db.commit()
    return dist


@router.get("/{distributor_id}", response_model=DistributorRead,
            dependencies=[Depends(require_permission("sales", "view"))])
async def get_distributor(distributor_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    dist = await crud.get_distributor(db, distributor_id)
    if not dist:
        raise HTTPException(status_code=404, detail="Distributor not found")
    return dist


@router.patch("/{distributor_id}", response_model=DistributorRead,
              dependencies=[Depends(require_permission("sales", "edit"))])
async def update_distributor(
    distributor_id: uuid.UUID,
    data: DistributorUpdate,
    db: AsyncSession = Depends(get_db),
):
    dist = await crud.get_distributor(db, distributor_id)
    if not dist:
        raise HTTPException(status_code=404, detail="Distributor not found")
    dist = await crud.update_distributor(db, dist, data)
    await db.commit()
    return dist


@router.post("/{distributor_id}/pricing", response_model=DistributorPricingTierRead, status_code=201,
             dependencies=[Depends(require_permission("sales", "edit"))])
async def add_pricing_tier(
    distributor_id: uuid.UUID,
    data: DistributorPricingTierCreate,
    db: AsyncSession = Depends(get_db),
):
    dist = await crud.get_distributor(db, distributor_id)
    if not dist:
        raise HTTPException(status_code=404, detail="Distributor not found")
    tier = await crud.add_pricing_tier(db, distributor_id, data)
    await db.commit()
    return tier
