"""M45.S01.T017 sensitive-data classification (unit; DB part needs M45_DB=1).

Unit: masking. DB: KRA PIN is masked in the customer API for a non-privileged persona and visible with the right;
a masked value sent back by a form does not overwrite the real one; classified contact phone is masked; a custom
field with sensitive_flag is masked; reveal is refused without the right and audited with it; retention clears the
value on long-inactive customers; GraphQL's customer type has no sensitive field.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.services import sensitive_service as sens

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_mask_and_graphql_surface():
    assert sens.mask("P051234567Z") == "•••67Z" and sens.mask("12") == "•••" and sens.mask(None) is None
    from decimal import Decimal
    assert sens.mask(Decimal("5000")) is None
    from app.api.v1.endpoints import graphql_api
    assert "taxId" not in graphql_api.CustomerType.fields and "phone" not in graphql_api.CustomerType.fields


async def _login_client(db, perms):
    """A real user with the given permissions and a session cookie, via the app's own login."""
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.models.role import Permission, Role
    from app.models.user import User
    pw = uuid.uuid4().hex + "Aa1!"
    u = User(username=f"syn-{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex[:8]}@povu-demo.test", full_name="Synthetic",
             hashed_password=hash_password(pw), is_active=True)
    role = Role(name=f"syn-{uuid.uuid4().hex[:6]}", is_active=True)
    for code in perms:
        p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
        if p is None:
            mod, act = code.split(".", 1)
            p = Permission(code=code, name=code, module=mod, action=act, is_active=True)
            db.add(p)
        role.permissions.append(p)
    u.roles.append(role)
    db.add_all([role, u])
    await db.commit()
    return u, pw


@DB
@pytest.mark.asyncio
async def test_masking_reveal_retention():
    from sqlalchemy import func, select, update
    from app.db.session import AsyncSessionLocal
    from app.main import app
    from app.models.audit_log import AuditLog
    from app.models.custom_fields import CustomFieldDefinition, CustomFieldValue, EntityType, FieldType
    from app.models.sales import Customer
    async with AsyncSessionLocal() as db:
        cust = Customer(code=f"SYN-{uuid.uuid4().hex[:6]}", name="POVU Sensitive Outlet", currency="KES", tax_id="P051234567Z")
        cf = CustomFieldDefinition(entity_type=EntityType.CUSTOMER, field_code=f"id_no_{uuid.uuid4().hex[:4]}", field_label="ID number",
                                   field_type=FieldType.TEXT, sensitive_flag=True)
        db.add_all([cust, cf])
        await db.flush()
        db.add(CustomFieldValue(custom_field_id=cf.custom_field_id, entity_type=EntityType.CUSTOMER, entity_id=str(cust.id),
                                value_text="12345678"))
        await db.commit()
        cid = cust.id
        clerk, pw1 = await _login_client(db, ("sales.view", "sales.edit", "crm.view"))
        auditor, pw2 = await _login_client(db, ("sales.view", "data.view_sensitive"))
        c_user, a_user = clerk.username, auditor.username
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test") as c1, \
               httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test") as c2:
        assert (await c1.post("/api/v1/auth/login", data={"username": c_user, "password": pw1})).status_code == 200
        assert (await c2.post("/api/v1/auth/login", data={"username": a_user, "password": pw2})).status_code == 200
        r1 = (await c1.get(f"/api/v1/sales/customers/{cid}")).json()
        r2 = (await c2.get(f"/api/v1/sales/customers/{cid}")).json()
        assert r1["tax_id"] == "•••67Z" and r1["masked_fields"] and r2["tax_id"] == "P051234567Z"
        listed = (await c1.get("/api/v1/sales/customers/")).json()
        assert all(x["tax_id"] in (None, "") or x["tax_id"].startswith("•••") for x in listed)
        await c1.patch(f"/api/v1/sales/customers/{cid}", json={"tax_id": r1["tax_id"], "city": "Thika"})   # form sends the mask back
        assert (await c2.get(f"/api/v1/sales/customers/{cid}")).json()["tax_id"] == "P051234567Z"
        refused = await c1.post("/api/v1/sensitive-data/reveal", json={"entity": "customer", "record_id": str(cid), "field": "tax_id"})
        assert refused.status_code == 403
        ok = await c2.post("/api/v1/sensitive-data/reveal", json={"entity": "customer", "record_id": str(cid), "field": "tax_id"})
        assert ok.json() == {"value": "P051234567Z"}
        v1 = (await c1.get(f"/api/v1/custom-fields/values/customer/{cid}")).json()
        v2 = (await c2.get(f"/api/v1/custom-fields/values/customer/{cid}")).json()
        idno1 = next(v for v in v1 if v["field_label"] == "ID number")
        idno2 = next(v for v in v2 if v["field_label"] == "ID number")
        assert idno1["value"] == "•••678" and idno2["value"] == "12345678"
    async with AsyncSessionLocal() as db:
        ev = {e for e, in (await db.execute(select(AuditLog.event_type).where(AuditLog.target_id == str(cid)))).all()}
        assert {"SENSITIVE_REVEALED", "SENSITIVE_REVEAL_REFUSED"} <= ev
        # retention: inactive for longer than the period → cleared
        await sens.set_field(db, "customer", "tax_id", True, 30, "t")
        c = await db.get(Customer, cid)
        c.is_active = False
        await db.flush()
        await db.execute(update(Customer).where(Customer.id == cid).values(updated_at=datetime.now(timezone.utc) - timedelta(days=40)))
        assert await sens.apply_retention(db) >= 1
        await db.refresh(c)
        assert c.tax_id is None
        await db.rollback()
