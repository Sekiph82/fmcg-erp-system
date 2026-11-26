"""M47.S01.T009 sales depth (unit + DB; the DB part needs M46_DB=1 and the T009 tables created).

Task calendar sync against the local provider simulator; 1-to-1 video links (expiry, revocation, view de-dupe, only
the link's own media); meeting recap (verbatim quotes, tasks on approval) and stored-facts brief; quote draft from a
deal (re-order, price book, DRAFT only); contract import (dry run, per-row errors, PDFs, renewals notice once);
trained deal-win model (cold start label, real holdout metrics). Synthetic POVU data only.
"""
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

DB = pytest.mark.skipif(os.environ.get("M46_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
PW = uuid.uuid4().hex + "Aa1!"
WEBM = b"\x1aE\xdf\xa3" + b"\x00" * 200
SIM = "http://127.0.0.1:8765"


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M46_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


# ── unit ──────────────────────────────────────────────────────────────────────

def test_recap_rules_quote_the_transcript():
    from app.services import meeting_service as svc
    t = ("Amina: We agreed on POVU AllClean 1 L for Duka Moja. Juma: I will send the price list tomorrow.\n"
         "Amina: Thanks. Juma: I will call the depot in 5 days.")
    r = svc.recap_rules(t)
    assert [d["quote"] for d in r["decisions"]] == ["We agreed on POVU AllClean 1 L for Duka Moja."]
    assert [(a["quote"], a["owner"], a["due_in_days"]) for a in r["action_items"]] == [
        ("I will send the price list tomorrow.", "Juma", 1), ("I will call the depot in 5 days.", "Juma", 5)]
    # AI output is kept only where its quote is verbatim in the transcript
    kept = svc.keep_quoted(t, {"decisions": [{"quote": "We agreed on a 20% discount."}],
                               "action_items": [{"quote": "I will send the price list tomorrow."}]})
    assert kept == {"decisions": [], "action_items": [{"quote": "I will send the price list tomorrow.", "owner": None, "due_in_days": 1}]}
    assert svc.keep_quoted(t, {"decisions": [{"quote": "Invented fact here"}]}) is None


# ── helpers ───────────────────────────────────────────────────────────────────

_mounted = False


def _client():
    global _mounted
    from fastapi import Depends
    from app.api.v1.endpoints import sales_depth, sales_depth_public
    from app.core.deps import get_current_user
    from app.main import app
    if not _mounted:                 # the coordinator registers these in module_registry; mounted here the same way
        app.include_router(sales_depth.router, prefix="/api/v1/sales-depth", dependencies=[Depends(get_current_user)])
        app.include_router(sales_depth_public.router, prefix="/api/v1/public/video")
        _mounted = True
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


async def _user(db, perms: tuple, tag: str):
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.models.role import Permission, Role
    from app.models.user import User
    u = User(id=uuid.uuid4(), username=f"{tag}-{uuid.uuid4().hex[:6]}", email=f"{tag}-{uuid.uuid4().hex[:6]}@povu-demo.test",
             full_name=tag.title(), hashed_password=hash_password(PW), is_active=True)
    role = Role(name=f"{tag}-{uuid.uuid4().hex[:6]}", is_active=True)
    for code in perms:
        p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
        if p is None:
            p = Permission(code=code, name=code, module=code.split(".")[0], action=code.split(".")[1], is_active=True)
            db.add(p)
            await db.flush()
        role.permissions.append(p)
    u.roles.append(role)
    db.add_all([role, u])
    return u


REP = ("crm.view_all", "crm.edit_all", "crm.create", "crm.edit", "sales.view", "sales.create", "sales.edit", "sales.import", "quality.view")


async def _login(c, username):
    r = await c.post("/api/v1/auth/login", data={"username": username, "password": PW})
    assert r.status_code == 200, r.text


async def _world(s: str):
    """Rep, customer, product with a customer price list, a confirmed order, an open deal, an open ticket."""
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMRecord, CRMRecordType
    from app.models.helpdesk import HelpdeskTicket
    from app.models.master import Product
    from app.models.price_list import PLHeader, PLLine, PLStatus, PLType
    from app.models.sales import Customer, SalesOrder, SOLine, SOStatus
    async with AsyncSessionLocal() as db:
        rep = await _user(db, REP, "rep")
        cust = Customer(id=uuid.uuid4(), code=f"DUKA-{s}", name="Duka Moja", currency="KES")
        prod = Product(id=uuid.uuid4(), sku=f"POVU-ALC-1L-{s}", name="POVU AllClean 1 L", category="HOUSEHOLD")
        db.add_all([cust, prod])
        await db.flush()
        pl = PLHeader(id=uuid.uuid4(), price_list_code=f"PL-{s}", price_list_name="Duka Moja prices", valid_from=date.today() - timedelta(days=1),
                      pl_type=PLType.CUSTOMER_SPECIFIC, customer_id=cust.id, status=PLStatus.ACTIVE, currency="KES")
        db.add(pl)
        await db.flush()
        db.add(PLLine(header_id=pl.id, product_id=prod.id, base_price=Decimal("55")))
        so = SalesOrder(id=uuid.uuid4(), order_no=f"SO-{s}", customer_id=cust.id, order_date=date.today() - timedelta(days=20),
                        requested_delivery_date=date.today() - timedelta(days=18), status=SOStatus.CONFIRMED, currency="KES")
        db.add(so)
        await db.flush()
        db.add(SOLine(so_id=so.id, line_no=1, product_id=prod.id, ordered_quantity=Decimal("24"), unit="PCS", unit_price=Decimal("50"),
                      tax_rate=Decimal("0.16")))
        deal = CRMRecord(id=uuid.uuid4(), record_type=CRMRecordType.OPPORTUNITY, company_name="Duka Moja re-order",
                         assigned_customer_id=cust.id, assigned_rep_id=str(rep.id), currency="KES", notes="Wants the usual POVU AllClean.")
        db.add(deal)
        db.add(HelpdeskTicket(ticket_no=f"TCK-{s}", subject="Late delivery of POVU AllClean", customer_id=cust.id))
        await db.commit()
        return rep.username, rep.id, cust.id, prod.id, so.id, deal.id


# ── 1. task calendar sync ─────────────────────────────────────────────────────

@pytest.fixture
def sim(monkeypatch):
    from app.core import provider_http
    from app.core.config import settings
    from tests.provider_sim import create_app, sim_settings
    app = create_app()
    for k, v in sim_settings(SIM).items():
        monkeypatch.setattr(settings, k, v)
    monkeypatch.setattr(settings, "PROVIDER_EGRESS", "local")
    provider_http.set_test_transport(httpx.ASGITransport(app=app))
    yield app
    provider_http.set_test_transport(None)


async def _connect(db, user, provider):
    from app.core import provider_http
    from app.services import oauth_service as oauth
    url = await oauth.start(db, user.id, provider, "calendar")
    parts = urlsplit(url)
    form = {k: v[0] for k, v in parse_qs(parts.query).items()}
    async with provider_http.provider_client() as c:
        r = await c.post(f"{parts.scheme}://{parts.netloc}{parts.path}", data={**form, "decision": "allow"})
    back = {k: v[0] for k, v in parse_qs(urlsplit(r.headers["location"]).query).items()}
    conn = await oauth.complete(db, state=back["state"], code=back["code"], error=None)
    await db.commit()
    return conn


@DB
@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["google", "microsoft"])
async def test_task_calendar_sync(sim, provider):
    from sqlalchemy import func, select
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMActivity, CRMActivityResult, CRMActivityType, CRMRecord, CRMRecordType
    from app.models.m47_sales_depth import CRMTaskCalendarLink
    from app.models.meetings import CalendarBusyBlock
    from app.services import calendar_sync_service as cal
    async with AsyncSessionLocal() as db:
        u = await _user(db, ("crm.view",), "cal")
        nobody = await _user(db, ("crm.view",), "nocal")
        rec = CRMRecord(id=uuid.uuid4(), record_type=CRMRecordType.OPPORTUNITY, company_name="Duka Moja")
        db.add(rec)
        await db.commit()
        assert (await cal.push_tasks_safely(db, nobody.id))["status"] == "NOT_CONFIGURED"
        conn = await _connect(db, u, provider)
        due = datetime.utcnow().replace(microsecond=0) + timedelta(days=2)
        t1 = CRMActivity(id=uuid.uuid4(), crm_record_id=rec.id, activity_type=CRMActivityType.TASK, subject="Call Duka Moja",
                         due_datetime=due, assigned_to=str(u.id), result_status=CRMActivityResult.PLANNED)
        t2 = CRMActivity(id=uuid.uuid4(), crm_record_id=rec.id, activity_type=CRMActivityType.TASK, subject="Send POVU price list",
                         due_datetime=due, assigned_to=u.username, result_status=CRMActivityResult.PLANNED)
        t3 = CRMActivity(id=uuid.uuid4(), crm_record_id=rec.id, activity_type=CRMActivityType.TASK, subject="No due date",
                         assigned_to=str(u.id), result_status=CRMActivityResult.PLANNED)
        db.add_all([t1, t2, t3])
        await db.commit()
        out = await cal.push_tasks_safely(db, u.id)
        await db.commit()
        assert out == {"status": "SYNCED", "SYNCED": 2}
        live = lambda: [e for e in sim.state.sim["cal"][provider].values() if not e.get("cancelled")]  # noqa: E731
        assert len(live()) == 2
        assert (await cal.push_tasks_safely(db, u.id)) == {"status": "SYNCED", "UNCHANGED": 2}
        t1.due_datetime = due + timedelta(hours=3)                            # update in place, no duplicate
        await db.commit()
        assert (await cal.push_tasks_safely(db, u.id))["SYNCED"] == 1
        await db.commit()
        assert len(live()) == 2
        t1.result_status = CRMActivityResult.COMPLETED                         # completed → event removed
        await db.delete(t2)                                                     # deleted → event removed
        await db.commit()
        assert (await cal.push_tasks_safely(db, u.id)) == {"status": "SYNCED", "DELETED": 2}
        await db.commit()
        assert live() == []
        assert (await db.execute(select(func.count()).select_from(CRMTaskCalendarLink).where(
            CRMTaskCalendarLink.connection_id == conn.id))).scalar_one() == 0
        # the background sync pushes tasks too and never turns task reminders into busy time
        t4 = CRMActivity(id=uuid.uuid4(), crm_record_id=rec.id, activity_type=CRMActivityType.TASK, subject="Visit depot",
                         due_datetime=due, assigned_to=str(u.id), result_status=CRMActivityResult.PLANNED)
        db.add(t4)
        await db.commit()
        res = await cal.sync_connection(db, conn)
        await db.commit()
        assert res["tasks"] == {"SYNCED": 1}
        assert (await db.execute(select(func.count()).select_from(CalendarBusyBlock).where(
            CalendarBusyBlock.connection_id == conn.id))).scalar_one() == 0


# ── 2. video messages ─────────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_video_message_link(tmp_path, monkeypatch):
    from sqlalchemy import select
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.m47_sales_depth import SalesVideoMessage, SalesVideoView
    monkeypatch.setattr(settings, "MEDIA_STORAGE_PATH", str(tmp_path))
    s = uuid.uuid4().hex[:5]
    rep, rep_id, cust_id, *_ = await _world(s)
    async with _client() as c:
        await _login(c, rep)
        r = await c.post("/api/v1/sales-depth/videos", files={"file": ("hello.webm", WEBM, "video/webm")},
                         data={"title": "Your POVU order", "contact_email": f"buyer{s}@example.com", "customer_id": str(cust_id), "days": "7"})
        assert r.status_code == 201, r.text
        token_a = r.json()["url"].rsplit("/", 1)[1]
        vid_a = r.json()["id"]
        other = WEBM + b"other"
        r2 = await c.post("/api/v1/sales-depth/videos", files={"file": ("b.webm", other, "video/webm")},
                          data={"title": "Second", "contact_email": f"other{s}@example.com"})
        token_b = r2.json()["url"].rsplit("/", 1)[1]
        bad = await c.post("/api/v1/sales-depth/videos", files={"file": ("x.mp3", b"ID3" + b"\x00" * 50, "audio/mpeg")},
                           data={"title": "Audio", "contact_email": f"a{s}@example.com"})
        assert bad.status_code == 422
        listing = (await c.get("/api/v1/sales-depth/videos")).json()
        assert any(v["id"] == vid_a for v in listing)
    async with _client() as pub:                                         # no login
        meta = await pub.get(f"/api/v1/public/video/{token_a}")
        assert meta.status_code == 200 and meta.json()["title"] == "Your POVU order"
        f = await pub.get(f"/api/v1/public/video/{token_a}/file")
        assert f.status_code == 200 and f.content == WEBM                  # only its own media
        assert (await pub.get(f"/api/v1/public/video/{token_b}/file")).content == other
        assert (await pub.post(f"/api/v1/public/video/{token_a}/view", json={"seconds": 12})).json() == {"recorded": True}
        assert (await pub.post(f"/api/v1/public/video/{token_a}/view", json={"seconds": 30})).json() == {"recorded": False}
        assert (await pub.get(f"/api/v1/public/video/{token_a[:-2]}xx")).status_code == 404
        async with AsyncSessionLocal() as db:
            vm = (await db.execute(select(SalesVideoMessage).where(SalesVideoMessage.id == uuid.UUID(vid_a)))).scalar_one()
            assert len(vm.token_hash) == 64 and token_a not in vm.token_hash
            # the staff-only media is not reachable through the CMS public media routes
            assert (await pub.get(f"/api/v1/public/cms/media/{vm.media_id}/file")).status_code in (401, 403)
            views = (await db.execute(select(SalesVideoView).where(SalesVideoView.video_id == vm.id))).scalars().all()
            assert len(views) == 1 and views[0].seconds == 30 and vm.customer_id == cust_id
            vm.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            await db.commit()
        assert (await pub.get(f"/api/v1/public/video/{token_a}/file")).status_code == 410
    async with _client() as c:
        await _login(c, rep)
        assert (await c.post(f"/api/v1/sales-depth/videos/{r2.json()['id']}/revoke")).status_code == 200
    async with _client() as pub:
        assert (await pub.get(f"/api/v1/public/video/{token_b}")).status_code == 410


# ── 3. meeting recap and brief ────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_meeting_recap_and_brief():
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMActivity
    from app.models.meetings import MeetingRecord
    s = uuid.uuid4().hex[:5]
    rep, rep_id, cust_id, prod_id, so_id, deal_id = await _world(s)
    async with AsyncSessionLocal() as db:
        m = MeetingRecord(id=uuid.uuid4(), title="Duka Moja review", platform="jitsi", host_id=rep_id, customer_id=cust_id,
                          crm_record_id=deal_id, scheduled_at=datetime.utcnow() + timedelta(days=1), duration_minutes=30,
                          status="SCHEDULED", attendees=[])
        db.add(m)
        await db.commit()
        mid = m.id
    async with _client() as c:
        await _login(c, rep)
        b = (await c.get(f"/api/v1/sales-depth/meetings/{mid}/brief")).json()
        assert b["facts_only"] and [d["id"] for d in b["open_deals"]] == [str(deal_id)]
        assert b["last_orders"][0]["order_no"] == f"SO-{s}" and b["last_orders"][0]["net_total"] == "1200.00"
        assert b["open_tickets"][0]["ticket_no"] == f"TCK-{s}"
        assert (await c.get(f"/api/v1/sales-depth/meetings/{mid}/recap")).json() == {"status": "NO_TRANSCRIPT"}
        audio = await c.post(f"/api/v1/sales-depth/meetings/{mid}/transcript", files={"file": ("call.mp3", b"ID3" + b"\x00" * 50, "audio/mpeg")})
        assert audio.status_code == 409 and "NOT_AVAILABLE" in audio.json()["detail"]
        t = "Amina: We agreed to list POVU WhiteCare 1 kg at Duka Moja.\nJuma: I will send the price list tomorrow.\nAmina: Fine."
        r = await c.post(f"/api/v1/sales-depth/meetings/{mid}/transcript", files={"file": ("notes.txt", t.encode(), "text/plain")})
        assert r.status_code == 200, r.text
        rc = r.json()
        assert rc["engine"] == "rules" and rc["status"] == "DRAFT"
        assert rc["recap"]["action_items"][0]["quote"] == "I will send the price list tomorrow."
        ok = await c.post(f"/api/v1/sales-depth/meetings/{mid}/recap/approve", json={"action_items": [0]})
        assert ok.status_code == 200 and len(ok.json()["task_ids"]) == 1
        assert (await c.post(f"/api/v1/sales-depth/meetings/{mid}/recap/approve", json={"action_items": [0]})).status_code == 409
    async with AsyncSessionLocal() as db:
        task = await db.get(CRMActivity, uuid.UUID(ok.json()["task_ids"][0]))
        assert task.crm_record_id == deal_id and task.assigned_to == str(rep_id) and task.subject == "I will send the price list tomorrow."
        assert task.due_datetime.date() == (datetime.utcnow() + timedelta(days=1)).date()


# ── 4. quote draft from a deal ────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_quote_draft_from_deal():
    from sqlalchemy import func, select
    from app.db.session import AsyncSessionLocal
    from app.models.quotation import Quotation
    s = uuid.uuid4().hex[:5]
    rep, rep_id, cust_id, prod_id, so_id, deal_id = await _world(s)
    async with AsyncSessionLocal() as db:
        before = (await db.execute(select(func.count()).select_from(Quotation))).scalar_one()
    async with _client() as c:
        await _login(c, rep)
        p = await c.post(f"/api/v1/cpq/deals/{deal_id}/quote-draft")
        assert p.status_code == 200, p.text
        d = p.json()
        assert d["engine"] == "rules" and d["based_on"] == f"SO-{s}"
        assert [(l["product_id"], l["qty"], l["unit_price"]) for l in d["lines"]] == [(str(prod_id), "24.000", "55.0000")]
        async with AsyncSessionLocal() as db:
            assert (await db.execute(select(func.count()).select_from(Quotation))).scalar_one() == before    # nothing saved
        lines = [{"product_id": l["product_id"], "qty": 30, "unit": l["unit"], "tax_rate": float(l["tax_rate"])} for l in d["lines"]]
        sv = await c.post(f"/api/v1/cpq/deals/{deal_id}/quote-draft/save", json={"lines": lines})
        assert sv.status_code == 201, sv.text
    async with AsyncSessionLocal() as db:
        from app.services import cpq_service as cpq
        q = await cpq._quote(db, uuid.UUID(sv.json()["id"]))
        assert q.status.value == "DRAFT" and q.sent_at is None and q.crm_record_id == deal_id and q.created_by_id == rep_id
        assert q.lines[0].qty == Decimal("30") and q.lines[0].unit_price == Decimal("55")


# ── 5. contract import ────────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_contract_import(tmp_path, monkeypatch):
    from sqlalchemy import select
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.contracts import Contract, ContractTerm
    from app.models.cpq import ContractRenewal
    from app.models.documents import Document
    from app.services import cpq_service as cpq
    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(tmp_path))
    s = uuid.uuid4().hex[:5]
    rep, rep_id, cust_id, *_ = await _world(s)
    end = (date.today() + timedelta(days=10)).isoformat()
    csv = ("contract_code,customer_code,start_date,end_date,value,currency,auto_renew,renewal_notice_days,attachment\n"
           f"CT-{s}-1,DUKA-{s},2026-01-01,{end},1200000,KES,true,30,duka-{s}.pdf\n"
           f"CT-{s}-2,NOPE-{s},2026-01-01,{end},5,KES,false,30,\n"
           f"CT-{s}-3,DUKA-{s},2026-05-01,2026-01-01,5,KES,false,30,\n"
           f"CT-{s}-4,DUKA-{s},2026-01-01,{end},5,KES,false,30,missing.pdf\n")
    pdf = b"%PDF-1.4\n% synthetic POVU contract\n%%EOF\n"
    async with _client() as c:
        await _login(c, rep)
        files = [("file", ("contracts.csv", csv.encode(), "text/csv")), ("attachments", (f"duka-{s}.pdf", pdf, "application/pdf"))]
        dry = await c.post("/api/v1/bulk-import/contracts/import-with-files", files=files, data={"dry_run": "true"})
        assert dry.status_code == 200, dry.text
        dj = dry.json()
        assert dj["dry_run"] and dj["valid_rows"] == 1 and sorted({e["row"] for e in dj["errors"]}) == [3, 4, 5]
        async with AsyncSessionLocal() as db:
            assert (await db.execute(select(Contract).where(Contract.contract_code == f"CT-{s}-1"))).scalar_one_or_none() is None
        real = await c.post("/api/v1/bulk-import/contracts/import-with-files", files=files, data={"dry_run": "false"})
        assert real.status_code == 200, real.text
        assert real.json()["attachments_stored"][0]["contract_code"] == f"CT-{s}-1"
        again = await c.post("/api/v1/bulk-import/contracts/import-with-files", files=files, data={"dry_run": "true"})
        assert any("Already exists" in e["message"] for e in again.json()["errors"] if e["row"] == 2)
    async with AsyncSessionLocal() as db:
        ct = (await db.execute(select(Contract).where(Contract.contract_code == f"CT-{s}-1"))).scalar_one()
        assert ct.party_id == cust_id and ct.auto_renew and ct.renewal_notice_days == 30
        term = (await db.execute(select(ContractTerm).where(ContractTerm.contract_id == ct.id))).scalar_one()
        assert term.value == Decimal("1200000")
        doc = (await db.execute(select(Document).where(Document.related_entity_id == str(ct.id)))).scalar_one()
        assert doc.file_name == f"duka-{s}.pdf" and doc.customer_id == cust_id
        ren = (await db.execute(select(ContractRenewal).where(ContractRenewal.contract_id == ct.id))).scalar_one()
        assert ren.notified_at == cpq.NOT_NOTIFIED
        await cpq.renewals_tick(db)                            # ends in 10 days with 30 days notice → noticed now
        first = ren.notified_at
        assert first > cpq.NOT_NOTIFIED and ren.renewal_quote_id is None
        await cpq.renewals_tick(db)                            # once only
        assert ren.notified_at == first
        await db.rollback()


# ── 6. trained deal-win model ─────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_deal_win_model_cold_start_and_training():
    from sqlalchemy import func, select
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMActivity, CRMActivityResult, CRMActivityType, CRMRecord, CRMRecordType, CRMStatus, CRMWinLoss
    from app.models.customer_intel import CIModel
    from app.services import crm_deal_score_service as ds
    s = uuid.uuid4().hex[:5]
    rep, rep_id, cust_id, prod_id, so_id, deal_id = await _world(s)
    async with AsyncSessionLocal() as db:
        assert (await db.execute(select(func.count()).select_from(CIModel).where(CIModel.kind == "DEAL_WIN"))).scalar_one() == 0
        open_deal = await db.get(CRMRecord, deal_id)
        cold = await ds.win_probability(db, open_deal)
        assert cold["status"] == "NOT_ENOUGH_DATA" and cold["probability"] is None and "Not enough data" in cold["label"]
        refused = await ds.train_win_model(db, "tester")
        assert not refused["trained"] and refused["status"] == "NOT_ENOUGH_DATA"
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(30):                                  # synthetic: won deals are larger and more worked
            won = i % 2 == 0
            r = CRMRecord(id=uuid.uuid4(), record_type=CRMRecordType.OPPORTUNITY, company_name=f"POVU synthetic {s}-{i}",
                          expected_revenue=Decimal(50000 if won else 2000) + i, status=CRMStatus.WON if won else CRMStatus.LOST,
                          created_at=base + timedelta(days=i))
            db.add(r)
            await db.flush()
            db.add(CRMWinLoss(crm_record_id=r.id, final_status="WON" if won else "LOST", close_date=(base + timedelta(days=i + 20)).date()))
            for k in range(6 if won else 1):
                db.add(CRMActivity(crm_record_id=r.id, activity_type=CRMActivityType.CALL, subject="Call",
                                   result_status=CRMActivityResult.COMPLETED, completed_datetime=datetime(2026, 1, 2)))
        await db.flush()
        out = await ds.train_win_model(db, "tester")
        assert out["trained"] and out["version"] == 1
        mt = out["metrics"]
        assert mt["won"] == 15 and mt["lost"] == 15 and mt["n_train"] == 22 and mt["n_holdout"] == 8
        assert mt["auc"] is not None and 0 <= mt["auc"] <= 1 and 0 <= mt["accuracy"] <= 1 and "synthetic" in mt["note"]
        await db.commit()
    async with _client() as c:
        await _login(c, rep)
        w = (await c.get(f"/api/v1/sales-depth/records/{deal_id}/win")).json()
        assert isinstance(w["rule_score"], int) and w["trained"]["status"] == "TRAINED" and 0 <= w["trained"]["probability"] <= 1
        assert w["trained"]["model_version"] == 1 and w["trained"]["metrics"]["n_holdout"] == 8
        assert (await c.get("/api/v1/sales-depth/deal-model")).json()["version"] == 1
