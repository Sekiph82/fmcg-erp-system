from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import quality as quality_api
from app.crud import quality as quality_crud
from app.models.production import ProductionOrderStatus
from app.models.quality import QCDecision, QCInspection, QCStatus, QCType, ParameterType
from app.schemas.quality import QCInspectionCreate
from app.services import production_service, qms_service, quality_service


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


async def _return(value):
    return [value]


async def _return_empty():
    return []


@pytest.mark.asyncio
async def test_production_release_gate_blocks_before_status_change(monkeypatch):
    order = SimpleNamespace(
        id=uuid4(), recipe_id=uuid4(), status=ProductionOrderStatus.PLANNED, order_no="PO-1"
    )
    recipe = SimpleNamespace(status=SimpleNamespace(value="APPROVED"))
    db = _ResultDB([_ScalarResult(order), _ScalarResult(recipe)])
    events = []

    async def lock(_db, module, event):
        events.append(("lock", module, event))

    async def check(_db, got_order, event, as_of_date):
        events.append(("check", got_order, event, as_of_date))
        raise ValueError("missing in-process QC")

    monkeypatch.setattr(qms_service, "lock_quality_gate_scope", lock)
    monkeypatch.setattr(qms_service, "ensure_production_quality_gates_pass", check)

    with pytest.raises(HTTPException) as raised:
        await production_service.release_order(db, order)

    assert raised.value.status_code == 422
    assert "missing in-process QC" in raised.value.detail
    assert order.status == ProductionOrderStatus.PLANNED
    assert events[0] == ("lock", "production", "ON_PRODUCTION_RELEASE")
    assert events[1][0:3] == ("check", order, "ON_PRODUCTION_RELEASE")


@pytest.mark.asyncio
async def test_production_completion_gate_blocks_before_inventory_side_effects(monkeypatch):
    order = SimpleNamespace(id=uuid4(), status=ProductionOrderStatus.IN_PROGRESS, order_no="PO-2")
    db = _ResultDB([_ScalarResult(order)])
    events = []

    async def lock(_db, module, event):
        events.append(("lock", module, event))

    async def check(_db, got_order, event, as_of_date):
        events.append(("check", got_order, event, as_of_date))
        raise ValueError("missing in-process QC")

    monkeypatch.setattr(qms_service, "lock_quality_gate_scope", lock)
    monkeypatch.setattr(qms_service, "ensure_production_quality_gates_pass", check)

    with pytest.raises(HTTPException) as raised:
        await production_service.complete_order(
            db,
            order,
            SimpleNamespace(actual_quantity=Decimal("2")),
            uuid4(),
        )

    assert raised.value.status_code == 422
    assert "missing in-process QC" in raised.value.detail
    assert db.added == []
    assert len(db.statements) == 1  # order lock; the mocked scope lock performs no SQL
    assert events[0] == ("lock", "production", "ON_IN_PROCESS")
    assert events[1][0:3] == ("check", order, "ON_IN_PROCESS")


@pytest.mark.asyncio
async def test_production_gate_requires_accepted_passed_mandatory_inspection(monkeypatch):
    template = SimpleNamespace(id=uuid4(), name="Release checks")
    gate = SimpleNamespace(is_mandatory=True, required_templates=[template])
    order = SimpleNamespace(id=uuid4(), order_no="PO-3")
    db = _ResultDB([_ScalarResult()])
    monkeypatch.setattr(qms_service, "list_production_quality_gates", lambda *_: _return(gate))

    with pytest.raises(ValueError, match=template.name):
        await qms_service.ensure_production_quality_gates_pass(
            db, order, "ON_PRODUCTION_RELEASE", date.today()
        )

    sql = str(db.statements[0])
    assert "qc_inspections.production_order_id" in sql
    assert "qc_inspections.template_id" in sql
    assert "qc_inspections.qc_type" in sql
    assert "qc_inspections.decision" in sql
    assert "qc_inspections.is_mandatory IS true" in sql
    assert "qc_inspections.blocks_progression IS true" in sql
    assert "qc_inspections.release_required IS true" in sql


@pytest.mark.asyncio
async def test_production_gate_is_backward_compatible_when_none_is_configured(monkeypatch):
    order = SimpleNamespace(id=uuid4(), order_no="PO-3B", actual_start=None)
    db = _ResultDB()
    monkeypatch.setattr(qms_service, "list_production_quality_gates", lambda *_: _return_empty())

    await qms_service.ensure_production_quality_gates_pass(
        db, order, "ON_IN_PROCESS", date.today()
    )

    assert db.statements == []


@pytest.mark.asyncio
async def test_in_process_gate_only_counts_inspections_created_after_production_start(monkeypatch):
    template = SimpleNamespace(id=uuid4(), name="In-process checks")
    gate = SimpleNamespace(is_mandatory=True, required_templates=[template])
    started = datetime(2026, 10, 29, 10, tzinfo=timezone.utc)
    order = SimpleNamespace(id=uuid4(), order_no="PO-3A", actual_start=started)
    db = _ResultDB([_ScalarResult()])
    monkeypatch.setattr(qms_service, "list_production_quality_gates", lambda *_: _return(gate))

    with pytest.raises(ValueError, match=template.name):
        await qms_service.ensure_production_quality_gates_pass(
            db, order, "ON_IN_PROCESS", date.today()
        )

    assert "qc_inspections.created_at" in str(db.statements[0])


@pytest.mark.asyncio
async def test_in_process_gate_inspection_derives_order_identity_and_flags(monkeypatch):
    gate, template = SimpleNamespace(is_mandatory=True), SimpleNamespace(id=uuid4())
    gate.required_templates = [template]
    product_id, warehouse_id, order_id = uuid4(), uuid4(), uuid4()
    order = SimpleNamespace(
        id=order_id, product_id=product_id, target_warehouse_id=warehouse_id, batch_no="B-4",
        status=ProductionOrderStatus.IN_PROGRESS, actual_start=datetime.now(timezone.utc),
    )
    db = _ResultDB()
    lock_scopes = []
    monkeypatch.setattr(qms_service, "lock_quality_gate_scopes", lambda _db, scopes: _capture(lock_scopes, scopes))
    monkeypatch.setattr(qms_service, "list_production_quality_gates", lambda *_: _return(gate))

    inspection = await quality_crud.create_inspection(
        db,
        {
            "inspection_no": "QC-IP-4", "qc_type": QCType.IN_PROCESS,
            "production_order_id": order_id, "template_id": template.id, "inspection_date": date.today(),
        },
        uuid4(),
        production_order=order,
    )

    assert inspection.product_id == product_id
    assert inspection.warehouse_id == warehouse_id
    assert inspection.batch_no == "B-4"
    assert inspection.is_mandatory is True
    assert inspection.blocks_progression is True
    assert inspection.release_required is True
    assert inspection.hold_flag is True
    assert len(lock_scopes) == 1
    assert {scope[1] for scope in lock_scopes[0]} == {"ON_PRODUCTION_RELEASE", "ON_IN_PROCESS"}


@pytest.mark.asyncio
async def test_in_process_template_cannot_be_inspected_before_order_starts(monkeypatch):
    template = SimpleNamespace(id=uuid4())
    process_gate = SimpleNamespace(is_mandatory=True, required_templates=[template])
    order = SimpleNamespace(
        id=uuid4(), product_id=uuid4(), target_warehouse_id=uuid4(), batch_no="B-6",
        status=ProductionOrderStatus.PLANNED, actual_start=None,
    )
    db = _ResultDB()
    monkeypatch.setattr(qms_service, "lock_quality_gate_scopes", lambda *_: _capture([], []))

    async def gates(_db, event, _as_of):
        return [process_gate] if event == "ON_IN_PROCESS" else []

    monkeypatch.setattr(qms_service, "list_production_quality_gates", gates)
    with pytest.raises(HTTPException, match="only after the production order starts"):
        await quality_crud.create_inspection(
            db,
            {
                "inspection_no": "QC-IP-PLANNED", "qc_type": QCType.IN_PROCESS,
                "production_order_id": order.id, "template_id": template.id,
                "inspection_date": date.today(),
            },
            uuid4(),
            production_order=order,
        )
    assert db.added == []


async def _capture(target, value):
    target.append(value)


@pytest.mark.asyncio
async def test_in_process_qc_acceptance_requires_every_template_parameter():
    template_id, parameter_id = uuid4(), uuid4()
    inspection = QCInspection(
        id=uuid4(), status=QCStatus.PENDING, decision=None, qc_type=QCType.IN_PROCESS,
        production_order_id=uuid4(), is_mandatory=True, template_id=template_id, test_results=[],
    )
    db = _ResultDB([_ScalarResult(values=[]), _ScalarResult(values=[parameter_id])])

    with pytest.raises(HTTPException, match="every template parameter"):
        await quality_service.make_decision(
            db, inspection, QCDecision.ACCEPT, uuid4(), None, False, False,
        )

    assert inspection.decision is None


@pytest.mark.asyncio
async def test_template_specs_are_canonical_for_in_process_gate_results():
    template_parameter_id = uuid4()
    parameter = SimpleNamespace(
        id=template_parameter_id, parameter_id=None, parameter_name="Viscosity",
        parameter_type=ParameterType.NUMERIC, unit="cP", min_value=Decimal("10"),
        max_value=Decimal("20"), target_value=None, is_critical=True,
    )
    template = SimpleNamespace(is_active=True, qc_type=QCType.IN_PROCESS, parameters=[parameter])
    db = _ResultDB([_ScalarResult(template)])
    inspection = SimpleNamespace(
        qc_type=QCType.IN_PROCESS, production_order_id=uuid4(), is_mandatory=True,
        template_id=uuid4(), grn_id=None, grn_line_id=None,
    )

    result = await qms_service.prepare_receiving_gate_test_result(db, inspection, {
        "template_parameter_id": template_parameter_id, "parameter_name": "spoofed",
        "parameter_type": ParameterType.TEXT, "unit": "fake", "numeric_value": Decimal("12"),
        "min_spec": None, "max_spec": None, "is_critical": False,
    })

    assert result["parameter_name"] == "Viscosity"
    assert result["template_parameter_id"] == template_parameter_id
    assert result["parameter_type"] == ParameterType.NUMERIC
    assert result["unit"] == "cP"
    assert result["min_spec"] == Decimal("10")
    assert result["max_spec"] == Decimal("20")
    assert result["is_critical"] is True


@pytest.mark.asyncio
async def test_inspection_create_permission_uses_production_order_warehouse(monkeypatch):
    order_id, product_id, warehouse_id = uuid4(), uuid4(), uuid4()
    order = SimpleNamespace(id=order_id, product_id=product_id, target_warehouse_id=warehouse_id, batch_no="B-5")
    authorized_targets = []
    inspection = SimpleNamespace(id=uuid4())
    monkeypatch.setattr(quality_api.crud, "get_production_order_context", lambda *_: _return_value(order))
    monkeypatch.setattr(quality_api, "_require_inspection_action", lambda _user, target, _action: authorized_targets.append(target))
    monkeypatch.setattr(quality_api.crud, "create_inspection", lambda *_, **__: _return_value(inspection))
    monkeypatch.setattr(quality_api.crud, "get_inspection", lambda *_: _return_value(inspection))
    monkeypatch.setattr(quality_api, "_build_detail", lambda value: value)

    async def commit():
        return None

    await quality_api.create_inspection(
        QCInspectionCreate(
            inspection_no="QC-SCOPE-IP", qc_type=QCType.IN_PROCESS, inspection_date=date.today(),
            production_order_id=order_id,
        ),
        SimpleNamespace(commit=commit),
        SimpleNamespace(id=uuid4()),
    )

    assert len(authorized_targets) == 1
    assert authorized_targets[0].warehouse_id == warehouse_id


@pytest.mark.asyncio
async def test_legacy_order_inspection_rejects_spoofed_warehouse_before_creation(monkeypatch):
    order_id, target_warehouse_id, other_warehouse_id = uuid4(), uuid4(), uuid4()
    order = SimpleNamespace(
        id=order_id, product_id=uuid4(), target_warehouse_id=target_warehouse_id, batch_no="B-7",
    )
    service_calls = []
    monkeypatch.setattr(quality_api.crud, "get_production_order_context", lambda *_: _return_value(order))
    monkeypatch.setattr(quality_api, "_require_inspection_action", lambda *_: None)
    monkeypatch.setattr(quality_api.svc, "create_qc_for_order", lambda *args, **kwargs: _capture(service_calls, kwargs))

    with pytest.raises(HTTPException) as raised:
        await quality_api.create_inspection_for_order(
            production_order_id=order_id, warehouse_id=other_warehouse_id,
            inspection_no="QC-SPOOFED", qc_type=QCType.IN_PROCESS,
            current_user=SimpleNamespace(id=uuid4()),
        )

    assert raised.value.status_code == 422
    assert service_calls == []


@pytest.mark.asyncio
async def test_order_qc_service_rejects_warehouse_mismatch_even_when_called_directly():
    order = SimpleNamespace(
        id=uuid4(), product_id=uuid4(), target_warehouse_id=uuid4(), batch_no="B-8",
        status=ProductionOrderStatus.PLANNED,
    )
    db = _ResultDB([_ScalarResult(order)])

    with pytest.raises(HTTPException, match="Warehouse does not match"):
        await quality_service.create_qc_for_order(
            db,
            production_order_id=order.id,
            product_id=order.product_id,
            warehouse_id=uuid4(),
            lot_number=None,
            batch_no=order.batch_no,
            inspection_no="QC-WH-MISMATCH",
            inspector_id=uuid4(),
            qc_type=QCType.IN_PROCESS,
        )

    assert db.added == []


async def _return_value(value):
    return value
