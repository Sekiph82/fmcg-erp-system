"""M38.S04.T001 employee self-service bound to the signed-in user, on disposable PostgreSQL through the real app:
auto-provisioning from Employee.user_id, isolation between employees, leave, server-time clock in/out, requests,
own payslips from approved runs only, expense claims filed for the signed-in employee."""
from __future__ import annotations

import os
import re
import uuid
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.deps import get_current_user
from app.db.session import AsyncSessionLocal, engine
from app.models.hr import Employee
from app.models.payroll_ke import KePayrollLine, PayrollRun, PayrollRunStatus, Payslip
from app.models.user import User

TASK_DB_ENV = "M38_S04_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M38_S04_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m38_s04_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")
E = "/api/v1/ess-self"


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _as(u, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".")[1], is_active=True) for c in codes]
    return SimpleNamespace(id=u.id, username=u.username, email=u.email, full_name=u.full_name, is_superuser=False, is_active=True,
                           access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_ess_is_the_signed_in_employees_own():
    from app.main import app
    from app.services import ess_service

    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        users = {k: User(email=f"{k}-{s}@example.com", username=f"{k}{s}", full_name=k.title(), hashed_password="x")
                 for k in ("amina", "brian", "nolink")}
        db.add_all(users.values())
        await db.flush()
        emps = {k: Employee(employee_code=f"{k[:3].upper()}-{s}", full_name=f"{k.title()} {s}", department="Production",
                            role="Operator", hire_date=date(2024, 1, 15), user_id=users[k].id, email=f"{k}-{s}@example.com")
                for k in ("amina", "brian")}
        db.add_all(emps.values())
        await db.flush()
        await ess_service.seed_leave_types(db)
        for k, status in (("amina", PayrollRunStatus.APPROVED), ("amina-draft", PayrollRunStatus.DRAFT)):
            run = PayrollRun(run_no=f"R-{k}-{s}", period_month=10 if status == PayrollRunStatus.APPROVED else 11,
                             period_year=2091 + len(k) % 3, period_start=date(2026, 10, 1), period_end=date(2026, 10, 31), status=status)
            db.add(run)
            await db.flush()
            for who in ("amina", "brian"):
                line = KePayrollLine(run_id=run.id, employee_id=emps[who].id, basic_salary=Decimal("50000"), gross_salary=Decimal("50000"),
                                     taxable_income=Decimal("47000"), paye_amount=Decimal("7000"), total_deductions=Decimal("12000"),
                                     net_salary=Decimal("38000") if who == "amina" else Decimal("99999"))
                db.add(line)
                await db.flush()
                db.add(Payslip(payroll_line_id=line.id, employee_id=emps[who].id, run_id=run.id, issue_date=date.today()))
        await db.commit()
        U = {k: _as(u) for k, u in users.items()}
        U["hr"] = _as(users["nolink"], "hr.edit")

    def who(u):
        app.dependency_overrides[get_current_user] = lambda: u

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            who(U["nolink"])
            assert (await c.get(f"{E}/me")).status_code == 404                      # not linked to an employee
            who(U["amina"])
            me = (await c.get(f"{E}/me")).json()
            assert me["employee"]["name"] == f"Amina {s}" and me["profile"]["full_name"] == f"Amina {s}"   # auto-provisioned
            leave = (await c.get(f"{E}/leave")).json()
            annual = next(t for t in leave["types"] if "annual" in t["type_name"].lower())
            start = date.today() + timedelta(days=30)
            r = await c.post(f"{E}/leave", json={"leave_type_id": annual["leave_type_id"], "start_date": start.isoformat(),
                                                 "end_date": (start + timedelta(days=1)).isoformat(), "reason": "family"})
            assert r.status_code == 201, r.text
            leave_id = r.json()["leave_request_id"]
            assert (await c.post(f"{E}/attendance/clock", json={"action": "out"})).status_code == 409
            assert (await c.post(f"{E}/attendance/clock", json={"action": "in"})).status_code == 200
            assert (await c.post(f"{E}/attendance/clock", json={"action": "in"})).status_code == 409
            assert (await c.post(f"{E}/attendance/clock", json={"action": "out"})).status_code == 200
            req = await c.post(f"{E}/requests", json={"request_type": "certificate", "subject": "Employment letter"})
            assert req.status_code == 201, req.text
            slips = (await c.get(f"{E}/payslips")).json()
            assert [x["net"] for x in slips] == [38000.0]                            # own, approved run only
            claim = await c.post("/api/v1/expenses/claims", json={"claim_date": date.today().isoformat(),
                                                                  "employee_id": str(emps["brian"].id)})
            assert claim.status_code == 200 and claim.json()["employee_id"] == str(emps["amina"].id)  # cannot file for Brian

            who(U["brian"])
            assert (await c.get(f"{E}/leave")).json()["requests"] == []             # never Amina's
            assert (await c.post(f"{E}/leave/{leave_id}/cancel")).status_code == 404
            assert [x["net"] for x in (await c.get(f"{E}/payslips")).json()] == [99999.0]
            assert (await c.get(f"{E}/requests")).json() == []
            who(U["hr"])
            claim = await c.post("/api/v1/expenses/claims", json={"claim_date": date.today().isoformat(), "employee_id": str(emps["brian"].id)})
            assert claim.json()["employee_id"] == str(emps["brian"].id)            # HR may file for an employee
            who(U["amina"])
            assert (await c.post(f"{E}/leave/{leave_id}/cancel")).status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)
