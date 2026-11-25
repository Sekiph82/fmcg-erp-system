"""M45.S01.T015 custom objects (unit; DB part needs M45_DB=1).

Unit: type validation and value coercion. DB: define a "freezer" type, create records (required/unique/select
enforced), associate to a customer, list records linked to the customer, report by field, CSV round trip, delete
with association cleanup; per-type roles and company isolation hide records; an agent event is queued on create.
"""
import os
import uuid
from types import SimpleNamespace

import pytest

from app.services import custom_object_service as cos

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
FREEZER = {"key": "freezer", "label": "Freezer", "fields": [
    {"key": "serial", "label": "Serial", "type": "text", "required": True, "unique": True},
    {"key": "model", "label": "Model", "type": "select", "options": ["POVU-100", "POVU-200"]},
    {"key": "litres", "label": "Litres", "type": "number"},
    {"key": "placed_on", "label": "Placed on", "type": "date"}], "display_field": "serial"}


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_validation_and_coercion():
    v = cos.validate_type(dict(FREEZER))
    assert v["display_field"] == "serial" and v["fields"][0]["unique"]
    for bad in ({**FREEZER, "key": "Bad Key"}, {**FREEZER, "fields": [{"key": "x", "type": "blob"}]},
                {**FREEZER, "fields": [{"key": "m", "type": "select"}]}, {**FREEZER, "display_field": "nope"}):
        with pytest.raises(cos.COError):
            cos.validate_type(bad)
    f = {"label": "Litres", "type": "number"}
    assert cos.coerce(f, "120") == 120.0 and cos.coerce({"label": "d", "type": "date"}, "2026-11-26T10:00") == "2026-11-26"
    with pytest.raises(cos.COError):
        cos.coerce({"label": "Model", "type": "select", "options": ["A"]}, "B")


def _user(**kw):
    return SimpleNamespace(id=None, username="admin", email=None, full_name="Admin", is_superuser=kw.get("su", True),
                           roles=kw.get("roles", []), access_scopes=[])


@DB
@pytest.mark.asyncio
async def test_objects_end_to_end():
    from sqlalchemy import func, select
    from app.db.session import AsyncSessionLocal
    from app.models.ai_hub import AIAgent, AIAgentJob, AIAgentVersion
    from app.models.custom_objects import CustomObjectAssociation, CustomObjectType
    from app.models.sales import Customer
    admin = _user()
    key = f"frz{uuid.uuid4().hex[:6]}"
    async with AsyncSessionLocal() as db:
        t = CustomObjectType(**cos.validate_type({**FREEZER, "key": key}), created_by="admin")
        cust = Customer(code=f"SYN-{uuid.uuid4().hex[:6]}", name="POVU Freezer Outlet", currency="KES")
        db.add_all([t, cust])
        await db.flush()
        ag = AIAgent(name="On freezer", run_as_id=None, budgets={}, current_version=1, status="ACTIVE")
        db.add(ag)
        await db.flush()
        db.add(AIAgentVersion(agent_id=ag.id, version=1, status="PUBLISHED", definition={
            "trigger": {"type": "event", "event": f"custom_object.{key}.created"}, "tools": ["kb_search"],
            "steps": [{"id": "s1", "type": "tool", "tool": "kb_search", "args": {"query": "freezer"}}]}))
        await db.flush()
        r1 = await cos.upsert(db, t, {"serial": "FZ-001", "model": "POVU-100", "litres": "120"}, admin)
        assert r1.display == "FZ-001" and r1.data["litres"] == 120.0
        assert (await db.execute(select(func.count()).select_from(AIAgentJob).where(AIAgentJob.agent_id == ag.id))).scalar_one() == 1
        with pytest.raises(cos.COError) as e:
            await cos.upsert(db, t, {"serial": "FZ-001"}, admin)
        assert e.value.status == 409
        with pytest.raises(cos.COError):
            await cos.upsert(db, t, {"model": "POVU-100"}, admin)                  # serial required
        with pytest.raises(cos.COError):
            await cos.upsert(db, t, {"serial": "FZ-9", "colour": "red"}, admin)     # unknown field
        r2 = await cos.upsert(db, t, {"serial": "FZ-002", "model": "POVU-200"}, admin)
        await cos.associate(db, r1, "customer", cust.id, "placed at")
        await cos.associate(db, r1, "customer", cust.id, "placed at")              # idempotent
        with pytest.raises(cos.COError):
            await cos.associate(db, r1, "customer", uuid.uuid4(), "x")
        linked = await cos.records_for(db, "customer", cust.id, admin)
        assert [x["display"] for x in linked] == ["FZ-001"]
        rep = await cos.report(db, t, admin, "model", "litres")
        assert {r["value"]: r["count"] for r in rep} == {"POVU-100": 1, "POVU-200": 1}
        csv_text = cos.export_csv(t, [r1, r2])
        assert "FZ-001" in csv_text and csv_text.startswith("id,serial,model")
        out = await cos.import_csv(db, t, "serial,model\nFZ-003,POVU-100\nFZ-001,POVU-100\nFZ-004,BAD\n", admin)
        assert out["created"] == 1 and len(out["errors"]) == 2
        # roles: a user without the type's role cannot see it
        t.view_roles, t.edit_roles = ["Freezer team"], ["Freezer team"]
        rep_user = _user(su=False, roles=[SimpleNamespace(name="Sales rep", is_active=True, permissions=[], access_scopes=[])])
        assert not cos.can(rep_user, t, False)
        # delete with association cleanup
        await db.delete(r1)
        await db.flush()
        assert (await db.execute(select(func.count()).select_from(CustomObjectAssociation).where(CustomObjectAssociation.target_id == cust.id))).scalar_one() == 0
        await db.rollback()


def test_company_isolation_filter():
    from sqlalchemy import select
    from app.models.custom_objects import CustomObjectRecord
    cid = uuid.uuid4()
    scoped = SimpleNamespace(is_superuser=False, roles=[], access_scopes=[SimpleNamespace(
        scope_type="company", scope_id=str(cid), scope_name="A", is_active=True, can_view=True, can_create=True, can_edit=True,
        can_delete=True, can_approve=True, can_export=True)])
    assert cos.companies(scoped) == {str(cid)}
    sql = str(cos.visible(select(CustomObjectRecord), scoped).compile(compile_kwargs={"literal_binds": True}))
    assert "company_id IS NULL" in sql and str(cid).replace("-", "") in sql.replace("-", "")
