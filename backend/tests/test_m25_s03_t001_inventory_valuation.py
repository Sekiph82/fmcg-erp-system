"""M25.S03.T001 disposable PostgreSQL rehearsal for GRN inventory valuation posting."""
from __future__ import annotations

import os
import re
from calendar import monthrange
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.core.deps import get_current_user, get_db
from app.models.company import Company
from app.models.finance import (
    AccountType,
    AccountingPeriod,
    AccountingPostingBatch,
    ChartOfAccount,
    InventoryAccountMapping,
    JournalEntry,
    JournalLine,
    OperationalPostingEvent,
    OperationalPostingStatus,
    PeriodStatus,
    PostingBatchStatus,
)
from app.models.inventory import CostLayer, MovementType, Stock, StockMovement, StockType
from app.models.master import Material, MaterialType, Supplier, UnitOfMeasure, Warehouse, WarehouseType
from app.models.procurement import GRNLine, GRNStatus, GoodsReceipt, POStatus, POLine, PurchaseOrder
from app.models.user import User
from app.services import procurement_service


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m25_s03_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M25_S03_T001_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M25_S03_T001_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database.")
    expected = os.environ.get("M25_S03_T001_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback M25.S03.T001 database.")


def test_database_guard_requires_exact_task_owned_loopback_database():
    name = "fmcg_m25_s03_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="test", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m25_s03_t001_0123456789abcdef0124")
    assert not _is_task_owned_database(safe, "fmcg_m25_s03_t001_short")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.com", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


def _actor(user_id, *permission_codes: str):
    return SimpleNamespace(
        id=user_id,
        is_superuser=False,
        roles=[SimpleNamespace(
            is_active=True,
            permissions=[SimpleNamespace(code=code, is_active=True) for code in permission_codes],
        )],
    )


async def _seed_grn(
    *, valuation_method="FIFO", standard_cost=None, period_status=PeriodStatus.OPEN, mapping=True,
    wrong_movement=False, company_mismatch=False, po_currency="USD", exchange_rate=Decimal("140.000000"),
    physical_post=False,
):
    suffix = uuid4().hex
    ids = {key: uuid4() for key in (
        "user", "company", "supplier", "warehouse", "material", "po", "po_line", "grn", "grn_line",
        "movement", "stock", "inventory_account", "grni_account", "variance_account", "mapping", "period",
        "other_company",
    )}
    posting_date = date(2026, 7 if period_status == PeriodStatus.CLOSED else 6, 15)
    account_code_suffix = suffix[:10].upper()
    async with AsyncSessionLocal() as db:
        db.add_all([
            User(
                id=ids["user"], email=f"m25-inventory-{suffix}@example.invalid",
                username=f"m25-inventory-{suffix}", full_name="Synthetic inventory poster",
                hashed_password="not-a-usable-password-hash", is_active=True,
            ),
            Company(id=ids["company"], name="Synthetic Inventory Company", short_code=f"IV{account_code_suffix}",
                    country="Kenya", base_currency="KES"),
            Supplier(id=ids["supplier"], code=f"IVS{account_code_suffix}", name="Synthetic Supplier"),
            ChartOfAccount(id=ids["inventory_account"], code=f"IVI{account_code_suffix}",
                           name="Synthetic inventory", account_type=AccountType.ASSET),
            ChartOfAccount(id=ids["grni_account"], code=f"IVG{account_code_suffix}",
                           name="Synthetic GRNI", account_type=AccountType.LIABILITY),
            ChartOfAccount(id=ids["variance_account"], code=f"IVV{account_code_suffix}",
                           name="Synthetic purchase variance", account_type=AccountType.EXPENSE),
        ])
        await db.flush()
        existing_period = await db.scalar(select(AccountingPeriod).where(
            AccountingPeriod.period_ym == f"{posting_date.year}-{posting_date.month:02d}"
        ))
        if existing_period:
            ids["period"] = existing_period.id
        else:
            db.add(AccountingPeriod(
                id=ids["period"], period_ym=f"{posting_date.year}-{posting_date.month:02d}",
                period_start=date(posting_date.year, posting_date.month, 1),
                period_end=date(posting_date.year, posting_date.month, monthrange(posting_date.year, posting_date.month)[1]),
                status=period_status, notes="Synthetic M25 inventory valuation rehearsal.",
            ))
            await db.flush()
        db.add_all([
            Warehouse(id=ids["warehouse"], code=f"IVW{account_code_suffix}", name="Synthetic Warehouse",
                      warehouse_type=WarehouseType.RAW_MATERIAL, country="Kenya", company_id=ids["company"]),
            Material(id=ids["material"], code=f"IVM{account_code_suffix}", name="Synthetic imported material",
                     material_type=MaterialType.RAW, uom=UnitOfMeasure.KG, standard_cost=standard_cost),
        ])
        await db.flush()
        if company_mismatch:
            db.add(Company(
                id=ids["other_company"], name="Synthetic Mismatched Company", short_code=f"IVX{account_code_suffix}",
                country="Kenya", base_currency="KES",
            ))
            await db.flush()
        db.add(PurchaseOrder(
            id=ids["po"], po_no=f"IVPO-{account_code_suffix}", supplier_id=ids["supplier"],
            company_id=ids["company"], order_date=posting_date, expected_delivery_date=posting_date,
            currency=po_currency, exchange_rate=exchange_rate,
            status=POStatus.ORDERED if physical_post else POStatus.RECEIVED,
        ))
        await db.flush()
        db.add(POLine(
            id=ids["po_line"], po_id=ids["po"], line_no=1, material_id=ids["material"],
            description="Synthetic imported raw material", ordered_quantity=Decimal("10"), unit="KG",
            unit_price=Decimal("2.0000"), received_quantity=Decimal("0") if physical_post else Decimal("10"),
        ))
        db.add(GoodsReceipt(
            id=ids["grn"], grn_no=f"IVGRN-{account_code_suffix}", po_id=ids["po"],
            company_id=ids["other_company"] if company_mismatch else ids["company"],
            received_date=posting_date, warehouse_id=ids["warehouse"], received_by_id=ids["user"],
            status=GRNStatus.DRAFT if physical_post else GRNStatus.POSTED,
        ))
        await db.flush()
        if not physical_post:
            db.add(StockMovement(
                id=ids["movement"], reference_number=f"IVGRN-{account_code_suffix}", movement_type=MovementType.RECEIPT,
                stock_type=StockType.PRODUCT if wrong_movement else StockType.MATERIAL,
                movement_date=posting_date, material_id=ids["material"],
                destination_warehouse_id=ids["warehouse"], quantity=Decimal("10"), created_by_id=ids["user"],
            ))
            db.add(Stock(
                id=ids["stock"], stock_type=StockType.MATERIAL, warehouse_id=ids["warehouse"],
                material_id=ids["material"], quantity_on_hand=Decimal("10"), quantity_reserved=Decimal("0"),
                quantity_available=Decimal("10"),
            ))
            await db.flush()
        db.add(GRNLine(
            id=ids["grn_line"], grn_id=ids["grn"], po_line_id=ids["po_line"], material_id=ids["material"],
            received_quantity=Decimal("10"), accepted_quantity=Decimal("10"), rejected_quantity=Decimal("0"),
            unit="KG", stock_movement_id=None if physical_post else ids["movement"],
        ))
        if mapping:
            db.add(InventoryAccountMapping(
                id=ids["mapping"], material_id=ids["material"], stock_type="MATERIAL",
                valuation_method=valuation_method, inventory_account_id=ids["inventory_account"],
                grni_account_id=ids["grni_account"], variance_account_id=ids["variance_account"],
                is_active=True,
            ))
        await db.commit()
    return ids


@pytest.mark.asyncio(loop_scope="session")
async def test_physical_receipt_and_inventory_valuation_commit_as_one_operation():
    _require_task_owned_database()
    ids = await _seed_grn(physical_post=True)
    async with AsyncSessionLocal() as db:
        grn = await db.get(GoodsReceipt, ids["grn"])
        result = await procurement_service.post_grn(db, grn, ids["user"])
        await db.commit()
        assert result.status == GRNStatus.POSTED
    async with AsyncSessionLocal() as db:
        line = await db.get(GRNLine, ids["grn_line"])
        movement = await db.get(StockMovement, line.stock_movement_id)
        stock = await db.scalar(select(Stock).where(Stock.material_id == ids["material"]))
        layer = await db.scalar(select(CostLayer).where(CostLayer.movement_id == movement.id))
        journal = await db.get(JournalEntry, line.journal_entry_id)
        assert stock.quantity_on_hand == Decimal("10")
        assert movement.accounting_status == OperationalPostingStatus.POSTED
        assert layer.qty_remaining == Decimal("10") and layer.unit_cost == Decimal("280.000000")
        assert journal.is_posted and journal.status.value == "POSTED"
        assert (await db.get(POLine, ids["po_line"])).received_quantity == Decimal("10")


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("kwargs", [{"mapping": False}, {"period_status": PeriodStatus.CLOSED}])
async def test_failed_valuation_rolls_back_physical_receipt_and_grn(kwargs):
    _require_task_owned_database()
    ids = await _seed_grn(physical_post=True, **kwargs)
    async with AsyncSessionLocal() as db:
        grn = await db.get(GoodsReceipt, ids["grn"])
        with pytest.raises(ValueError):
            await procurement_service.post_grn(db, grn, ids["user"])
    async with AsyncSessionLocal() as db:
        assert (await db.get(GoodsReceipt, ids["grn"])).status == GRNStatus.DRAFT
        assert (await db.get(POLine, ids["po_line"])).received_quantity == Decimal("0")
        grn = await db.get(GoodsReceipt, ids["grn"])
        line = await db.get(GRNLine, ids["grn_line"])
        assert line.stock_movement_id is None
        assert await db.scalar(select(func.count()).select_from(StockMovement).where(
            StockMovement.reference_number == grn.grn_no
        )) == 0
        assert await db.scalar(select(func.count()).select_from(Stock).where(
            Stock.material_id == ids["material"]
        )) == 0
        assert await db.scalar(select(func.count()).select_from(JournalEntry).where(
            JournalEntry.source_id == ids["grn_line"]
        )) == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_fifo_grn_valuation_posts_balanced_journal_layer_and_links_once():
    _require_task_owned_database()
    ids = await _seed_grn()
    async with AsyncSessionLocal() as db:
        result = await procurement_service.post_grn_inventory_valuation(db, ids["grn"], ids["user"])
        await db.commit()
        assert result["status"] == "POSTED"
        assert result["posted_lines"] == 1
        assert result["idempotent_replay"] is False

    async with AsyncSessionLocal() as db:
        line = await db.get(GRNLine, ids["grn_line"])
        movement = await db.get(StockMovement, ids["movement"])
        layer = (await db.execute(select(CostLayer).where(CostLayer.movement_id == ids["movement"]))).scalar_one()
        journal = await db.get(JournalEntry, line.journal_entry_id)
        journal_lines = list((await db.execute(select(JournalLine).where(JournalLine.entry_id == journal.id))).scalars())
        assert line.accounting_status == OperationalPostingStatus.POSTED
        assert movement.accounting_status == OperationalPostingStatus.POSTED
        assert movement.valuation_method == "FIFO"
        assert movement.valuation_currency == "KES"
        assert movement.unit_cost == Decimal("280.0000")
        assert movement.valuation_amount == Decimal("2800.0000")
        assert layer.qty_remaining == Decimal("10")
        assert layer.unit_cost == Decimal("280.000000")
        assert journal.is_posted is True
        assert sum((entry.debit for entry in journal_lines), Decimal("0")) == Decimal("2800.0000")
        assert sum((entry.credit for entry in journal_lines), Decimal("0")) == Decimal("2800.0000")
        assert {entry.account_id for entry in journal_lines} == {ids["inventory_account"], ids["grni_account"]}
        assert line.posting_batch_id == movement.posting_batch_id == journal.posting_batch_id
        assert await db.scalar(select(func.count()).select_from(OperationalPostingEvent).where(
            OperationalPostingEvent.source_line_id == str(ids["grn_line"])
        )) == 1

    async with AsyncSessionLocal() as db:
        replay = await procurement_service.post_grn_inventory_valuation(db, ids["grn"], ids["user"])
        await db.commit()
        assert replay["idempotent_replay"] is True
        assert await db.scalar(select(func.count()).select_from(JournalEntry).where(
            JournalEntry.source_id == ids["grn_line"]
        )) == 1
        assert await db.scalar(select(func.count()).select_from(CostLayer).where(
            CostLayer.movement_id == ids["movement"]
        )) == 1

    async with AsyncSessionLocal() as db:
        line = await db.get(GRNLine, ids["grn_line"])
        batch = await db.get(AccountingPostingBatch, line.posting_batch_id)
        batch.status = PostingBatchStatus.FAILED  # Deliberate persisted-link corruption for fail-closed replay check.
        await db.commit()
    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError, match="inconsistent posted valuation links"):
            await procurement_service.post_grn_inventory_valuation(db, ids["grn"], ids["user"])


@pytest.mark.asyncio(loop_scope="session")
async def test_fx_rounding_reconciles_unit_cost_stock_layer_movement_and_gl():
    _require_task_owned_database()
    ids = await _seed_grn(exchange_rate=Decimal("140.123456"))
    async with AsyncSessionLocal() as db:
        await procurement_service.post_grn_inventory_valuation(db, ids["grn"], ids["user"])
        await db.commit()
    async with AsyncSessionLocal() as db:
        movement = await db.get(StockMovement, ids["movement"])
        line = await db.get(GRNLine, ids["grn_line"])
        layer = await db.scalar(select(CostLayer).where(CostLayer.movement_id == ids["movement"]))
        journal_lines = list((await db.scalars(
            select(JournalLine).where(JournalLine.entry_id == line.journal_entry_id)
        )).all())
        expected_unit = Decimal("280.2469")
        expected_total = Decimal("2802.4690")
        assert movement.unit_cost == expected_unit
        assert layer.unit_cost == expected_unit
        assert movement.total_cost == movement.valuation_amount == expected_total
        assert movement.quantity * movement.unit_cost == expected_total
        assert sum((entry.debit for entry in journal_lines), Decimal("0")) == expected_total
        assert sum((entry.credit for entry in journal_lines), Decimal("0")) == expected_total


@pytest.mark.asyncio(loop_scope="session")
async def test_finance_permission_is_required_for_atomic_stock_and_valuation_post():
    _require_task_owned_database()
    ids = await _seed_grn(physical_post=True)
    from fastapi import FastAPI
    from app.api.v1.endpoints.procurement import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/procurement")

    async def override_db():
        async with AsyncSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: _actor(
        ids["user"], "procurement.view", "procurement.post_all"
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        denied = await client.post(f"/api/v1/procurement/grn/{ids['grn']}/post")
        assert denied.status_code == 403

    app.dependency_overrides[get_current_user] = lambda: _actor(
        ids["user"], "procurement.view", "procurement.post_all", "finance.post"
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        posted = await client.post(f"/api/v1/procurement/grn/{ids['grn']}/post")
        assert posted.status_code == 200, posted.text
        assert posted.json()["valuation_status"] == "POSTED"
        assert posted.json()["lines"][0]["accounting_status"] == "POSTED"


@pytest.mark.asyncio(loop_scope="session")
async def test_legacy_valuation_fails_closed_after_outbound_movement():
    _require_task_owned_database()
    ids = await _seed_grn()
    async with AsyncSessionLocal() as db:
        db.add(StockMovement(
            reference_number="SYNTHETIC-ISSUE-AFTER-UNVALUED-RECEIPT",
            movement_type=MovementType.ISSUE, stock_type=StockType.MATERIAL,
            movement_date=date(2026, 7, 16), material_id=ids["material"],
            source_warehouse_id=ids["warehouse"], quantity=Decimal("1"),
            created_by_id=ids["user"],
        ))
        await db.commit()
    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError, match="outbound stock movements after its unvalued receipt"):
            await procurement_service.post_grn_inventory_valuation(db, ids["grn"], ids["user"])


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(("standard_cost", "variance_side", "expected_variance"), [
    (Decimal("300.0000"), "credit", Decimal("200.0000")),
    (Decimal("250.0000"), "debit", Decimal("300.0000")),
])
async def test_standard_valuation_posts_receipt_variance_from_saved_po_rate(standard_cost, variance_side, expected_variance):
    _require_task_owned_database()
    ids = await _seed_grn(valuation_method="STANDARD", standard_cost=standard_cost)
    async with AsyncSessionLocal() as db:
        await procurement_service.post_grn_inventory_valuation(db, ids["grn"], ids["user"])
        await db.commit()
    async with AsyncSessionLocal() as db:
        line = await db.get(GRNLine, ids["grn_line"])
        movement = await db.get(StockMovement, ids["movement"])
        journal_lines = list((await db.execute(select(JournalLine).where(
            JournalLine.entry_id == line.journal_entry_id
        ))).scalars())
        valuation_amount = (standard_cost * Decimal("10")).quantize(Decimal("0.0001"))
        assert movement.unit_cost == standard_cost
        assert movement.total_cost == valuation_amount
        assert sum((entry.debit for entry in journal_lines), Decimal("0")) == max(valuation_amount, Decimal("2800.0000"))
        assert sum((entry.credit for entry in journal_lines), Decimal("0")) == max(valuation_amount, Decimal("2800.0000"))
        variance_line = next(entry for entry in journal_lines if entry.account_id == ids["variance_account"])
        assert getattr(variance_line, variance_side) == expected_variance


@pytest.mark.asyncio(loop_scope="session")
async def test_weighted_average_method_persists_actual_base_currency_receipt_value():
    _require_task_owned_database()
    ids = await _seed_grn(valuation_method="WEIGHTED_AVG")
    async with AsyncSessionLocal() as db:
        result = await procurement_service.post_grn_inventory_valuation(db, ids["grn"], ids["user"])
        await db.commit()
        assert result["status"] == "POSTED"
    async with AsyncSessionLocal() as db:
        movement = await db.get(StockMovement, ids["movement"])
        layer = (await db.execute(select(CostLayer).where(CostLayer.movement_id == ids["movement"]))).scalar_one()
        assert movement.valuation_method == "WEIGHTED_AVG"
        assert movement.valuation_amount == Decimal("2800.0000")
        assert layer.total_value == Decimal("2800.0000")


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("kwargs, message", [
    ({"mapping": False}, "needs active inventory and GRNI account mappings"),
    ({"period_status": PeriodStatus.CLOSED}, "is CLOSED"),
    ({"wrong_movement": True}, "does not resolve to its accepted receipt movement"),
    ({"company_mismatch": True}, "belong to different companies"),
    ({"po_currency": "USD", "exchange_rate": Decimal("1")}, "needs a non-default saved exchange rate"),
])
async def test_missing_mapping_or_closed_period_rolls_back_all_valuation_state(kwargs, message):
    _require_task_owned_database()
    ids = await _seed_grn(**kwargs)
    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError, match=message):
            await procurement_service.post_grn_inventory_valuation(db, ids["grn"], ids["user"])
    async with AsyncSessionLocal() as db:
        line = await db.get(GRNLine, ids["grn_line"])
        movement = await db.get(StockMovement, ids["movement"])
        assert line.accounting_status is None
        assert movement.accounting_status is None
        assert await db.scalar(select(func.count()).select_from(CostLayer).where(
            CostLayer.movement_id == ids["movement"]
        )) == 0
        assert await db.scalar(select(func.count()).select_from(JournalEntry).where(
            JournalEntry.source_id == ids["grn_line"]
        )) == 0
