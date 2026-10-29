from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.endpoints.qms import _require_quality_waiver_scope_permission
from app.schemas.qms import QualityGateWaiverDecision, QualityGateWaiverRequest


class _WarehouseResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return self.values

    def __iter__(self):
        return iter(self.values)


class _WarehouseDB:
    def __init__(self, warehouse_ids):
        self.warehouse_ids = warehouse_ids

    async def execute(self, _query):
        return _WarehouseResult(self.warehouse_ids)


def _scoped_user(permission_code, warehouse_ids, *, can_create=False, can_approve=False):
    access_scopes = [SimpleNamespace(
        scope_type="warehouse", scope_id=str(warehouse_id), is_active=True,
        can_view=True, can_create=can_create, can_edit=False, can_delete=False,
        can_approve=can_approve, can_post=False, can_release=False, can_cancel=False,
        can_export=False, can_import=False, can_transfer=False, can_adjust=False,
        can_receive=False, can_dispatch=False,
    ) for warehouse_id in warehouse_ids]
    permission = SimpleNamespace(code=permission_code, is_active=True)
    role = SimpleNamespace(is_active=True, permissions=[permission], access_scopes=[])
    return SimpleNamespace(is_superuser=False, roles=[role], access_scopes=access_scopes)


@pytest.mark.asyncio
async def test_scoped_waiver_permission_requires_every_warehouse_for_the_action():
    first, second = uuid4(), uuid4()
    user = _scoped_user("quality.create_own_scope", [first], can_create=True)
    await _require_quality_waiver_scope_permission(_WarehouseDB([first]), user, "request", "LOT", uuid4())

    with pytest.raises(HTTPException) as denied:
        await _require_quality_waiver_scope_permission(
            _WarehouseDB([first, second]), user, "request", "LOT", uuid4()
        )
    assert denied.value.status_code == 403


@pytest.mark.asyncio
async def test_scoped_approval_uses_approve_capability_not_create_capability():
    warehouse = uuid4()
    user = _scoped_user("quality.approve_own_scope", [warehouse], can_approve=True)
    await _require_quality_waiver_scope_permission(
        _WarehouseDB([warehouse]), user, "approve", "LOT", uuid4()
    )
    with pytest.raises(HTTPException) as denied:
        await _require_quality_waiver_scope_permission(
            _WarehouseDB([warehouse]), user, "request", "LOT", uuid4()
        )
    assert denied.value.status_code == 403


def test_waiver_request_normalizes_scope_and_requires_a_real_reason():
    body = QualityGateWaiverRequest(
        gate_definition_id=uuid4(), deviation_id=uuid4(), scope_type=" lot ",
        scope_id=uuid4(), reason="  Synthetic, documented reason  ",
    )
    assert body.scope_type == "LOT"
    assert body.reason == "Synthetic, documented reason"
    with pytest.raises(ValidationError):
        QualityGateWaiverRequest(
            gate_definition_id=uuid4(), deviation_id=uuid4(), scope_type="LOT", scope_id=uuid4(), reason="  "
        )
    with pytest.raises(ValidationError):
        QualityGateWaiverDecision(decision="maybe")
