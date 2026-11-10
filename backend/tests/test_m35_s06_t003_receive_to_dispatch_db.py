"""M35.S06.T003 — receive → produce → release → dispatch quality-gate flow on disposable PostgreSQL.

One continuous synthetic flow through the real services: GRN posting is blocked by the
receiving gate until incoming QC passes, production release / completion are blocked by
their gates, finished goods stay quarantined until FG QC passes (conditional release
without a concession is refused), a CoA is issued by a second person, dispatch is blocked
until release and then issues stock from the FG lot, and the lot traces back to the
received material lot. A second test runs the supplier audit lifecycle with row locks.
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1.endpoints import qms as qms_api
from app.db.session import AsyncSessionLocal, engine
from app.models.company import Company
from app.models.finance import AccountType, AccountingPeriod, ChartOfAccount, InventoryAccountMapping, PeriodStatus
from app.models.inventory import Lot, MovementType, Stock, StockMovement
from app.models.master import (
    Material, MaterialType, Product, ProductCategory, Supplier, UnitOfMeasure, Warehouse, WarehouseType,
)
from app.models.procurement import GRNLine, GoodsReceipt, POLine, POStatus, PurchaseOrder
from app.models.production import FinishedGoodsReceipt, ProductionOrder, ProductionOrderStatus
from app.models.quality import (
    CorrectiveAction, ParameterType, QCDecision, QCInspection, QCStatus, QCTemplate,
    QCTemplateParameter, QCTestResult, QCType, QualityAuditChecklist, SupplierFoodSafetyApproval,
    SupplierFoodSafetyStatus,
)
from app.models.recipe import Recipe, RecipeItem, RecipeStatus
from app.models.sales import (
    Customer, CustomerChannel, SOLine, SOStatus, SalesOrder, Shipment, ShipmentLine, ShipmentStatus,
)
from app.models.user import User
from app.schemas.production import CompleteOrderRequest
from app.models.traceability import RecallHeader, RecallSeverity, RecallStatus, RecallTrigger, RecallType
from app.schemas.traceability import RecallReturnCreate
from app.services import production_service, recall_service, traceability_service
from app.services.procurement_service import post_grn
from app.services.qms_service import (
    PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT, PRODUCTION_RELEASE_GATE_TRIGGER_EVENT, create_quality_gate_definition,
    release_lot,
)
from app.services.quality_service import make_decision, release_qc_quarantine
from app.services.sales_service import dispatch_shipment

TASK_DB_ENV = "M35_S06_T003_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M35_S06_T003_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m35_s06_t003_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")

QA_PERMS = ("quality.view", "quality.create", "quality.edit", "quality.approve")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get(TASK_DB_NAME_ENV, "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert engine.url.password is None
    assert TASK_DB_PATTERN.fullmatch(expected)
    assert (await db.execute(select(func.current_database()))).scalar_one() == expected


def _actor(user_id):
    """Request user for endpoint calls: a real user id with quality permissions."""
    perms = [SimpleNamespace(code=c, is_active=True) for c in QA_PERMS]
    return SimpleNamespace(id=user_id, is_superuser=False, full_name="Synthetic", username="synthetic",
                           roles=[SimpleNamespace(is_active=True, permissions=perms, access_scopes=[])])


async def _template(db, name: str, qc_type: QCType) -> QCTemplate:
    template = QCTemplate(name=name, qc_type=qc_type, is_mandatory=True, blocks_progression=True,
                          release_required=True, is_active=True)
    db.add(template)
    await db.flush()
    db.add(QCTemplateParameter(template_id=template.id, parameter_name=f"{name} value",
                               parameter_type=ParameterType.NUMERIC, unit="KG", target_value="10",
                               min_value=Decimal("9"), max_value=Decimal("11"), is_critical=True))
    await db.flush()
    return template


async def _gate(db, code: str, gate_type: str, event: str, module: str, template_id) -> None:
    await create_quality_gate_definition(db, {
        "code": code, "name": f"Synthetic {code}", "gate_type": gate_type, "trigger_event": event,
        "target_module": module, "effective_from": date.today(), "is_active": True, "is_mandatory": True,
        "required_template_ids": [template_id],
    })


async def _users(db, suffix: str, *tags: str) -> list[User]:
    users = [User(email=f"m35-{t}-{suffix}@example.invalid", username=f"m35{t}{suffix}",
                  full_name=f"Synthetic M35 {t} {suffix}", hashed_password="synthetic-test-only-not-a-credential")
             for t in tags]
    db.add_all(users)
    await db.flush()
    return users


@pytest.mark.asyncio
async def test_receive_produce_release_dispatch_quality_gates_end_to_end():
    s = uuid4().hex[:16]
    today = date.today()
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        operator, qa_head = await _users(db, s, "op", "qa")
        supplier = Supplier(code=f"M35-SUP-{s}", name=f"Synthetic supplier {s}")
        customer = Customer(code=f"M35-C-{s}", name=f"Synthetic customer {s}", channel=CustomerChannel.WHOLESALE)
        raw_wh = Warehouse(code=f"M35-RAW-{s}", name=f"Synthetic raw {s}", warehouse_type=WarehouseType.RAW_MATERIAL)
        fg_wh = Warehouse(code=f"M35-FG-{s}", name=f"Synthetic FG {s}", warehouse_type=WarehouseType.FINISHED_GOODS)
        material = Material(code=f"M35-MAT-{s}", name=f"Synthetic sugar {s}", material_type=MaterialType.RAW, uom=UnitOfMeasure.KG)
        product = Product(sku=f"M35-P-{s}", name=f"Synthetic syrup {s}", category=ProductCategory.FOOD, uom=UnitOfMeasure.KG)
        db.add_all([supplier, customer, raw_wh, fg_wh, material, product])
        await db.flush()
        recipe = Recipe(product_id=product.id, version="1", name=f"Synthetic recipe {s}",
                        status=RecipeStatus.APPROVED, is_active=True)
        db.add(recipe)
        await db.flush()
        db.add(RecipeItem(recipe_id=recipe.id, material_id=material.id, line_no=1, quantity=Decimal("1"), unit="KG"))

        incoming = await _template(db, f"Incoming {s}", QCType.INCOMING)
        release_t = await _template(db, f"Release {s}", QCType.IN_PROCESS)
        process_t = await _template(db, f"Process {s}", QCType.IN_PROCESS)
        fg_t = await _template(db, f"FG {s}", QCType.FINISHED_GOODS)
        await _gate(db, f"M35RCV_{s}", "INCOMING_QUALITY", "ON_RECEIPT", "procurement", incoming.id)
        await _gate(db, f"M35REL_{s}", "IN_PROCESS_QUALITY", PRODUCTION_RELEASE_GATE_TRIGGER_EVENT.lower(), "Production", release_t.id)
        await _gate(db, f"M35INP_{s}", "IN_PROCESS_QUALITY", PRODUCTION_IN_PROCESS_GATE_TRIGGER_EVENT.lower(), "Production", process_t.id)
        await _gate(db, f"M35FGR_{s}", "FINISHED_GOODS_QUALITY", "on_finished_goods_release", "Inventory", fg_t.id)
        await _gate(db, f"M35DSP_{s}", "FINISHED_GOODS_DISPATCH_QUALITY", "on_dispatch", "SALES", fg_t.id)

        # ── receive ──────────────────────────────────────────────────────────
        company = Company(name=f"Synthetic M35 company {s}", short_code=f"M35{s[:8].upper()}", country="Kenya",
                          base_currency="KES")
        inv_acc = ChartOfAccount(code=f"M35I{s[:8].upper()}", name="Synthetic inventory", account_type=AccountType.ASSET)
        grni_acc = ChartOfAccount(code=f"M35G{s[:8].upper()}", name="Synthetic GRNI", account_type=AccountType.LIABILITY)
        db.add_all([company, inv_acc, grni_acc])
        await db.flush()
        raw_wh.company_id = company.id
        db.add(InventoryAccountMapping(material_id=material.id, stock_type="MATERIAL", valuation_method="FIFO",
                                       inventory_account_id=inv_acc.id, grni_account_id=grni_acc.id, is_active=True))
        period = today.strftime("%Y-%m")
        if not await db.scalar(select(AccountingPeriod.id).where(AccountingPeriod.period_ym == period)):
            db.add(AccountingPeriod(period_ym=period, period_start=today.replace(day=1),
                                    period_end=(today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1),
                                    status=PeriodStatus.OPEN, notes="Synthetic M35 receipt period."))
        po = PurchaseOrder(po_no=f"M35-PO-{s}", supplier_id=supplier.id, company_id=company.id, currency="KES",
                           exchange_rate=Decimal("1"), order_date=today, expected_delivery_date=today,
                           status=POStatus.ORDERED, created_by_id=operator.id)
        db.add(po)
        await db.flush()
        po_line = POLine(po_id=po.id, line_no=1, material_id=material.id, ordered_quantity=Decimal("20"),
                         unit="KG", unit_price=Decimal("1"))
        db.add(po_line)
        await db.flush()
        grn = GoodsReceipt(grn_no=f"M35-GRN-{s}", po_id=po.id, company_id=company.id, received_date=today,
                           received_by_id=operator.id, warehouse_id=raw_wh.id)
        db.add(grn)
        await db.flush()
        grn_line = GRNLine(grn_id=grn.id, po_line_id=po_line.id, material_id=material.id, unit="KG",
                           received_quantity=Decimal("20"), accepted_quantity=Decimal("20"),
                           rejected_quantity=Decimal("0"), lot_number=f"M35-RAWLOT-{s}")
        db.add(grn_line)
        await db.commit()
        ids = SimpleNamespace(grn=grn.id, grn_line=grn_line.id, po=po.id, material=material.id, product=product.id,
                              raw_wh=raw_wh.id, fg_wh=fg_wh.id, recipe=recipe.id, op=operator.id, qa=qa_head.id,
                              customer=customer.id, incoming=incoming.id, release_t=release_t.id, process_t=process_t.id)

        with pytest.raises(HTTPException, match="no accepted, passed inspection"):
            await post_grn(db, await db.get(GoodsReceipt, ids.grn), ids.op)
        await db.rollback()
        db.add(QCInspection(inspection_no=f"M35-IQC-{s}", qc_type=QCType.INCOMING, status=QCStatus.PASSED,
                            decision=QCDecision.ACCEPT, grn_id=ids.grn, grn_line_id=ids.grn_line,
                            template_id=ids.incoming, material_id=ids.material, warehouse_id=ids.raw_wh,
                            inspection_date=today, is_mandatory=True, blocks_progression=True, release_required=True))
        await db.commit()
        await post_grn(db, await db.get(GoodsReceipt, ids.grn), ids.op)
        await db.commit()
        raw_lot = (await db.execute(select(Lot).where(Lot.lot_number == f"M35-RAWLOT-{s}"))).scalar_one()
        raw_stock = (await db.execute(select(Stock).where(Stock.lot_id == raw_lot.id))).scalar_one()
        assert raw_stock.quantity_on_hand == Decimal("20")
        raw_lot_id, raw_stock_id = raw_lot.id, raw_stock.id

        # ── produce ──────────────────────────────────────────────────────────
        order = ProductionOrder(order_no=f"M35-MO-{s}", product_id=ids.product, recipe_id=ids.recipe,
                                planned_quantity=Decimal("10"), uom="KG", status=ProductionOrderStatus.PLANNED,
                                target_warehouse_id=ids.fg_wh, source_warehouse_id=ids.raw_wh, created_by=ids.op,
                                scheduled_start=datetime.now(timezone.utc), scheduled_end=datetime.now(timezone.utc),
                                batch_no=f"M35-FGLOT-{s}")
        db.add(order)
        await db.commit()
        order_id = order.id
        await production_service.approve_order(db, await db.get(ProductionOrder, order_id), ids.qa)
        await db.commit()
        with pytest.raises(HTTPException, match="accepted, passed inspection"):
            await production_service.release_order(db, await db.get(ProductionOrder, order_id), ids.op)
        await db.rollback()

        def _ipqc(no, template_id, **extra):
            return QCInspection(inspection_no=no, qc_type=QCType.IN_PROCESS, status=QCStatus.PASSED,
                                decision=QCDecision.ACCEPT, production_order_id=order_id, template_id=template_id,
                                product_id=ids.product, warehouse_id=ids.fg_wh, batch_no=f"M35-FGLOT-{s}",
                                inspection_date=today, is_mandatory=True, blocks_progression=True,
                                release_required=True, **extra)

        db.add(_ipqc(f"M35-RQC-{s}", ids.release_t))
        await db.commit()
        await production_service.release_order(db, await db.get(ProductionOrder, order_id), ids.op)
        await db.commit()
        started = datetime.now(timezone.utc) - timedelta(minutes=5)
        await production_service.start_order(db, await db.get(ProductionOrder, order_id), started, ids.op)
        await db.commit()
        complete = CompleteOrderRequest(actual_quantity=Decimal("10"), source_warehouse_id=ids.raw_wh,
                                        material_lot_ids={ids.material: raw_lot_id})
        with pytest.raises(HTTPException, match="accepted, passed inspection"):
            await production_service.complete_order(db, await db.get(ProductionOrder, order_id), complete, ids.op)
        await db.rollback()
        db.add(_ipqc(f"M35-PQC-{s}", ids.process_t))
        await db.commit()
        await production_service.complete_order(db, await db.get(ProductionOrder, order_id), complete, ids.op)
        await db.commit()
        assert (await db.get(ProductionOrder, order_id)).status == ProductionOrderStatus.COMPLETED
        assert (await db.get(Stock, raw_stock_id)).quantity_on_hand == Decimal("19")  # recipe: 1 KG per batch
        fg_lot = (await db.execute(select(Lot).where(Lot.lot_number == f"M35-FGLOT-{s}",
                                                     Lot.product_id == ids.product))).scalar_one()
        fg_lot_id = fg_lot.id
        fg_stock = (await db.execute(select(Stock).where(Stock.lot_id == fg_lot_id))).scalar_one()
        fg_stock_id = fg_stock.id
        assert fg_stock.quantity_on_hand == Decimal("10") and fg_stock.is_blocked is True  # quarantined
        assert (await db.execute(select(func.count()).select_from(FinishedGoodsReceipt).where(
            FinishedGoodsReceipt.production_order_id == order_id))).scalar_one() == 1

        # ── dispatch blocked while quarantined ───────────────────────────────
        so = SalesOrder(order_no=f"M35-SO-{s}", customer_id=ids.customer, order_date=today,
                        requested_delivery_date=today, status=SOStatus.PICKING, warehouse_id=ids.fg_wh,
                        created_by_id=ids.op)
        db.add(so)
        await db.flush()
        so_line = SOLine(so_id=so.id, line_no=1, product_id=ids.product, ordered_quantity=Decimal("4"), unit="KG",
                         unit_price=Decimal("2"), allocated_quantity=Decimal("4"), shipped_quantity=Decimal("0"))
        shipment = Shipment(shipment_no=f"M35-SHIP-{s}", so_id=so.id, warehouse_id=ids.fg_wh,
                            status=ShipmentStatus.PACKED, scheduled_date=today, created_by_id=ids.op)
        db.add_all([so_line, shipment])
        await db.flush()
        db.add(ShipmentLine(shipment_id=shipment.id, so_line_id=so_line.id, product_id=ids.product, lot_id=fg_lot_id,
                            quantity=Decimal("4"), unit="KG"))
        await db.commit()
        shipment_id = shipment.id
        with pytest.raises(HTTPException):
            await dispatch_shipment(db, await db.get(Shipment, shipment_id), today, ids.op)
        await db.rollback()
        assert (await db.get(Shipment, shipment_id)).status == ShipmentStatus.PACKED
        assert (await db.get(Stock, fg_stock_id)).quantity_on_hand == Decimal("10")

        # ── FG QC: conditional release needs a concession; accept + release ───
        fg_insp = (await db.execute(select(QCInspection).where(
            QCInspection.production_order_id == order_id, QCInspection.qc_type == QCType.FINISHED_GOODS,
            QCInspection.lot_id == fg_lot_id))).scalar_one()
        fg_insp_id = fg_insp.id
        param = (await db.execute(select(QCTemplateParameter).where(
            QCTemplateParameter.template_id == fg_insp.template_id))).scalar_one()
        db.add(QCTestResult(inspection_id=fg_insp_id, template_parameter_id=param.id, parameter_name=param.parameter_name,
                            parameter_type=param.parameter_type, unit=param.unit, numeric_value=Decimal("10"),
                            min_spec=param.min_value, max_spec=param.max_value, is_passed=True,
                            is_critical=param.is_critical, tested_by_id=ids.qa))
        await db.commit()
        with pytest.raises(HTTPException, match="concession"):
            await make_decision(db, await db.get(QCInspection, fg_insp_id), QCDecision.CONDITIONAL_RELEASE, ids.qa,
                                "Try without concession", False, False)
        await db.rollback()
        await make_decision(db, await db.get(QCInspection, fg_insp_id), QCDecision.ACCEPT, ids.qa,
                            "Synthetic FG accepted", False, False)
        await db.commit()
        await release_qc_quarantine(db, await db.get(QCInspection, fg_insp_id), ids.qa, "FG release")
        await db.commit()
        assert (await db.get(Stock, fg_stock_id)).is_blocked is False

        # ── CoA: prepared by operator, issued by QA head (not the preparer) ───
        lot_status = await release_lot(db, fg_lot_id, ids.qa, "Synthetic QA lot release")
        await db.commit()
        assert getattr(lot_status.release_status, "value", lot_status.release_status) == "RELEASED"
        assert lot_status.hold_flag is False
        coa = await qms_api.create_coa({"coa_no": f"M35-COA-{s}", "lot_id": str(fg_lot_id), "product_id": str(ids.product),
                                        "inspection_id": str(fg_insp_id), "issue_date": today.isoformat()},
                                       db=db, current_user=_actor(ids.op))
        with pytest.raises(HTTPException) as same_person:
            await qms_api.issue_coa(coa_id=uuid_of(coa["id"]), db=db, current_user=_actor(ids.op))
        assert same_person.value.status_code == 409
        await db.rollback()
        issued = await qms_api.issue_coa(coa_id=uuid_of(coa["id"]), db=db, current_user=_actor(ids.qa))
        assert issued["status"] == "ISSUED"

        # ── dispatch now passes and issues from the FG lot ───────────────────
        await dispatch_shipment(db, await db.get(Shipment, shipment_id), today, ids.op)
        await db.commit()
        assert (await db.get(Shipment, shipment_id)).status == ShipmentStatus.DISPATCHED
        assert (await db.get(Stock, fg_stock_id)).quantity_on_hand == Decimal("6")
        issue = (await db.execute(select(StockMovement).where(
            StockMovement.reference_number == f"M35-SHIP-{s}", StockMovement.movement_type == MovementType.ISSUE))).scalar_one()
        assert issue.lot_id == fg_lot_id and issue.quantity == Decimal("4")

        # ── traceability: FG lot timeline and backward trace to the received lot ─
        timeline = await traceability_service.build_trace_timeline(db, fg_lot_id)
        assert timeline, "FG lot should have trace events"
        backward = await traceability_service.backward_trace(db, fg_lot_id)
        assert str(raw_lot_id) in repr(backward)

        # ── M35.S06.T004 mock recall from the received raw lot ───────────────
        recall = RecallHeader(recall_no=f"MOCK-M35-{s}", recall_type=RecallType.mock_recall,
                              recall_reason="Synthetic mock recall exercise", trigger_source=RecallTrigger.qc,
                              severity_level=RecallSeverity.high, status=RecallStatus.draft,
                              source_lot_id=raw_lot_id, initiation_datetime=datetime.utcnow() - timedelta(hours=1))
        db.add(recall)
        await db.commit()
        recall_id = recall.id
        scope = await recall_service.calculate_scope(db, recall_id)
        await db.commit()
        assert fg_lot_id in {line.affected_lot_id for line in scope}
        await recall_service.contain_recall(db, recall_id)
        await db.commit()
        impacts = await recall_service.build_customer_impact(db, recall_id)
        await db.commit()
        assert ids.customer in {impact.customer_id for impact in impacts}, "dispatch must be visible to recall"
        impact = next(i for i in impacts if i.customer_id == ids.customer)
        await recall_service.notify_customer(db, impact.id, method="email")
        await recall_service.record_return(db, recall_id, RecallReturnCreate(
            customer_id=ids.customer, lot_id=fg_lot_id, qty_requested=Decimal("4"), qty_received=Decimal("4")))
        await recall_service.close_recall(db, recall_id, effectiveness_score=Decimal("100"))
        await db.commit()
        closed = await db.get(RecallHeader, recall_id)
        await db.refresh(closed)
        assert getattr(closed.status, "value", closed.status) == "closed"


def uuid_of(value):
    from uuid import UUID
    return value if isinstance(value, UUID) else UUID(str(value))


@pytest.mark.asyncio
async def test_supplier_audit_lifecycle_on_postgresql():
    s = uuid4().hex[:16]
    today = date.today()
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        auditor, qa_head = await _users(db, s, "aud", "qah")
        supplier = Supplier(code=f"M35-SA-{s}", name=f"Synthetic audited supplier {s}")
        db.add(supplier)
        await db.flush()
        aud, head = _actor(auditor.id), _actor(qa_head.id)
        sup_id, head_id = supplier.id, qa_head.id
        await db.commit()

        fsa = await qms_api.create_supplier_fsa(qms_api.SupplierFSAIn(supplier_id=sup_id, approval_type="HALAL"),
                                                db=db, current_user=aud)
        assert fsa["status"] == "PENDING"

        async def run_audit(results, closer):
            audit = await qms_api.create_audit_checklist(qms_api.AuditChecklistIn(
                standard="HALAL", audit_type="THIRD_PARTY", audit_date=today, lead_auditor="J. Auditor",
                supplier_id=sup_id), db=db, current_user=aud)
            body = [qms_api.AuditItemResult(item_index=i, result=r, finding="gap" if r == "fail" else None)
                    for i, r in enumerate(results)]
            await qms_api.update_checklist_items(audit["id"], body, db=db, current_user=aud)
            closed = await qms_api.close_audit(audit["id"], next_audit_date=today + timedelta(days=365),
                                               db=db, current_user=closer)
            return audit["id"], closed

        audit_id, _ = await run_audit(["pass"] * 6, head)
        decision = qms_api.SupplierFSADecisionIn(status="APPROVED", audit_checklist_id=uuid_of(audit_id),
                                                 expiry_date=today + timedelta(days=300))
        with pytest.raises(HTTPException) as sod:
            await qms_api.decide_supplier_fsa(uuid_of(fsa["id"]), decision, db=db, current_user=head)
        assert sod.value.status_code == 409
        await db.rollback()
        approved = await qms_api.decide_supplier_fsa(uuid_of(fsa["id"]), decision, db=db, current_user=aud)
        assert approved["status"] == "APPROVED" and approved["is_current"] and approved["audit_score"] == 100.0

        _, failed = await run_audit(["fail"] * 6, head)
        assert failed["suspended_approval_ids"] == [fsa["id"]]
        row = await db.get(SupplierFoodSafetyApproval, uuid_of(fsa["id"]))
        await db.refresh(row)
        assert row.status == SupplierFoodSafetyStatus.SUSPENDED and row.decided_by_id == head_id
        capa = await db.get(CorrectiveAction, uuid_of(failed["corrective_action_id"]))
        assert capa.supplier_id == sup_id and capa.trigger_type == "AUDIT"
        # re-audit path: back to PENDING, the old PASS is not the latest closed audit any more
        await qms_api.decide_supplier_fsa(uuid_of(fsa["id"]), qms_api.SupplierFSADecisionIn(status="PENDING"),
                                          db=db, current_user=aud)
        with pytest.raises(HTTPException) as stale:
            await qms_api.decide_supplier_fsa(uuid_of(fsa["id"]), decision, db=db, current_user=aud)
        assert "most recent closed audit" in stale.value.detail
        await db.rollback()
        reaudit_id, _ = await run_audit(["pass"] * 6, head)
        again = await qms_api.decide_supplier_fsa(
            uuid_of(fsa["id"]), decision.model_copy(update={"audit_checklist_id": uuid_of(reaudit_id)}),
            db=db, current_user=aud)
        assert again["status"] == "APPROVED" and again["audit_checklist_id"] == reaudit_id
        audit_row = await db.get(QualityAuditChecklist, uuid_of(audit_id))
        assert audit_row.supplier_id == sup_id and audit_row.closed_by_id == head_id
