from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.crud import quality as quality_crud
from app.models.procurement import GRNStatus, POStatus
from app.models.quality import QCDecision, QCInspection, QCStatus, QCType, ParameterType
from app.schemas.quality import QCInspectionCreate
from app.api.v1.endpoints import quality as quality_api
from app.services import qms_service, quality_service
from app.services import procurement_service


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

    async def refresh(self, value):
        return None


def _gate(template_id=None, name="Incoming checks", mandatory=True):
    template = SimpleNamespace(id=template_id or uuid4(), name=name)
    return SimpleNamespace(is_mandatory=mandatory, required_templates=[template]), template


@pytest.mark.asyncio
async def test_receiving_gate_blocks_post_when_any_required_template_is_not_passed(monkeypatch):
    gate, template = _gate()
    grn = SimpleNamespace(
        id=uuid4(), grn_no="GRN-TEST-1", received_date=date.today(),
        lines=[SimpleNamespace(id=uuid4(), accepted_quantity=Decimal("3"), material_id=uuid4(), product_id=None)],
    )
    db = _ResultDB([_ScalarResult()])
    monkeypatch.setattr(qms_service, "list_receiving_quality_gates", lambda *_: _return(gate))

    with pytest.raises(ValueError, match=template.name):
        await qms_service.ensure_receiving_quality_gates_pass(db, grn)

    sql = str(db.statements[0])
    assert "qc_inspections.grn_line_id" in sql
    assert "qc_inspections.template_id" in sql
    assert "qc_inspections.status" in sql


@pytest.mark.asyncio
async def test_receiving_gate_accepts_only_a_passed_accepted_mandatory_inspection(monkeypatch):
    gate, template = _gate()
    grn = SimpleNamespace(
        id=uuid4(), grn_no="GRN-TEST-2", received_date=date.today(),
        lines=[SimpleNamespace(id=uuid4(), accepted_quantity=Decimal("1"), material_id=uuid4(), product_id=None)],
    )
    db = _ResultDB([_ScalarResult(uuid4())])
    monkeypatch.setattr(qms_service, "list_receiving_quality_gates", lambda *_: _return(gate))

    await qms_service.ensure_receiving_quality_gates_pass(db, grn)
    sql = str(db.statements[0])
    assert "qc_inspections.decision" in sql
    assert "qc_inspections.is_mandatory IS true" in sql
    assert "qc_inspections.blocks_progression IS true" in sql
    assert "qc_inspections.release_required IS true" in sql


@pytest.mark.asyncio
async def test_receiving_gate_does_not_require_qc_for_rejected_or_empty_lines(monkeypatch):
    gate, _ = _gate()
    grn = SimpleNamespace(
        id=uuid4(), grn_no="GRN-TEST-3", received_date=date.today(),
        lines=[
            SimpleNamespace(id=uuid4(), accepted_quantity=Decimal("0"), material_id=uuid4(), product_id=None),
            SimpleNamespace(id=uuid4(), accepted_quantity=Decimal("2"), material_id=None, product_id=None),
        ],
    )
    db = _ResultDB()
    monkeypatch.setattr(qms_service, "list_receiving_quality_gates", lambda *_: _return(gate))

    await qms_service.ensure_receiving_quality_gates_pass(db, grn)
    assert db.statements == []


@pytest.mark.asyncio
async def test_grn_post_checks_gate_before_any_stock_or_movement_mutation(monkeypatch):
    gate, template = _gate()
    po = SimpleNamespace(id=uuid4(), status=POStatus.ORDERED)
    line = SimpleNamespace(id=uuid4(), accepted_quantity=Decimal("4"), material_id=uuid4(), product_id=None)
    grn = SimpleNamespace(
        id=uuid4(), po_id=po.id, status=GRNStatus.DRAFT, lines=[line],
        received_date=date.today(), grn_no="GRN-BLOCKED", received_date_text=None,
    )
    db = _ResultDB([_ScalarResult(po), _ScalarResult(grn), _ScalarResult(), _ScalarResult()])
    monkeypatch.setattr(qms_service, "list_receiving_quality_gates", lambda *_: _return(gate))

    with pytest.raises(HTTPException) as raised:
        await procurement_service.post_grn(db, grn, uuid4())

    assert raised.value.status_code == 422
    assert template.name in str(raised.value.detail)
    assert db.added == []
    assert len(db.statements) == 4


async def _return(value):
    return [value]


async def _return_value(value):
    return value


@pytest.mark.asyncio
async def test_grn_line_inspection_derives_identity_and_mandatory_flags_from_gate(monkeypatch):
    gate, template = _gate()
    supplier_id, material_id, warehouse_id, grn_id, line_id = (uuid4() for _ in range(5))
    grn = SimpleNamespace(id=grn_id, received_date=date.today(), warehouse_id=warehouse_id,
                          po=SimpleNamespace(supplier_id=supplier_id))
    line = SimpleNamespace(id=line_id, grn_id=grn_id, grn=grn, supplier_id=uuid4(), material_id=material_id,
                           product_id=None, lot_number="LOT-1")
    db = _ResultDB([_ScalarResult(line), _ScalarResult()])
    monkeypatch.setattr(qms_service, "list_receiving_quality_gates", lambda *_: _return(gate))

    inspection = await quality_crud.create_inspection(
        db,
        {
            "inspection_no": "QC-RECEIVE-1", "qc_type": QCType.INCOMING,
            "grn_line_id": line_id, "template_id": template.id,
        },
        uuid4(),
    )

    assert inspection.grn_id == grn_id
    assert inspection.supplier_id == supplier_id
    assert inspection.material_id == material_id
    assert inspection.product_id is None
    assert inspection.warehouse_id == warehouse_id
    assert inspection.template_id == template.id
    assert inspection.is_mandatory is True
    assert inspection.blocks_progression is True
    assert inspection.release_required is True
    assert inspection.hold_flag is True


@pytest.mark.asyncio
async def test_receiving_inspection_authorization_uses_grn_warehouse_scope(monkeypatch):
    warehouse_id, line_id = uuid4(), uuid4()
    line = SimpleNamespace(id=line_id, grn=SimpleNamespace(warehouse_id=warehouse_id))
    authorized_targets = []
    inspection = SimpleNamespace(id=uuid4())
    monkeypatch.setattr(quality_api.crud, "get_grn_line_context", lambda *_: _return_value(line))
    monkeypatch.setattr(quality_api, "_require_inspection_action", lambda _user, target, _action: authorized_targets.append(target))
    monkeypatch.setattr(quality_api.crud, "create_inspection", lambda *_, **__: _return_value(inspection))
    monkeypatch.setattr(quality_api.crud, "get_inspection", lambda *_: _return_value(inspection))
    monkeypatch.setattr(quality_api, "_build_detail", lambda value: value)

    async def commit():
        return None

    db = SimpleNamespace(commit=commit)
    await quality_api.create_inspection(
        QCInspectionCreate(
            inspection_no="QC-SCOPE", qc_type=QCType.INCOMING, inspection_date=date.today(), grn_line_id=line_id,
        ),
        db,
        SimpleNamespace(id=uuid4()),
    )

    assert len(authorized_targets) == 1
    assert authorized_targets[0].warehouse_id == warehouse_id


@pytest.mark.asyncio
async def test_receiving_gate_test_specs_are_taken_from_template_not_request(monkeypatch):
    template_id, parameter_id = uuid4(), uuid4()
    parameter = SimpleNamespace(
        id=parameter_id, parameter_id=None, parameter_name="pH", parameter_type=ParameterType.NUMERIC,
        unit="pH", min_value=Decimal("5.0"), max_value=Decimal("7.0"),
        target_value="6.0", is_critical=True,
    )
    template = SimpleNamespace(is_active=True, qc_type=QCType.INCOMING, parameters=[parameter])
    db = _ResultDB([_ScalarResult(template)])
    inspection = SimpleNamespace(
        qc_type=QCType.INCOMING, grn_id=uuid4(), grn_line_id=uuid4(),
        is_mandatory=True, template_id=template_id,
    )

    data = await qms_service.prepare_receiving_gate_test_result(db, inspection, {
        "template_parameter_id": parameter_id, "parameter_id": uuid4(),
        "parameter_name": "forged", "parameter_type": ParameterType.TEXT,
        "unit": "fake", "numeric_value": Decimal("6.0"), "min_spec": None,
        "max_spec": None, "expected_text": None, "is_passed": True, "is_critical": False,
    })

    assert data["parameter_name"] == "pH"
    assert data["parameter_id"] is None
    assert data["template_parameter_id"] == parameter_id
    assert data["parameter_type"] == ParameterType.NUMERIC
    assert data["unit"] == "pH"
    assert data["min_spec"] == Decimal("5.0")
    assert data["max_spec"] == Decimal("7.0")
    assert data["expected_text"] == "6.0"
    assert data["is_critical"] is True
    assert data["is_passed"] is None


@pytest.mark.asyncio
async def test_receiving_gate_inspection_cannot_be_accepted_before_all_template_parameters(monkeypatch):
    template_id, expected_parameter_id = uuid4(), uuid4()
    inspection = QCInspection(
        id=uuid4(), status=QCStatus.PENDING, decision=None, qc_type=QCType.INCOMING,
        grn_id=uuid4(), grn_line_id=uuid4(), is_mandatory=True, template_id=template_id,
        test_results=[],
    )
    db = _ResultDB([_ScalarResult(values=[]), _ScalarResult(values=[expected_parameter_id])])

    with pytest.raises(HTTPException, match="every template parameter"):
        await quality_service.make_decision(
            db, inspection, QCDecision.ACCEPT, uuid4(), None, False, False,
        )

    assert inspection.decision is None


@pytest.mark.asyncio
async def test_inspection_mutation_load_can_request_a_fresh_row_lock():
    inspection = SimpleNamespace(id=uuid4())
    db = _ResultDB([_ScalarResult(inspection)])

    result = await quality_crud.get_inspection(db, inspection.id, for_update=True)

    assert result is inspection
    assert "FOR UPDATE" in str(db.statements[0]).upper()


@pytest.mark.asyncio
async def test_multiple_gate_scope_locks_use_a_stable_order():
    scopes = [("warehouse", "SHIP"), ("procurement", "ON_RECEIPT")]
    observed = []
    for requested in (scopes, list(reversed(scopes))):
        db = _ResultDB()
        await qms_service.lock_quality_gate_scopes(db, requested)
        keys = []
        for statement in db.statements:
            parameters = statement.compile().params.values()
            keys.append(next(value for value in parameters if isinstance(value, str)))
        observed.append(keys)

    assert observed[0] == observed[1]
    assert observed[0] == sorted(observed[0])


@pytest.mark.asyncio
async def test_legacy_create_for_grn_uses_derived_warehouse_scope(monkeypatch):
    grn_id, line_id, warehouse_id, supplier_id, material_id = (uuid4() for _ in range(5))
    line = SimpleNamespace(
        id=line_id, material_id=material_id, product_id=None, lot_number="LOT-SCOPE",
        grn_id=grn_id,
        grn=SimpleNamespace(id=grn_id, warehouse_id=warehouse_id, po=SimpleNamespace(supplier_id=supplier_id)),
    )
    authorized_targets = []
    inspection = SimpleNamespace(id=uuid4())
    monkeypatch.setattr(quality_api.crud, "get_grn_line_context", lambda *_: _return_value(line))
    monkeypatch.setattr(quality_api, "_require_inspection_action", lambda _user, target, _action: authorized_targets.append(target))
    monkeypatch.setattr(quality_api.crud, "create_inspection", lambda *_, **__: _return_value(inspection))
    monkeypatch.setattr(quality_api.crud, "get_inspection", lambda *_: _return_value(inspection))
    monkeypatch.setattr(quality_api, "_build_detail", lambda value: value)

    async def commit():
        return None

    db = SimpleNamespace(commit=commit)
    await quality_api.create_inspection_for_grn(
        grn_id=grn_id,
        grn_line_id=line_id,
        template_id=None,
        material_id=None,
        supplier_id=None,
        warehouse_id=None,
        lot_number=None,
        inspection_no="QC-LEGACY-SCOPE",
        db=db,
        current_user=SimpleNamespace(id=uuid4()),
    )

    assert authorized_targets[0].warehouse_id == warehouse_id
