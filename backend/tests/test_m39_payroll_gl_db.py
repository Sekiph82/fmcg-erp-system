"""M39 hand-off HR → accounting: approving a payroll run books it in the general ledger through the payroll posting
rule (gross expense = net pay payable + statutory deductions payable), once; without a rule, approval still works."""
from __future__ import annotations

import os
import re
import uuid
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.finance import AccountingPostingRule, AccountType, ChartOfAccount, JournalEntry, JournalLine
from app.models.payroll_ke import PayrollRun, PayrollRunStatus
from app.models.user import User
from app.services.payroll_ke_service import approve_payroll_run, post_payroll_to_gl

TASK_DB_ENV = "M39_PAY_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M39_PAY_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m39_pay_[a-f0-9]{24}")
pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _run(year: int) -> PayrollRun:
    return PayrollRun(run_no=f"PR-{uuid.uuid4().hex[:8]}", period_month=1, period_year=year, period_start=date(year, 1, 1),
                      period_end=date(year, 1, 31), status=PayrollRunStatus.CALCULATED, total_gross=Decimal("100000"),
                      total_paye=Decimal("20000"), total_nhif=Decimal("2750"), total_nssf=Decimal("2160"),
                      total_housing_levy=Decimal("1500"), total_net=Decimal("73590"))


@pytest.mark.asyncio
async def test_approved_payroll_is_booked_in_the_ledger():
    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        hr = User(email=f"hr-{s}@example.com", username=f"hr{s}", full_name="HR", hashed_password="x")
        db.add(hr)
        await db.flush()
        # no rule yet: approval works, nothing is booked
        bare = _run(2101)
        db.add(bare)
        await db.flush()
        await approve_payroll_run(db, bare, hr.id)
        assert bare.status == PayrollRunStatus.APPROVED
        assert (await db.execute(select(func.count()).select_from(JournalEntry).where(JournalEntry.source_id == bare.id))).scalar() == 0

        exp, net, ded = (ChartOfAccount(code=f"PAYX{s}", name="Salaries", account_type=AccountType.EXPENSE, currency="KES"),
                         ChartOfAccount(code=f"PAYN{s}", name="Net pay payable", account_type=AccountType.LIABILITY, currency="KES"),
                         ChartOfAccount(code=f"PAYD{s}", name="Statutory payable", account_type=AccountType.LIABILITY, currency="KES"))
        db.add_all([exp, net, ded])
        await db.flush()
        db.add(AccountingPostingRule(source_module="payroll", source_event="PAYROLL_APPROVED", rule_name="Payroll",
                                     debit_account_id=exp.id, credit_account_id=net.id, tax_account_id=ded.id,
                                     priority=1, is_active=True))
        run = _run(2102)
        db.add(run)
        await db.flush()
        await approve_payroll_run(db, run, hr.id)
        await db.commit()

        je = (await db.execute(select(JournalEntry).where(JournalEntry.source_id == run.id))).scalar_one()
        assert je.source_module == "payroll" and je.is_posted and je.entry_date == date(2102, 1, 31)
        lines = {(l.account_id, l.debit, l.credit) for l in (await db.execute(select(JournalLine).where(JournalLine.entry_id == je.id))).scalars()}
        assert lines == {(exp.id, Decimal("100000"), Decimal("0")), (net.id, Decimal("0"), Decimal("73590")),
                         (ded.id, Decimal("0"), Decimal("26410"))}, lines
        again = await post_payroll_to_gl(db, run, hr.id)       # booked once, never twice
        assert again.id == je.id


@pytest.mark.asyncio
async def test_finance_approved_expense_claim_is_booked_in_the_ledger():
    from sqlalchemy.orm import selectinload

    from app.models.expenses import ExpenseClaim
    from app.services.expenses_service import _post_claim_to_gl

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        fin = User(email=f"fin-{s}@example.com", username=f"fin{s}", full_name="Fin", hashed_password="x")
        exp, pay = (ChartOfAccount(code=f"EXPX{s}", name="Travel", account_type=AccountType.EXPENSE, currency="KES"),
                    ChartOfAccount(code=f"EXPP{s}", name="Employee payable", account_type=AccountType.LIABILITY, currency="KES"))
        db.add_all([fin, exp, pay])
        await db.flush()
        claim = ExpenseClaim(claim_no=f"EC-{s}", employee_id=uuid.uuid4(), claim_date=date.today(),
                             total_approved_amount=Decimal("5000"), approved_by_finance=fin.id)
        db.add(claim)
        await db.flush()
        claim = (await db.execute(select(ExpenseClaim).options(selectinload(ExpenseClaim.lines))
                                  .where(ExpenseClaim.expense_claim_id == claim.expense_claim_id))).scalar_one()
        assert await _post_claim_to_gl(db, claim) is None                   # no rule: sub-ledger only
        db.add(AccountingPostingRule(source_module="expenses", source_event="EXPENSE_FINANCE_APPROVED", rule_name="Expenses",
                                     debit_account_id=exp.id, credit_account_id=pay.id, priority=1, is_active=True))
        await db.flush()
        je = await _post_claim_to_gl(db, claim)
        await db.commit()
        lines = {(l.account_id, l.debit, l.credit) for l in (await db.execute(select(JournalLine).where(JournalLine.entry_id == je.id))).scalars()}
        assert je.source_module == "expenses" and lines == {(exp.id, Decimal("5000"), Decimal("0")), (pay.id, Decimal("0"), Decimal("5000"))}


@pytest.mark.asyncio
async def test_supplier_payment_is_booked_in_the_ledger():
    from sqlalchemy.orm import selectinload

    from app.crud.procurement import create_supplier_payment
    from app.models.master import Supplier
    from app.models.procurement import PurchaseOrder

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        buyer = User(email=f"ap-{s}@example.com", username=f"ap{s}", full_name="AP", hashed_password="x")
        sup = Supplier(code=f"SUP-{s}", name="Pack Ltd")
        ap, bank = (ChartOfAccount(code=f"APX{s}", name="Payables", account_type=AccountType.LIABILITY, currency="KES"),
                    ChartOfAccount(code=f"BNK{s}", name="Bank", account_type=AccountType.ASSET, currency="KES"))
        db.add_all([buyer, sup, ap, bank])
        await db.flush()
        db.add(AccountingPostingRule(source_module="procurement", source_event="SUPPLIER_PAYMENT_MADE", rule_name="AP pay",
                                     debit_account_id=ap.id, credit_account_id=bank.id, priority=1, is_active=True))
        po = PurchaseOrder(po_no=f"PO-{s}", supplier_id=sup.id, order_date=date.today(), expected_delivery_date=date.today(),
                           currency="KES")
        db.add(po)
        await db.flush()
        po = (await db.execute(select(PurchaseOrder).options(selectinload(PurchaseOrder.lines)).where(PurchaseOrder.id == po.id))).scalar_one()
        pay = await create_supplier_payment(db, po, {"payment_date": date.today(), "amount": Decimal("12000"), "method": "bank"}, buyer.id)
        await db.commit()
        je = (await db.execute(select(JournalEntry).where(JournalEntry.source_id == pay.id))).scalar_one()
        lines = {(l.account_id, l.debit, l.credit) for l in (await db.execute(select(JournalLine).where(JournalLine.entry_id == je.id))).scalars()}
        assert je.source_module == "procurement" and lines == {(ap.id, Decimal("12000"), Decimal("0")), (bank.id, Decimal("0"), Decimal("12000"))}


@pytest.mark.asyncio
async def test_stock_count_shortage_and_surplus_are_booked():
    from types import SimpleNamespace

    from app.services.cycle_count_service import _post_adjustment_to_gl

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        clerk = User(email=f"wh-{s}@example.com", username=f"wh{s}", full_name="WH", hashed_password="x")
        shrink, inv = (ChartOfAccount(code=f"SHR{s}", name="Stock adjustments", account_type=AccountType.EXPENSE, currency="KES"),
                       ChartOfAccount(code=f"INV{s}", name="Inventory", account_type=AccountType.ASSET, currency="KES"))
        db.add_all([clerk, shrink, inv])
        await db.flush()
        db.add(AccountingPostingRule(source_module="inventory", source_event="STOCK_ADJUSTMENT", rule_name="Counts",
                                     debit_account_id=shrink.id, credit_account_id=inv.id, priority=1, is_active=True))
        await db.flush()
        entry = SimpleNamespace(unit_cost=Decimal("50"))
        short = SimpleNamespace(id=uuid.uuid4(), adjustment_qty=Decimal("-3"), adjustment_value=None, stock_movement_ref="ADJ-1",
                                approved_by_id=clerk.id)
        extra = SimpleNamespace(id=uuid.uuid4(), adjustment_qty=Decimal("2"), adjustment_value=Decimal("100"), stock_movement_ref="ADJ-2",
                                approved_by_id=clerk.id)
        j1, j2 = await _post_adjustment_to_gl(db, entry, short), await _post_adjustment_to_gl(db, entry, extra)
        await db.commit()

        async def lines(je):
            return {(l.account_id, l.debit, l.credit) for l in (await db.execute(select(JournalLine).where(JournalLine.entry_id == je.id))).scalars()}
        assert await lines(j1) == {(shrink.id, Decimal("150"), Decimal("0")), (inv.id, Decimal("0"), Decimal("150"))}
        assert await lines(j2) == {(inv.id, Decimal("100"), Decimal("0")), (shrink.id, Decimal("0"), Decimal("100"))}


@pytest.mark.asyncio
async def test_pos_sale_is_booked_with_output_tax():
    from types import SimpleNamespace

    from app.api.v1.endpoints.pos import _post_pos_sale_to_gl

    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        cashier = User(email=f"pos-{s}@example.com", username=f"pos{s}", full_name="Till", hashed_password="x")
        till, rev, vat = (ChartOfAccount(code=f"TIL{s}", name="Till", account_type=AccountType.ASSET, currency="KES"),
                          ChartOfAccount(code=f"REV{s}", name="Counter sales", account_type=AccountType.REVENUE, currency="KES"),
                          ChartOfAccount(code=f"VAT{s}", name="Output VAT", account_type=AccountType.LIABILITY, currency="KES"))
        db.add_all([cashier, till, rev, vat])
        await db.flush()
        db.add(AccountingPostingRule(source_module="pos", source_event="POS_SALE", rule_name="POS", debit_account_id=till.id,
                                     credit_account_id=rev.id, tax_account_id=vat.id, priority=1, is_active=True))
        await db.flush()
        sale = SimpleNamespace(id=uuid.uuid4(), sale_no=f"POS-{s}", sale_total=Decimal("1160"), tax_total=Decimal("160"))
        je = await _post_pos_sale_to_gl(db, sale, cashier.id)
        await db.commit()
        lines = {(l.account_id, l.debit, l.credit) for l in (await db.execute(select(JournalLine).where(JournalLine.entry_id == je.id))).scalars()}
        assert lines == {(till.id, Decimal("1160"), Decimal("0")), (rev.id, Decimal("0"), Decimal("1000")), (vat.id, Decimal("0"), Decimal("160"))}
        from app.api.v1.endpoints.pos import _reverse_pos_sale_in_gl     # voiding the sale takes the entry back
        back = await _reverse_pos_sale_in_gl(db, sale, cashier.id)
        await db.commit()
        rlines = {(l.account_id, l.debit, l.credit) for l in (await db.execute(select(JournalLine).where(JournalLine.entry_id == back.id))).scalars()}
        assert back.is_posted and rlines == {(a, cr, dr) for a, dr, cr in lines}
        assert await _reverse_pos_sale_in_gl(db, sale, cashier.id) is None   # only once


@pytest.mark.asyncio
async def test_completed_production_is_booked_materials_packaging_conversion_to_finished_goods(monkeypatch):
    """Owner 2026-11-20: raw material, packaging and conversion flow into WIP, WIP into finished goods, one journal."""
    from types import SimpleNamespace

    from app.models.master import MaterialType
    from app.services import production_ledger_service as pls

    async def by_type(_db, _order_id):
        return {MaterialType.RAW: Decimal("600.00"), MaterialType.PACKAGING: Decimal("150.00")}

    async def order_cost(_db, _order):
        return {"total_labor_cost": 200.0, "total_machine_cost": 40.0, "total_energy_cost": 10.0}

    monkeypatch.setattr(pls, "material_cost_by_type", by_type)
    monkeypatch.setattr("app.services.production_cost_service.compute_order_cost", order_cost)
    s = uuid.uuid4().hex[:6]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        planner = User(email=f"pp-{s}@example.com", username=f"pp{s}", full_name="PP", hashed_password="x")
        acc = {k: ChartOfAccount(code=f"{k[:4].upper()}{s}", name=k, account_type=t, currency="KES") for k, t in (
            ("wip", AccountType.ASSET), ("raw", AccountType.ASSET), ("pack", AccountType.ASSET), ("fg", AccountType.ASSET),
            ("applied", AccountType.EXPENSE))}
        db.add_all([planner, *acc.values()])
        await db.flush()
        order = SimpleNamespace(id=uuid.uuid4(), order_no=f"PO-{s}")
        assert await pls.post_production_completion(db, order, planner.id) is None   # no rules: nothing booked
        for event, dr, cr in (("RAW_MATERIAL_ISSUE", "wip", "raw"), ("PACKAGING_ISSUE", "wip", "pack"),
                              ("CONVERSION_APPLIED", "wip", "applied"), ("FINISHED_GOODS_RECEIPT", "fg", "wip")):
            db.add(AccountingPostingRule(source_module="production", source_event=event, rule_name=event,
                                         debit_account_id=acc[dr].id, credit_account_id=acc[cr].id, priority=1, is_active=True))
        await db.flush()
        je = await pls.post_production_completion(db, order, planner.id)
        await db.commit()
        rows = [(l.account_id, l.debit, l.credit) for l in (await db.execute(select(JournalLine).where(JournalLine.entry_id == je.id))).scalars()]
        net = {}
        for a, d, c in rows:
            net[a] = net.get(a, Decimal("0")) + d - c
        assert je.source_module == "production" and je.is_posted
        assert net[acc["fg"].id] == Decimal("1000.00")          # 600 raw + 150 packaging + 250 conversion
        assert net[acc["raw"].id] == Decimal("-600.00") and net[acc["pack"].id] == Decimal("-150.00")
        assert net[acc["applied"].id] == Decimal("-250.00") and net[acc["wip"].id] == Decimal("0")


def test_packaging_and_semi_finished_come_from_their_linked_warehouse():
    from app.models.master import MaterialType
    from app.services.production_ledger_service import material_warehouse

    src, pack, wip = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    links = {"packaging_warehouse_id": pack, "wip_warehouse_id": wip}
    assert material_warehouse(MaterialType.PACKAGING, src, links) == pack
    assert material_warehouse(MaterialType.SEMI_FINISHED, src, links) == wip
    assert material_warehouse(MaterialType.RAW, src, links) == src
    assert material_warehouse(MaterialType.PACKAGING, src, {}) == src
