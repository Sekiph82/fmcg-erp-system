"""M37.S04 barcode-driven raw-material flow + role-gated dashboard (disposable PostgreSQL)."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.engine import URL

from app.api.v1.endpoints.dashboard import get_dashboard_summary
from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Lot
from app.models.master import Material, MaterialType, UnitOfMeasure
from app.models.material_flow import PreparedLot
from app.models.production_execution import ExecOrderMaterial, ExecWorkOrder, ProdExecOrder
from app.models.shop_floor import SFSession, WOActivityLog
from app.models.user import User
from app.services import material_barcode_flow_service as flow
from app.services import production_execution_service as exec_svc

NAME_RE = r"fmcg_m37_s04_[a-f0-9]{20,32}"


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(NAME_RE, expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> str:
    expected = os.environ.get("M37_S04_DISPOSABLE_TEST_DATABASE_NAME")
    if os.environ.get("M37_S04_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M37_S04_DISPOSABLE_TEST_DATABASE=1 only for its task-owned disposable PostgreSQL database.")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing integration writes unless DATABASE_URL targets the exact loopback M37.S04 database.")
    return expected


def test_database_guard_rejects_non_task_databases():
    name = "fmcg_m37_s04_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_erp")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


def _user(*codes: str):
    perms = [SimpleNamespace(code=c, is_active=True) for c in codes]
    return SimpleNamespace(id=uuid4(), is_superuser=False, roles=[SimpleNamespace(is_active=True, permissions=perms)])


@pytest.mark.asyncio
async def test_dashboard_summary_is_role_gated():
    _require_task_owned_database()
    async with AsyncSessionLocal() as db:
        operator = await get_dashboard_summary(db=db, current_user=_user("shop_floor.view_own_scope", "production.view_own_scope"))
        assert operator.production is None and operator.inventory is None and operator.sales is None
        assert operator.mpesa is None and operator.logistics is None and operator.alerts == []

        coo = await get_dashboard_summary(db=db, current_user=_user("production.view", "inventory.view", "logistics.view"))
        assert coo.production is not None and coo.inventory is not None and coo.logistics is not None
        assert coo.sales is None and coo.mpesa is None

        ceo = await get_dashboard_summary(db=db, current_user=_user("sales.view", "finance.view"))
        assert ceo.sales is not None and ceo.mpesa is not None and ceo.production is None


@pytest.mark.asyncio
async def test_dispense_label_scan_consume_and_scan_log():
    _require_task_owned_database()
    sfx = uuid4().hex[:12]
    line = f"M37-LINE-{sfx}"
    async with AsyncSessionLocal() as db:
        user = User(email=f"m37-{sfx}@example.invalid", username=f"m37op{sfx}", full_name="Synthetic operator", hashed_password="test-only")
        sugar = Material(code=f"SUGAR-{sfx}", name="Synthetic sugar", material_type=MaterialType.RAW, uom=UnitOfMeasure.KG)
        salt = Material(code=f"SALT-{sfx}", name="Synthetic salt", material_type=MaterialType.RAW, uom=UnitOfMeasure.KG)
        db.add_all([user, sugar, salt])
        await db.flush()
        good_lot = Lot(lot_number=f"SUG-{sfx}", material_id=sugar.id, expiry_date=date.today() + timedelta(days=90))
        quarantine_lot = Lot(lot_number=f"SUGQ-{sfx}", material_id=sugar.id, is_quarantine=True)
        salt_lot = Lot(lot_number=f"SAL-{sfx}", material_id=salt.id)
        parent = ProdExecOrder(order_no=f"M37-PO-{sfx}", planned_qty=Decimal("10"), uom="KG", status="IN_PROGRESS", line_id=line)
        db.add_all([good_lot, quarantine_lot, salt_lot, parent])
        await db.flush()
        wo = ExecWorkOrder(production_order_id=parent.id, operation_code="MIX", step_sequence=1, step_name="Mixing",
                           line_id=line, planned_qty=Decimal("10"), status="IN_PROGRESS")
        db.add(wo)
        await db.flush()
        machine_id = uuid4()
        session = SFSession(session_code=f"M37-{sfx}", authenticated_user_id=user.id, operator_name="Synthetic operator",
                            line_id=line, machine_id=machine_id, current_work_order_id=wo.id, status="ACTIVE")
        mat_line = ExecOrderMaterial(production_order_id=parent.id, work_order_id=wo.id, item_type="MATERIAL",
                                     item_id=sugar.id, item_name="Synthetic sugar", item_code=sugar.code,
                                     required_qty=Decimal("5"), uom="KG", status="RESERVED")
        db.add_all([session, mat_line])
        await db.commit()
        ids = SimpleNamespace(user=user.id, wo=wo.id, session=session.id, line=mat_line.id, good_lot=good_lot.lot_number)

        # Warehouse: wrong material and quarantined lots are refused; good lot is weighed + issued.
        with pytest.raises(ValueError, match="not Synthetic sugar"):
            await flow.dispense_prepared_lot(db, exec_material_id=ids.line, source_lot_code=salt_lot.lot_number,
                                             actual_quantity=Decimal("3"), tolerance_pct=None, actor_user_id=ids.user)
        await db.rollback()
        with pytest.raises(ValueError, match="quarantine"):
            await flow.dispense_prepared_lot(db, exec_material_id=ids.line, source_lot_code=f"SUGQ-{sfx}",
                                             actual_quantity=Decimal("3"), tolerance_pct=None, actor_user_id=ids.user)
        await db.rollback()
        with pytest.raises(ValueError, match="re-weigh"):
            await flow.dispense_prepared_lot(db, exec_material_id=ids.line, source_lot_code=ids.good_lot,
                                             actual_quantity=Decimal("3"), tolerance_pct=Decimal("2"), actor_user_id=ids.user,
                                             target_quantity=Decimal("5"))
        await db.rollback()
        prepared = await flow.dispense_prepared_lot(db, exec_material_id=ids.line, source_lot_code=ids.good_lot,
                                                    actual_quantity=Decimal("3"), tolerance_pct=Decimal("5"), actor_user_id=ids.user,
                                                    target_quantity=Decimal("3.05"))
        label_no = prepared.prepared_lot_no
        refreshed = await db.get(ExecOrderMaterial, ids.line, populate_existing=True)
        assert refreshed.issued_qty == Decimal("3") and ids.good_lot in refreshed.lot_numbers

        # The label resolves to everything the floor needs.
        info = await flow.resolve_code(db, label_no)
        assert info["type"] == "PREPARED_LOT" and info["material_name"] == "Synthetic sugar"
        assert info["lot_number"] == ids.good_lot and Decimal(info["quantity"]) == Decimal("3")
        label = flow.prepared_lot_label(prepared, info)
        assert label["code128_svg_b64"] and label["qr_png_b64"]

        # Operator scans the label: label quantity is authoritative, typed qty ignored.
        device_time = datetime(2026, 11, 19, 8, 30, tzinfo=timezone.utc)
        material, _ = await flow.scan_consume(db, ids.wo, session_id=ids.session, code=label_no, qty=Decimal("99"),
                                              client_scanned_at=device_time, actor_user_id=ids.user,
                                              idempotency_key="scan-1", request_fingerprint="a" * 64)
        assert material.consumed_qty == Decimal("3")
        assert (await db.execute(select(PreparedLot.consumed).where(PreparedLot.prepared_lot_no == label_no))).scalar_one()

        # Network retry of the same scan does not double-consume.
        material, meta = await flow.scan_consume(db, ids.wo, session_id=ids.session, code=label_no, qty=Decimal("99"),
                                                 client_scanned_at=device_time, actor_user_id=ids.user,
                                                 idempotency_key="scan-1", request_fingerprint="a" * 64)
        assert meta == {"replayed": True} and material.consumed_qty == Decimal("3")

        # Second scan of a used label, an unknown code, and a non-recipe lot are refused and logged.
        with pytest.raises(flow.ScanRejected, match="already consumed"):
            await flow.scan_consume(db, ids.wo, session_id=ids.session, code=label_no, qty=None, client_scanned_at=None,
                                    actor_user_id=ids.user, idempotency_key="scan-2", request_fingerprint="b" * 64)
        with pytest.raises(flow.ScanRejected, match="Unknown barcode"):
            await flow.scan_consume(db, ids.wo, session_id=ids.session, code=f"NOPE-{sfx}", qty=None, client_scanned_at=None,
                                    actor_user_id=ids.user, idempotency_key="scan-3", request_fingerprint="c" * 64)
        with pytest.raises(flow.ScanRejected, match="not in this operation's recipe"):
            await flow.scan_consume(db, ids.wo, session_id=ids.session, code=f"SAL-{sfx}", qty=Decimal("1"), client_scanned_at=None,
                                    actor_user_id=ids.user, idempotency_key="scan-4", request_fingerprint="d" * 64)

        # Supplier GS1 label: lot + net weight come from the barcode.
        await exec_svc.issue_material(db, (await db.get(ExecWorkOrder, ids.wo)).production_order_id, ids.line, Decimal("2"), ids.good_lot)
        material, _ = await flow.scan_consume(db, ids.wo, session_id=ids.session, code=f"(10){ids.good_lot}(3103)001250",
                                              qty=None, client_scanned_at=None, actor_user_id=ids.user,
                                              idempotency_key="scan-5", request_fingerprint="e" * 64)
        assert material.consumed_qty == Decimal("4.25")

        scans = (await db.execute(
            select(WOActivityLog).where(WOActivityLog.work_order_id == ids.wo, WOActivityLog.event_type == "MATERIAL_SCAN")
            .order_by(WOActivityLog.created_at)
        )).scalars().all()
        assert [s.reason_code for s in scans] == ["ACCEPTED", "REJECTED", "REJECTED", "REJECTED", "ACCEPTED"]
        first = scans[0]
        assert first.timestamp_start is not None and first.machine_id == machine_id and first.line_id == line
        assert first.extra_data["client_scanned_at"] == device_time.isoformat()
        assert first.extra_data["prepared_lot_no"] == label_no and first.extra_data["qty"] == "3.000"
        assert (await db.execute(text("SELECT count(*) FROM sf_activity_logs WHERE work_order_id = :w AND event_type = 'MATERIAL_DISPENSED'"),
                                 {"w": ids.wo})).scalar_one() == 1
