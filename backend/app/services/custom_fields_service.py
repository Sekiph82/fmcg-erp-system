from __future__ import annotations
import re
import ast
import operator
from datetime import datetime
from typing import Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from app.models.custom_fields import (
    CustomFieldDefinition, CustomFieldOption, CustomFieldValue,
    CustomFieldValidationRule, CFAIRecommendation, WorkflowTriggerRule,
    FieldType, EntityType, ValidationRuleType,
    CFAIAgentType, CFAIRecStatus,
)
from app.schemas.custom_fields import (
    CustomFieldCreate, CustomFieldUpdate, FieldValuesSet,
    FieldValueOut, ValidationResult, ValidationError, UsageStat, CFAIRecAck,
    FormLayoutReorder, WorkflowRuleCreate, WorkflowRuleUpdate,
)


# ── Safe formula evaluator ────────────────────────────────────────────────────

_SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    raise ValueError("Unsupported expression")


def _safe_eval_formula(formula: str, vars_: dict) -> Optional[float]:
    expr = formula
    for k, v in vars_.items():
        expr = expr.replace(f"{{{k}}}", str(v or 0))
    expr = re.sub(r"\{[^}]+\}", "0", expr)
    try:
        return _eval_node(ast.parse(expr, mode="eval").body)
    except Exception:
        return None


# ── Value storage helpers ─────────────────────────────────────────────────────

def _store_kwargs(field_type: FieldType, value: Any) -> dict:
    if field_type in (FieldType.TEXT, FieldType.LONG_TEXT, FieldType.URL,
                      FieldType.EMAIL, FieldType.PHONE, FieldType.SELECT,
                      FieldType.REFERENCE, FieldType.COMPUTED):
        return {"value_text": str(value) if value is not None else None}
    if field_type in (FieldType.NUMBER, FieldType.DECIMAL, FieldType.CURRENCY):
        try:
            return {"value_number": float(value)}
        except (ValueError, TypeError):
            return {"value_text": str(value)}
    if field_type in (FieldType.DATE, FieldType.DATETIME):
        if isinstance(value, str):
            try:
                return {"value_date": datetime.fromisoformat(value)}
            except ValueError:
                return {}
        return {"value_date": value}
    if field_type == FieldType.BOOLEAN:
        if isinstance(value, str):
            return {"value_boolean": value.lower() in ("1", "true", "yes")}
        return {"value_boolean": bool(value)}
    if field_type == FieldType.MULTI_SELECT:
        return {"value_json": value if isinstance(value, list) else ([value] if value else [])}
    if field_type == FieldType.FILE_ATTACHMENT:
        return {"file_ref": str(value) if value else None}
    return {"value_text": str(value) if value is not None else None}


def _extract_value(val: CustomFieldValue, field_type: FieldType) -> Any:
    if field_type in (FieldType.TEXT, FieldType.LONG_TEXT, FieldType.URL,
                      FieldType.EMAIL, FieldType.PHONE, FieldType.SELECT,
                      FieldType.REFERENCE, FieldType.COMPUTED):
        return val.value_text
    if field_type in (FieldType.NUMBER, FieldType.DECIMAL, FieldType.CURRENCY):
        return val.value_number
    if field_type in (FieldType.DATE, FieldType.DATETIME):
        return val.value_date.isoformat() if val.value_date else None
    if field_type == FieldType.BOOLEAN:
        return val.value_boolean
    if field_type == FieldType.MULTI_SELECT:
        return val.value_json
    if field_type == FieldType.FILE_ATTACHMENT:
        return val.file_ref
    return val.value_text


def _display_value(value: Any, field: CustomFieldDefinition) -> Optional[str]:
    if value is None:
        return None
    if field.field_type == FieldType.SELECT:
        for opt in field.options:
            if opt.option_value == str(value):
                return opt.option_label
        return str(value)
    if field.field_type == FieldType.MULTI_SELECT and isinstance(value, list):
        labels = []
        for v in value:
            for opt in field.options:
                if opt.option_value == v:
                    labels.append(opt.option_label)
                    break
            else:
                labels.append(v)
        return ", ".join(labels)
    if field.field_type == FieldType.BOOLEAN:
        return "Yes" if value else "No"
    if field.field_type == FieldType.CURRENCY and value is not None:
        try:
            return f"KES {float(value):,.2f}"
        except (ValueError, TypeError):
            pass
    return str(value)


# ── Load helper ───────────────────────────────────────────────────────────────

async def _load_field(db: AsyncSession, custom_field_id: str) -> Optional[CustomFieldDefinition]:
    result = await db.execute(
        select(CustomFieldDefinition)
        .options(
            selectinload(CustomFieldDefinition.options),
            selectinload(CustomFieldDefinition.validation_rules),
        )
        .where(CustomFieldDefinition.custom_field_id == custom_field_id)
    )
    return result.scalar_one_or_none()


# ── Field CRUD ────────────────────────────────────────────────────────────────

async def list_fields(
    db: AsyncSession,
    entity_type: Optional[str] = None,
    active_only: bool = True,
) -> List[CustomFieldDefinition]:
    q = select(CustomFieldDefinition).options(
        selectinload(CustomFieldDefinition.options),
        selectinload(CustomFieldDefinition.validation_rules),
    )
    if entity_type:
        q = q.where(CustomFieldDefinition.entity_type == entity_type)
    if active_only:
        q = q.where(CustomFieldDefinition.active_flag == True)
    result = await db.execute(q.order_by(CustomFieldDefinition.entity_type, CustomFieldDefinition.display_order))
    return result.scalars().all()


async def get_field(db: AsyncSession, custom_field_id: str) -> Optional[CustomFieldDefinition]:
    return await _load_field(db, custom_field_id)


async def create_field(db: AsyncSession, data: CustomFieldCreate) -> CustomFieldDefinition:
    field = CustomFieldDefinition(**{
        k: v for k, v in data.model_dump(exclude={"options", "validation_rules"}).items()
    })
    db.add(field)
    await db.flush()

    for i, opt in enumerate(data.options):
        db.add(CustomFieldOption(custom_field_id=field.custom_field_id, **opt.model_dump()))
    for rule in data.validation_rules:
        db.add(CustomFieldValidationRule(custom_field_id=field.custom_field_id, **rule.model_dump()))

    await db.commit()
    return await _load_field(db, field.custom_field_id)


async def update_field(db: AsyncSession, custom_field_id: str, data: CustomFieldUpdate) -> CustomFieldDefinition:
    field = await _load_field(db, custom_field_id)
    if not field:
        raise ValueError("Custom field not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(field, k, v)
    await db.commit()
    return await _load_field(db, custom_field_id)


async def disable_field(db: AsyncSession, custom_field_id: str) -> CustomFieldDefinition:
    field = await _load_field(db, custom_field_id)
    if not field:
        raise ValueError("Custom field not found")
    field.active_flag = False
    await db.commit()
    return await _load_field(db, custom_field_id)


async def add_option(db: AsyncSession, custom_field_id: str, option_value: str, option_label: str, display_order: int = 0) -> None:
    db.add(CustomFieldOption(
        custom_field_id=custom_field_id,
        option_value=option_value,
        option_label=option_label,
        display_order=display_order,
    ))
    await db.commit()


async def remove_option(db: AsyncSession, option_id: str) -> None:
    result = await db.execute(
        select(CustomFieldOption).where(CustomFieldOption.option_id == option_id)
    )
    opt = result.scalar_one_or_none()
    if opt:
        opt.active_flag = False
        await db.commit()


# ── Entity fields ─────────────────────────────────────────────────────────────

async def get_entity_fields(db: AsyncSession, entity_type: str) -> List[CustomFieldDefinition]:
    result = await db.execute(
        select(CustomFieldDefinition)
        .options(
            selectinload(CustomFieldDefinition.options),
            selectinload(CustomFieldDefinition.validation_rules),
        )
        .where(
            and_(
                CustomFieldDefinition.entity_type == entity_type,
                CustomFieldDefinition.active_flag == True,
            )
        )
        .order_by(CustomFieldDefinition.display_order, CustomFieldDefinition.field_label)
    )
    return result.scalars().all()


# ── Values ────────────────────────────────────────────────────────────────────

async def get_values(db: AsyncSession, entity_type: str, entity_id: str) -> List[FieldValueOut]:
    fields = await get_entity_fields(db, entity_type)
    if not fields:
        return []

    values_result = await db.execute(
        select(CustomFieldValue).where(
            and_(
                CustomFieldValue.entity_id == entity_id,
                CustomFieldValue.custom_field_id.in_([f.custom_field_id for f in fields]),
            )
        )
    )
    values_map = {v.custom_field_id: v for v in values_result.scalars().all()}

    # Collect raw values for computed fields
    raw_by_code: dict = {}
    for f in fields:
        v = values_map.get(f.custom_field_id)
        if v:
            raw_by_code[f.field_code] = _extract_value(v, f.field_type)

    results = []
    for field in fields:
        v = values_map.get(field.custom_field_id)
        if field.field_type == FieldType.COMPUTED and field.formula:
            computed = _safe_eval_formula(field.formula, raw_by_code)
            raw = computed
        else:
            raw = _extract_value(v, field.field_type) if v else None

        results.append(FieldValueOut(
            custom_field_id=field.custom_field_id,
            field_code=field.field_code,
            field_label=field.field_label,
            field_type=field.field_type,
            value=raw,
            display_value=_display_value(raw, field),
            required_flag=field.required_flag,
            sensitive_flag=field.sensitive_flag,
        ))
    return results


async def validate_values(
    db: AsyncSession, entity_type: str, values: Dict[str, Any], entity_id: Optional[str] = None
) -> ValidationResult:
    fields = await get_entity_fields(db, entity_type)
    field_by_code = {f.field_code: f for f in fields}
    errors: List[ValidationError] = []

    for field in fields:
        value = values.get(field.field_code)
        field_errors: List[str] = []

        if field.required_flag and (value is None or value == ""):
            field_errors.append(f"{field.field_label} is required")

        if value is not None and value != "":
            if field.field_type in (FieldType.NUMBER, FieldType.DECIMAL, FieldType.CURRENCY):
                try:
                    float(value)
                except (ValueError, TypeError):
                    field_errors.append(f"{field.field_label} must be a number")

            if field.field_type == FieldType.SELECT:
                allowed = [o.option_value for o in field.options if o.active_flag]
                if str(value) not in allowed:
                    field_errors.append(f"Invalid option for {field.field_label}")

            if field.field_type == FieldType.EMAIL and value:
                if not re.match(r"^[^@]+@[^@]+\.[^@]+$", str(value)):
                    field_errors.append(f"{field.field_label} must be a valid email address")

            if field.field_type == FieldType.URL and value:
                if not str(value).startswith(("http://", "https://")):
                    field_errors.append(f"{field.field_label} must start with http:// or https://")

            for rule in field.validation_rules:
                if not rule.active_flag:
                    continue
                err_msg = rule.error_message or f"{field.field_label} validation failed"
                if rule.rule_type == ValidationRuleType.MIN:
                    try:
                        if float(value) < float(rule.rule_value):
                            field_errors.append(err_msg)
                    except (ValueError, TypeError):
                        pass
                elif rule.rule_type == ValidationRuleType.MAX:
                    try:
                        if float(value) > float(rule.rule_value):
                            field_errors.append(err_msg)
                    except (ValueError, TypeError):
                        pass
                elif rule.rule_type == ValidationRuleType.MIN_LENGTH:
                    try:
                        if len(str(value)) < int(rule.rule_value):
                            field_errors.append(err_msg)
                    except (ValueError, TypeError):
                        pass
                elif rule.rule_type == ValidationRuleType.MAX_LENGTH:
                    try:
                        if len(str(value)) > int(rule.rule_value):
                            field_errors.append(err_msg)
                    except (ValueError, TypeError):
                        pass
                elif rule.rule_type == ValidationRuleType.REGEX:
                    if not re.match(rule.rule_value, str(value)):
                        field_errors.append(err_msg)
                elif rule.rule_type == ValidationRuleType.UNIQUE and entity_id:
                    dup = await db.execute(
                        select(CustomFieldValue).where(
                            and_(
                                CustomFieldValue.custom_field_id == field.custom_field_id,
                                CustomFieldValue.value_text == str(value),
                                CustomFieldValue.entity_id != entity_id,
                            )
                        )
                    )
                    if dup.scalar_one_or_none():
                        field_errors.append(f"{field.field_label} must be unique")

        if field_errors:
            errors.append(ValidationError(
                field_code=field.field_code,
                field_label=field.field_label,
                errors=field_errors,
            ))

    return ValidationResult(valid=len(errors) == 0, errors=errors)


async def set_values(
    db: AsyncSession, entity_type: str, entity_id: str, data: FieldValuesSet
) -> List[FieldValueOut]:
    fields = await get_entity_fields(db, entity_type)
    field_by_code = {f.field_code: f for f in fields}

    existing_result = await db.execute(
        select(CustomFieldValue).where(
            and_(
                CustomFieldValue.entity_id == entity_id,
                CustomFieldValue.custom_field_id.in_([f.custom_field_id for f in fields]),
            )
        )
    )
    existing_map = {v.custom_field_id: v for v in existing_result.scalars().all()}

    for code, value in data.values.items():
        field = field_by_code.get(code)
        if not field:
            continue
        if field.field_type == FieldType.COMPUTED:
            continue

        kwargs = _store_kwargs(field.field_type, value)
        existing = existing_map.get(field.custom_field_id)
        if existing:
            for k, v in kwargs.items():
                setattr(existing, k, v)
            existing.updated_by = data.updated_by
            existing.updated_at = datetime.utcnow()
        else:
            db.add(CustomFieldValue(
                custom_field_id=field.custom_field_id,
                entity_type=entity_type,
                entity_id=entity_id,
                updated_by=data.updated_by,
                **kwargs,
            ))

    await db.commit()
    return await get_values(db, entity_type, entity_id)


# ── Stats & reports ───────────────────────────────────────────────────────────

async def get_usage_stats(db: AsyncSession) -> List[UsageStat]:
    result = await db.execute(
        select(CustomFieldValue.custom_field_id, func.count().label("cnt"))
        .group_by(CustomFieldValue.custom_field_id)
    )
    usage = {r[0]: r[1] for r in result.all()}

    fields = await list_fields(db, active_only=False)
    stats = []
    for f in fields:
        stats.append(UsageStat(
            custom_field_id=f.custom_field_id,
            field_code=f.field_code,
            field_label=f.field_label,
            entity_type=f.entity_type.value if hasattr(f.entity_type, "value") else str(f.entity_type),
            value_count=usage.get(f.custom_field_id, 0),
        ))
    return sorted(stats, key=lambda s: s.value_count, reverse=True)


async def get_metadata(db: AsyncSession) -> dict:
    fields = await list_fields(db, active_only=True)
    meta: dict = {}
    for f in fields:
        et = f.entity_type.value if hasattr(f.entity_type, "value") else str(f.entity_type)
        meta.setdefault(et, []).append({
            "field_code": f.field_code,
            "field_label": f.field_label,
            "field_type": f.field_type.value if hasattr(f.field_type, "value") else str(f.field_type),
            "reportable": f.reportable_flag,
            "filterable": f.filterable_flag,
        })
    return meta


async def get_missing_required(db: AsyncSession, entity_type: str) -> List[dict]:
    req_fields_result = await db.execute(
        select(CustomFieldDefinition)
        .where(
            and_(
                CustomFieldDefinition.entity_type == entity_type,
                CustomFieldDefinition.required_flag == True,
                CustomFieldDefinition.active_flag == True,
            )
        )
    )
    req_fields = req_fields_result.scalars().all()
    if not req_fields:
        return []

    entity_ids_result = await db.execute(
        select(CustomFieldValue.entity_id)
        .where(CustomFieldValue.entity_type == entity_type)
        .distinct()
        .limit(200)
    )
    entity_ids = [r[0] for r in entity_ids_result.all()]

    missing = []
    for entity_id in entity_ids:
        for field in req_fields:
            val_result = await db.execute(
                select(CustomFieldValue).where(
                    and_(
                        CustomFieldValue.custom_field_id == field.custom_field_id,
                        CustomFieldValue.entity_id == entity_id,
                    )
                )
            )
            val = val_result.scalar_one_or_none()
            raw = _extract_value(val, field.field_type) if val else None
            if raw is None or raw == "":
                missing.append({
                    "entity_id": entity_id,
                    "field_code": field.field_code,
                    "field_label": field.field_label,
                })
    return missing


# ── AI Agents ─────────────────────────────────────────────────────────────────

_COMMON_SUGGESTIONS = {
    "customer": ["Customer Tier", "Industry", "Account Manager", "KAM Notes"],
    "supplier": ["Supplier Category", "Risk Rating", "Lead Time (Days)"],
    "product": ["Product Line", "Brand", "Shelf Life (Days)", "Storage Temp (°C)"],
    "sales_order": ["Priority", "Campaign Code", "Special Instructions"],
    "purchase_order": ["Urgency Level", "Budget Code", "Approval Notes"],
    "employee": ["Department Code", "Skill Level", "Work Location"],
    "asset": ["Insurance Policy No.", "Maintenance Vendor", "Warranty Expiry"],
    "contract": ["Contract Category", "Review Cycle (Months)", "Key Terms"],
    "crm_record": ["Lead Temperature", "Decision Maker", "Competition"],
    "expense": ["Project Code", "Business Purpose"],
    "production_order": ["Quality Hold Reason", "Batch Notes"],
    "lot": ["Quarantine Reason", "Customs Reference"],
}


async def list_ai_recs(db: AsyncSession) -> list:
    result = await db.execute(
        select(CFAIRecommendation).order_by(CFAIRecommendation.created_at.desc())
    )
    return result.scalars().all()


async def ack_ai_rec(db: AsyncSession, rec_id: str, data: CFAIRecAck) -> CFAIRecommendation:
    result = await db.execute(
        select(CFAIRecommendation).where(CFAIRecommendation.rec_id == rec_id)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise ValueError("Recommendation not found")
    r.status = data.status
    await db.commit()
    await db.refresh(r)
    return r


async def run_field_design_assistant(db: AsyncSession) -> int:
    counts_result = await db.execute(
        select(CustomFieldDefinition.entity_type, func.count().label("cnt"))
        .where(CustomFieldDefinition.active_flag == True)
        .group_by(CustomFieldDefinition.entity_type)
    )
    entity_counts = {str(r[0].value if hasattr(r[0], "value") else r[0]): r[1] for r in counts_result.all()}

    recs = []
    for et in EntityType:
        count = entity_counts.get(et.value, 0)
        if count == 0:
            suggestions = _COMMON_SUGGESTIONS.get(et.value, ["Priority", "Tags", "Notes"])
            recs.append(CFAIRecommendation(
                agent_type=CFAIAgentType.FIELD_DESIGN_ASSISTANT,
                entity_type=et.value,
                title=f"No custom fields for {et.value.replace('_', ' ').title()}",
                body=(
                    f"The '{et.value}' module has no custom fields. "
                    f"Consider adding: {', '.join(suggestions[:4])}."
                ),
                score=70.0,
                rec_metadata={"entity_type": et.value, "suggestions": suggestions},
            ))

    # Duplicate label detection
    all_result = await db.execute(
        select(CustomFieldDefinition).where(CustomFieldDefinition.active_flag == True)
    )
    all_fields = all_result.scalars().all()
    label_map: dict = {}
    for f in all_fields:
        ll = f.field_label.lower().strip()
        label_map.setdefault(ll, []).append(f)
    for label, dupes in label_map.items():
        if len(dupes) > 1 and len({f.entity_type for f in dupes}) > 1:
            entities = list({str(f.entity_type.value if hasattr(f.entity_type, "value") else f.entity_type) for f in dupes})
            recs.append(CFAIRecommendation(
                agent_type=CFAIAgentType.FIELD_DESIGN_ASSISTANT,
                title=f"Duplicate field label detected: '{label}'",
                body=(
                    f"Field '{label}' exists across {len(dupes)} entity types "
                    f"({', '.join(entities[:3])}). Consider standardizing naming conventions."
                ),
                score=60.0,
                rec_metadata={"label": label, "entity_types": entities},
            ))

    for r in recs[:8]:
        db.add(r)
    await db.commit()
    return len(recs)


# ── Form Layout ────────────────────────────────────────────────────────────────

async def get_form_layout(db: AsyncSession, entity_type: str) -> List[CustomFieldDefinition]:
    result = await db.execute(
        select(CustomFieldDefinition)
        .options(
            selectinload(CustomFieldDefinition.options),
            selectinload(CustomFieldDefinition.validation_rules),
        )
        .where(
            and_(
                CustomFieldDefinition.entity_type == entity_type,
                CustomFieldDefinition.active_flag == True,
            )
        )
        .order_by(CustomFieldDefinition.display_order)
    )
    return result.scalars().all()


async def reorder_form_layout(db: AsyncSession, entity_type: str, data: FormLayoutReorder) -> List[CustomFieldDefinition]:
    for item in data.items:
        result = await db.execute(
            select(CustomFieldDefinition).where(
                and_(
                    CustomFieldDefinition.custom_field_id == item.custom_field_id,
                    CustomFieldDefinition.entity_type == entity_type,
                )
            )
        )
        field = result.scalar_one_or_none()
        if field:
            field.display_order = item.display_order
            if item.section_label is not None:
                field.section_label = item.section_label
            if item.field_width is not None:
                field.field_width = item.field_width
            field.updated_at = datetime.utcnow()
    await db.commit()
    return await get_form_layout(db, entity_type)


# ── Workflow Rules ─────────────────────────────────────────────────────────────

async def list_workflow_rules(
    db: AsyncSession,
    entity_type: Optional[str] = None,
    active_only: bool = False,
) -> List[WorkflowTriggerRule]:
    q = select(WorkflowTriggerRule)
    if entity_type:
        q = q.where(WorkflowTriggerRule.entity_type == entity_type)
    if active_only:
        q = q.where(WorkflowTriggerRule.active_flag == True)
    result = await db.execute(q.order_by(WorkflowTriggerRule.created_at.desc()))
    return result.scalars().all()


async def create_workflow_rule(db: AsyncSession, data: WorkflowRuleCreate) -> WorkflowTriggerRule:
    rule = WorkflowTriggerRule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def update_workflow_rule(db: AsyncSession, rule_id: str, data: WorkflowRuleUpdate) -> WorkflowTriggerRule:
    result = await db.execute(
        select(WorkflowTriggerRule).where(WorkflowTriggerRule.rule_id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise ValueError("Workflow rule not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(rule, k, v)
    rule.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(rule)
    return rule


async def delete_workflow_rule(db: AsyncSession, rule_id: str) -> None:
    result = await db.execute(
        select(WorkflowTriggerRule).where(WorkflowTriggerRule.rule_id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise ValueError("Workflow rule not found")
    await db.delete(rule)
    await db.commit()


async def run_data_quality_monitor(db: AsyncSession) -> int:
    usage_result = await db.execute(
        select(CustomFieldValue.custom_field_id, func.count().label("cnt"))
        .group_by(CustomFieldValue.custom_field_id)
    )
    usage = {r[0]: r[1] for r in usage_result.all()}

    all_result = await db.execute(
        select(CustomFieldDefinition).where(CustomFieldDefinition.active_flag == True)
    )
    all_fields = all_result.scalars().all()

    recs = []
    for f in all_fields:
        count = usage.get(f.custom_field_id, 0)
        et = f.entity_type.value if hasattr(f.entity_type, "value") else str(f.entity_type)
        if count == 0 and f.required_flag:
            recs.append(CFAIRecommendation(
                agent_type=CFAIAgentType.DATA_QUALITY_MONITOR,
                entity_type=et,
                title=f"Required field with no values: {f.field_label}",
                body=(
                    f"'{f.field_label}' ({et}) is marked required but has 0 recorded values. "
                    "Verify it's being populated on entity creation/import."
                ),
                score=90.0,
                rec_metadata={"field_id": f.custom_field_id, "entity_type": et},
            ))
        elif count > 0 and count < 5 and not f.required_flag:
            recs.append(CFAIRecommendation(
                agent_type=CFAIAgentType.DATA_QUALITY_MONITOR,
                entity_type=et,
                title=f"Low adoption field: {f.field_label} ({count} values)",
                body=(
                    f"'{f.field_label}' ({et}) has only {count} values recorded. "
                    "If this field is important, consider making it required or adding help text."
                ),
                score=40.0,
                rec_metadata={"field_id": f.custom_field_id, "value_count": count},
            ))

    for r in recs[:8]:
        db.add(r)
    await db.commit()
    return len(recs)


async def run_reporting_assistant(db: AsyncSession) -> int:
    usage_result = await db.execute(
        select(CustomFieldValue.custom_field_id, func.count().label("cnt"))
        .group_by(CustomFieldValue.custom_field_id)
        .having(func.count() >= 5)
    )
    high_usage = {r[0]: r[1] for r in usage_result.all()}

    if not high_usage:
        await db.commit()
        return 0

    fields_result = await db.execute(
        select(CustomFieldDefinition).where(
            and_(
                CustomFieldDefinition.active_flag == True,
                CustomFieldDefinition.reportable_flag == False,
                CustomFieldDefinition.custom_field_id.in_(list(high_usage.keys())),
            )
        )
    )
    fields = fields_result.scalars().all()

    recs = []
    for f in fields:
        count = high_usage[f.custom_field_id]
        et = f.entity_type.value if hasattr(f.entity_type, "value") else str(f.entity_type)
        recs.append(CFAIRecommendation(
            agent_type=CFAIAgentType.REPORTING_ASSISTANT,
            entity_type=et,
            title=f"Enable reporting for: {f.field_label}",
            body=(
                f"'{f.field_label}' ({et}) has {count} recorded values but "
                "reportable_flag is OFF. Enable it to include in the Report Builder."
            ),
            score=round(min(count / 50 * 100, 90), 1),
            rec_metadata={"field_id": f.custom_field_id, "value_count": count},
        ))

    for r in recs[:8]:
        db.add(r)
    await db.commit()
    return len(recs)
