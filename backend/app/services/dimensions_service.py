"""Accounting Dimensions / Cost Centers service layer."""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dimensions import (
    DimType, DimValue, CostCenter, TransactionDimension,
    DimValidationRule, AllocationRule, AllocationRuleLine,
    AllocationRun, AllocationRunLine, DimDefaultRule,
    DimReclassification, DimAIRecommendation,
    AllocationRunStatus, DimAIAgentType, DimAIRecStatus,
    DimSourceType, ValidationSeverity,
)
from app.schemas.dimensions import (
    DimTypeCreate, DimValueCreate, CostCenterCreate,
    TransactionDimensionCreate, DimValidationRuleCreate,
    AllocationRuleCreate, AllocationRunRequest, DimDefaultRuleCreate,
    ReclassifyRequest, ValidateResult, ValidationIssue, DeriveResult,
)


# ── Dim Type ───────────────────────────────────────────────────────────────────

async def list_dim_types(db: AsyncSession, active_only: bool = False):
    q = select(DimType)
    if active_only:
        q = q.where(DimType.active == True)
    result = await db.execute(q.order_by(DimType.type_code))
    types = result.scalars().all()
    # attach value_count
    count_q = select(DimValue.dim_type_id, func.count().label("cnt")).group_by(DimValue.dim_type_id)
    counts = {r.dim_type_id: r.cnt for r in (await db.execute(count_q)).all()}
    for t in types:
        t.value_count = counts.get(t.id, 0)
    return types


async def create_dim_type(db: AsyncSession, data: DimTypeCreate) -> DimType:
    obj = DimType(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    obj.value_count = 0
    return obj


async def update_dim_type(db: AsyncSession, type_id, data: dict) -> DimType:
    obj = await db.get(DimType, type_id)
    if not obj:
        raise ValueError("Dimension type not found")
    for k, v in data.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


# ── Dim Value ──────────────────────────────────────────────────────────────────

async def list_dim_values(db: AsyncSession, dim_type_id=None, active_only=False):
    q = select(DimValue).options(selectinload(DimValue.dim_type), selectinload(DimValue.parent))
    if dim_type_id:
        q = q.where(DimValue.dim_type_id == dim_type_id)
    if active_only:
        q = q.where(DimValue.active == True)
    result = await db.execute(q.order_by(DimValue.level_no, DimValue.dim_code))
    values = result.scalars().all()
    # children counts
    child_q = select(DimValue.parent_id, func.count().label("cnt")).where(DimValue.parent_id != None).group_by(DimValue.parent_id)
    child_counts = {r.parent_id: r.cnt for r in (await db.execute(child_q)).all()}
    for v in values:
        v.dim_type_name = v.dim_type.type_name if v.dim_type else None
        v.parent_name = v.parent.dim_name if v.parent else None
        v.children_count = child_counts.get(v.id, 0)
    return values


async def create_dim_value(db: AsyncSession, data: DimValueCreate) -> DimValue:
    obj = DimValue(**data.model_dump())
    if obj.parent_id:
        parent = await db.get(DimValue, obj.parent_id)
        if parent:
            obj.level_no = parent.level_no + 1
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


# ── Cost Center ────────────────────────────────────────────────────────────────

async def list_cost_centers(db: AsyncSession, active_only=False):
    q = select(CostCenter).options(selectinload(CostCenter.parent))
    if active_only:
        q = q.where(CostCenter.active == True)
    result = await db.execute(q.order_by(CostCenter.cost_center_code))
    ccs = result.scalars().all()
    child_q = select(CostCenter.parent_id, func.count().label("cnt")).where(CostCenter.parent_id != None).group_by(CostCenter.parent_id)
    child_counts = {r.parent_id: r.cnt for r in (await db.execute(child_q)).all()}
    for cc in ccs:
        cc.parent_name = cc.parent.cost_center_name if cc.parent else None
        cc.children_count = child_counts.get(cc.id, 0)
    return ccs


async def create_cost_center(db: AsyncSession, data: CostCenterCreate) -> CostCenter:
    obj = CostCenter(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_cost_center(db: AsyncSession, cc_id, data: dict) -> CostCenter:
    obj = await db.get(CostCenter, cc_id)
    if not obj:
        raise ValueError("Cost center not found")
    for k, v in data.items():
        setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


# ── Transaction Dimensions ─────────────────────────────────────────────────────

async def tag_transaction(db: AsyncSession, data: TransactionDimensionCreate) -> TransactionDimension:
    # Check for existing tag for this transaction + dim_type, update if exists
    q = select(TransactionDimension).where(
        TransactionDimension.transaction_type == data.transaction_type,
        TransactionDimension.transaction_id == data.transaction_id,
        TransactionDimension.dim_type_id == data.dim_type_id,
    )
    if data.line_id:
        q = q.where(TransactionDimension.line_id == data.line_id)
    result = await db.execute(q)
    existing = result.scalar_one_or_none()
    if existing:
        if existing.locked:
            raise ValueError("Dimension tag is locked and cannot be changed")
        existing.dim_value_id = data.dim_value_id
        existing.source_type = data.source_type
        existing.notes = data.notes
        await db.commit()
        await db.refresh(existing)
        return existing
    obj = TransactionDimension(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_transaction_dimensions(db: AsyncSession, transaction_type: str, transaction_id: str):
    q = select(TransactionDimension).options(
        selectinload(TransactionDimension.dim_type),
        selectinload(TransactionDimension.dim_value),
    ).where(
        TransactionDimension.transaction_type == transaction_type,
        TransactionDimension.transaction_id == transaction_id,
    )
    result = await db.execute(q)
    tags = result.scalars().all()
    for t in tags:
        t.dim_type_code = t.dim_type.type_code if t.dim_type else None
        t.dim_type_name = t.dim_type.type_name if t.dim_type else None
        t.dim_value_code = t.dim_value.dim_code if t.dim_value else None
        t.dim_value_name = t.dim_value.dim_name if t.dim_value else None
    return tags


# ── Default Derivation Engine ──────────────────────────────────────────────────

async def derive_dimensions(
    db: AsyncSession,
    transaction_type: str,
    source_field: Optional[str] = None,
    source_field_value: Optional[str] = None,
) -> List[DeriveResult]:
    q = select(DimDefaultRule).options(
        selectinload(DimDefaultRule.dim_type),
        selectinload(DimDefaultRule.dim_value),
    ).where(
        DimDefaultRule.active == True,
        DimDefaultRule.transaction_type == transaction_type,
    ).order_by(DimDefaultRule.priority)

    if source_field:
        q = q.where(
            or_(
                DimDefaultRule.source_field == None,
                and_(
                    DimDefaultRule.source_field == source_field,
                    DimDefaultRule.source_field_value == source_field_value,
                ),
            )
        )

    result = await db.execute(q)
    rules = result.scalars().all()
    seen_types = set()
    derived: List[DeriveResult] = []
    for rule in rules:
        if rule.dim_type_id in seen_types:
            continue
        seen_types.add(rule.dim_type_id)
        derived.append(DeriveResult(
            dim_type_id=rule.dim_type_id,
            dim_type_name=rule.dim_type.type_name if rule.dim_type else "",
            dim_value_id=rule.dim_value_id,
            dim_value_name=rule.dim_value.dim_name if rule.dim_value else "",
            source_type=DimSourceType.RULE_BASED,
        ))
    return derived


# ── Validation Engine ──────────────────────────────────────────────────────────

async def validate_dimensions(
    db: AsyncSession,
    transaction_type: str,
    present_dim_type_ids: List,
) -> ValidateResult:
    q = select(DimValidationRule).options(selectinload(DimValidationRule.dim_type)).where(
        DimValidationRule.active == True,
        or_(
            DimValidationRule.transaction_type == None,
            DimValidationRule.transaction_type == transaction_type,
        ),
    )
    result = await db.execute(q)
    rules = result.scalars().all()

    issues: List[ValidationIssue] = []
    for rule in rules:
        if rule.dim_type_id not in present_dim_type_ids:
            issues.append(ValidationIssue(
                dim_type_code=rule.dim_type.type_code if rule.dim_type else "",
                dim_type_name=rule.dim_type.type_name if rule.dim_type else "",
                severity=rule.severity,
                message=f"Required dimension '{rule.dim_type.type_name if rule.dim_type else rule.dim_type_id}' is missing.",
            ))

    blocking = any(i.severity == ValidationSeverity.BLOCK for i in issues)
    return ValidateResult(valid=not blocking, issues=issues)


# ── Validation Rules CRUD ──────────────────────────────────────────────────────

async def list_validation_rules(db: AsyncSession):
    q = select(DimValidationRule).options(selectinload(DimValidationRule.dim_type))
    result = await db.execute(q)
    rules = result.scalars().all()
    for r in rules:
        r.dim_type_name = r.dim_type.type_name if r.dim_type else None
    return rules


async def create_validation_rule(db: AsyncSession, data: DimValidationRuleCreate) -> DimValidationRule:
    obj = DimValidationRule(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


# ── Allocation Rules ───────────────────────────────────────────────────────────

async def list_allocation_rules(db: AsyncSession):
    q = select(AllocationRule).options(
        selectinload(AllocationRule.source_dim_value),
        selectinload(AllocationRule.target_dim_type),
        selectinload(AllocationRule.lines).selectinload(AllocationRuleLine.target_dim_value),
    )
    result = await db.execute(q)
    rules = result.scalars().all()
    for r in rules:
        r.source_dim_value_name = r.source_dim_value.dim_name if r.source_dim_value else None
        r.target_dim_type_name = r.target_dim_type.type_name if r.target_dim_type else None
        for line in r.lines:
            line.target_dim_value_name = line.target_dim_value.dim_name if line.target_dim_value else None
    return rules


async def create_allocation_rule(db: AsyncSession, data: AllocationRuleCreate) -> AllocationRule:
    lines_data = data.lines
    obj_data = data.model_dump(exclude={"lines"})
    obj = AllocationRule(**obj_data)
    db.add(obj)
    await db.flush()
    for line_data in lines_data:
        line = AllocationRuleLine(rule_id=obj.id, **line_data.model_dump())
        db.add(line)
    await db.commit()
    await db.refresh(obj)
    return obj


# ── Allocation Engine ──────────────────────────────────────────────────────────

async def run_allocation(db: AsyncSession, req: AllocationRunRequest, posted_by_id=None) -> AllocationRun:
    rule = await db.get(AllocationRule, req.rule_id, options=[
        selectinload(AllocationRule.lines).selectinload(AllocationRuleLine.target_dim_value),
    ])
    if not rule:
        raise ValueError("Allocation rule not found")

    total_weight = sum(
        (line.fixed_pct or line.weight_value or Decimal(0))
        for line in rule.lines if line.active
    )

    run = AllocationRun(
        rule_id=req.rule_id,
        period_start=req.period_start,
        period_end=req.period_end,
        dry_run=req.dry_run,
        status=AllocationRunStatus.DRAFT,
        source_pool_amount=req.source_pool_amount,
        run_notes=req.run_notes,
        posted_by_id=posted_by_id,
    )
    db.add(run)
    await db.flush()

    total_allocated = Decimal(0)
    for line in rule.lines:
        if not line.active:
            continue
        if rule.allocation_basis == "FIXED_PCT" and line.fixed_pct:
            pct = line.fixed_pct / Decimal(100)
        elif total_weight > 0:
            pct = (line.weight_value or Decimal(0)) / total_weight
        else:
            pct = Decimal(0)

        amount = req.source_pool_amount * pct
        total_allocated += amount

        run_line = AllocationRunLine(
            run_id=run.id,
            target_dim_value_id=line.target_dim_value_id,
            pct_applied=pct * Decimal(100),
            allocated_amount=amount,
            journal_entry_id=None if req.dry_run else f"ALLOC-{run.id}-{line.id}",
        )
        db.add(run_line)

    run.total_allocated = total_allocated
    run.status = AllocationRunStatus.PREVIEWED if req.dry_run else AllocationRunStatus.POSTED

    await db.commit()
    await db.refresh(run)
    return run


async def list_allocation_runs(db: AsyncSession, rule_id=None, limit: int = 200):
    q = select(AllocationRun).options(
        selectinload(AllocationRun.rule),
        selectinload(AllocationRun.lines).selectinload(AllocationRunLine.target_dim_value),
    )
    if rule_id:
        q = q.where(AllocationRun.rule_id == rule_id)
    result = await db.execute(q.order_by(AllocationRun.created_at.desc()).limit(limit))
    runs = result.scalars().all()
    for run in runs:
        run.rule_name = run.rule.rule_name if run.rule else None
        for line in run.lines:
            line.target_dim_value_name = line.target_dim_value.dim_name if line.target_dim_value else None
    return runs


# ── Default Rules CRUD ─────────────────────────────────────────────────────────

async def list_default_rules(db: AsyncSession):
    q = select(DimDefaultRule).options(
        selectinload(DimDefaultRule.dim_type),
        selectinload(DimDefaultRule.dim_value),
    )
    result = await db.execute(q.order_by(DimDefaultRule.priority))
    rules = result.scalars().all()
    for r in rules:
        r.dim_type_name = r.dim_type.type_name if r.dim_type else None
        r.dim_value_name = r.dim_value.dim_name if r.dim_value else None
    return rules


async def create_default_rule(db: AsyncSession, data: DimDefaultRuleCreate) -> DimDefaultRule:
    obj = DimDefaultRule(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


# ── Reclassification ───────────────────────────────────────────────────────────

async def reclassify(db: AsyncSession, req: ReclassifyRequest, user_id=None) -> DimReclassification:
    # Find existing tag
    q = select(TransactionDimension).where(
        TransactionDimension.transaction_type == req.transaction_type,
        TransactionDimension.transaction_id == req.transaction_id,
        TransactionDimension.dim_type_id == req.dim_type_id,
    )
    result = await db.execute(q)
    existing = result.scalar_one_or_none()
    old_value_id = existing.dim_value_id if existing else None

    # Record the reclassification
    rec = DimReclassification(
        transaction_type=req.transaction_type,
        transaction_id=req.transaction_id,
        dim_type_id=req.dim_type_id,
        old_dim_value_id=old_value_id,
        new_dim_value_id=req.new_dim_value_id,
        reason=req.reason,
        journal_entry_ref=req.journal_entry_ref,
        reclassified_by_id=user_id,
    )
    db.add(rec)

    # Update or create the tag
    if existing:
        existing.dim_value_id = req.new_dim_value_id
        existing.source_type = DimSourceType.MANUAL
        existing.locked = False
    else:
        tag = TransactionDimension(
            transaction_type=req.transaction_type,
            transaction_id=req.transaction_id,
            dim_type_id=req.dim_type_id,
            dim_value_id=req.new_dim_value_id,
            source_type=DimSourceType.MANUAL,
        )
        db.add(tag)

    await db.commit()
    await db.refresh(rec)
    return rec


async def list_reclassifications(db: AsyncSession, transaction_type: str = None, limit: int = 200):
    q = select(DimReclassification).options(
        selectinload(DimReclassification.dim_type),
        selectinload(DimReclassification.old_dim_value),
        selectinload(DimReclassification.new_dim_value),
    )
    if transaction_type:
        q = q.where(DimReclassification.transaction_type == transaction_type)
    result = await db.execute(q.order_by(DimReclassification.created_at.desc()).limit(limit))
    recs = result.scalars().all()
    for r in recs:
        r.dim_type_name = r.dim_type.type_name if r.dim_type else None
        r.old_dim_value_name = r.old_dim_value.dim_name if r.old_dim_value else None
        r.new_dim_value_name = r.new_dim_value.dim_name if r.new_dim_value else None
    return recs


# ── Reporting ──────────────────────────────────────────────────────────────────

async def report_tagging_completeness(db: AsyncSession):
    q = select(
        TransactionDimension.transaction_type,
        func.count(TransactionDimension.id).label("tagged_count"),
    ).group_by(TransactionDimension.transaction_type)
    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "transaction_type": r.transaction_type,
            "total_transactions": r.tagged_count,
            "tagged_count": r.tagged_count,
            "untagged_count": 0,
            "completeness_pct": 100.0,
        }
        for r in rows
    ]


async def report_untagged_transactions(db: AsyncSession, mandatory_dim_type_ids: List):
    # Return counts grouped by transaction_type where mandatory dims are missing
    # Simplified: count transaction_dimensions for mandatory types
    q = select(
        TransactionDimension.transaction_type,
        TransactionDimension.transaction_id,
        TransactionDimension.dim_type_id,
    ).where(TransactionDimension.dim_type_id.in_(mandatory_dim_type_ids))
    result = await db.execute(q)
    return result.all()


async def dashboard_summary(db: AsyncSession):
    dt_count = (await db.execute(select(func.count()).select_from(DimType))).scalar()
    dv_count = (await db.execute(select(func.count()).select_from(DimValue))).scalar()
    cc_count = (await db.execute(select(func.count()).select_from(CostCenter).where(CostCenter.active == True))).scalar()
    ar_count = (await db.execute(select(func.count()).select_from(AllocationRule).where(AllocationRule.active == True))).scalar()
    ai_count = (await db.execute(select(func.count()).select_from(DimAIRecommendation).where(DimAIRecommendation.status == DimAIRecStatus.PENDING))).scalar()
    return {
        "total_dim_types": dt_count,
        "total_dim_values": dv_count,
        "total_cost_centers": cc_count,
        "active_allocation_rules": ar_count,
        "untagged_transactions_today": 0,
        "pending_ai_recs": ai_count,
    }


# ── AI Agents ──────────────────────────────────────────────────────────────────

async def run_ai_agents(db: AsyncSession) -> List[DimAIRecommendation]:
    created = []

    # Agent 1: Completeness Monitor — find dim types with no values
    q = select(DimType).where(DimType.active == True)
    types = (await db.execute(q)).scalars().all()
    count_q = select(DimValue.dim_type_id, func.count().label("cnt")).group_by(DimValue.dim_type_id)
    type_counts = {r.dim_type_id: r.cnt for r in (await db.execute(count_q)).all()}
    for t in types:
        if type_counts.get(t.id, 0) == 0:
            rec = DimAIRecommendation(
                agent_type=DimAIAgentType.COMPLETENESS_MONITOR,
                title=f"Dimension type '{t.type_name}' has no values defined",
                detail="This dimension type exists but no values have been created. Tagging rules referencing it will fail.",
                severity="warning",
                dim_type_id=t.id,
            )
            db.add(rec)
            created.append(rec)

    # Agent 1b: mandatory types flagged
    mandatory_types = [t for t in types if t.is_mandatory]
    tagged_type_q = select(TransactionDimension.dim_type_id).distinct()
    tagged_types = {r for r in (await db.execute(tagged_type_q)).scalars().all()}
    for t in mandatory_types:
        if t.id not in tagged_types:
            rec = DimAIRecommendation(
                agent_type=DimAIAgentType.COMPLETENESS_MONITOR,
                title=f"Mandatory dimension '{t.type_name}' has zero tagged transactions",
                detail="This dimension is marked mandatory but no transaction has been tagged with it. Consider enforcing via validation rules.",
                severity="critical",
                dim_type_id=t.id,
            )
            db.add(rec)
            created.append(rec)

    # Agent 2: Allocation Optimizer — rules with no lines
    alloc_q = select(AllocationRule).where(AllocationRule.active == True).options(selectinload(AllocationRule.lines))
    alloc_rules = (await db.execute(alloc_q)).scalars().all()
    for rule in alloc_rules:
        active_lines = [l for l in rule.lines if l.active]
        if not active_lines:
            rec = DimAIRecommendation(
                agent_type=DimAIAgentType.ALLOCATION_OPTIMIZER,
                title=f"Allocation rule '{rule.rule_name}' has no active target lines",
                detail="The allocation rule cannot distribute costs because no target lines are configured. Add target dimension values and percentages.",
                severity="warning",
                allocation_rule_id=rule.id,
            )
            db.add(rec)
            created.append(rec)
        elif sum(l.fixed_pct or 0 for l in active_lines if rule.allocation_basis == "FIXED_PCT") != 100:
            if rule.allocation_basis == "FIXED_PCT":
                rec = DimAIRecommendation(
                    agent_type=DimAIAgentType.ALLOCATION_OPTIMIZER,
                    title=f"Allocation rule '{rule.rule_name}' percentages do not sum to 100%",
                    detail="Fixed percentage lines must total exactly 100%. Review and correct the allocation splits.",
                    severity="warning",
                    allocation_rule_id=rule.id,
                )
                db.add(rec)
                created.append(rec)

    # Agent 3: Profitability Lens — cost centers with no type classification
    cc_q = select(CostCenter).where(CostCenter.active == True)
    cost_centers = (await db.execute(cc_q)).scalars().all()
    production_ccs = [cc for cc in cost_centers if cc.cost_center_type == "PRODUCTION"]
    if len(production_ccs) == 0 and len(cost_centers) > 0:
        rec = DimAIRecommendation(
            agent_type=DimAIAgentType.PROFITABILITY_LENS,
            title="No production cost centers defined — line profitability analysis unavailable",
            detail="To enable per-line cost analysis, create cost centers of type PRODUCTION mapped to each production line.",
            severity="info",
        )
        db.add(rec)
        created.append(rec)

    await db.commit()
    return created


async def list_ai_recs(db: AsyncSession, status: DimAIRecStatus = None, limit: int = 200):
    q = select(DimAIRecommendation)
    if status:
        q = q.where(DimAIRecommendation.status == status)
    result = await db.execute(q.order_by(DimAIRecommendation.created_at.desc()).limit(limit))
    return result.scalars().all()


async def ack_ai_rec(db: AsyncSession, rec_id, status: DimAIRecStatus) -> DimAIRecommendation:
    rec = await db.get(DimAIRecommendation, rec_id)
    if not rec:
        raise ValueError("Recommendation not found")
    rec.status = status
    await db.commit()
    await db.refresh(rec)
    return rec
