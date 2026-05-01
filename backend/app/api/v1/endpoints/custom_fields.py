from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.db.session import get_db
from app.schemas.custom_fields import (
    CustomFieldOut, CustomFieldCreate, CustomFieldUpdate,
    FieldOptionCreate, ValidationRuleCreate,
    FieldValueOut, FieldValuesSet, ValidationResult,
    UsageStat, CFAIRecOut, CFAIRecAck,
)
from app.services import custom_fields_service

router = APIRouter()


# ── Field definitions ─────────────────────────────────────────────────────────

@router.get("/metadata")
async def get_metadata(db: AsyncSession = Depends(get_db)):
    return await custom_fields_service.get_metadata(db)


@router.get("/usage-stats", response_model=List[UsageStat])
async def get_usage_stats(db: AsyncSession = Depends(get_db)):
    return await custom_fields_service.get_usage_stats(db)


@router.get("/entity/{entity_type}", response_model=List[CustomFieldOut])
async def get_entity_fields(entity_type: str, db: AsyncSession = Depends(get_db)):
    return await custom_fields_service.get_entity_fields(db, entity_type)


@router.get("/ai/recs", response_model=List[CFAIRecOut])
async def list_ai_recs(db: AsyncSession = Depends(get_db)):
    return await custom_fields_service.list_ai_recs(db)


@router.post("/ai/run/field-design-assistant")
async def run_field_design_assistant(db: AsyncSession = Depends(get_db)):
    count = await custom_fields_service.run_field_design_assistant(db)
    return {"generated": count}


@router.post("/ai/run/data-quality-monitor")
async def run_data_quality_monitor(db: AsyncSession = Depends(get_db)):
    count = await custom_fields_service.run_data_quality_monitor(db)
    return {"generated": count}


@router.post("/ai/run/reporting-assistant")
async def run_reporting_assistant(db: AsyncSession = Depends(get_db)):
    count = await custom_fields_service.run_reporting_assistant(db)
    return {"generated": count}


@router.patch("/ai/recs/{rec_id}", response_model=CFAIRecOut)
async def ack_ai_rec(rec_id: str, data: CFAIRecAck, db: AsyncSession = Depends(get_db)):
    try:
        return await custom_fields_service.ack_ai_rec(db, rec_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("", response_model=List[CustomFieldOut])
async def list_fields(
    entity_type: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    return await custom_fields_service.list_fields(db, entity_type, active_only)


@router.post("", response_model=CustomFieldOut)
async def create_field(data: CustomFieldCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await custom_fields_service.create_field(db, data)
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/{custom_field_id}", response_model=CustomFieldOut)
async def get_field(custom_field_id: str, db: AsyncSession = Depends(get_db)):
    f = await custom_fields_service.get_field(db, custom_field_id)
    if not f:
        raise HTTPException(404, "Custom field not found")
    return f


@router.patch("/{custom_field_id}", response_model=CustomFieldOut)
async def update_field(
    custom_field_id: str, data: CustomFieldUpdate, db: AsyncSession = Depends(get_db)
):
    try:
        return await custom_fields_service.update_field(db, custom_field_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{custom_field_id}/disable", response_model=CustomFieldOut)
async def disable_field(custom_field_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return await custom_fields_service.disable_field(db, custom_field_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{custom_field_id}/options")
async def add_option(
    custom_field_id: str, data: FieldOptionCreate, db: AsyncSession = Depends(get_db)
):
    await custom_fields_service.add_option(
        db, custom_field_id, data.option_value, data.option_label, data.display_order
    )
    return {"ok": True}


@router.delete("/options/{option_id}")
async def remove_option(option_id: str, db: AsyncSession = Depends(get_db)):
    await custom_fields_service.remove_option(db, option_id)
    return {"ok": True}


# ── Values ────────────────────────────────────────────────────────────────────

@router.get("/values/{entity_type}/{entity_id}", response_model=List[FieldValueOut])
async def get_values(entity_type: str, entity_id: str, db: AsyncSession = Depends(get_db)):
    return await custom_fields_service.get_values(db, entity_type, entity_id)


@router.post("/values/{entity_type}/{entity_id}", response_model=List[FieldValueOut])
async def set_values(
    entity_type: str, entity_id: str, data: FieldValuesSet, db: AsyncSession = Depends(get_db)
):
    return await custom_fields_service.set_values(db, entity_type, entity_id, data)


@router.post("/values/{entity_type}/{entity_id}/validate", response_model=ValidationResult)
async def validate_values(
    entity_type: str, entity_id: str, data: FieldValuesSet, db: AsyncSession = Depends(get_db)
):
    return await custom_fields_service.validate_values(db, entity_type, data.values, entity_id)


@router.get("/values/{entity_type}/missing-required")
async def get_missing_required(entity_type: str, db: AsyncSession = Depends(get_db)):
    return await custom_fields_service.get_missing_required(db, entity_type)
