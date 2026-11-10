"""Focused contracts for reviewed predictive-maintenance actions."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.maintenance import MaintenancePredictionStatus
from app.schemas.maintenance import PMWorkOrderCreate
from app.services import maintenance_service


def _result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_reviewed_prediction_creates_and_links_one_work_order(monkeypatch):
    prediction_id = uuid4()
    asset_id = uuid4()
    plan_id = uuid4()
    actor_id = uuid4()
    work_order_id = uuid4()
    prediction = SimpleNamespace(
        id=prediction_id,
        asset_id=asset_id,
        status=MaintenancePredictionStatus.REVIEWED,
        work_order_id=None,
    )
    plan = SimpleNamespace(id=plan_id, asset_id=asset_id, is_active=True)
    db = SimpleNamespace(
        execute=AsyncMock(side_effect=[_result(prediction), _result(plan)]),
        flush=AsyncMock(),
    )
    create_work_order = AsyncMock(return_value=SimpleNamespace(id=work_order_id))
    monkeypatch.setattr(maintenance_service.maintenance_crud, "create_work_order", create_work_order)
    body = PMWorkOrderCreate(plan_id=str(plan_id), scheduled_date=date(2026, 11, 12))

    result = await maintenance_service.create_work_order_from_prediction(
        db, prediction_id, body, actor_id
    )

    assert result is prediction
    assert prediction.status == MaintenancePredictionStatus.WORK_ORDER_CREATED
    assert prediction.work_order_id == work_order_id
    assert prediction.work_order_created_by_id == actor_id
    assert prediction.work_order_created_at is not None
    create_work_order.assert_awaited_once()
    assert create_work_order.await_args.args[2] == f"WO-PRED-{prediction_id.hex[:12].upper()}"
    assert create_work_order.await_args.args[1]["plan_id"] == plan_id


@pytest.mark.asyncio
async def test_prediction_action_rejects_a_plan_for_another_asset(monkeypatch):
    prediction_id = uuid4()
    prediction = SimpleNamespace(
        id=prediction_id,
        asset_id=uuid4(),
        status=MaintenancePredictionStatus.REVIEWED,
        work_order_id=None,
    )
    plan = SimpleNamespace(id=uuid4(), asset_id=uuid4(), is_active=True)
    db = SimpleNamespace(execute=AsyncMock(side_effect=[_result(prediction), _result(plan)]))
    create_work_order = AsyncMock()
    monkeypatch.setattr(maintenance_service.maintenance_crud, "create_work_order", create_work_order)
    body = PMWorkOrderCreate(plan_id=str(plan.id), scheduled_date=date(2026, 11, 12))

    with pytest.raises(HTTPException) as error:
        await maintenance_service.create_work_order_from_prediction(db, prediction_id, body, uuid4())

    assert error.value.status_code == 422
    create_work_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_prediction_work_order_action_is_idempotent_after_link(monkeypatch):
    prediction = SimpleNamespace(
        id=uuid4(),
        status=MaintenancePredictionStatus.WORK_ORDER_CREATED,
        work_order_id=uuid4(),
    )
    db = SimpleNamespace(execute=AsyncMock(return_value=_result(prediction)))
    create_work_order = AsyncMock()
    monkeypatch.setattr(maintenance_service.maintenance_crud, "create_work_order", create_work_order)
    body = PMWorkOrderCreate(plan_id=str(uuid4()), scheduled_date=date(2026, 11, 12))

    result = await maintenance_service.create_work_order_from_prediction(db, prediction.id, body, uuid4())

    assert result is prediction
    create_work_order.assert_not_awaited()


@pytest.mark.asyncio
async def test_prediction_cannot_be_marked_as_work_order_created_by_review_only():
    prediction = SimpleNamespace(status=MaintenancePredictionStatus.OPEN)
    db = SimpleNamespace(flush=AsyncMock(), refresh=AsyncMock())

    with pytest.raises(HTTPException) as error:
        await maintenance_service.review_maintenance_prediction(
            db,
            prediction,
            MaintenancePredictionStatus.WORK_ORDER_CREATED,
            reviewed_by=str(uuid4()),
        )

    assert error.value.status_code == 422
    db.flush.assert_not_awaited()
