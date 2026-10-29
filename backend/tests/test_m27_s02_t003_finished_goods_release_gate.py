from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import quality as quality_api
from app.models.quality import QCDecision, QCInspection, QCStatus, QCType, ParameterType
from app.services import qms_service, quality_service


@pytest.fixture(autouse=True)
def _stub_audit_persistence_for_service_contract_tests(monkeypatch):
    async def record(**kwargs):
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(qms_service, "_record_quality_gate_audit_event", record)

    async def no_waiver(*_args, **_kwargs):
        return None

    monkeypatch.setattr(qms_service, "get_active_quality_gate_waiver_id", no_waiver)


class _ScalarResult:
    def __init__(self, value=None, values=None):
        self.value = value
        self.values = values if values is not None else ([] if value is None else [value])

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)


class _ResultDB:
    def __init__(self, results=()):
        self.results = list(results)
        self.statements = []
        self.added = []

    async def execute(self, statement):
        self.statements.append(statement)
        if self.results:
            return self.results.pop(0)
        return _ScalarResult()

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None


async def _return(value):
    return [value]


@pytest.mark.asyncio
async def test_finished_goods_gate_requires_passed_inspection_for_each_linked_template(monkeypatch):
    template = SimpleNamespace(id=uuid4(), name="Synthetic FG release test")
    gate = SimpleNamespace(id=uuid4(), is_mandatory=True, required_templates=[template])
    inspection = SimpleNamespace(
        id=uuid4(), production_order_id=uuid4(), lot_id=uuid4(), lot_number="FG-LOT-1",
    )
    db = _ResultDB([_ScalarResult()])
    monkeypatch.setattr(qms_service, "list_finished_goods_quality_gates", lambda *_: _return(gate))

    with pytest.raises(ValueError, match=template.name):
        await qms_service.ensure_finished_goods_quality_gates_pass(db, inspection, date.today())

    sql = str(db.statements[0])
    assert "qc_inspections.production_order_id" in sql
    assert "qc_inspections.lot_id" in sql
    assert "qc_inspections.template_id" in sql
    assert "qc_inspections.status" in sql
    assert "FOR UPDATE" in sql.upper()


@pytest.mark.asyncio
async def test_finished_goods_release_also_blocks_other_unresolved_mandatory_inspection(monkeypatch):
    gate = SimpleNamespace(id=uuid4(), is_mandatory=True, required_templates=[])
    inspection = SimpleNamespace(id=uuid4(), production_order_id=uuid4(), lot_id=uuid4(), lot_number="FG-LOT-2")
    db = _ResultDB([_ScalarResult(uuid4())])
    monkeypatch.setattr(qms_service, "list_finished_goods_quality_gates", lambda *_: _return(gate))

    with pytest.raises(ValueError, match="another mandatory"):
        await qms_service.ensure_finished_goods_quality_gates_pass(db, inspection, date.today())

    assert "DECISION IS DISTINCT FROM" in str(db.statements[0]).upper()
    assert "FOR UPDATE" in str(db.statements[0]).upper()


@pytest.mark.asyncio
async def test_finished_goods_gate_blocks_release_before_inventory_unblock(monkeypatch):
    inspection = SimpleNamespace(
        id=uuid4(), qc_type=QCType.FINISHED_GOODS, decision=QCDecision.ACCEPT, status=QCStatus.PASSED,
        quarantine_applied=True, lot_id=uuid4(), warehouse_id=uuid4(), production_order_id=uuid4(),
    )
    db = _ResultDB()

    async def lock(*_args):
        return None

    async def block(*_args, **_kwargs):
        raise ValueError("missing required finished-goods template")

    monkeypatch.setattr(qms_service, "lock_quality_gate_scope", lock)
    monkeypatch.setattr(qms_service, "ensure_finished_goods_quality_gates_pass", block)

    with pytest.raises(HTTPException) as raised:
        await quality_service.release_qc_quarantine(db, inspection, uuid4())

    assert raised.value.status_code == 422
    assert "missing required finished-goods template" in raised.value.detail
    assert db.statements == []
    assert db.added == []
    assert inspection.quarantine_applied is True


@pytest.mark.asyncio
async def test_finished_goods_gate_result_specs_are_template_authoritative(monkeypatch):
    template_parameter_id = uuid4()
    parameter = SimpleNamespace(
        id=template_parameter_id, parameter_id=None, parameter_name="Synthetic FG weight",
        parameter_type=ParameterType.NUMERIC, unit="KG", min_value=Decimal("9"),
        max_value=Decimal("11"), target_value=None, is_critical=True,
    )
    template = SimpleNamespace(is_active=True, qc_type=QCType.FINISHED_GOODS, parameters=[parameter])
    inspection = SimpleNamespace(
        qc_type=QCType.FINISHED_GOODS, production_order_id=uuid4(), lot_id=uuid4(),
        is_mandatory=True, template_id=uuid4(), grn_id=None, grn_line_id=None,
    )
    db = _ResultDB([_ScalarResult(template)])

    result = await qms_service.prepare_receiving_gate_test_result(db, inspection, {
        "template_parameter_id": template_parameter_id, "parameter_name": "forged",
        "parameter_type": ParameterType.TEXT, "unit": "fake", "numeric_value": Decimal("10"),
        "min_spec": None, "max_spec": None, "is_critical": False,
    })

    assert result["template_parameter_id"] == template_parameter_id
    assert result["parameter_name"] == "Synthetic FG weight"
    assert result["parameter_type"] == ParameterType.NUMERIC
    assert result["unit"] == "KG"
    assert result["min_spec"] == Decimal("9")
    assert result["max_spec"] == Decimal("11")
    assert result["is_critical"] is True


def test_finished_goods_release_gate_rejects_non_finished_goods_templates():
    with pytest.raises(ValueError, match="FINISHED_GOODS QC templates"):
        qms_service._validate_gate_template_scope(
            "inventory", "ON_FINISHED_GOODS_RELEASE", [SimpleNamespace(qc_type=QCType.IN_PROCESS)]
        )


@pytest.mark.asyncio
async def test_release_quarantine_endpoint_authorizes_then_locks_scope_before_inspection_refresh(monkeypatch):
    inspection = SimpleNamespace(id=uuid4(), qc_type=QCType.FINISHED_GOODS)
    events = []

    async def get_inspection(_db, _inspection_id, *, for_update=False):
        events.append(("load", for_update))
        return inspection

    async def lock_scope(_db, target_module, trigger_event):
        events.append(("scope", (target_module, trigger_event)))

    def authorize(_user, _inspection, _action):
        events.append(("authorize", None))

    async def release(*_args):
        events.append(("release", None))

    async def commit():
        events.append(("commit", None))

    monkeypatch.setattr(quality_api.crud, "get_inspection", get_inspection)
    monkeypatch.setattr(quality_api.qms_svc, "lock_quality_gate_scope", lock_scope)
    monkeypatch.setattr(quality_api, "_require_inspection_action", authorize)
    monkeypatch.setattr(quality_api.svc, "release_qc_quarantine", release)
    monkeypatch.setattr(quality_api, "_build_detail", lambda value: value)

    result = await quality_api.release_quarantine(
        inspection.id, db=SimpleNamespace(commit=commit), current_user=SimpleNamespace(id=uuid4()),
    )

    assert result is inspection
    assert events == [
        ("load", False),
        ("authorize", None),
        ("scope", ("inventory", "ON_FINISHED_GOODS_RELEASE")),
        ("load", True),
        ("authorize", None),
        ("release", None),
        ("commit", None),
        ("load", False),
    ]
