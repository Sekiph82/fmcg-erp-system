"""M28 — Traceability & Recall verification suite.

Runs the real traceability_service / recall_service code against an in-memory
fake AsyncSession that evaluates the services' `select(...).where(...)`
statements. No PostgreSQL is involved: this proves the traversal, scope,
containment and recovery logic, not SQL/index behaviour on a live database.
"""
from __future__ import annotations

import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList
from sqlalchemy.sql.functions import FunctionElement

import app.models  # noqa: F401 - register all mappers
from app.models.inventory import Lot, Stock
from app.models.traceability import (
    GenealogyRelType, LotGenealogyLink, RecallCustomerImpact, RecallHeader,
    RecallRiskStatus, RecallScopeLine, RecallSeverity, RecallStatus, RecallStatusLog,
    RecallTrigger, RecallType, TraceEvent, TraceEventLine, TraceEventType, TraceItemStage,
)
from app.models.wms import HandlingUnit, HandlingUnitItem, HandlingUnitStatus, HandlingUnitType
from app.schemas.traceability import RecallReturnCreate, RecallStatusUpdate
from app.services import recall_service as recall_svc
from app.services import traceability_service as trace_svc


# ── In-memory session ─────────────────────────────────────────────────────────

def _match(expr, obj) -> bool:
    if expr is None:
        return True
    if isinstance(expr, BooleanClauseList):
        results = [_match(c, obj) for c in expr.clauses]
        return any(results) if expr.operator is operators.or_ else all(results)
    if isinstance(expr, BinaryExpression) and expr.operator is operators.eq:
        return getattr(obj, expr.left.key) == expr.right.value
    raise NotImplementedError(f"unsupported where clause: {expr!r}")


class _Result:
    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)

    def scalar(self):
        return self._rows[0] if self._rows else None

    scalar_one_or_none = scalar


class FakeDB:
    def __init__(self):
        self.rows: dict[type, list] = defaultdict(list)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if obj not in self.rows[type(obj)]:
            self.rows[type(obj)].append(obj)
        return obj

    def add_all(self, objs):
        for o in objs:
            self.add(o)

    async def get(self, model, ident):
        return next((r for r in self.rows[model] if r.id == ident), None)

    async def execute(self, stmt):
        desc = stmt.column_descriptions[0]
        entity, expr = desc["entity"], desc["expr"]
        matched = [r for r in self.rows[entity] if _match(stmt.whereclause, r)]
        if isinstance(expr, FunctionElement):
            assert expr.name == "sum", expr.name
            col = list(expr.clauses)[0].key
            vals = [getattr(r, col) for r in matched if getattr(r, col) is not None]
            return _Result([sum(vals, Decimal("0")) if vals else None])
        return _Result(matched)

    async def delete(self, obj):
        self.rows[type(obj)].remove(obj)

    async def flush(self):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


# ── Fixture graph ─────────────────────────────────────────────────────────────
#
#  supplier S ─GRN─▶ R (raw) ─▶ I (intermediate) ─▶ F (finished, packed)
#                                     PK (packaging) ─────┘
#  F: 55 in stock, 40 shipped to customer C, 5 scrapped

T0 = datetime(2026, 11, 1, 8, 0, 0)


def _lot(db, number, **kw):
    return db.add(Lot(id=uuid.uuid4(), lot_number=number, **kw))


def _link(db, parent, child, rel, qty, po=None, pstage=None, cstage=None):
    return db.add(LotGenealogyLink(
        id=uuid.uuid4(), parent_lot_id=parent.id, child_lot_id=child.id,
        relationship_type=rel, quantity_linked=Decimal(qty), production_order_id=po,
        parent_stage=pstage, child_stage=cstage,
    ))


def _event(db, etype, minutes, line_kw, notes=None):
    ev = db.add(TraceEvent(id=uuid.uuid4(), trace_event_type=etype,
                           event_datetime=T0 + timedelta(minutes=minutes),
                           reference_number=f"{etype.value}-{minutes}", notes=notes))
    db.add(TraceEventLine(id=uuid.uuid4(), event_id=ev.id, **line_kw))
    return ev


@pytest.fixture
def graph():
    db = FakeDB()
    supplier, customer, po = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    grn, shipment = uuid.uuid4(), uuid.uuid4()
    R = _lot(db, "RAW-001", supplier_id=supplier)
    I = _lot(db, "INT-001")
    F = _lot(db, "FG-001", product_id=uuid.uuid4())
    PK = _lot(db, "PKG-001", material_id=uuid.uuid4())

    _link(db, R, I, GenealogyRelType.intermediate_from, "100", po, TraceItemStage.raw_stock, TraceItemStage.intermediate)
    _link(db, I, F, GenealogyRelType.packed_from, "100", po, TraceItemStage.intermediate, TraceItemStage.finished_good)
    _link(db, PK, F, GenealogyRelType.packed_from, "100", po, TraceItemStage.packaging, TraceItemStage.finished_good)

    _event(db, TraceEventType.receipt, 0, dict(child_lot_id=R.id, quantity=Decimal("100"), uom="kg",
                                                  linked_grn_id=grn, linked_supplier_id=supplier))
    _event(db, TraceEventType.shipment, 120, dict(source_lot_id=F.id, quantity=Decimal("40"), uom="pcs",
                                                     linked_customer_id=customer, linked_shipment_id=shipment),
           notes="=HYPERLINK(\"http://evil\")")
    _event(db, TraceEventType.scrap, 60, dict(source_lot_id=F.id, quantity=Decimal("5"), uom="pcs"))

    db.add(Stock(id=uuid.uuid4(), lot_id=F.id, quantity_available=Decimal("55"), is_blocked=False))
    return dict(db=db, R=R, I=I, F=F, PK=PK, supplier=supplier, customer=customer,
                po=po, grn=grn, shipment=shipment)


def _ids(rows, key="lot_id"):
    return {uuid.UUID(r[key]) for r in rows}


# ── M28.S01 — Genealogy ───────────────────────────────────────────────────────

def test_event_type_to_genealogy_relationship_mapping():
    assert trace_svc._infer_rel_type(TraceEventType.receipt) == GenealogyRelType.received_from
    assert trace_svc._infer_rel_type(TraceEventType.transformation) == GenealogyRelType.intermediate_from
    assert trace_svc._infer_rel_type(TraceEventType.packaging) == GenealogyRelType.packed_from
    assert trace_svc._infer_rel_type(TraceEventType.rework) == GenealogyRelType.reworked_from
    assert trace_svc._infer_rel_type(TraceEventType.transfer) == GenealogyRelType.prepared_from


async def test_raw_lot_to_batch_to_sku_forward_genealogy(graph):
    fwd = await trace_svc.forward_trace(graph["db"], graph["R"].id)
    assert _ids(fwd.affected_lots) == {graph["I"].id, graph["F"].id}
    assert {r["rel_type"] for r in fwd.affected_lots} == {"intermediate_from", "packed_from"}


async def test_packaging_component_genealogy_reaches_finished_goods(graph):
    fwd = await trace_svc.forward_trace(graph["db"], graph["PK"].id)
    assert _ids(fwd.affected_lots) == {graph["F"].id}
    assert fwd.qty_shipped == Decimal("40")


async def test_pallet_license_plate_hierarchy_for_lot(graph):
    db = graph["db"]
    wh = uuid.uuid4()
    pallet = db.add(HandlingUnit(id=uuid.uuid4(), license_plate="PAL-0001", warehouse_id=wh,
                                 hu_type=HandlingUnitType.PALLET, status=HandlingUnitStatus.OPEN))
    carton = db.add(HandlingUnit(id=uuid.uuid4(), license_plate="CTN-0001", warehouse_id=wh,
                                 hu_type=HandlingUnitType.CARTON, status=HandlingUnitStatus.OPEN,
                                 parent_hu_id=pallet.id))
    db.add(HandlingUnitItem(id=uuid.uuid4(), handling_unit_id=carton.id, stock_type="PRODUCT",
                            lot_id=graph["F"].id, quantity=Decimal("12"), unit="pcs"))

    hus = await trace_svc.handling_units_for_lot(db, graph["F"].id)
    assert len(hus) == 1
    assert hus[0]["license_plate"] == "CTN-0001"
    assert [a["license_plate"] for a in hus[0]["ancestors"]] == ["PAL-0001"]
    assert hus[0]["quantity"] == 12.0


async def test_handling_unit_parent_cycle_terminates(graph):
    db = graph["db"]
    a_id, b_id = uuid.uuid4(), uuid.uuid4()
    db.add(HandlingUnit(id=a_id, license_plate="A", warehouse_id=uuid.uuid4(),
                        hu_type=HandlingUnitType.PALLET, status=HandlingUnitStatus.OPEN, parent_hu_id=b_id))
    db.add(HandlingUnit(id=b_id, license_plate="B", warehouse_id=uuid.uuid4(),
                        hu_type=HandlingUnitType.PALLET, status=HandlingUnitStatus.OPEN, parent_hu_id=a_id))
    db.add(HandlingUnitItem(id=uuid.uuid4(), handling_unit_id=a_id, stock_type="PRODUCT",
                            lot_id=graph["I"].id, quantity=Decimal("1"), unit="pcs"))
    hus = await trace_svc.handling_units_for_lot(db, graph["I"].id)
    assert [a["license_plate"] for a in hus[0]["ancestors"]] == ["B"]


# ── M28.S02 — One-click trace ─────────────────────────────────────────────────

async def test_forward_trace_quantities_and_customers(graph):
    fwd = await trace_svc.forward_trace(graph["db"], graph["F"].id)
    assert fwd.qty_in_stock == Decimal("55")
    assert fwd.qty_shipped == Decimal("40")
    assert fwd.qty_scrapped == Decimal("5")
    assert fwd.total_affected_qty == Decimal("100")
    assert _ids(fwd.affected_customers, "customer_id") == {graph["customer"]}
    assert fwd.affected_shipments[0]["shipment_ref"] == graph["shipment"]


async def test_backward_trace_reaches_supplier_grn_and_production_order(graph):
    bwd = await trace_svc.backward_trace(graph["db"], graph["F"].id)
    assert _ids(bwd.source_lots) == {graph["I"].id, graph["R"].id, graph["PK"].id}
    assert _ids(bwd.production_orders, "id") == {graph["po"]}
    assert _ids(bwd.suppliers, "id") == {graph["supplier"]}
    assert [uuid.UUID(g["grn_id"]) for g in bwd.grns] == [graph["grn"]]
    assert bwd.genealogy_depth == 2


async def test_trace_handles_genealogy_cycles():
    db = FakeDB()
    a, b = _lot(db, "A"), _lot(db, "B")
    _link(db, a, b, GenealogyRelType.split_from, "1")
    _link(db, b, a, GenealogyRelType.merged_from, "1")
    fwd = await trace_svc.forward_trace(db, a.id)
    bwd = await trace_svc.backward_trace(db, a.id)
    assert _ids(fwd.affected_lots) == {a.id, b.id}
    assert _ids(bwd.source_lots) == {a.id, b.id}


async def test_genealogy_tree_both_directions(graph):
    tree = await trace_svc.get_genealogy_tree(graph["db"], graph["I"].id, direction="both")
    assert {n.lot_number for n in tree.nodes} == {"RAW-001", "INT-001", "FG-001"}
    assert {(e["source"], e["target"]) for e in tree.edges} == {
        (str(graph["I"].id), str(graph["F"].id)),
        (str(graph["R"].id), str(graph["I"].id)),
    }


async def test_trace_timeline_is_chronological_with_direction(graph):
    rows = await trace_svc.build_trace_timeline(graph["db"], graph["F"].id)
    assert [r["event_type"] for r in rows] == ["scrap", "shipment"]
    assert all(r["direction"] == "out" for r in rows)
    rows_r = await trace_svc.build_trace_timeline(graph["db"], graph["R"].id)
    assert [(r["event_type"], r["direction"]) for r in rows_r] == [("receipt", "in")]


async def test_trace_timeline_csv_export_neutralises_formulas(graph):
    rows = await trace_svc.build_trace_timeline(graph["db"], graph["F"].id)
    csv_text = trace_svc.timeline_to_csv(rows)
    lines = csv_text.strip().splitlines()
    assert lines[0].split(",") == trace_svc.TIMELINE_COLUMNS
    assert len(lines) == 3
    assert "'=HYPERLINK" in csv_text
    assert ",=HYPERLINK" not in csv_text


def test_csv_cell_keeps_negative_numbers_and_formats_datetimes():
    assert trace_svc._csv_cell(Decimal("-5")) == "-5"
    assert trace_svc._csv_cell("-cmd") == "'-cmd"
    assert trace_svc._csv_cell(None) == ""
    assert trace_svc._csv_cell(T0) == "2026-11-01T08:00:00"


# ── M28.S03 — Recall ──────────────────────────────────────────────────────────

def _recall(db, **kw):
    defaults = dict(id=uuid.uuid4(), recall_no="MOCK-TEST-0001", recall_type=RecallType.mock_recall,
                    recall_reason="Synthetic mock recall", trigger_source=RecallTrigger.qc,
                    severity_level=RecallSeverity.high, status=RecallStatus.draft,
                    initiation_datetime=datetime.utcnow() - timedelta(hours=3))
    defaults.update(kw)
    return db.add(RecallHeader(**defaults))


@pytest.mark.parametrize("shipped,expected", [
    (Decimal("0"), RecallRiskStatus.low), (Decimal("11"), RecallRiskStatus.medium),
    (Decimal("101"), RecallRiskStatus.high), (Decimal("1001"), RecallRiskStatus.critical),
])
def test_recall_risk_thresholds(shipped, expected):
    fwd = type("F", (), {"qty_shipped": shipped})()
    assert recall_svc._derive_risk(None, fwd) == expected


async def test_recall_scope_from_raw_lot(graph):
    db = graph["db"]
    recall = _recall(db, source_lot_id=graph["R"].id)
    lines = await recall_svc.calculate_scope(db, recall.id)
    by_lot = {sl.affected_lot_id: sl for sl in lines}
    assert set(by_lot) == {graph["R"].id, graph["I"].id, graph["F"].id}
    assert by_lot[graph["F"].id].affected_qty_shipped == Decimal("40")
    assert by_lot[graph["F"].id].risk_status == RecallRiskStatus.medium
    assert recall.total_affected_customers == 1
    assert recall.status == RecallStatus.active
    assert recall.scope_calculated_at is not None


async def test_recall_scope_recalculation_replaces_lines(graph):
    db = graph["db"]
    recall = _recall(db, source_lot_id=graph["F"].id)
    await recall_svc.calculate_scope(db, recall.id)
    await recall_svc.calculate_scope(db, recall.id)
    assert len([s for s in db.rows[RecallScopeLine] if s.recall_id == recall.id]) == 1


async def test_containment_blocks_stock_and_places_holds(graph):
    db = graph["db"]
    recall = _recall(db, source_lot_id=graph["R"].id)
    await recall_svc.calculate_scope(db, recall.id)
    result = await recall_svc.contain_recall(db, recall.id)
    assert result == {"holds_placed": 3}
    assert all(s.is_blocked for s in db.rows[Stock])
    assert recall.status == RecallStatus.contained
    assert (await recall_svc.contain_recall(db, recall.id)) == {"holds_placed": 0}


async def test_customer_containment_list(graph):
    db = graph["db"]
    recall = _recall(db, source_lot_id=graph["F"].id)
    await recall_svc.calculate_scope(db, recall.id)
    impacts = await recall_svc.build_customer_impact(db, recall.id)
    assert len(impacts) == 1
    assert impacts[0].customer_id == graph["customer"]
    assert impacts[0].qty_delivered == Decimal("40")
    assert impacts[0].priority_rank == 3


async def test_recall_status_change_is_logged(graph):
    db = graph["db"]
    recall = _recall(db)
    await recall_svc.update_recall_status(db, recall.id, RecallStatusUpdate(status=RecallStatus.under_review,
                                                                             notes="QA review"))
    log = db.rows[RecallStatusLog][0]
    assert (log.from_status, log.to_status) == ("draft", "under_review")
    assert recall.status == RecallStatus.under_review


# ── M28.S03.T004 — Effectiveness metrics ─────────────────────────────────────

async def test_recovery_pct_counts_returned_and_destroyed(graph):
    db = graph["db"]
    recall = _recall(db, total_affected_qty=Decimal("100"))
    ret = await recall_svc.record_return(db, recall.id, RecallReturnCreate(
        qty_requested=Decimal("40"), qty_received=Decimal("30"), qty_destroyed_at_customer=Decimal("10")))
    assert recall.recovery_pct == Decimal("40.0")
    assert ret.discrepancy == Decimal("10")
    assert ret.follow_up_required is True


async def test_close_recall_records_time_to_contain_and_effectiveness(graph):
    db = graph["db"]
    recall = _recall(db)
    await recall_svc.close_recall(db, recall.id, effectiveness_score=Decimal("92.5"))
    assert recall.status == RecallStatus.closed
    assert recall.effectiveness_score == Decimal("92.5")
    assert Decimal("2.9") <= recall.time_to_contain_hours <= Decimal("3.1")


async def test_regulatory_report_summarises_scope(graph):
    db = graph["db"]
    recall = _recall(db, source_lot_id=graph["R"].id)
    await recall_svc.calculate_scope(db, recall.id)
    report = await recall_svc.generate_regulatory_report(db, recall.id)
    assert report.source_lot_number == "RAW-001"
    assert len(report.affected_lots) == 3
    assert "MOCK-TEST-0001" in report.summary_narrative


# ── M28.S04 — Integrity / performance ─────────────────────────────────────────

async def test_mock_recall_end_to_end(graph):
    db = graph["db"]
    recall = _recall(db, source_lot_id=graph["R"].id)
    await recall_svc.calculate_scope(db, recall.id)
    await recall_svc.contain_recall(db, recall.id)
    impacts = await recall_svc.build_customer_impact(db, recall.id)
    await recall_svc.notify_customer(db, impacts[0].id, method="email")
    await recall_svc.record_return(db, recall.id, RecallReturnCreate(
        customer_id=graph["customer"], lot_id=graph["F"].id,
        qty_requested=Decimal("40"), qty_received=Decimal("40")))
    await recall_svc.close_recall(db, recall.id, effectiveness_score=Decimal("100"))

    assert db.rows[RecallCustomerImpact][0].notification_sent is True
    assert recall.recovery_pct == Decimal(str(round(40 / float(recall.total_affected_qty) * 100, 2)))
    assert recall.status == RecallStatus.closed


async def test_max_depth_bounds_forward_trace():
    db = FakeDB()
    lots = [_lot(db, f"L{i}") for i in range(30)]
    for p, c in zip(lots, lots[1:]):
        _link(db, p, c, GenealogyRelType.prepared_from, "1")
    fwd = await trace_svc.forward_trace(db, lots[0].id, max_depth=5)
    # depths 0..5 are expanded, each contributes its one child
    assert _ids(fwd.affected_lots) == {l.id for l in lots[1:7]}


async def test_deep_genealogy_backward_trace_performance():
    db = FakeDB()
    lots = [_lot(db, f"D{i}") for i in range(300)]
    for p, c in zip(lots, lots[1:]):
        _link(db, p, c, GenealogyRelType.prepared_from, "1")
    start = time.perf_counter()
    bwd = await trace_svc.backward_trace(db, lots[-1].id, max_depth=400)
    elapsed = time.perf_counter() - start
    assert len(bwd.source_lots) == 299
    assert bwd.genealogy_depth == 299
    assert elapsed < 10, f"deep trace took {elapsed:.2f}s"
