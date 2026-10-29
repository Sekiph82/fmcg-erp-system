"""M13.S03.T001 PostgreSQL rehearsal for landed-cost valuation and GL posting."""
from __future__ import annotations

import asyncio
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

from app.core.deps import get_current_user, get_db
from app.db.session import AsyncSessionLocal, engine
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
from app.models.inventory import CostLayer, MovementType, StockMovement, StockType
from app.models.landed_cost import LCInventoryAdjustment, LandedCostAllocationLine, LandedCostHeader, LandedCostLine
from app.models.master import Material, MaterialType, Supplier, UnitOfMeasure, Warehouse, WarehouseType
from app.models.procurement import (
    GRNLine,
    GRNStatus,
    GoodsReceipt,
    POStatus,
    POLine,
    PurchaseOrder,
)
from app.models.user import User
from app.schemas.landed_cost import LandedCostGRNLinkCreate, LandedCostHeaderCreate, LandedCostLineCreate
from app.services import landed_cost_service as landed_cost


def _is_task_owned_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m13_s03_t001_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_owned_database() -> None:
    if os.environ.get("M13_S03_T001_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M13_S03_T001_DISPOSABLE_TEST_DATABASE=1 only for this task's disposable PostgreSQL database.")
    expected = os.environ.get("M13_S03_T001_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_owned_database(engine.url, expected):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback M13.S03.T001 database.")


def test_m13_landed_cost_database_guard_requires_exact_loopback_database():
    name = "fmcg_m13_s03_t001_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="test", host="127.0.0.1", database=name)
    assert _is_task_owned_database(safe, name)
    assert not _is_task_owned_database(safe, "fmcg_m13_s03_t001_0123456789abcdef0124")
    assert not _is_task_owned_database(safe, "fmcg_m13_s03_t001_short")
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


def _app(actor):
    from fastapi import FastAPI
    from app.api.v1.endpoints.landed_cost import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/landed-cost")

    async def override_db():
        async with AsyncSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: actor
    return app


async def _seed_receipt(
    *,
    on_hand: Decimal = Decimal("8"),
    period_status=PeriodStatus.OPEN,
    bill_date: date = date(2026, 6, 15),
):
    suffix = uuid4().hex
    user_id, company_id, material_id, grn_id, grn_line_id, movement_id = (uuid4() for _ in range(6))
    inventory_account_id, clearing_account_id, cogs_account_id = (uuid4() for _ in range(3))
    expense_account_code = f"LCE{uuid4().hex[:8].upper()}"
    year, month = bill_date.year, bill_date.month
    period_id, cost_layer_id = uuid4(), uuid4()

    async with AsyncSessionLocal() as db:
        db.add_all([
            User(
                id=user_id,
                email=f"m13-lc-{suffix}@example.invalid",
                username=f"m13-lc-{suffix}",
                full_name="Synthetic landed-cost poster",
                hashed_password="not-a-usable-password-hash",
                is_active=True,
            ),
            Company(
                id=company_id,
                name="Synthetic Landed Cost Company",
                short_code=f"LC{suffix[:10].upper()}",
                country="Kenya",
                base_currency="KES",
            ),
            Supplier(id=uuid4(), code=f"LCS{suffix[:10].upper()}", name="Synthetic Supplier"),
            ChartOfAccount(id=inventory_account_id, code=f"LCI{suffix[:8].upper()}", name="Synthetic inventory", account_type=AccountType.ASSET),
            ChartOfAccount(id=clearing_account_id, code=f"LCC{suffix[:8].upper()}", name="Synthetic landed-cost clearing", account_type=AccountType.LIABILITY),
            ChartOfAccount(id=cogs_account_id, code=expense_account_code, name="Synthetic consumed-cost expense", account_type=AccountType.EXPENSE),
            AccountingPeriod(
                id=period_id,
                period_ym=f"{year}-{month:02d}",
                period_start=date(year, month, 1),
                period_end=date(year, month, monthrange(year, month)[1]),
                status=period_status,
                notes="Synthetic M13 landed-cost posting rehearsal.",
            ),
        ])
        await db.flush()
        supplier = (await db.execute(select(Supplier).where(Supplier.code == f"LCS{suffix[:10].upper()}"))).scalar_one()
        warehouse = Warehouse(
            code=f"LCW{suffix[:10].upper()}",
            name="Synthetic raw-material warehouse",
            warehouse_type=WarehouseType.RAW_MATERIAL,
            company_id=company_id,
            country="Kenya",
        )
        material = Material(
            id=material_id,
            code=f"LCM{suffix[:10].upper()}",
            name="Synthetic imported material",
            material_type=MaterialType.RAW,
            uom=UnitOfMeasure.KG,
            standard_cost=Decimal("100.0000"),
            supplier_id=supplier.id,
        )
        db.add_all([warehouse, material])
        await db.flush()
        po = PurchaseOrder(
            po_no=f"LCPO-{suffix[:12].upper()}",
            supplier_id=supplier.id,
            company_id=company_id,
            order_date=bill_date,
            expected_delivery_date=bill_date,
            currency="USD",
            exchange_rate=Decimal("140.000000"),
            status=POStatus.RECEIVED,
        )
        db.add(po)
        await db.flush()
        po_line = POLine(
            po_id=po.id,
            line_no=1,
            material_id=material_id,
            description="Synthetic imported raw material",
            ordered_quantity=Decimal("10"),
            unit="KG",
            unit_price=Decimal("1"),
            received_quantity=Decimal("10"),
        )
        db.add(po_line)
        await db.flush()
        receipt = GoodsReceipt(
            id=grn_id,
            grn_no=f"LCGRN-{suffix[:12].upper()}",
            po_id=po.id,
            company_id=company_id,
            received_date=bill_date,
            warehouse_id=warehouse.id,
            received_by_id=user_id,
            status=GRNStatus.POSTED,
        )
        movement = StockMovement(
            id=movement_id,
            reference_number=f"LCRECEIPT-{suffix[:12].upper()}",
            movement_type=MovementType.RECEIPT,
            stock_type=StockType.MATERIAL,
            movement_date=bill_date,
            material_id=material_id,
            destination_warehouse_id=warehouse.id,
            quantity=Decimal("8"),
            unit_cost=Decimal("100.0000"),
            total_cost=Decimal("800.0000"),
            valuation_method="FIFO",
            valuation_currency="KES",
            created_by_id=user_id,
        )
        db.add_all([receipt, movement])
        await db.flush()
        grn_line = GRNLine(
            id=grn_line_id,
            grn_id=grn_id,
            po_line_id=po_line.id,
            material_id=material_id,
            received_quantity=Decimal("10"),
            accepted_quantity=Decimal("8"),
            rejected_quantity=Decimal("2"),
            unit="KG",
            lot_number=f"LCLOT-{suffix[:10].upper()}",
            stock_movement_id=movement_id,
        )
        layer = CostLayer(
            id=cost_layer_id,
            stock_type=StockType.MATERIAL,
            material_id=material_id,
            warehouse_id=warehouse.id,
            movement_id=movement_id,
            receipt_date=bill_date,
            qty_received=Decimal("8"),
            qty_remaining=on_hand,
            unit_cost=Decimal("100.000000"),
            total_value=(on_hand * Decimal("100")).quantize(Decimal("0.0001")),
            is_exhausted=on_hand == 0,
        )
        mapping = InventoryAccountMapping(
            material_id=material_id,
            stock_type="MATERIAL",
            valuation_method="FIFO",
            inventory_account_id=inventory_account_id,
            cogs_account_id=cogs_account_id,
            landed_cost_clearing_account_id=clearing_account_id,
            is_active=True,
            priority=1,
            notes="Synthetic task-owned mapping only.",
        )
        db.add_all([grn_line, layer, mapping])
        await db.commit()

    return {
        "suffix": suffix,
        "user_id": user_id,
        "company_id": company_id,
        "material_id": material_id,
        "grn_id": grn_id,
        "grn_line_id": grn_line_id,
        "movement_id": movement_id,
        "warehouse_id": warehouse.id,
        "po_line_id": po_line.id,
        "cost_layer_id": cost_layer_id,
        "period_id": period_id,
        "inventory_account_id": inventory_account_id,
        "clearing_account_id": clearing_account_id,
        "cogs_account_id": cogs_account_id,
        "expense_account_code": expense_account_code,
        "bill_date": bill_date,
    }


async def _create_allocated_landed_cost(
    context,
    *,
    include_noncapitalizable: bool = False,
    cost_amount: Decimal = Decimal("80.0000"),
    negative_cost_amount: Decimal | None = None,
    allocate: bool = True,
):
    async with AsyncSessionLocal() as db:
        header = await landed_cost.create_header(db, LandedCostHeaderCreate(
            reference_type="GRN",
            vendor_name="Synthetic Freight Provider",
            bill_no=f"SYN-LC-{context['suffix'][:10].upper()}",
            bill_date=context["bill_date"],
            currency_code="KES",
            exchange_rate=Decimal("1"),
            allocation_method="BY_VALUE",
            notes="Synthetic landed-cost posting rehearsal; not live finance data.",
        ))
        await landed_cost.add_cost_line(db, header.id, LandedCostLineCreate(
            cost_type="FREIGHT_LAND",
            description="Synthetic inbound freight",
            amount_fc=cost_amount,
            currency_code="KES",
            exchange_rate=Decimal("1"),
            allocation_method="BY_VALUE",
            is_included_in_valuation=True,
        ))
        if include_noncapitalizable:
            await landed_cost.add_cost_line(db, header.id, LandedCostLineCreate(
                cost_type="INSURANCE",
                description="Synthetic non-capitalizable insurance",
                amount_fc=Decimal("20.0000"),
                currency_code="KES",
                exchange_rate=Decimal("1"),
                allocation_method="BY_VALUE",
                is_included_in_valuation=False,
                account_code=context["expense_account_code"],
            ))
        if negative_cost_amount is not None:
            await landed_cost.add_cost_line(db, header.id, LandedCostLineCreate(
                cost_type="FREIGHT_LAND",
                description="Synthetic negative credit requiring a reversal flow",
                amount_fc=negative_cost_amount,
                currency_code="KES",
                exchange_rate=Decimal("1"),
                allocation_method="BY_VALUE",
                is_included_in_valuation=True,
            ))
        await landed_cost.add_grn_link(db, header.id, LandedCostGRNLinkCreate(
            grn_id=context["grn_id"],
            grn_no=f"SYN-GRN-{context['suffix'][:10].upper()}",
        ))
        if allocate:
            allocated = await landed_cost.run_allocation(db, header.id)
            return allocated.id
        return header.id


@pytest.mark.asyncio
async def test_post_requires_finance_permission_and_links_fifo_value_to_balanced_gl():
    _require_task_owned_database()
    context = await _seed_receipt()
    header_id = await _create_allocated_landed_cost(context)
    actor = _actor(context["user_id"])
    app = _app(actor)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://m13-landed.test") as client:
            denied = await client.post(f"/api/v1/landed-cost/{header_id}/post")
            assert denied.status_code == 403
            async with AsyncSessionLocal() as db:
                header = await db.get(LandedCostHeader, header_id)
                layer = await db.get(CostLayer, context["cost_layer_id"])
                assert header.status == "VALIDATED"
                assert header.total_lc_amount_fc == Decimal("80.0000")
                assert header.total_lc_amount_base == Decimal("80.0000")
                assert layer.unit_cost == Decimal("100.000000")
                assert await db.scalar(
                    select(func.count()).select_from(JournalEntry).where(JournalEntry.source_ref == header.lc_no)
                ) == 0

            actor.roles[0].permissions = [SimpleNamespace(code="finance.post", is_active=True)]
            posted = await client.post(f"/api/v1/landed-cost/{header_id}/post")
            assert posted.status_code == 200, posted.text
            assert posted.json()["status"] == "POSTED"

            async with AsyncSessionLocal() as db:
                header = await db.get(LandedCostHeader, header_id)
                layer = await db.get(CostLayer, context["cost_layer_id"])
                allocation = (await db.execute(
                    select(LandedCostAllocationLine).where(LandedCostAllocationLine.header_id == header_id)
                )).scalar_one()
                adjustment = await db.get(LCInventoryAdjustment, allocation.inventory_adj_id)
                entry = await db.get(JournalEntry, allocation.journal_entry_id)
                batch = await db.get(AccountingPostingBatch, allocation.posting_batch_id)
                event = (await db.execute(
                    select(OperationalPostingEvent).where(OperationalPostingEvent.source_id == str(header_id))
                )).scalar_one()
                journal_lines = list((await db.execute(
                    select(JournalLine).where(JournalLine.entry_id == entry.id)
                )).scalars().all())
                assert header.status == "POSTED"
                assert allocation.is_posted is True
                assert allocation.accounting_status == OperationalPostingStatus.POSTED
                assert allocation.inventory_adj_id and allocation.journal_entry_id and allocation.posting_batch_id
                assert adjustment.accounting_status == OperationalPostingStatus.POSTED
                assert adjustment.adjustment_amount == Decimal("80.0000")
                assert adjustment.qty_on_hand == Decimal("8.000")
                assert adjustment.old_avg_cost == Decimal("100.000000")
                assert adjustment.new_avg_cost == Decimal("110.000000")
                assert layer.qty_remaining == Decimal("8.000")
                assert layer.unit_cost == Decimal("110.000000")
                assert layer.total_value == Decimal("880.0000")
                assert entry.is_posted is True and entry.posted_by_id == context["user_id"]
                assert entry.company_id == context["company_id"]
                assert batch.status == PostingBatchStatus.POSTED and batch.journal_entry_id == entry.id
                assert event.status == OperationalPostingStatus.POSTED and event.journal_entry_id == entry.id
                assert sum((line.debit for line in journal_lines), Decimal("0")) == Decimal("80.0000")
                assert sum((line.credit for line in journal_lines), Decimal("0")) == Decimal("80.0000")
                assert {line.account_id for line in journal_lines} == {
                    context["inventory_account_id"], context["clearing_account_id"],
                }

            duplicate = await client.post(f"/api/v1/landed-cost/{header_id}/post")
            assert duplicate.status_code == 400
            async with AsyncSessionLocal() as db:
                header = await db.get(LandedCostHeader, header_id)
                assert await db.scalar(
                    select(func.count()).select_from(JournalEntry).where(JournalEntry.source_ref == header.lc_no)
                ) == 1
                layer = await db.get(CostLayer, context["cost_layer_id"])
                assert layer.total_value == Decimal("880.0000")
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_partial_fifo_layer_splits_remaining_inventory_and_consumed_cogs():
    _require_task_owned_database()
    context = await _seed_receipt(on_hand=Decimal("4"), bill_date=date(2026, 7, 15))
    header_id = await _create_allocated_landed_cost(context)
    try:
        async with AsyncSessionLocal() as db:
            await landed_cost.post_landed_cost(
                db,
                header_id,
                posted_by=str(context["user_id"]),
                posted_by_id=context["user_id"],
            )
        async with AsyncSessionLocal() as db:
            allocation = (await db.execute(
                select(LandedCostAllocationLine).where(LandedCostAllocationLine.header_id == header_id)
            )).scalar_one()
            layer = await db.get(CostLayer, context["cost_layer_id"])
            entry = await db.get(JournalEntry, allocation.journal_entry_id)
            lines = list((await db.execute(select(JournalLine).where(JournalLine.entry_id == entry.id))).scalars().all())
            debit_by_account = {line.account_id: line.debit for line in lines if line.debit > 0}
            credit_by_account = {line.account_id: line.credit for line in lines if line.credit > 0}
            assert layer.qty_remaining == Decimal("4.000")
            assert layer.unit_cost == Decimal("110.000000")
            assert layer.total_value == Decimal("440.0000")
            assert debit_by_account == {
                context["inventory_account_id"]: Decimal("40.0000"),
                context["cogs_account_id"]: Decimal("40.0000"),
            }
            assert credit_by_account == {context["clearing_account_id"]: Decimal("80.0000")}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_noncapitalizable_cost_uses_explicit_expense_and_configured_clearing_accounts():
    _require_task_owned_database()
    context = await _seed_receipt(bill_date=date(2026, 11, 15))
    header_id = await _create_allocated_landed_cost(context, include_noncapitalizable=True)
    try:
        async with AsyncSessionLocal() as db:
            header = await db.get(LandedCostHeader, header_id)
            assert header.total_lc_amount_fc == Decimal("100.0000")
            assert header.total_lc_amount_base == Decimal("100.0000")
            await landed_cost.post_landed_cost(
                db,
                header_id,
                posted_by=str(context["user_id"]),
                posted_by_id=context["user_id"],
            )

        async with AsyncSessionLocal() as db:
            header = await db.get(LandedCostHeader, header_id)
            layer = await db.get(CostLayer, context["cost_layer_id"])
            expense_account = (await db.execute(
                select(ChartOfAccount).where(ChartOfAccount.code == context["expense_account_code"])
            )).scalar_one()
            expense_allocation = (await db.execute(
                select(LandedCostAllocationLine)
                .join(LandedCostLine, LandedCostLine.id == LandedCostAllocationLine.lc_line_id)
                .where(
                    LandedCostAllocationLine.header_id == header_id,
                    LandedCostLine.is_included_in_valuation.is_(False),
                )
            )).scalar_one()
            expense_entry = await db.get(JournalEntry, expense_allocation.journal_entry_id)
            expense_lines = list((await db.execute(
                select(JournalLine).where(JournalLine.entry_id == expense_entry.id)
            )).scalars().all())
            assert header.status == "POSTED"
            assert layer.qty_remaining == Decimal("8.000")
            assert layer.total_value == Decimal("880.0000")
            assert expense_allocation.is_posted is True
            assert expense_allocation.inventory_adj_id is None
            assert expense_allocation.accounting_status == OperationalPostingStatus.POSTED
            assert {line.account_id: (line.debit, line.credit) for line in expense_lines} == {
                expense_account.id: (Decimal("20.0000"), Decimal("0.0000")),
                context["clearing_account_id"]: (Decimal("0.0000"), Decimal("20.0000")),
            }
            assert await db.scalar(
                select(func.count()).select_from(LCInventoryAdjustment).where(
                    LCInventoryAdjustment.header_id == header_id
                )
            ) == 1
            assert await db.scalar(
                select(func.count()).select_from(JournalEntry).where(JournalEntry.source_ref == header.lc_no)
            ) == 2
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_wrong_material_mapping_with_same_stock_type_is_never_selected():
    _require_task_owned_database()
    context = await _seed_receipt(bill_date=date(2026, 12, 15))
    header_id = await _create_allocated_landed_cost(context)
    decoy_material_id = uuid4()
    decoy_inventory_id, decoy_clearing_id, decoy_cogs_id = (uuid4() for _ in range(3))
    try:
        async with AsyncSessionLocal() as db:
            db.add_all([
                Material(
                    id=decoy_material_id,
                    code=f"LCD{context['suffix'][:10].upper()}",
                    name="Synthetic unrelated material",
                    material_type=MaterialType.RAW,
                    uom=UnitOfMeasure.KG,
                    standard_cost=Decimal("1"),
                ),
                ChartOfAccount(
                    id=decoy_inventory_id,
                    code=f"LDI{context['suffix'][:8].upper()}",
                    name="Decoy inventory account",
                    account_type=AccountType.ASSET,
                ),
                ChartOfAccount(
                    id=decoy_clearing_id,
                    code=f"LDC{context['suffix'][:8].upper()}",
                    name="Decoy landed-cost clearing account",
                    account_type=AccountType.LIABILITY,
                ),
                ChartOfAccount(
                    id=decoy_cogs_id,
                    code=f"LDG{context['suffix'][:8].upper()}",
                    name="Decoy COGS account",
                    account_type=AccountType.EXPENSE,
                ),
            ])
            await db.flush()
            db.add(InventoryAccountMapping(
                material_id=decoy_material_id,
                stock_type="MATERIAL",
                valuation_method="FIFO",
                inventory_account_id=decoy_inventory_id,
                cogs_account_id=decoy_cogs_id,
                landed_cost_clearing_account_id=decoy_clearing_id,
                is_active=True,
                priority=0,
                notes="Synthetic wrong-material mapping used to verify strict scope matching.",
            ))
            await db.commit()

        async with AsyncSessionLocal() as db:
            await landed_cost.post_landed_cost(
                db,
                header_id,
                posted_by=str(context["user_id"]),
                posted_by_id=context["user_id"],
            )

        async with AsyncSessionLocal() as db:
            header = await db.get(LandedCostHeader, header_id)
            allocation = (await db.execute(
                select(LandedCostAllocationLine).where(LandedCostAllocationLine.header_id == header_id)
            )).scalar_one()
            lines = list((await db.execute(
                select(JournalLine).where(JournalLine.entry_id == allocation.journal_entry_id)
            )).scalars().all())
            assert header.status == "POSTED"
            assert {line.account_id for line in lines} == {
                context["inventory_account_id"], context["clearing_account_id"],
            }
            assert decoy_inventory_id not in {line.account_id for line in lines}
            assert decoy_clearing_id not in {line.account_id for line in lines}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_missing_mapping_and_closed_period_leave_landed_cost_unposted():
    _require_task_owned_database()
    context = await _seed_receipt(bill_date=date(2026, 8, 15))
    header_id = await _create_allocated_landed_cost(context)
    try:
        async with AsyncSessionLocal() as db:
            # This database is task-owned and disposable. Remove every synthetic
            # fallback too, so a stock-type mapping cannot mask the missing-map case.
            await db.execute(InventoryAccountMapping.__table__.delete())
            await db.commit()
        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError, match="needs an active landed-cost clearing account mapping"):
                await landed_cost.post_landed_cost(
                    db,
                    header_id,
                    posted_by=str(context["user_id"]),
                    posted_by_id=context["user_id"],
                )
        async with AsyncSessionLocal() as db:
            header = await db.get(LandedCostHeader, header_id)
            layer = await db.get(CostLayer, context["cost_layer_id"])
            assert header.status == "VALIDATED"
            assert layer.unit_cost == Decimal("100.000000")
            assert await db.scalar(
                select(func.count()).select_from(LCInventoryAdjustment).where(
                    LCInventoryAdjustment.header_id == header_id
                )
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(JournalEntry).where(JournalEntry.source_ref == header.lc_no)
            ) == 0

        async with AsyncSessionLocal() as db:
            db.add(InventoryAccountMapping(
                material_id=context["material_id"],
                stock_type="MATERIAL",
                valuation_method="FIFO",
                inventory_account_id=context["inventory_account_id"],
                cogs_account_id=context["cogs_account_id"],
                landed_cost_clearing_account_id=context["clearing_account_id"],
                is_active=True,
                priority=1,
            ))
            period = await db.get(AccountingPeriod, context["period_id"])
            period.status = PeriodStatus.CLOSED
            await db.commit()
        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError, match="is CLOSED"):
                await landed_cost.post_landed_cost(
                    db,
                    header_id,
                    posted_by=str(context["user_id"]),
                    posted_by_id=context["user_id"],
                )
        async with AsyncSessionLocal() as db:
            header = await db.get(LandedCostHeader, header_id)
            layer = await db.get(CostLayer, context["cost_layer_id"])
            assert header.status == "VALIDATED"
            assert layer.unit_cost == Decimal("100.000000")
            assert await db.scalar(
                select(func.count()).select_from(LCInventoryAdjustment).where(
                    LCInventoryAdjustment.header_id == header_id
                )
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(JournalEntry).where(JournalEntry.source_ref == header.lc_no)
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(OperationalPostingEvent).where(
                    OperationalPostingEvent.source_id == str(header_id)
                )
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(AccountingPostingBatch).where(
                    AccountingPostingBatch.source_module == "landed_cost",
                    AccountingPostingBatch.source_ref == header.lc_no,
                )
            ) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_journal_validation_failure_rolls_back_every_posting_record():
    _require_task_owned_database()
    context = await _seed_receipt(bill_date=date(2026, 9, 15))
    header_id = await _create_allocated_landed_cost(context)
    try:
        async with AsyncSessionLocal() as db:
            account = await db.get(ChartOfAccount, context["inventory_account_id"])
            account.is_control = True
            await db.commit()

        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError, match="control account"):
                await landed_cost.post_landed_cost(
                    db,
                    header_id,
                    posted_by=str(context["user_id"]),
                    posted_by_id=context["user_id"],
                )

        async with AsyncSessionLocal() as db:
            header = await db.get(LandedCostHeader, header_id)
            layer = await db.get(CostLayer, context["cost_layer_id"])
            allocation = (await db.execute(
                select(LandedCostAllocationLine).where(LandedCostAllocationLine.header_id == header_id)
            )).scalar_one()
            assert header.status == "VALIDATED"
            assert layer.unit_cost == Decimal("100.000000")
            assert layer.total_value == Decimal("800.0000")
            assert allocation.is_posted is False
            assert allocation.accounting_status is None
            assert allocation.journal_entry_id is None
            assert await db.scalar(
                select(func.count()).select_from(LCInventoryAdjustment).where(
                    LCInventoryAdjustment.header_id == header_id
                )
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(JournalEntry).where(JournalEntry.source_ref == header.lc_no)
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(OperationalPostingEvent).where(
                    OperationalPostingEvent.source_id == str(header_id)
                )
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(AccountingPostingBatch).where(
                    AccountingPostingBatch.source_module == "landed_cost",
                    AccountingPostingBatch.source_ref == header.lc_no,
                )
            ) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_post_attempts_create_only_one_valuation_and_journal():
    _require_task_owned_database()
    context = await _seed_receipt(bill_date=date(2026, 10, 15))
    header_id = await _create_allocated_landed_cost(context)

    async def post_once():
        async with AsyncSessionLocal() as db:
            return await landed_cost.post_landed_cost(
                db,
                header_id,
                posted_by=str(context["user_id"]),
                posted_by_id=context["user_id"],
            )

    try:
        results = await asyncio.gather(post_once(), post_once(), return_exceptions=True)
        assert sum(not isinstance(result, BaseException) for result in results) == 1
        assert sum(isinstance(result, ValueError) for result in results) == 1

        async with AsyncSessionLocal() as db:
            header = await db.get(LandedCostHeader, header_id)
            layer = await db.get(CostLayer, context["cost_layer_id"])
            allocation = (await db.execute(
                select(LandedCostAllocationLine).where(LandedCostAllocationLine.header_id == header_id)
            )).scalar_one()
            assert header.status == "POSTED"
            assert layer.qty_remaining == Decimal("8.000")
            assert layer.total_value == Decimal("880.0000")
            assert allocation.is_posted is True
            assert await db.scalar(
                select(func.count()).select_from(LCInventoryAdjustment).where(
                    LCInventoryAdjustment.header_id == header_id
                )
            ) == 1
            assert await db.scalar(
                select(func.count()).select_from(JournalEntry).where(JournalEntry.source_ref == header.lc_no)
            ) == 1
            assert await db.scalar(
                select(func.count()).select_from(OperationalPostingEvent).where(
                    OperationalPostingEvent.source_id == str(header_id)
                )
            ) == 1
            assert await db.scalar(
                select(func.count()).select_from(AccountingPostingBatch).where(
                    AccountingPostingBatch.source_module == "landed_cost",
                    AccountingPostingBatch.source_ref == header.lc_no,
                )
            ) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_zero_rounded_share_is_omitted_and_remaining_share_posts():
    _require_task_owned_database()
    context = await _seed_receipt(bill_date=date(2027, 1, 15))
    second_movement_id, second_layer_id = uuid4(), uuid4()
    async with AsyncSessionLocal() as db:
        po_line = await db.get(POLine, context["po_line_id"])
        po_line.ordered_quantity = Decimal("12")
        po_line.received_quantity = Decimal("12")
        db.add(StockMovement(
            id=second_movement_id,
            reference_number=f"LCRECEIPT2-{context['suffix'][:12].upper()}",
            movement_type=MovementType.RECEIPT,
            stock_type=StockType.MATERIAL,
            movement_date=context["bill_date"],
            material_id=context["material_id"],
            destination_warehouse_id=context["warehouse_id"],
            quantity=Decimal("2"),
            unit_cost=Decimal("100.0000"),
            total_cost=Decimal("200.0000"),
            valuation_method="FIFO",
            valuation_currency="KES",
            created_by_id=context["user_id"],
        ))
        await db.flush()
        db.add_all([
            GRNLine(
                grn_id=context["grn_id"],
                po_line_id=context["po_line_id"],
                material_id=context["material_id"],
                received_quantity=Decimal("2"),
                accepted_quantity=Decimal("2"),
                rejected_quantity=Decimal("0"),
                unit="KG",
                lot_number=f"LCLOT2-{context['suffix'][:10].upper()}",
                stock_movement_id=second_movement_id,
            ),
            CostLayer(
                id=second_layer_id,
                stock_type=StockType.MATERIAL,
                material_id=context["material_id"],
                warehouse_id=context["warehouse_id"],
                movement_id=second_movement_id,
                receipt_date=context["bill_date"],
                qty_received=Decimal("2"),
                qty_remaining=Decimal("2"),
                unit_cost=Decimal("100.000000"),
                total_value=Decimal("200.0000"),
                is_exhausted=False,
            ),
        ])
        await db.commit()

    header_id = await _create_allocated_landed_cost(context, cost_amount=Decimal("0.0001"))
    try:
        async with AsyncSessionLocal() as db:
            allocations = list((await db.execute(
                select(LandedCostAllocationLine).where(LandedCostAllocationLine.header_id == header_id)
            )).scalars().all())
            assert len(allocations) == 1
            assert allocations[0].grn_line_id == context["grn_line_id"]
            assert allocations[0].allocated_amount == Decimal("0.0001")
            await landed_cost.post_landed_cost(
                db,
                header_id,
                posted_by=str(context["user_id"]),
                posted_by_id=context["user_id"],
            )
        async with AsyncSessionLocal() as db:
            header = await db.get(LandedCostHeader, header_id)
            original_layer = await db.get(CostLayer, context["cost_layer_id"])
            skipped_layer = await db.get(CostLayer, second_layer_id)
            assert header.status == "POSTED"
            assert original_layer.total_value == Decimal("800.0001")
            assert skipped_layer.total_value == Decimal("200.0000")
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_negative_cost_line_fails_closed_instead_of_being_silently_omitted():
    _require_task_owned_database()
    context = await _seed_receipt(bill_date=date(2027, 2, 15))
    header_id = await _create_allocated_landed_cost(
        context,
        negative_cost_amount=Decimal("-5.0000"),
        allocate=False,
    )
    try:
        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError, match="Negative landed-cost lines require"):
                await landed_cost.run_allocation(db, header_id)
            await db.rollback()

        async with AsyncSessionLocal() as db:
            header = await db.get(LandedCostHeader, header_id)
            assert header.status == "DRAFT"
            assert await db.scalar(
                select(func.count()).select_from(LandedCostAllocationLine).where(
                    LandedCostAllocationLine.header_id == header_id
                )
            ) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_missing_source_fifo_layer_leaves_document_and_gl_unposted():
    _require_task_owned_database()
    context = await _seed_receipt(bill_date=date(2027, 3, 15))
    header_id = await _create_allocated_landed_cost(context)
    try:
        async with AsyncSessionLocal() as db:
            layer = await db.get(CostLayer, context["cost_layer_id"])
            await db.delete(layer)
            await db.commit()

        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError, match="has no matching FIFO cost layer"):
                await landed_cost.post_landed_cost(
                    db,
                    header_id,
                    posted_by=str(context["user_id"]),
                    posted_by_id=context["user_id"],
                )

        async with AsyncSessionLocal() as db:
            header = await db.get(LandedCostHeader, header_id)
            allocation = (await db.execute(
                select(LandedCostAllocationLine).where(LandedCostAllocationLine.header_id == header_id)
            )).scalar_one()
            assert header.status == "VALIDATED"
            assert allocation.is_posted is False
            assert allocation.accounting_status is None
            assert allocation.journal_entry_id is None
            assert await db.scalar(
                select(func.count()).select_from(LCInventoryAdjustment).where(
                    LCInventoryAdjustment.header_id == header_id
                )
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(JournalEntry).where(JournalEntry.source_ref == header.lc_no)
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(OperationalPostingEvent).where(
                    OperationalPostingEvent.source_id == str(header_id)
                )
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(AccountingPostingBatch).where(
                    AccountingPostingBatch.source_module == "landed_cost",
                    AccountingPostingBatch.source_ref == header.lc_no,
                )
            ) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_missing_accounting_period_leaves_document_and_valuation_unposted():
    _require_task_owned_database()
    context = await _seed_receipt(bill_date=date(2027, 4, 15))
    header_id = await _create_allocated_landed_cost(context)
    try:
        async with AsyncSessionLocal() as db:
            period = await db.get(AccountingPeriod, context["period_id"])
            await db.delete(period)
            await db.commit()

        async with AsyncSessionLocal() as db:
            with pytest.raises(ValueError, match="No accounting period exists"):
                await landed_cost.post_landed_cost(
                    db,
                    header_id,
                    posted_by=str(context["user_id"]),
                    posted_by_id=context["user_id"],
                )

        async with AsyncSessionLocal() as db:
            header = await db.get(LandedCostHeader, header_id)
            layer = await db.get(CostLayer, context["cost_layer_id"])
            allocation = (await db.execute(
                select(LandedCostAllocationLine).where(LandedCostAllocationLine.header_id == header_id)
            )).scalar_one()
            assert header.status == "VALIDATED"
            assert layer.unit_cost == Decimal("100.000000")
            assert layer.total_value == Decimal("800.0000")
            assert allocation.is_posted is False
            assert allocation.accounting_status is None
            assert allocation.journal_entry_id is None
            assert await db.scalar(
                select(func.count()).select_from(LCInventoryAdjustment).where(
                    LCInventoryAdjustment.header_id == header_id
                )
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(JournalEntry).where(JournalEntry.source_ref == header.lc_no)
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(OperationalPostingEvent).where(
                    OperationalPostingEvent.source_id == str(header_id)
                )
            ) == 0
            assert await db.scalar(
                select(func.count()).select_from(AccountingPostingBatch).where(
                    AccountingPostingBatch.source_module == "landed_cost",
                    AccountingPostingBatch.source_ref == header.lc_no,
                )
            ) == 0
    finally:
        await engine.dispose()
