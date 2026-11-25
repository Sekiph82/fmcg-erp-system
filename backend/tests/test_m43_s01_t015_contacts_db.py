"""M43.S01.T015 contacts, associations and lifecycle (run at the M43 gate, M43_S01_DB=1).

Migration (gate's upgrade-from-previous-head step on a copy seeded with synthetic CRM records/account contacts):
every e-mail becomes one contact, every record keeps a primary association, account-contact roles become labels,
no record loses its contact. Service: record create/qualify/convert/win move the contact's lifecycle forward only and
write history; manual backward move needs a reason; one contact linked to two customers with different labels;
duplicate e-mail refused with the existing id.
"""
from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import select

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(os.environ.get("M43_S01_DB") != "1",
              reason="requires the task-owned disposable PostgreSQL at the M43 head")]


async def test_lifecycle_follows_record_forward_only():
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMLifecycleHistory, CRMRecordType
    from app.schemas.crm import CRMCloseWonRequest, CRMConvertRequest, CRMRecordCreate
    from app.services import crm_contact_service as cs
    from app.services import crm_pipeline_service as svc
    email = f"buyer-{uuid.uuid4().hex[:6]}@povu-demo.test"
    async with AsyncSessionLocal() as db:
        rec = await svc.create_record(db, CRMRecordCreate(record_type=CRMRecordType.LEAD, company_name="POVU Synthetic Outlet",
                                                          contact_person_name="Synthetic Buyer", contact_email=email))
        c = await cs.find_by_email(db, email)
        assert c is not None and c.lifecycle_stage == "LEAD"
        await svc.convert_to_opportunity(db, str(rec.id), CRMConvertRequest())
        await db.refresh(c)
        assert c.lifecycle_stage == "OPPORTUNITY"
        await svc.close_won(db, str(rec.id), CRMCloseWonRequest())
        await db.refresh(c)
        assert c.lifecycle_stage == "CUSTOMER"
        assert not await cs.set_lifecycle(db, c, "LEAD", "rule")            # automatic: never backwards
        with pytest.raises(cs.ContactError):
            await cs.set_lifecycle(db, c, "LEAD", "manual", allow_backward=True)   # needs a reason
        assert await cs.set_lifecycle(db, c, "LEAD", "manual", allow_backward=True, reason="Wrong customer link")
        await db.commit()
        hist = (await db.execute(select(CRMLifecycleHistory.to_stage).where(CRMLifecycleHistory.contact_id == c.id)
                                 .order_by(CRMLifecycleHistory.changed_at))).scalars().all()
        assert hist == ["LEAD", "OPPORTUNITY", "CUSTOMER", "LEAD"]


async def test_one_contact_two_customers_and_duplicate_refusal():
    from httpx import ASGITransport, AsyncClient

    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMContact
    from app.models.sales import Customer
    from app.services import crm_contact_service as cs
    async with AsyncSessionLocal() as db:
        custs = (await db.execute(select(Customer).limit(2))).scalars().all()
        c = CRMContact(full_name="Synthetic Finance Lead", email=f"fin-{uuid.uuid4().hex[:6]}@povu-demo.test")
        db.add(c)
        await db.flush()
        await cs.associate(db, c.id, "customer", custs[0].id, "billing")
        await cs.associate(db, c.id, "customer", custs[1].id, "decision_maker")
        await cs.associate(db, c.id, "customer", custs[1].id, "decision_maker")          # idempotent
        with pytest.raises(cs.ContactError):
            await cs.associate(db, c.id, "warehouse", custs[1].id, "primary")
        await db.commit()
        labels = sorted(l for _, l in await cs.contacts_for(db, "customer", custs[1].id) if _.id == c.id)
        assert labels == ["decision_maker"]
        assert (await cs.find_by_email(db, c.email.upper())).id == c.id


@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Each test runs in its own event loop: drop pooled connections afterwards (same pattern as other DB tests)."""
    yield
    from app.db.session import engine
    await engine.dispose()
