from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.qms import _require_lot_hold_release_access


class _ScalarsResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return iter(self._values)


class _DB:
    def __init__(self, warehouse_ids):
        self.warehouse_ids = warehouse_ids
        self.execute_calls = 0

    async def execute(self, _statement):
        self.execute_calls += 1
        return _ScalarsResult(self.warehouse_ids)


def _user(permission_codes=(), scopes=()):
    permissions = [SimpleNamespace(code=code, is_active=True) for code in permission_codes]
    role = SimpleNamespace(is_active=True, permissions=permissions, access_scopes=[])
    return SimpleNamespace(
        is_superuser=False,
        roles=[role],
        access_scopes=list(scopes),
    )


def _scope(warehouse_id, **actions):
    return SimpleNamespace(
        scope_type="warehouse",
        scope_id=str(warehouse_id),
        is_active=True,
        **{f"can_{action}": allowed for action, allowed in actions.items()},
    )


@pytest.mark.asyncio
async def test_broad_quality_permission_does_not_need_warehouse_lookup():
    db = _DB([])

    await _require_lot_hold_release_access(db, _user(["quality.edit"]), uuid4(), "hold")

    assert db.execute_calls == 0


@pytest.mark.asyncio
async def test_scoped_hold_requires_edit_permission_in_every_warehouse():
    first, second = uuid4(), uuid4()
    db = _DB([first, second])
    user = _user(
        ["quality.edit_own_scope"],
        [_scope(first, edit=True), _scope(second, edit=True)],
    )

    await _require_lot_hold_release_access(db, user, uuid4(), "hold")

    assert db.execute_calls == 1


@pytest.mark.asyncio
async def test_scoped_release_requires_release_capability_in_every_warehouse():
    first, second = uuid4(), uuid4()
    db = _DB([first, second])
    user = _user(
        ["quality.release_own_scope"],
        [_scope(first, release=True), _scope(second, release=True)],
    )

    await _require_lot_hold_release_access(db, user, uuid4(), "release")

    assert db.execute_calls == 1


@pytest.mark.asyncio
async def test_scoped_permission_cannot_change_lot_shared_status_with_partial_scope():
    first, second = uuid4(), uuid4()
    db = _DB([first, second])
    user = _user(
        ["quality.edit_own_scope"],
        [_scope(first, edit=True)],
    )

    with pytest.raises(HTTPException) as exc:
        await _require_lot_hold_release_access(db, user, uuid4(), "hold")

    assert exc.value.status_code == 403
    assert "every warehouse" in exc.value.detail["detail"]


@pytest.mark.asyncio
async def test_scoped_user_cannot_change_unstocked_lot_status():
    db = _DB([])
    user = _user(["quality.release_own_scope"])

    with pytest.raises(HTTPException) as exc:
        await _require_lot_hold_release_access(db, user, uuid4(), "release")

    assert exc.value.status_code == 403
