"""M48.S01.T023: remediation of the T015 independent M36 audit, authorization, AI and migrations.

F3 evidence tables archived (not dropped) by downgrades; F4 shared approval guard, company scope and daily cap for ABM
group campaigns and design single-sends; F5 contact and add-in writes use edit scope; F6 transcript redaction before
the AI provider and insight purge with the source; F9 landing convert 422; F10 production proxy warning.
DB tests run only with M48_DB=1 against a disposable PostgreSQL database (never the dev DB).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select, text

from app.core.config import settings
from app.core.deploy_warnings import proxy_warning

DB = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="needs M48_DB=1 and a disposable PostgreSQL DATABASE_URL")
POVU_DOC = {"theme": {"brand_color": "#1D4ED8"}, "blocks": [
    {"type": "heading", "text": "Hi {first_name|there}", "level": 1},
    {"type": "text", "text": "POVU AllClean 1 L is back in stock."},
    {"type": "footer", "text": "POVU synthetic"}]}


def _user(uid, username, *codes, scopes=()):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uid, username=username, email=f"{username}@povu-demo.test", full_name=username,
                           is_superuser=False, access_scopes=list(scopes),
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


def _scope(company_id, edit=True):
    return SimpleNamespace(scope_type="company", scope_id=str(company_id), is_active=True, can_view=True, can_edit=edit)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


async def _safe_db(db):
    from app.db.session import engine
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.port != 5432
    from app.models.m48_crm_send_approval import CRMSendApproval
    async with engine.begin() as c:
        await c.run_sync(lambda s: CRMSendApproval.__table__.create(s, checkfirst=True))


# ── F10 / F9: no database ───────────────────────────────────────────────────────

def test_f10_proxy_warning():
    assert proxy_warning("development", None) is None
    assert proxy_warning("production", "10.0.0.5") is None
    assert "not set" in proxy_warning("production", None)
    assert "not set" in proxy_warning("production", "  ")
    assert "forge" in proxy_warning("production", "*")
    assert "forge" in proxy_warning("production", "10.0.0.5, *")


@pytest.mark.asyncio
async def test_f9_landing_missing_field_is_422(monkeypatch):
    from app.api.v1.endpoints import crm_landing_public as lpapi
    from app.services import crm_lead_capture_service as capture
    page = SimpleNamespace(id=uuid4(), slug="povu-allclean", lead_form_id=uuid4())
    form = SimpleNamespace(active_flag=True, success_message=None)

    async def _resolve(db, slug, visitor):
        return page, None

    async def _seen(db, p, v):
        return None

    async def _submit(*a, **k):
        raise capture.MissingField("Please fill in: company")

    class _DB:
        async def get(self, model, key):
            return form

    monkeypatch.setattr(lpapi, "_resolve", _resolve)
    monkeypatch.setattr(lpapi.lp, "seen_variant", _seen)
    monkeypatch.setattr(lpapi.capture, "submit", _submit)
    body = lpapi.ConvertIn(visitor="v" * 20, lead=capture.LeadSubmission(contact_person_name="Asha Buyer", contact_email="asha@example.com"))
    with pytest.raises(HTTPException) as e:
        await lpapi.convert("povu-allclean", body, SimpleNamespace(client=None), _DB())
    assert e.value.status_code == 422 and "company" in e.value.detail


# ── F3: archive instead of drop ───────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_f3_archive_keeps_rows_and_frees_names():
    from app.db.downgrade_archive import archive_tables
    from app.db.session import engine
    s = uuid4().hex[:8]
    parent, child = f"t023p_{s}", f"t023c_{s}"
    async with engine.begin() as c:
        await c.execute(text(f"CREATE TABLE {parent} (id int PRIMARY KEY)"))
        await c.execute(text(f"CREATE TABLE {child} (id int PRIMARY KEY, p int REFERENCES {parent}(id), email text UNIQUE)"))
        await c.execute(text(f"CREATE INDEX ix_{child}_p ON {child} (p)"))
        await c.execute(text(f"INSERT INTO {parent} VALUES (1)"))
        await c.execute(text(f"INSERT INTO {child} VALUES (1, 1, 'keep@povu-demo.test')"))
        names = await c.run_sync(lambda conn: archive_tables(conn, [child, "no_such_table_t023"], "0099"))
        assert names == [f"{child}_archived_0099"]
        assert (await c.execute(text(f"SELECT email FROM {child}_archived_0099"))).scalar_one() == "keep@povu-demo.test"
        # the original names are free again: the forward migration can recreate table, PK, unique and index
        await c.execute(text(f"CREATE TABLE {child} (id int PRIMARY KEY, p int REFERENCES {parent}(id), email text UNIQUE)"))
        await c.execute(text(f"CREATE INDEX ix_{child}_p ON {child} (p)"))
        # the archive has no outgoing foreign key, so it never blocks dropping the parent
        fks = (await c.execute(text("SELECT count(*) FROM pg_constraint WHERE conrelid = CAST(:t AS regclass) AND contype = 'f'"),
                               {"t": f"{child}_archived_0099"})).scalar_one()
        assert fks == 0
        again = await c.run_sync(lambda conn: archive_tables(conn, [child], "0099"))
        assert again == [f"{child}_archived_0099_2"]
        for t in (f"{child}_archived_0099", f"{child}_archived_0099_2", parent):
            await c.execute(text(f"DROP TABLE {t}"))


# ── F4: approval guard, company scope and cap ─────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_f4_design_single_send_guard(monkeypatch):
    from app.api.v1.endpoints import email_designs as api
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMOutboundMessage, EmailDesign
    from app.services import email_design_service as eds
    from app.services import marketing_send_guard as guard
    from app.models.user import User
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        await _safe_db(db)
        u1 = User(email=f"ed1-{s}@povu-demo.test", username=f"ed1{s}", full_name="Editor One", hashed_password="x")
        u2 = User(email=f"ed2-{s}@povu-demo.test", username=f"ed2{s}", full_name="Editor Two", hashed_password="x")
        db.add_all([u1, u2])
        await db.flush()
        d = EmailDesign(family_id=uuid4(), version=1, name=f"POVU restock {s}", document=eds.validate(POVU_DOC)[0], status="PUBLISHED",
                        created_by_id=u1.id)
        db.add(d)
        await db.commit()
        ed1, ed2 = _user(u1.id, u1.username, "marketing.edit"), _user(u2.id, u2.username, "marketing.edit")
        did = d.id
        body = lambda **k: api.SingleSendIn(to_email=f"buyer-{s}@povu-demo.test", subject="POVU AllClean 1 L restock", **k)

        monkeypatch.setattr(settings, "MARKETING_EMAIL_APPROVAL_REQUIRED", True)
        with pytest.raises(HTTPException) as e:                       # no approval → refused, nothing queued
            await api.single_send(did, body(), db, ed1)
        assert e.value.status_code == 409
        req = await api.request_send_approval(did, body(), db, ed1)
        aid = uuid.UUID(req["id"])
        assert req["status"] == "PENDING" and req["payload"]["to_email"] == f"buyer-{s}@povu-demo.test"
        assert len(req["content_hash"]) == 64                          # shown to the approver in the UI
        pol = await api.send_policy(db, ed1)
        assert pol["approval_required"] is True and pol["used_today"] == 0 and pol["daily_cap"] >= 1
        with pytest.raises(HTTPException) as e:                       # requester cannot approve their own send
            await api.decide_send_approval(aid, "approve", db, ed1)
        assert e.value.status_code == 403
        with pytest.raises(HTTPException) as e:                       # still pending → not usable
            await api.single_send(did, body(approval_id=aid), db, ed1)
        assert e.value.status_code == 409
        assert (await api.decide_send_approval(aid, "approve", db, ed2))["status"] == "APPROVED"
        with pytest.raises(HTTPException) as e:                       # approval is for this exact content only
            await api.single_send(did, api.SingleSendIn(to_email=f"other-{s}@povu-demo.test", subject="POVU AllClean 1 L restock",
                                                        approval_id=aid), db, ed1)
        assert e.value.status_code == 409
        out = await api.single_send(did, body(approval_id=aid), db, ed1)
        assert out["status"] in ("QUEUED", "SUPPRESSED")
        with pytest.raises(HTTPException) as e:                       # used once
            await api.single_send(did, body(approval_id=aid), db, ed1)
        assert e.value.status_code == 409
        assert (await api.list_send_approvals("USED", db, ed2))[0]["id"] == str(aid)

        monkeypatch.setattr(settings, "MARKETING_EMAIL_APPROVAL_REQUIRED", False)
        monkeypatch.setattr(guard, "daily_cap", lambda: 2)   # MARKETING_DIRECT_SEND_DAILY_CAP (not yet in config)
        await api.single_send(did, body(), db, ed1)                   # 2 of 2
        with pytest.raises(HTTPException) as e:
            await api.single_send(did, body(), db, ed1)
        assert e.value.status_code == 429
        await api.single_send(did, body(), db, ed2)                   # the cap is per editor
        n = (await db.execute(select(func.count()).select_from(CRMOutboundMessage).where(
            CRMOutboundMessage.dedupe_key.like(f"single:{did}:%")))).scalar_one()
        assert n == 3


@DB
@pytest.mark.asyncio
async def test_f4_abm_company_scope_cap_and_approval(monkeypatch):
    from app.api.v1.endpoints import crm_abm as api
    from app.db.session import AsyncSessionLocal
    from app.models.company import Company
    from app.models.crm import CRMContactConsent, CRMOutboundMessage
    from app.services import marketing_send_guard as guard
    from app.models.sales import Customer, CustomerChannel
    from app.models.user import User
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        await _safe_db(db)
        ca = Company(name=f"POVU Kenya {s}", short_code=f"KA{s[:6].upper()}", country="Kenya", base_currency="KES")
        cb = Company(name=f"POVU Uganda {s}", short_code=f"UG{s[:6].upper()}", country="Uganda", base_currency="UGX")
        u1 = User(email=f"abm1-{s}@povu-demo.test", username=f"abm1{s}", full_name="Key Accounts", hashed_password="x")
        u2 = User(email=f"abm2-{s}@povu-demo.test", username=f"abm2{s}", full_name="Approver", hashed_password="x")
        db.add_all([ca, cb, u1, u2])
        await db.flush()
        ka = Customer(code=f"KA-{s}", name=f"Nairobi Chain {s}", channel=CustomerChannel.DISTRIBUTOR, currency="KES", company_id=ca.id)
        ug = Customer(code=f"UG-{s}", name=f"Kampala Chain {s}", channel=CustomerChannel.DISTRIBUTOR, currency="UGX", company_id=cb.id)
        db.add_all([ka, ug])
        await db.commit()
        mkt = _user(u1.id, u1.username, "marketing.edit")
        approver = _user(u2.id, u2.username, "marketing.edit")
        scoped_b = _user(u1.id, u1.username, "marketing.edit", scopes=[_scope(cb.id)])
        ca_id, cb_id, ka_id, ug_id = ca.id, cb.id, ka.id, ug.id

        gid = uuid.UUID((await api.create_group(api.GroupIn(name=f"Key chains {s}"), db, mkt))["id"])
        for cust in (ka_id, ug_id):
            await api.add_member(gid, api.MemberIn(customer_id=cust, tier=1), db, mkt)
        await api.add_contact(ka_id, api.ContactIn(full_name="Grace Buyer", email=f"grace-{s}@example.com", committee_role="BUYER"), db, mkt)
        await api.add_contact(ka_id, api.ContactIn(full_name="David Director", email=f"david-{s}@example.com", committee_role="DECISION_MAKER"), db, mkt)
        await api.add_contact(ug_id, api.ContactIn(full_name="Ruth Buyer", email=f"ruth-{s}@example.com", committee_role="BUYER"), db, mkt)
        db.add(CRMContactConsent(email=f"grace-{s}@example.com", status="SUBSCRIBED", source="test", updated_at=datetime.now(timezone.utc)))
        await db.commit()
        camp = lambda **k: api.CampaignIn(subject="New POVU range for {company_name}", body="Hello {contact_name}, POVU AllClean 1 L.", **k)

        with pytest.raises(HTTPException) as e:                       # mixed companies need an explicit company
            await api.group_campaign(gid, camp(), db, mkt)
        assert e.value.status_code == 422
        with pytest.raises(HTTPException) as e:                       # scoped to Uganda only → not Kenya
            await api.group_campaign(gid, camp(company_id=ca_id), db, scoped_b)
        assert e.value.status_code == 403
        with pytest.raises(HTTPException) as e:
            await api.group_campaign(gid, camp(company_id=uuid4()), db, mkt)
        assert e.value.status_code == 422

        monkeypatch.setattr(guard, "daily_cap", lambda: 1)   # MARKETING_DIRECT_SEND_DAILY_CAP (not yet in config)
        with pytest.raises(HTTPException) as e:                       # 2 Kenya recipients > cap 1, nothing queued
            await api.group_campaign(gid, camp(company_id=ca_id), db, mkt)
        assert e.value.status_code == 429
        monkeypatch.setattr(guard, "daily_cap", lambda: 200)   # MARKETING_DIRECT_SEND_DAILY_CAP (not yet in config)

        monkeypatch.setattr(settings, "MARKETING_EMAIL_APPROVAL_REQUIRED", True)
        with pytest.raises(HTTPException) as e:
            await api.group_campaign(gid, camp(company_id=ca_id), db, mkt)
        assert e.value.status_code == 409
        req = await api.request_campaign_approval(gid, camp(company_id=ca_id), db, mkt)
        aid = uuid.UUID(req["id"])
        with pytest.raises(HTTPException) as e:
            await api.decide_campaign_approval(aid, "approve", db, mkt)
        assert e.value.status_code == 403
        assert [r["id"] for r in await api.list_campaign_approvals("PENDING", db, approver)] == [str(aid)]
        await api.decide_campaign_approval(aid, "approve", db, approver)
        with pytest.raises(HTTPException) as e:                       # the approval names Kenya, not Uganda
            await api.group_campaign(gid, camp(company_id=cb_id, approval_id=aid), db, mkt)
        assert e.value.status_code == 409
        out = await api.group_campaign(gid, camp(company_id=ca_id, approval_id=aid), db, mkt)
        assert out == {"queued": 1, "suppressed": 1}
        msgs = (await db.execute(select(CRMOutboundMessage).where(CRMOutboundMessage.dedupe_key.like("abm:%"),
                                                                  CRMOutboundMessage.to_email.like(f"%-{s}@example.com")))).scalars().all()
        assert {m.customer_id for m in msgs} == {ka_id}               # Uganda's committee was not mailed
        with pytest.raises(HTTPException) as e:
            await api.group_campaign(gid, camp(company_id=ca_id, approval_id=aid), db, mkt)
        assert e.value.status_code == 409


# ── F5: edit scope for contact and add-in writes ──────────────────────────────

@DB
@pytest.mark.asyncio
async def test_f5_contact_and_addin_writes_need_edit_scope():
    from app.api.v1.endpoints import crm_addin, crm_contacts as api
    from app.db.session import AsyncSessionLocal
    from app.models.company import Company
    from app.models.crm import CRMContact, CRMContactAssociation, CRMRecord
    from app.models.user import User
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        await _safe_db(db)
        ca = Company(name=f"POVU Kenya {s}", short_code=f"KB{s[:6].upper()}", country="Kenya", base_currency="KES")
        cb = Company(name=f"POVU Tanzania {s}", short_code=f"TZ{s[:6].upper()}", country="Tanzania", base_currency="TZS")
        owner = User(email=f"own-{s}@povu-demo.test", username=f"own{s}", full_name="Owner", hashed_password="x")
        rep = User(email=f"rep-{s}@povu-demo.test", username=f"rep{s}", full_name="Rep", hashed_password="x")
        db.add_all([ca, cb, owner, rep])
        await db.flush()
        rec_a = CRMRecord(company_name=f"Nairobi Outlet {s}", company_id=ca.id, assigned_rep_id=str(owner.id))
        rec_b = CRMRecord(company_name=f"Dar Outlet {s}", company_id=cb.id, assigned_rep_id=str(owner.id))
        c1 = CRMContact(full_name="Asha Buyer", email=f"asha-{s}@povu-demo.test", owner_user_id=owner.id, source="manual")
        c2 = CRMContact(full_name="Juma Buyer", email=f"juma-{s}@povu-demo.test", owner_user_id=owner.id, source="manual")
        db.add_all([rec_a, rec_b, c1, c2])
        await db.flush()
        db.add_all([CRMContactAssociation(contact_id=c1.id, object_type="crm_record", object_id=rec_b.id, label="primary", created_at=datetime.now(timezone.utc)),
                    CRMContactAssociation(contact_id=c2.id, object_type="crm_record", object_id=rec_a.id, label="primary", created_at=datetime.now(timezone.utc))])
        await db.commit()
        # the audit case: company-wide view plus edit only in Kenya
        viewer_editor = _user(rep.id, rep.username, "crm.view_all", "crm.edit_own_scope", scopes=[_scope(ca.id)])
        editor_all = _user(rep.id, rep.username, "crm.edit_all")
        c1_id, c2_id, rb_id, ra_id = c1.id, c2.id, rec_b.id, rec_a.id

        assert (await api.get_contact(c1_id, db, viewer_editor))["full_name"] == "Asha Buyer"   # still visible
        for call in (lambda: api.update_contact(c1_id, api.ContactIn(full_name="Changed"), db, viewer_editor),
                     lambda: api.set_lifecycle(c1_id, api.LifecycleIn(stage="MQL"), db, viewer_editor),
                     lambda: api.set_property(c1_id, api.PropertyIn(key="pack_size", value="1 L"), db, viewer_editor),
                     lambda: api.add_association(c1_id, api.AssocIn(object_type="customer", object_id=uuid4()), db, viewer_editor)):
            with pytest.raises(HTTPException) as e:
                await call()
            assert e.value.status_code == 403
        # a contact linked to a Kenya deal is in the caller's edit scope
        assert (await api.update_contact(c2_id, api.ContactIn(full_name="Juma Buyer K"), db, viewer_editor))["full_name"] == "Juma Buyer K"
        assert (await api.update_contact(c1_id, api.ContactIn(full_name="Asha Buyer E"), db, editor_all))["full_name"] == "Asha Buyer E"

        with pytest.raises(HTTPException) as e:                       # add-in note on the Tanzania deal
            await crm_addin.note(crm_addin.NoteIn(crm_record_id=rb_id, text="POVU Hand Wash Powder 1 kg follow-up"), db,
                                 (viewer_editor, None))
        assert e.value.status_code == 403
        ok = await crm_addin.note(crm_addin.NoteIn(crm_record_id=ra_id, text="POVU AllClean 1 L reorder"), db, (viewer_editor, None))
        assert ok["activity_id"]


# ── F6: redaction before AI, quotes redacted, purge with source ───────────────

@DB
@pytest.mark.asyncio
async def test_f6_redaction_and_purge(monkeypatch):
    from app.api.v1.endpoints import conversation_intel as api
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMChatMessage, CRMChatSession, CRMConversationInsight
    from app.models.user import User
    from app.models.voip import CallLog
    from app.services import ai_provider
    from app.services import conversation_intel_service as ci
    s = uuid4().hex[:8]
    sent: list[str] = []

    class FakeProvider:
        async def generate_structured_output(self, prompt, system=None, schema_hint=None):
            sent.append(prompt)
            return {"findings": [{"kind": "next_step", "label": "call", "quote": "Call me on [phone] tomorrow."}]}, {}

    monkeypatch.setattr(ai_provider, "get_ai_provider", lambda: FakeProvider())
    monkeypatch.setattr(settings, "CONVERSATION_INTELLIGENCE_ENABLED", True)
    transcript = (f"Customer: The POVU AllClean price is too expensive, write to me at asha-{s}@povu-demo.test. "
                  "Customer: Call me on 0712 345 678 tomorrow. Agent: I will send the price list.")
    async with AsyncSessionLocal() as db:
        await _safe_db(db)
        mgr_u = User(email=f"mgr-{s}@povu-demo.test", username=f"mgr{s}", full_name="Manager", hashed_password="x")
        db.add(mgr_u)
        await db.flush()
        call = CallLog(call_ref=f"CALL-T023-{s}", phone_number="+254700000009", agent_id=mgr_u.id, recording_consent=True,
                       transcript=transcript)
        now = datetime.now(timezone.utc)
        chat = CRMChatSession(token_hash=uuid4().hex, status="CLOSED", created_at=now, last_message_at=now)
        db.add_all([call, chat])
        await db.flush()
        db.add_all([CRMChatMessage(session_id=chat.id, sender="VISITOR", body="My number is +254 712 345 678, the POVU pouch leaked.", created_at=now),
                    CRMChatMessage(session_id=chat.id, sender="AGENT", body="Sorry, we will replace it tomorrow.", created_at=now)])
        await db.commit()
        mgr = _user(mgr_u.id, mgr_u.username, "crm.view_all", "crm.edit_all")
        call_id, chat_id = call.id, chat.id

        out = await api.analyse("call", call_id, db, mgr)
        assert sent and "0712" not in sent[0] and "@povu-demo.test" not in sent[0] and "[phone]" in sent[0] and "[email]" in sent[0]
        quotes = " ".join(f["quote"] for f in out["findings"])
        assert "0712" not in quotes and "@povu-demo.test" not in quotes
        assert out["engine"] == "rules+ai"
        chat_out = await api.analyse("chat", chat_id, db, mgr)
        assert "712 345" not in " ".join(f["quote"] for f in chat_out["findings"])

        # the source goes (chat retention purge deletes the session; call purge clears the transcript) → insights go
        await db.execute(CRMChatSession.__table__.delete().where(CRMChatSession.id == chat_id))
        await db.commit()
        assert await ci.purge_orphaned(db) >= 1
        await db.commit()
        left = (await db.execute(select(CRMConversationInsight.source_id).where(
            CRMConversationInsight.source_id.in_([call_id, chat_id])))).scalars().all()
        assert left == [call_id]                                       # the call still has its transcript
        await db.execute(CallLog.__table__.update().where(CallLog.id == call_id).values(transcript=None))
        await ci.purge_orphaned(db)
        await db.commit()
        assert (await db.execute(select(func.count()).select_from(CRMConversationInsight).where(
            CRMConversationInsight.source_id == call_id))).scalar_one() == 0
