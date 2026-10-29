from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.qms import (
    _require_deviation_capa_create_permission,
    _require_linked_capa_verified,
    update_deviation,
)
from app.models.quality import CorrectiveActionStatus, DeviationStatus
from app.schemas.qms import QCDeviationUpdate


class _WarehouseResult:
    def __init__(self, values=(), scalar=None):
        self.values = list(values)
        self.scalar = scalar

    def scalars(self):
        return self

    def all(self):
        return self.values

    def __iter__(self):
        return iter(self.values)

    def scalar_one_or_none(self):
        return self.scalar


class _WarehouseDB:
    def __init__(self, warehouse_ids=(), scalar=None):
        self.warehouse_ids = warehouse_ids
        self.scalar = scalar

    async def execute(self, _query):
        return _WarehouseResult(self.warehouse_ids, self.scalar)


class _DeviationRouteDB:
    def __init__(self, deviation, capa_status):
        self.deviation = deviation
        self.capa_status = capa_status
        self.calls = 0

    async def execute(self, _query):
        self.calls += 1
        value = self.deviation if self.calls == 1 else self.capa_status
        return _WarehouseResult(scalar=value)


def _scoped_user(warehouse_id, *, can_create=False, can_edit=False):
    scope = SimpleNamespace(
        scope_type="warehouse", scope_id=str(warehouse_id), is_active=True,
        can_view=True, can_create=can_create, can_edit=can_edit, can_delete=False,
        can_approve=False, can_post=False, can_release=False, can_cancel=False,
        can_export=False, can_import=False, can_transfer=False, can_adjust=False,
        can_receive=False, can_dispatch=False,
    )
    permission = SimpleNamespace(code="quality.create_own_scope", is_active=True)
    role = SimpleNamespace(is_active=True, permissions=[permission], access_scopes=[])
    return SimpleNamespace(is_superuser=False, roles=[role], access_scopes=[scope])


@pytest.mark.asyncio
async def test_scoped_quality_create_permission_is_required_for_linking_a_deviation_capa():
    warehouse_id = uuid4()
    deviation = SimpleNamespace(
        lot_id=uuid4(), production_order_id=uuid4(), inspection_id=None,
    )
    user = _scoped_user(warehouse_id, can_create=True)
    await _require_deviation_capa_create_permission(
        _WarehouseDB([warehouse_id]), user, deviation,
    )

    with pytest.raises(HTTPException) as denied:
        await _require_deviation_capa_create_permission(
            _WarehouseDB([uuid4()]), user, deviation,
        )
    assert denied.value.status_code == 403


@pytest.mark.asyncio
async def test_linked_capa_must_be_verified_before_deviation_resolution_or_closure():
    await _require_linked_capa_verified(_WarehouseDB(), SimpleNamespace(corrective_action_id=None))
    await _require_linked_capa_verified(
        _WarehouseDB(scalar=CorrectiveActionStatus.VERIFIED),
        SimpleNamespace(corrective_action_id=uuid4()),
    )

    with pytest.raises(HTTPException) as blocked:
        await _require_linked_capa_verified(
            _WarehouseDB(scalar=CorrectiveActionStatus.IN_PROGRESS),
            SimpleNamespace(corrective_action_id=uuid4()),
        )
    assert blocked.value.status_code == 409


@pytest.mark.asyncio
async def test_pending_capa_supplied_in_same_patch_is_checked_before_resolution():
    deviation = SimpleNamespace(corrective_action_id=None)
    with pytest.raises(HTTPException) as blocked:
        await _require_linked_capa_verified(
            _WarehouseDB(scalar=CorrectiveActionStatus.IN_PROGRESS),
            deviation,
            candidate_capa_id=uuid4(),
        )
    assert blocked.value.status_code == 409


@pytest.mark.asyncio
async def test_patch_cannot_resolve_a_deviation_while_attaching_an_unverified_capa():
    deviation_id, candidate_capa_id = uuid4(), uuid4()
    deviation = SimpleNamespace(
        id=deviation_id,
        status=DeviationStatus.OPEN,
        corrective_action_id=None,
    )
    with pytest.raises(HTTPException) as blocked:
        await update_deviation(
            deviation_id,
            QCDeviationUpdate(
                status=DeviationStatus.RESOLVED,
                corrective_action_id=candidate_capa_id,
            ),
            _DeviationRouteDB(deviation, CorrectiveActionStatus.IN_PROGRESS),
            SimpleNamespace(),
        )
    assert blocked.value.status_code == 409
