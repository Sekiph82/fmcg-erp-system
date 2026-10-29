from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.v1.endpoints import qms
from app.api.v1.endpoints.qms import _require_quality_gate_definition_permission
from app.schemas.qms import QualityGateDefinitionCreate, QualityGateDefinitionUpdate


def _user(*permission_codes):
    permissions = [SimpleNamespace(code=code, is_active=True) for code in permission_codes]
    return SimpleNamespace(
        is_superuser=False,
        roles=[SimpleNamespace(is_active=True, permissions=permissions)],
    )


def test_definition_schema_normalizes_identifiers_without_fixing_gate_vocabulary():
    definition = QualityGateDefinitionCreate(
        code=" incoming_release ",
        name=" Incoming inspection ",
        gate_type=" material_quality ",
        trigger_event=" on_receipt ",
        target_module=" PROCUREMENT ",
        description="  configurable reference  ",
    )

    assert definition.code == "INCOMING_RELEASE"
    assert definition.gate_type == "MATERIAL_QUALITY"
    assert definition.trigger_event == "ON_RECEIPT"
    assert definition.target_module == "procurement"
    assert definition.description == "configurable reference"


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("code", "   "),
        ("gate_type", "bad-code"),
        ("trigger_event", ""),
        ("target_module", "not a module"),
    ],
)
def test_definition_schema_rejects_blank_or_unsafe_identifiers(field_name, value):
    values = {
        "code": "QC_GATE",
        "name": "Quality gate",
        "gate_type": "QC",
        "trigger_event": "ON_RECEIPT",
        "target_module": "procurement",
    }
    values[field_name] = value

    with pytest.raises(ValidationError):
        QualityGateDefinitionCreate(**values)


def test_definition_patch_requires_a_change_and_rejects_null_for_required_fields():
    with pytest.raises(ValidationError):
        QualityGateDefinitionUpdate()
    with pytest.raises(ValidationError):
        QualityGateDefinitionUpdate(name=None)
    assert QualityGateDefinitionUpdate(is_active=False).is_active is False


def test_definition_reads_require_global_quality_read_permission():
    with pytest.raises(HTTPException) as exc:
        _require_quality_gate_definition_permission(_user("quality.view"), "view")
    assert exc.value.status_code == 403
    _require_quality_gate_definition_permission(_user("quality.view_all"), "view")
    _require_quality_gate_definition_permission(_user("quality.gate_configure"), "view")


def test_definition_writes_require_quality_gate_configuration_permission():
    with pytest.raises(HTTPException) as exc:
        _require_quality_gate_definition_permission(_user("quality.edit_all"), "edit")
    assert exc.value.status_code == 403
    _require_quality_gate_definition_permission(_user("quality.gate_configure"), "edit")


@pytest.mark.asyncio
async def test_create_route_denies_writer_without_gate_configuration_permission(monkeypatch):
    called = False

    async def create_should_not_run(_db, _data):
        nonlocal called
        called = True

    monkeypatch.setattr(qms.svc, "create_quality_gate_definition", create_should_not_run)
    body = QualityGateDefinitionCreate(
        code="QC_GATE", name="QC gate", gate_type="QC",
        trigger_event="ON_RECEIPT", target_module="procurement",
    )

    with pytest.raises(HTTPException) as exc:
        await qms.create_quality_gate_definition(body, object(), _user("quality.view_all"))

    assert exc.value.status_code == 403
    assert called is False


class _IntegrityFailingDB:
    def __init__(self):
        self.rollback_called = False

    async def commit(self):
        original = SimpleNamespace(
            diag=SimpleNamespace(constraint_name="uq_quality_gate_definitions_code")
        )
        raise IntegrityError("insert", {}, original)

    async def rollback(self):
        self.rollback_called = True


@pytest.mark.asyncio
async def test_create_route_returns_conflict_for_duplicate_gate_code(monkeypatch):
    async def create_definition(_db, data):
        return SimpleNamespace(id=uuid4(), **data)

    monkeypatch.setattr(qms.svc, "create_quality_gate_definition", create_definition)
    body = QualityGateDefinitionCreate(
        code="QC_GATE", name="QC gate", gate_type="QC",
        trigger_event="ON_RECEIPT", target_module="procurement",
    )
    db = _IntegrityFailingDB()

    with pytest.raises(HTTPException) as exc:
        await qms.create_quality_gate_definition(body, db, _user("quality.gate_configure"))

    assert exc.value.status_code == 409
    assert db.rollback_called is True
