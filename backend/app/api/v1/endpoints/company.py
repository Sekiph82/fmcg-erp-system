"""
Multi-Company / Multi-Branch API
──────────────────────────────────
Prefix: /api/v1/companies

Routes:
  GET  /                      – list companies (user has access to)
  POST /                      – create company
  GET  /{id}                  – company detail
  PATCH /{id}                 – update company
  POST /{id}/set-default      – set as user's default company
  GET  /{id}/branches         – list branches
  POST /{id}/branches         – add branch
  PATCH /branches/{bid}       – update branch
  GET  /{id}/users            – list users with access
  POST /{id}/users            – grant user access
  DELETE /{id}/users/{uid}    – revoke access
  GET  /{id}/summary          – aggregated KPIs for the company
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_db, require_permission
from app.models.company import Company, Branch, UserCompanyAccess, CompanyUserRole
from app.models.user import User
from app.schemas.company import (
    CompanyCreate, CompanyUpdate, CompanyRead,
    BranchCreate, BranchRead,
    GrantUserAccess, UserAccessRead,
    CompanySummary,
)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _build_company_read(db: AsyncSession, c: Company) -> CompanyRead:
    branch_count_q = select(func.count(Branch.id)).where(Branch.company_id == c.id)
    user_count_q = select(func.count(UserCompanyAccess.id)).where(UserCompanyAccess.company_id == c.id)
    branch_count = (await db.execute(branch_count_q)).scalar() or 0
    user_count = (await db.execute(user_count_q)).scalar() or 0
    row = CompanyRead.model_validate(c)
    row.branch_count = branch_count
    row.user_count = user_count
    return row


async def _get_or_404(db: AsyncSession, company_id: uuid.UUID) -> Company:
    c = await db.get(Company, company_id)
    if not c:
        raise HTTPException(404, "Company not found")
    return c


async def _check_company_access(db: AsyncSession, user: User, company_id: uuid.UUID) -> None:
    """Raise 403 if user has no UserCompanyAccess row and is not superuser."""
    if user.is_superuser:
        return
    access = (await db.execute(
        select(UserCompanyAccess).where(
            UserCompanyAccess.user_id == user.id,
            UserCompanyAccess.company_id == company_id,
        )
    )).scalar_one_or_none()
    if not access:
        raise HTTPException(403, "No access to this company")


# ── Companies ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[CompanyRead])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("company", "view")),
):
    """List companies the current user has access to. Superusers see all."""
    if current_user.is_superuser:
        q = select(Company).where(Company.is_active.is_(True)).order_by(Company.name)
        companies = list((await db.execute(q)).scalars().all())
    else:
        access_q = select(UserCompanyAccess.company_id).where(UserCompanyAccess.user_id == current_user.id)
        company_ids = list((await db.execute(access_q)).scalars().all())
        q = select(Company).where(Company.id.in_(company_ids), Company.is_active.is_(True)).order_by(Company.name)
        companies = list((await db.execute(q)).scalars().all())

    return [await _build_company_read(db, c) for c in companies]


@router.post("/", response_model=CompanyRead, status_code=201)
async def create_company(
    body: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("company", "create")),
):
    existing = (await db.execute(
        select(Company).where(Company.short_code == body.short_code)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"Company code '{body.short_code}' already exists")

    company = Company(**body.model_dump(), created_by_id=current_user.id)
    db.add(company)
    await db.flush()

    # Auto-grant creator ADMIN access
    db.add(UserCompanyAccess(
        user_id=current_user.id,
        company_id=company.id,
        role=CompanyUserRole.ADMIN,
        is_default=True,
        granted_by_id=current_user.id,
    ))
    await db.commit()
    await db.refresh(company)
    return await _build_company_read(db, company)


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("company", "view")),
):
    await _check_company_access(db, current_user, company_id)
    c = await _get_or_404(db, company_id)
    return await _build_company_read(db, c)


@router.patch("/{company_id}", response_model=CompanyRead)
async def update_company(
    company_id: uuid.UUID,
    body: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("company", "edit")),
):
    await _check_company_access(db, current_user, company_id)
    c = await _get_or_404(db, company_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return await _build_company_read(db, c)


@router.post("/{company_id}/set-default", response_model=CompanyRead)
async def set_default_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("company", "view")),
):
    """Set this company as the current user's default."""
    access = (await db.execute(
        select(UserCompanyAccess).where(
            UserCompanyAccess.user_id == current_user.id,
            UserCompanyAccess.company_id == company_id,
        )
    )).scalar_one_or_none()
    if not access and not current_user.is_superuser:
        raise HTTPException(403, "No access to this company")

    # Clear existing default
    all_access = list((await db.execute(
        select(UserCompanyAccess).where(UserCompanyAccess.user_id == current_user.id)
    )).scalars().all())
    for a in all_access:
        a.is_default = (a.company_id == company_id)

    await db.commit()
    c = await _get_or_404(db, company_id)
    return await _build_company_read(db, c)


# ── Branches ──────────────────────────────────────────────────────────────────

@router.get("/{company_id}/branches", response_model=List[BranchRead])
async def list_branches(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("company", "view")),
):
    await _check_company_access(db, current_user, company_id)
    q = select(Branch).where(Branch.company_id == company_id).order_by(Branch.name)
    return [BranchRead.model_validate(b) for b in (await db.execute(q)).scalars().all()]


@router.post("/{company_id}/branches", response_model=BranchRead, status_code=201)
async def add_branch(
    company_id: uuid.UUID,
    body: BranchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("company", "edit")),
):
    await _check_company_access(db, current_user, company_id)
    await _get_or_404(db, company_id)
    branch = Branch(**body.model_dump(), company_id=company_id)
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return BranchRead.model_validate(branch)


@router.patch("/branches/{branch_id}", response_model=BranchRead)
async def update_branch(
    branch_id: uuid.UUID,
    body: BranchCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("company", "edit")),
):
    branch = await db.get(Branch, branch_id)
    if not branch:
        raise HTTPException(404, "Branch not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(branch, k, v)
    await db.commit()
    await db.refresh(branch)
    return BranchRead.model_validate(branch)


# ── User Access ───────────────────────────────────────────────────────────────

@router.get("/{company_id}/users", response_model=List[UserAccessRead])
async def list_company_users(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("company", "manage")),
):
    await _check_company_access(db, current_user, company_id)
    q = select(UserCompanyAccess).options(selectinload(UserCompanyAccess.user)).where(
        UserCompanyAccess.company_id == company_id
    )
    rows = list((await db.execute(q)).scalars().all())
    result = []
    for r in rows:
        row = UserAccessRead.model_validate(r)
        if r.user:
            row.username = r.user.username
            row.full_name = r.user.full_name
        result.append(row)
    return result


@router.post("/{company_id}/users", response_model=UserAccessRead, status_code=201)
async def grant_access(
    company_id: uuid.UUID,
    body: GrantUserAccess,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("company", "manage")),
):
    await _check_company_access(db, current_user, company_id)
    await _get_or_404(db, company_id)
    existing = (await db.execute(
        select(UserCompanyAccess).where(
            UserCompanyAccess.user_id == body.user_id,
            UserCompanyAccess.company_id == company_id,
        )
    )).scalar_one_or_none()
    if existing:
        existing.role = body.role
        existing.is_default = body.is_default
        await db.commit()
        await db.refresh(existing)
        access = existing
    else:
        access = UserCompanyAccess(
            user_id=body.user_id,
            company_id=company_id,
            role=body.role,
            is_default=body.is_default,
            granted_by_id=current_user.id,
        )
        db.add(access)
        await db.commit()
        await db.refresh(access)

    await db.refresh(access)
    result = await db.execute(
        select(UserCompanyAccess).options(selectinload(UserCompanyAccess.user)).where(UserCompanyAccess.id == access.id)
    )
    row_obj = result.scalar_one()
    row = UserAccessRead.model_validate(row_obj)
    if row_obj.user:
        row.username = row_obj.user.username
        row.full_name = row_obj.user.full_name
    return row


@router.delete("/{company_id}/users/{user_id}", status_code=204)
async def revoke_access(
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("company", "manage")),
):
    await _check_company_access(db, current_user, company_id)
    access = (await db.execute(
        select(UserCompanyAccess).where(
            UserCompanyAccess.company_id == company_id,
            UserCompanyAccess.user_id == user_id,
        )
    )).scalar_one_or_none()
    if not access:
        raise HTTPException(404, "Access record not found")
    await db.delete(access)
    await db.commit()


# ── Company Summary ───────────────────────────────────────────────────────────

@router.get("/{company_id}/summary", response_model=CompanySummary)
async def company_summary(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("company", "view")),
):
    """Aggregated KPI snapshot for a company (best-effort from shared data)."""
    await _check_company_access(db, current_user, company_id)
    c = await _get_or_404(db, company_id)

    branch_count = (await db.execute(
        select(func.count(Branch.id)).where(Branch.company_id == company_id)
    )).scalar() or 0

    user_count = (await db.execute(
        select(func.count(UserCompanyAccess.id)).where(UserCompanyAccess.company_id == company_id)
    )).scalar() or 0

    # Best-effort aggregates from global tables
    from app.models.finance import Budget
    from app.models.master import Product, Warehouse
    from app.models.procurement import PurchaseOrder, POStatus
    from app.models.sales import SalesOrder, SOStatus

    product_count = (await db.execute(
        select(func.count(Product.id)).where(Product.is_active.is_(True))
    )).scalar() or 0

    warehouse_count = (await db.execute(
        select(func.count(Warehouse.id))
    )).scalar() or 0

    open_po_count = (await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.status.in_([POStatus.PENDING, POStatus.APPROVED, POStatus.PARTIAL])
        )
    )).scalar() or 0

    open_so_count = (await db.execute(
        select(func.count(SalesOrder.id)).where(
            SalesOrder.status.in_([SOStatus.CONFIRMED, SOStatus.ALLOCATED, SOStatus.PICKING])
        )
    )).scalar() or 0

    return CompanySummary(
        company_id=c.id,
        company_name=c.name,
        short_code=c.short_code,
        base_currency=c.base_currency,
        branch_count=branch_count,
        user_count=user_count,
        total_budgeted=Decimal("0"),
        open_po_count=open_po_count,
        open_so_count=open_so_count,
        product_count=product_count,
        warehouse_count=warehouse_count,
    )
