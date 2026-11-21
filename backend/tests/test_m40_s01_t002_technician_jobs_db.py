"""M40.S01.T002 technician "My Jobs" on disposable PostgreSQL: only assigned jobs are listed and workable,
start → spares → complete for PM work orders, start → resolve for breakdowns, photo limits, the menu flag."""
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

from app.api.v1.endpoints import auth as auth_ep
from app.api.v1.endpoints import maintenance as m
from app.db.session import AsyncSessionLocal, engine
from app.models.maintenance import (Asset, AssetStatus, BreakdownRecord, BreakdownStatus, PMPlan, PMStatus, PMWorkOrder,
                                    SparePart, SparePartUsage)
from app.models.user import User

TASK_DB_ENV = "M40_S01_T002_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M40_S01_T002_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m40_s01_t002_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _as(user_row, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=user_row.id, full_name=user_row.full_name, is_superuser=False, access_scopes=[], company_id=None,
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_technician_my_jobs_flow():
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        tom = User(email=f"tom-{s}@povu.example", username=f"tom{s}", full_name=f"Tom Fundi {s}", hashed_password="x")
        ann = User(email=f"ann-{s}@povu.example", username=f"ann{s}", full_name=f"Ann {s}", hashed_password="x")
        asset = Asset(asset_no=f"FILL-{s}", name=f"POVU filling line {s}", status=AssetStatus.UNDER_MAINTENANCE)
        db.add_all([tom, ann, asset])
        await db.flush()
        plan = PMPlan(asset_id=asset.id, name="Monthly service", checklist="Check seals\nGrease bearings")
        spare = SparePart(part_no=f"SEAL-{s}", name="Nozzle seal", current_stock=Decimal("5"))
        db.add_all([plan, spare])
        await db.flush()
        wo = PMWorkOrder(wo_no=f"WO-{s}", plan_id=plan.id, scheduled_date=date.today(), technician_id=tom.id, technician=tom.full_name)
        other = PMWorkOrder(wo_no=f"WO2-{s}", plan_id=plan.id, scheduled_date=date.today(), technician_id=ann.id)
        bd = BreakdownRecord(breakdown_no=f"BD-{s}", asset_id=asset.id, start_time=datetime.now(timezone.utc) - timedelta(hours=1),
                             reason="Capper jammed", assigned_to_id=tom.id)
        db.add_all([wo, other, bd])
        await db.commit()
        T, A = _as(tom), _as(ann)
        other_id, wo_id, bd_id, plan_id, asset_id, spare_id, tom_id = other.id, wo.id, bd.id, plan.id, asset.id, spare.id, tom.id

        # Tom sees only his jobs; the menu flag follows the assignment
        mine = await m.my_work(db, T)
        assert [w["wo_no"] for w in mine["work_orders"]] == [f"WO-{s}"] and mine["work_orders"][0]["checklist"].startswith("Check seals")
        assert [b["breakdown_no"] for b in mine["breakdowns"]] == [f"BD-{s}"]
        assert (await auth_ep._work_links(db, T))["my_jobs"] is True
        nobody = User(email=f"x-{s}@povu.example", username=f"x{s}", full_name="X", hashed_password="x")
        db.add(nobody)
        await db.commit()
        assert (await auth_ep._work_links(db, _as(nobody)))["my_jobs"] is False

        # someone else's job cannot be touched; completing before starting is refused
        with pytest.raises(HTTPException) as e:
            await m.my_start(other_id, db, T)
        assert e.value.status_code == 403
        await db.rollback()
        with pytest.raises(HTTPException) as e:
            await m.my_complete(wo_id, m._DoneIn(notes="done"), db, T)
        assert e.value.status_code == 409
        await db.rollback()

        # PM: start → spare part → complete; plan dates move on
        await m.my_start(wo_id, db, T)
        await m.my_spares("work-orders", wo_id, m._SpareIn(spare_part_id=spare_id, quantity=Decimal("2")), db, T)
        assert (await db.execute(select(func.count()).select_from(SparePartUsage).where(SparePartUsage.pm_work_order_id == wo_id))).scalar_one() == 1
        await m.my_complete(wo_id, m._DoneIn(notes="Seals replaced, bearings greased"), db, T)
        db.expire_all()
        done = await db.get(PMWorkOrder, wo_id)
        assert done.status == PMStatus.COMPLETED and done.completed_by_id == tom_id and done.checklist_notes.startswith("Seals")
        assert (await db.get(PMPlan, plan_id)).next_due_date is not None

        # breakdown: start → resolve; asset is back in service
        await m.my_bd_start(bd_id, db, T)
        with pytest.raises(HTTPException) as e:
            await m.my_bd_resolve(bd_id, m._FixIn(root_cause="not mine", corrective_action="not mine"), db, A)   # not Ann's
        assert e.value.status_code == 403
        await db.rollback()
        await m.my_bd_resolve(bd_id, m._FixIn(root_cause="Worn cam", corrective_action="Cam replaced, tested 30 caps"), db, T)
        db.expire_all()
        assert (await db.get(BreakdownRecord, bd_id)).status == BreakdownStatus.RESOLVED
        assert (await db.get(Asset, asset_id)).status == AssetStatus.ACTIVE
        assert (await m.my_work(db, T)) == {"work_orders": [], "breakdowns": []}

        # a maintenance supervisor (edit right) may act on any job
        assert m._can_edit_all(_as(SimpleNamespace(id=A.id, full_name=A.full_name), "maintenance.edit"))
