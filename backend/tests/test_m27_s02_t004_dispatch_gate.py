from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.quality import QCType
from app.models.sales import ShipmentStatus
from app.services import qms_service, sales_service


class _Result:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _ResultDB:
    def __init__(self, values=()):
        self.values = list(values)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return _Result(self.values.pop(0) if self.values else None)


async def _return(value):
    return [value]


@pytest.mark.asyncio
async def test_dispatch_gate_requires_passed_finished_goods_template_for_each_lot(monkeypatch):
    template_id = uuid4()
    gate = SimpleNamespace(is_mandatory=True, required_templates=[SimpleNamespace(id=template_id)])
    line = SimpleNamespace(lot_id=uuid4(), product_id=uuid4())
    shipment = SimpleNamespace(shipment_no="SYN-DISPATCH-1", warehouse_id=uuid4(), lines=[line])
    db = _ResultDB([None])
    monkeypatch.setattr(qms_service, "list_dispatch_quality_gates", lambda *_: _return(gate))

    with pytest.raises(ValueError, match="required template"):
        await qms_service.ensure_dispatch_quality_gates_pass(db, shipment, date.today())

    sql = str(db.statements[0])
    for predicate in (
        "qc_inspections.lot_id", "qc_inspections.product_id", "qc_inspections.warehouse_id",
        "qc_inspections.template_id", "qc_inspections.status", "qc_inspections.decision",
    ):
        assert predicate in sql
    assert "FOR UPDATE" in sql.upper()


@pytest.mark.asyncio
async def test_dispatch_gate_rejects_untraceable_shipment_lines(monkeypatch):
    gate = SimpleNamespace(is_mandatory=True, required_templates=[SimpleNamespace(id=uuid4())])
    shipment = SimpleNamespace(shipment_no="SYN-DISPATCH-2", lines=[SimpleNamespace(lot_id=None)])
    db = _ResultDB()
    monkeypatch.setattr(qms_service, "list_dispatch_quality_gates", lambda *_: _return(gate))

    with pytest.raises(ValueError, match="lot is missing"):
        await qms_service.ensure_dispatch_quality_gates_pass(db, shipment, date.today())

    assert db.statements == []


@pytest.mark.asyncio
async def test_dispatch_gate_blocks_other_unresolved_mandatory_inspection(monkeypatch):
    gate = SimpleNamespace(is_mandatory=True, required_templates=[SimpleNamespace(id=uuid4())])
    shipment = SimpleNamespace(
        shipment_no="SYN-DISPATCH-3", warehouse_id=uuid4(),
        lines=[SimpleNamespace(lot_id=uuid4(), product_id=uuid4())],
    )
    db = _ResultDB([uuid4(), uuid4()])
    monkeypatch.setattr(qms_service, "list_dispatch_quality_gates", lambda *_: _return(gate))

    with pytest.raises(ValueError, match="unresolved mandatory"):
        await qms_service.ensure_dispatch_quality_gates_pass(db, shipment, date.today())

    assert len(db.statements) == 2
    assert all("FOR UPDATE" in str(statement).upper() for statement in db.statements)


@pytest.mark.asyncio
async def test_dispatch_gate_is_inactive_without_mandatory_configuration(monkeypatch):
    shipment = SimpleNamespace(shipment_no="SYN-DISPATCH-4", lines=[SimpleNamespace(lot_id=None)])
    db = _ResultDB()
    monkeypatch.setattr(qms_service, "list_dispatch_quality_gates", lambda *_: _return(
        SimpleNamespace(is_mandatory=False, required_templates=[])
    ))

    await qms_service.ensure_dispatch_quality_gates_pass(db, shipment, date.today())

    assert db.statements == []


def test_dispatch_gate_accepts_only_finished_goods_qc_templates():
    with pytest.raises(ValueError, match="only FINISHED_GOODS"):
        qms_service._validate_gate_template_scope(
            " SALES ", " on_dispatch ", [SimpleNamespace(qc_type=QCType.INCOMING)]
        )


@pytest.mark.asyncio
async def test_dispatch_service_blocks_before_stock_or_ledger_side_effects(monkeypatch):
    shipment = SimpleNamespace(
        id=uuid4(), so_id=uuid4(), shipment_no="SYN-DISPATCH-5", warehouse_id=uuid4(),
        status=ShipmentStatus.PACKED, lines=[SimpleNamespace(id=uuid4())],
    )
    sales_order = SimpleNamespace(id=shipment.so_id)
    db = _ResultDB([shipment, sales_order])
    events = []

    async def lock_scope(_db, module, trigger):
        events.append(("lock", module, trigger))

    async def block(_db, current_shipment, as_of_date):
        events.append(("gate", current_shipment, as_of_date))
        raise ValueError("required finished-goods QC template is pending")

    monkeypatch.setattr(qms_service, "lock_quality_gate_scope", lock_scope)
    monkeypatch.setattr(qms_service, "ensure_dispatch_quality_gates_pass", block)

    with pytest.raises(HTTPException) as raised:
        await sales_service.dispatch_shipment(db, shipment, date.today(), uuid4())

    assert raised.value.status_code == 422
    assert events[0] == ("lock", "sales", "ON_DISPATCH")
    assert events[1][0:2] == ("gate", shipment)
    assert len(db.statements) == 2
