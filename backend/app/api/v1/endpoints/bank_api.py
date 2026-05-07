"""Bank API / Open Banking endpoints."""
from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.bank_api import (
    BankApiDashboard, BankConnectionCreate, BankConnectionRead, BankSyncResult,
    BankTransactionRead, ClassifyBankTransaction, ReconcileBankTransaction,
)
from app.services import bank_api_service as svc

router = APIRouter()


@router.post("/connections", response_model=BankConnectionRead, status_code=201)
async def create_connection(
    body: BankConnectionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await svc.create_connection(db, body)


@router.get("/connections", response_model=List[BankConnectionRead])
async def list_connections(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await svc.list_connections(db)


@router.get("/connections/{connection_id}", response_model=BankConnectionRead)
async def get_connection(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return await svc.get_connection(db, connection_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/connections/{connection_id}/sync", response_model=BankSyncResult)
async def sync_connection(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return await svc.sync_connection(db, connection_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/transactions", response_model=List[BankTransactionRead])
async def list_transactions(
    connection_id: Optional[uuid.UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    reconciled: Optional[bool] = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await svc.list_transactions(db, connection_id, start_date, end_date, reconciled, limit)


@router.post("/transactions/{transaction_id}/reconcile", response_model=BankTransactionRead)
async def reconcile_transaction(
    transaction_id: uuid.UUID,
    body: ReconcileBankTransaction,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return await svc.reconcile_transaction(
            db, transaction_id, body.matched_record_type, body.matched_record_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/transactions/{transaction_id}/classify", response_model=BankTransactionRead)
async def classify_transaction(
    transaction_id: uuid.UUID,
    body: ClassifyBankTransaction,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return await svc.classify_transaction(db, transaction_id, body.classification)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/dashboard", response_model=BankApiDashboard)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await svc.get_dashboard(db)
