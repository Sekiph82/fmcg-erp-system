"""M25.S03.T002 synthetic PostgreSQL tests for post-estimate variance journals."""
from __future__ import annotations

import os
import re
from calendar import monthrange
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.engine import URL

from app.core.deps import get_current_user, get_db
from app.db.session import AsyncSessionLocal, engine
from app.models.company import Company
from app.models.finance import (
    AccountType,
    ChartOfAccount,
    InventoryAccountMapping,
    JournalEntry,
    JournalLine,
    OperationalPostingEvent,
    OperationalPostingStatus,
    AccountingPeriod,
    PeriodStatus,
)
from app.models.inventory import CostLayer, MovementType, Stock, StockMovement, StockType
from app.models.landed_cost import (
    LandedCostActualVariancePosting,
    LandedCostAllocationLine,
    LandedCostHeader,
    LandedCostType,
)
from app.models.master import Material, MaterialType, Supplier, UnitOfMeasure, Warehouse, WarehouseType
from app.models.procurement import GRNLine, GRNStatus, GoodsReceipt, POStatus, POLine, PurchaseOrder
from app.models.user import User
from app.schemas.landed_cost import (
    LandedCostHeaderCreate,
    LandedCostLineActualCreate,
    LandedCostLineCreate,
)
from app.services import landed_cost_service as service
from app.services import procurement_service


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m25_s03_t002_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M25_S03_T002_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M25_S03_T002_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database.")
    expected = os.environ.get("M25_S03_T002_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback M25.S03.T002 database.")


def test_database_guard_rejects_wrong_task_or_non_loopback_database():
    name = "fmcg_m25_s03_t002_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m25_s03_t001_0123456789abcdef0123")
    assert not _is_task_owned_database(safe, "fmcg_m25_s03_t002_short")
    assert not _is_task_owned_database(URL.create("postgresql+asyncpg", host="db.example.invalid", database=name), name)
    assert not _is_task_owned_database(URL.create("sqlite+aiosqlite", database=name), name)


def _actor(user_id, *permission_codes: str):
    from types import SimpleNamespace
    return SimpleNamespace(
        id=user_id,
        is_superuser=False,
        roles=[SimpleNamespace(
            is_active=True,
            permissions=[SimpleNamespace(code=code, is_active=True) for code in permission_codes],
        )],
    )


async def _seed_grn():
    suffix = uuid4().hex
    ids = {key: uuid4() for key in (
        "user", "company", "supplier", "warehouse", "material", "po", "po_line", "grn", "grn_line",
        "movement", "stock", "inventory_account", "grni_account", "variance_account", "mapping", "period",
    )}
    posting_date = date(2026, 6, 15)
    code_suffix = suffix[:10].upper()
    async with AsyncSessionLocal() as db:
        db.add_all([
            User(
                id=ids["user"], email=f"m25-t002-{suffix}@example.invalid",
                username=f"m25_t002_{suffix}", full_name="Synthetic variance poster",
                hashed_password="not-a-usable-password-hash", is_active=True,
            ),
            Company(id=ids["company"], name="Synthetic Variance Company", short_code=f"VC{code_suffix}",
                    country="Kenya", base_currency="KES"),
            Supplier(id=ids["supplier"], code=f"VS{code_suffix}", name="Synthetic Import Supplier"),
            ChartOfAccount(id=ids["inventory_account"], code=f"VI{code_suffix}",
                           name="Synthetic inventory", account_type=AccountType.ASSET),
            ChartOfAccount(id=ids["grni_account"], code=f"VG{code_suffix}",
                           name="Synthetic GRNI", account_type=AccountType.LIABILITY),
            ChartOfAccount(id=ids["variance_account"], code=f"VV{code_suffix}",
                           name="Synthetic landed cost expense", account_type=AccountType.EXPENSE),
        ])
        await db.flush()
        period = await db.scalar(select(AccountingPeriod).where(AccountingPeriod.period_ym == "2026-06"))
        if not period:
            db.add(AccountingPeriod(
                id=ids["period"], period_ym="2026-06", period_start=date(2026, 6, 1),
                period_end=date(2026, 6, monthrange(2026, 6)[1]),
                status=PeriodStatus.OPEN, notes="Synthetic M25.S03.T002 test period",
            ))
            await db.flush()
        db.add_all([
            Warehouse(id=ids["warehouse"], code=f"VW{code_suffix}", name="Synthetic variance warehouse",
                      warehouse_type=WarehouseType.RAW_MATERIAL, country="Kenya", company_id=ids["company"]),
            Material(id=ids["material"], code=f"VM{code_suffix}", name="Synthetic imported raw material",
                     material_type=MaterialType.RAW, uom=UnitOfMeasure.KG),
        ])
        await db.flush()
        db.add(PurchaseOrder(
            id=ids["po"], po_no=f"VPO-{code_suffix}", supplier_id=ids["supplier"],
            company_id=ids["company"], order_date=posting_date, expected_delivery_date=posting_date,
            currency="KES", exchange_rate=Decimal("1"), status=POStatus.RECEIVED,
        ))
        await db.flush()
        db.add(POLine(
            id=ids["po_line"], po_id=ids["po"], line_no=1, material_id=ids["material"],
            description="Synthetic imported material", ordered_quantity=Decimal("10"), unit="KG",
            unit_price=Decimal("280.0000"), received_quantity=Decimal("10"),
        ))
        db.add(GoodsReceipt(
            id=ids["grn"], grn_no=f"VGRN-{code_suffix}", po_id=ids["po"], company_id=ids["company"],
            received_date=posting_date, warehouse_id=ids["warehouse"], received_by_id=ids["user"],
            status=GRNStatus.POSTED,
        ))
        await db.flush()
        db.add(StockMovement(
            id=ids["movement"], reference_number=f"VGRN-{code_suffix}", movement_type=MovementType.RECEIPT,
            stock_type=StockType.MATERIAL, movement_date=posting_date, material_id=ids["material"],
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
            unit="KG", stock_movement_id=ids["movement"],
        ))
        db.add(InventoryAccountMapping(
            id=ids["mapping"], material_id=ids["material"], stock_type="MATERIAL",
            valuation_method="FIFO", inventory_account_id=ids["inventory_account"],
            grni_account_id=ids["grni_account"], variance_account_id=ids["variance_account"],
            is_active=True,
        ))
        await db.commit()
    return ids


async def _prepare_posted_landed_cost(
    *, amount: Decimal, capitalizable: bool, partial_stock: bool = False,
    bill_date: date = date(2026, 6, 15),
):
    ids = await _seed_grn()
    await _post_grn_valuation(ids)
    clearing_id, cogs_id = uuid4(), uuid4()
    async with AsyncSessionLocal() as db:
        suffix = uuid4().hex[:10].upper()
        clearing = ChartOfAccount(
            id=clearing_id, code=f"LCC{suffix}", name="Synthetic landed-cost clearing",
            account_type=AccountType.LIABILITY,
        )
        cogs = ChartOfAccount(
            id=cogs_id, code=f"LCS{suffix}", name="Synthetic consumption expense",
            account_type=AccountType.EXPENSE,
        )
        db.add_all([clearing, cogs])
        mapping = await db.get(InventoryAccountMapping, ids["mapping"])
        mapping.landed_cost_clearing_account_id = clearing_id
        mapping.cogs_account_id = cogs_id
        period = await db.scalar(select(AccountingPeriod).where(
            AccountingPeriod.period_start <= bill_date,
            AccountingPeriod.period_end >= bill_date,
        ))
        if not period:
            db.add(AccountingPeriod(
                period_ym=f"{bill_date.year}-{bill_date.month:02d}",
                period_start=date(bill_date.year, bill_date.month, 1),
                period_end=date(bill_date.year, bill_date.month, monthrange(bill_date.year, bill_date.month)[1]),
                status=PeriodStatus.OPEN,
                notes="Synthetic M25.S03.T002 test period",
            ))
            await db.flush()
        layer = await db.scalar(select(CostLayer).where(CostLayer.movement_id == ids["movement"]).with_for_update())
        if partial_stock:
            layer.qty_remaining = Decimal("5.000")
            layer.total_value = (Decimal("5.000") * Decimal(layer.unit_cost)).quantize(Decimal("0.0001"))
            layer.is_exhausted = False
            stock = await db.scalar(select(Stock).where(Stock.material_id == ids["material"]).with_for_update())
            stock.quantity_on_hand = Decimal("5.000")
            stock.quantity_available = Decimal("5.000")
            db.add(StockMovement(
                reference_number=f"SYNTHETIC-M25-T002-ISSUE-{uuid4().hex[:12]}",
                movement_type=MovementType.ISSUE,
                stock_type=StockType.MATERIAL,
                movement_date=date(2026, 6, 16),
                material_id=ids["material"],
                source_warehouse_id=ids["warehouse"],
                quantity=Decimal("5.000"),
                created_by_id=ids["user"],
            ))
        await db.flush()
        expense = await db.get(ChartOfAccount, ids["variance_account"])
        header = await service.create_header(db, LandedCostHeaderCreate(
            currency_code="KES",
            bill_date=bill_date,
            cost_lines=[LandedCostLineCreate(
                cost_type=LandedCostType.FREIGHT_SEA,
                amount_fc=amount,
                estimated_amount_fc=amount,
                is_included_in_valuation=capitalizable,
                account_code=None if capitalizable else expense.code,
            )],
        ))
        line = header.cost_lines[0]
        header.status = "VALIDATED"
        db.add(LandedCostAllocationLine(
            header_id=header.id,
            lc_line_id=line.id,
            grn_id=ids["grn"],
            grn_line_id=ids["grn_line"],
            material_id=ids["material"],
            material_name="Synthetic imported material",
            received_qty=Decimal("10.000"),
            allocated_amount=amount,
            is_posted=False,
        ))
        await db.commit()
        header_id, line_id = header.id, line.id

    async with AsyncSessionLocal() as db:
        posted = await service.post_landed_cost(
            db, header_id, posted_by=str(ids["user"]), posted_by_id=ids["user"],
        )
        assert posted.status == "POSTED"
    return ids, header_id, line_id, clearing_id, cogs_id


async def _post_grn_valuation(ids):
    async with AsyncSessionLocal() as db:
        grn_line = await db.scalar(select(GRNLine).where(GRNLine.id == ids["grn_line"]))
        await procurement_service.post_grn_inventory_valuation(db, ids["grn"], ids["user"])
        await db.commit()
        assert grn_line is not None


async def _record_actual(ids, header_id, line_id, amount: Decimal):
    async with AsyncSessionLocal() as db:
        return await service.record_actual_cost(
            db, header_id, line_id,
            LandedCostLineActualCreate(amount_fc=amount, source_reference=f"SYNTHETIC-INVOICE-{uuid4().hex[:10]}"),
            recorded_by_id=ids["user"],
        )


@pytest.mark.asyncio(loop_scope="session")
async def test_capitalized_actual_variance_updates_remaining_fifo_layer_and_posts_balanced_gl():
    _require_task_owned_database()
    ids, header_id, line_id, clearing_id, cogs_id = await _prepare_posted_landed_cost(
        amount=Decimal("100.0000"), capitalizable=True, partial_stock=True,
    )
    recorded = await _record_actual(ids, header_id, line_id, Decimal("120.0000"))
    actual = recorded.cost_lines[0].actual_record
    assert actual.variance_status == "PENDING"
    assert actual.actual_amount_base == Decimal("120.0000")
    assert actual.variance_amount_base == Decimal("20.0000")
    assert recorded.cost_lines[0].amount_base == Decimal("100.0000")

    async with AsyncSessionLocal() as db:
        posted = await service.post_landed_cost_actual_variance(
            db, header_id, line_id, posted_by_id=ids["user"],
        )
        actual = posted.cost_lines[0].actual_record
        assert actual.variance_status == "POSTED"
        assert len(actual.variance_postings) == 1
        assert actual.variance_postings[0].accounting_status == OperationalPostingStatus.POSTED
        layer = await db.scalar(select(CostLayer).where(CostLayer.movement_id == ids["movement"]))
        assert layer.qty_remaining == Decimal("5.000")
        assert layer.unit_cost == Decimal("292.000000")
        assert layer.total_value == Decimal("1460.0000")
        journal = await db.get(JournalEntry, actual.variance_postings[0].journal_entry_id)
        lines = list((await db.scalars(select(JournalLine).where(JournalLine.entry_id == journal.id))).all())
        amounts = {(entry.account_id, entry.debit, entry.credit) for entry in lines}
        assert amounts == {
            (ids["inventory_account"], Decimal("10.0000"), Decimal("0.0000")),
            (cogs_id, Decimal("10.0000"), Decimal("0.0000")),
            (clearing_id, Decimal("0.0000"), Decimal("20.0000")),
        }
        assert journal.is_posted
        assert sum((entry.debit for entry in lines), Decimal("0")) == sum(
            (entry.credit for entry in lines), Decimal("0")
        ) == Decimal("20.0000")


@pytest.mark.asyncio(loop_scope="session")
async def test_negative_noncapitalizable_variance_reverses_expense_and_repeat_is_idempotent():
    _require_task_owned_database()
    ids, header_id, line_id, clearing_id, _ = await _prepare_posted_landed_cost(
        amount=Decimal("50.0000"), capitalizable=False,
    )
    recorded = await _record_actual(ids, header_id, line_id, Decimal("45.0000"))
    assert recorded.cost_lines[0].actual_record.variance_amount_base == Decimal("-5.0000")
    async with AsyncSessionLocal() as db:
        posted = await service.post_landed_cost_actual_variance(db, header_id, line_id, posted_by_id=ids["user"])
        actual = posted.cost_lines[0].actual_record
        posting = actual.variance_postings[0]
        journal = await db.get(JournalEntry, posting.journal_entry_id)
        lines = list((await db.scalars(select(JournalLine).where(JournalLine.entry_id == journal.id))).all())
        expense_id = (await db.scalar(select(ChartOfAccount.id).where(
            ChartOfAccount.id == ids["variance_account"],
        )))
        assert expense_id == ids["variance_account"]
        assert {(entry.account_id, entry.debit, entry.credit) for entry in lines} == {
            (clearing_id, Decimal("5.0000"), Decimal("0.0000")),
            (expense_id, Decimal("0.0000"), Decimal("5.0000")),
        }
        before = await db.scalar(select(func.count()).select_from(OperationalPostingEvent).where(
            OperationalPostingEvent.source_event == "LANDED_COST_ACTUAL_VARIANCE_POST",
            OperationalPostingEvent.source_id == str(header_id),
        ))
        repeated = await service.post_landed_cost_actual_variance(db, header_id, line_id, posted_by_id=ids["user"])
        after = await db.scalar(select(func.count()).select_from(OperationalPostingEvent).where(
            OperationalPostingEvent.source_event == "LANDED_COST_ACTUAL_VARIANCE_POST",
            OperationalPostingEvent.source_id == str(header_id),
        ))
        assert repeated.cost_lines[0].actual_record.variance_status == "POSTED"
        assert before == after == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_zero_variance_is_finalized_without_creating_a_journal_or_batch():
    _require_task_owned_database()
    ids, header_id, line_id, _, _ = await _prepare_posted_landed_cost(
        amount=Decimal("40.0000"), capitalizable=False,
    )
    recorded = await _record_actual(ids, header_id, line_id, Decimal("40.0000"))
    assert recorded.cost_lines[0].actual_record.variance_status == "NOT_REQUIRED"
    async with AsyncSessionLocal() as db:
        result = await service.post_landed_cost_actual_variance(db, header_id, line_id, posted_by_id=ids["user"])
        assert result.cost_lines[0].actual_record.variance_status == "NOT_REQUIRED"
        assert result.cost_lines[0].actual_record.variance_postings == []
        assert await db.scalar(select(func.count()).select_from(OperationalPostingEvent).where(
            OperationalPostingEvent.source_event == "LANDED_COST_ACTUAL_VARIANCE_POST",
            OperationalPostingEvent.source_id == str(header_id),
        )) == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_closed_period_keeps_actual_pending_and_creates_no_partial_variance_posting():
    _require_task_owned_database()
    ids, header_id, line_id, _, _ = await _prepare_posted_landed_cost(
        amount=Decimal("25.0000"), capitalizable=False, bill_date=date(2027, 7, 15),
    )
    await _record_actual(ids, header_id, line_id, Decimal("30.0000"))
    async with AsyncSessionLocal() as db:
        await db.execute(text(
            "UPDATE accounting_periods SET status = 'CLOSED' WHERE period_ym = '2027-07'"
        ))
        await db.commit()
    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError, match="CLOSED"):
            await service.post_landed_cost_actual_variance(db, header_id, line_id, posted_by_id=ids["user"])
        await db.rollback()
    async with AsyncSessionLocal() as db:
        actual = await db.scalar(select(service.LandedCostLineActual).where(
            service.LandedCostLineActual.lc_line_id == line_id,
        ))
        assert actual.variance_status == "PENDING"
        assert await db.scalar(select(func.count()).select_from(LandedCostActualVariancePosting).where(
            LandedCostActualVariancePosting.actual_id == actual.id,
        )) == 0
        assert await db.scalar(select(func.count()).select_from(OperationalPostingEvent).where(
            OperationalPostingEvent.source_event == "LANDED_COST_ACTUAL_VARIANCE_POST",
            OperationalPostingEvent.source_id == str(header_id),
        )) == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_actual_variance_endpoint_requires_finance_post_permission():
    _require_task_owned_database()
    ids, header_id, line_id, _, _ = await _prepare_posted_landed_cost(
        amount=Decimal("10.0000"), capitalizable=False,
    )
    await _record_actual(ids, header_id, line_id, Decimal("11.0000"))
    from fastapi import FastAPI
    from app.api.v1.endpoints.landed_cost import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/landed-cost")

    async def override_db():
        async with AsyncSessionLocal() as db:
            try:
                yield db
            except Exception:
                await db.rollback()
                raise

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: _actor(ids["user"], "finance.view")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        denied = await client.post(f"/api/v1/landed-cost/{header_id}/lines/{line_id}/actual/post")
        assert denied.status_code == 403

    app.dependency_overrides[get_current_user] = lambda: _actor(ids["user"], "finance.view", "finance.post")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        accepted = await client.post(f"/api/v1/landed-cost/{header_id}/lines/{line_id}/actual/post")
        assert accepted.status_code == 200, accepted.text
        actual = accepted.json()["cost_lines"][0]["actual_record"]
        assert actual["variance_status"] == "POSTED"
        assert len(actual["variance_postings"]) == 1


@pytest.mark.asyncio(loop_scope="session")
async def test_recorded_before_initial_post_uses_actual_amount_and_needs_no_variance_journal():
    _require_task_owned_database()
    ids = await _seed_grn()
    await _post_grn_valuation(ids)
    clearing_id, cogs_id = uuid4(), uuid4()
    async with AsyncSessionLocal() as db:
        suffix = uuid4().hex[:10].upper()
        db.add_all([
            ChartOfAccount(id=clearing_id, code=f"PCL{suffix}", name="Synthetic clearing", account_type=AccountType.LIABILITY),
            ChartOfAccount(id=cogs_id, code=f"PCS{suffix}", name="Synthetic COGS", account_type=AccountType.EXPENSE),
        ])
        mapping = await db.get(InventoryAccountMapping, ids["mapping"])
        mapping.landed_cost_clearing_account_id = clearing_id
        mapping.cogs_account_id = cogs_id
        header = await service.create_header(db, LandedCostHeaderCreate(
            bill_date=date(2026, 6, 15),
            cost_lines=[LandedCostLineCreate(
                cost_type=LandedCostType.FREIGHT_SEA,
                amount_fc=Decimal("10.0000"),
                estimated_amount_fc=Decimal("10.0000"),
            )],
        ))
        header_id, line_id = header.id, header.cost_lines[0].id
        await service.record_actual_cost(
            db, header_id, line_id,
            LandedCostLineActualCreate(amount_fc=Decimal("12.0000"), source_reference="SYNTHETIC-PREPOST-ACTUAL"),
            recorded_by_id=ids["user"],
        )
        await db.execute(
            select(LandedCostHeader).where(LandedCostHeader.id == header_id).with_for_update()
        )
        db.add(LandedCostAllocationLine(
            header_id=header_id, lc_line_id=line_id, grn_id=ids["grn"], grn_line_id=ids["grn_line"],
            material_id=ids["material"], received_qty=Decimal("10.000"),
            allocated_amount=Decimal("12.0000"), is_posted=False,
        ))
        await db.flush()
        header = await db.get(LandedCostHeader, header_id)
        header.status = "VALIDATED"
        await db.commit()
    async with AsyncSessionLocal() as db:
        posted = await service.post_landed_cost(db, header_id, posted_by_id=ids["user"])
        actual = posted.cost_lines[0].actual_record
        assert actual.variance_status == "NOT_REQUIRED"
        assert actual.actual_amount_base == Decimal("12.0000")
        assert actual.variance_amount_base == Decimal("0.0000")
        assert actual.variance_postings == []


@pytest.mark.asyncio(loop_scope="session")
async def test_document_and_variance_postings_are_backed_by_the_expected_synthetic_database():
    _require_task_owned_database()
    async with AsyncSessionLocal() as db:
        actual_name = (await db.execute(text("SELECT current_database()"))).scalar_one()
        assert actual_name == os.environ["M25_S03_T002_DISPOSABLE_TEST_DATABASE_NAME"]
