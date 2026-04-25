"""Accounting Dimensions / Cost Centers API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.schemas.dimensions import (
    DimTypeCreate, DimTypeRead,
    DimValueCreate, DimValueRead,
    CostCenterCreate, CostCenterRead,
    TransactionDimensionCreate, TransactionDimensionRead,
    DimValidationRuleCreate, DimValidationRuleRead,
    AllocationRuleCreate, AllocationRuleRead,
    AllocationRunRequest, AllocationRunRead,
    DimDefaultRuleCreate, DimDefaultRuleRead,
    ReclassifyRequest, ReclassifyRead,
    ValidateRequest, ValidateResult,
    DeriveRequest, DeriveResult,
    DimAIRecRead, AckDimAIRec, DimDashboardSummary,
)
from app.models.dimensions import DimAIRecStatus
import app.services.dimensions_service as svc
import uuid

router = APIRouter()


# ── Dashboard ──────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DimDashboardSummary)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await svc.dashboard_summary(db)


# ── Dimension Types ────────────────────────────────────────────────────────────

@router.get("/types", response_model=List[DimTypeRead])
async def list_types(active_only: bool = False, db: AsyncSession = Depends(get_db)):
    return await svc.list_dim_types(db, active_only)


@router.post("/types", response_model=DimTypeRead, status_code=201)
async def create_type(data: DimTypeCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_dim_type(db, data)


@router.patch("/types/{type_id}", response_model=DimTypeRead)
async def update_type(type_id: uuid.UUID, data: dict, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.update_dim_type(db, type_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Dimension Values ───────────────────────────────────────────────────────────

@router.get("/values", response_model=List[DimValueRead])
async def list_values(
    dim_type_id: Optional[uuid.UUID] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_dim_values(db, dim_type_id, active_only)


@router.post("/values", response_model=DimValueRead, status_code=201)
async def create_value(data: DimValueCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_dim_value(db, data)


# ── Cost Centers ───────────────────────────────────────────────────────────────

@router.get("/cost-centers", response_model=List[CostCenterRead])
async def list_cost_centers(active_only: bool = False, db: AsyncSession = Depends(get_db)):
    return await svc.list_cost_centers(db, active_only)


@router.post("/cost-centers", response_model=CostCenterRead, status_code=201)
async def create_cost_center(data: CostCenterCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_cost_center(db, data)


@router.patch("/cost-centers/{cc_id}", response_model=CostCenterRead)
async def update_cost_center(cc_id: uuid.UUID, data: dict, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.update_cost_center(db, cc_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ── Transaction Dimension Tagging ──────────────────────────────────────────────

@router.get("/tags", response_model=List[TransactionDimensionRead])
async def get_tags(
    transaction_type: str = Query(...),
    transaction_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_transaction_dimensions(db, transaction_type, transaction_id)


@router.post("/tags", response_model=TransactionDimensionRead, status_code=201)
async def tag_transaction(data: TransactionDimensionCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.tag_transaction(db, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Default Derivation ─────────────────────────────────────────────────────────

@router.post("/derive", response_model=List[DeriveResult])
async def derive_dimensions(data: DeriveRequest, db: AsyncSession = Depends(get_db)):
    return await svc.derive_dimensions(
        db,
        data.transaction_type,
        data.source_field,
        data.source_field_value,
    )


# ── Validation ─────────────────────────────────────────────────────────────────

@router.post("/validate", response_model=ValidateResult)
async def validate_dimensions(data: ValidateRequest, db: AsyncSession = Depends(get_db)):
    present_ids = [tag.dim_type_id for tag in data.dim_tags]
    return await svc.validate_dimensions(db, data.transaction_type, present_ids)


# ── Validation Rules ───────────────────────────────────────────────────────────

@router.get("/validation-rules", response_model=List[DimValidationRuleRead])
async def list_validation_rules(db: AsyncSession = Depends(get_db)):
    return await svc.list_validation_rules(db)


@router.post("/validation-rules", response_model=DimValidationRuleRead, status_code=201)
async def create_validation_rule(data: DimValidationRuleCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_validation_rule(db, data)


# ── Default Rules ──────────────────────────────────────────────────────────────

@router.get("/default-rules", response_model=List[DimDefaultRuleRead])
async def list_default_rules(db: AsyncSession = Depends(get_db)):
    return await svc.list_default_rules(db)


@router.post("/default-rules", response_model=DimDefaultRuleRead, status_code=201)
async def create_default_rule(data: DimDefaultRuleCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_default_rule(db, data)


# ── Allocation Rules ───────────────────────────────────────────────────────────

@router.get("/allocation-rules", response_model=List[AllocationRuleRead])
async def list_allocation_rules(db: AsyncSession = Depends(get_db)):
    return await svc.list_allocation_rules(db)


@router.post("/allocation-rules", response_model=AllocationRuleRead, status_code=201)
async def create_allocation_rule(data: AllocationRuleCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_allocation_rule(db, data)


# ── Allocation Runs ────────────────────────────────────────────────────────────

@router.get("/allocation-runs", response_model=List[AllocationRunRead])
async def list_allocation_runs(
    rule_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_allocation_runs(db, rule_id)


@router.post("/allocation-runs/preview", response_model=AllocationRunRead, status_code=201)
async def preview_allocation(data: AllocationRunRequest, db: AsyncSession = Depends(get_db)):
    data.dry_run = True
    try:
        return await svc.run_allocation(db, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/allocation-runs/post", response_model=AllocationRunRead, status_code=201)
async def post_allocation(data: AllocationRunRequest, db: AsyncSession = Depends(get_db)):
    data.dry_run = False
    try:
        return await svc.run_allocation(db, data)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Reclassification ───────────────────────────────────────────────────────────

@router.get("/reclassifications", response_model=List[ReclassifyRead])
async def list_reclassifications(
    transaction_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_reclassifications(db, transaction_type)


@router.post("/reclassify", response_model=ReclassifyRead, status_code=201)
async def reclassify(data: ReclassifyRequest, db: AsyncSession = Depends(get_db)):
    return await svc.reclassify(db, data)


# ── Reporting ──────────────────────────────────────────────────────────────────

@router.get("/reports/tagging-completeness")
async def report_tagging_completeness(db: AsyncSession = Depends(get_db)):
    return await svc.report_tagging_completeness(db)


# ── AI Agents ──────────────────────────────────────────────────────────────────

@router.post("/ai/run-agents")
async def run_ai_agents(db: AsyncSession = Depends(get_db)):
    recs = await svc.run_ai_agents(db)
    return {"generated": len(recs)}


@router.get("/ai/recommendations", response_model=List[DimAIRecRead])
async def list_ai_recs(
    status: Optional[DimAIRecStatus] = None,
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_ai_recs(db, status)


@router.patch("/ai/recommendations/{rec_id}", response_model=DimAIRecRead)
async def ack_ai_rec(rec_id: uuid.UUID, data: AckDimAIRec, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.ack_ai_rec(db, rec_id, data.status)
    except ValueError as e:
        raise HTTPException(404, str(e))
