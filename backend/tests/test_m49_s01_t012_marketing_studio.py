"""M49.S01.T012 Integrated Marketing Studio: brief -> approved creative -> audience -> ads / social / e-mail linked from
their own modules (local submission only) -> budget against the finance cap -> analytics with ERP order attribution.
Synthetic POVU data. Needs the disposable PostgreSQL: M49_DB=1."""
import importlib
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.session import AsyncSessionLocal, engine
from tests.m48_ads_support import approve, campaign_body, client, login, make_user, setup_account, sim  # noqa: F401
from tests.m49_audience_support import M49, mount

API = "/api/v1/marketing-studio"


def _mount():
    from app.main import app
    mount()
    if not any(getattr(r, "path", "").startswith(API) for r in app.routes):
        app.include_router(importlib.import_module("app.api.v1.endpoints.marketing_studio").router, prefix=API)


_mount()


@pytest.fixture(autouse=True)
async def _dispose():
    yield
    await engine.dispose()


@pytest.fixture
def no_2fa(monkeypatch):
    """Finance roles force TOTP at login; the second-person logic is what is tested here, not the 2FA enrolment."""
    async def off(db, uid):
        return False
    from app.api.v1.endpoints import auth
    from app.services import auth_2fa_policy
    monkeypatch.setattr(auth_2fa_policy, "requires_privileged_2fa", off)
    monkeypatch.setattr(auth, "requires_privileged_2fa", off)


async def seed(tag: str) -> dict:
    """A campaign, an approved DAM asset, a published design, an audience, and two companies' orders."""
    from app.models.company import Company
    from app.models.crm import CRMEmailCampaign, CRMLeadForm, CRMLeadSubmission, EmailDesign, MarketingAudience
    from app.models.documents import Document, DocumentCategory, DocumentStatus
    from app.models.master import Product, ProductCategory, UnitOfMeasure
    from app.models.marketing import Campaign, CampaignType, CustomerSegment, SegmentType
    from app.models.sales import Customer, SalesOrder, SOLine, SOStatus
    async with AsyncSessionLocal() as db:
        c = Campaign(campaign_code=f"POVU-AC-{tag}".upper(), campaign_name=f"POVU AllClean spring {tag}",
                     campaign_type=CampaignType.DIGITAL, start_date=date(2026, 12, 1), end_date=date(2026, 12, 31))
        doc = Document(title=f"POVU AllClean 1 L hero {tag}", category=DocumentCategory.MARKETING_CREATIVE, status=DocumentStatus.DRAFT)
        design = EmailDesign(name=f"POVU AllClean launch mail {tag}", document={"theme": {}, "blocks": []}, status="PUBLISHED")
        aud = MarketingAudience(name=f"POVU AllClean buyers {tag}", rules={"all": []}, member_count=3)
        seg = CustomerSegment(segment_name=f"Duka {tag}", segment_type=SegmentType.KIOSK)
        co_a, co_b = Company(name=f"POVU A {tag}", short_code=f"A{tag}"[:20]), Company(name=f"POVU B {tag}", short_code=f"B{tag}"[:20])
        prod = Product(sku=f"POVU-ALC-1L-{tag}", name="POVU AllClean 1 L", category=ProductCategory.OTHER, uom=UnitOfMeasure.PCS)
        cust = Customer(code=f"T12-{tag}", name=f"Duka {tag}")
        form = CRMLeadForm(slug=f"povu-{tag}", name="POVU enquiry", title="POVU enquiry")
        db.add_all([c, doc, design, aud, seg, co_a, co_b, prod, cust, form])
        await db.flush()
        db.add(CRMEmailCampaign(name=f"AllClean mail {tag}", subject="POVU AllClean", body="Hello", segment_id=seg.id,
                                marketing_campaign_id=c.id, design_id=design.id, approval_status="APPROVED", status="QUEUED"))
        for n, (co, status) in enumerate([(co_a, SOStatus.CONFIRMED), (co_a, SOStatus.CANCELLED), (co_b, SOStatus.CONFIRMED)]):
            so = SalesOrder(order_no=f"T12-{tag}-{n}", customer_id=cust.id, order_date=date(2026, 12, 5),
                            requested_delivery_date=date(2026, 12, 6), status=status, company_id=co.id, campaign_id=c.id, currency="KES")
            db.add(so)
            await db.flush()
            db.add(SOLine(so_id=so.id, line_no=1, product_id=prod.id, ordered_quantity=Decimal("10"), unit_price=Decimal("250"),
                          discount_pct=Decimal("0.1")))               # 10 x 250 x 0.9 = 2250.00
        db.add(CRMLeadSubmission(form_id=form.id, received_at=datetime.now(timezone.utc), status="NEW", consent_given=True,
                                 utm_source="Facebook", utm_campaign=c.campaign_code.lower()))
        await db.commit()
        return {"cid": str(c.id), "code": c.campaign_code, "doc": doc.id, "design": str(design.id), "aud": str(aud.id),
                "co_a": str(co_a.id), "co_b": str(co_b.id), "tag": tag}


async def approve_doc(doc_id):
    from app.models.documents import Document, DocumentStatus
    async with AsyncSessionLocal() as db:
        d = await db.get(Document, doc_id)
        d.status, d.mime_type = DocumentStatus.APPROVED, "image/png"
        await db.commit()


@M49
async def test_t012_studio_flow_roles_cap_and_attribution(sim, no_2fa):
    tag = uuid.uuid4().hex[:6]
    s = await seed(tag)
    cid, base = s["cid"], f"{API}/campaigns/{s['cid']}"
    p = await setup_account("meta")                          # author / approver (ad account members), intruder, outsider
    async with AsyncSessionLocal() as db:
        viewer = await make_user(db, ("marketing.view",), "viewer")
        finance = await make_user(db, ("finance.approve", "marketing.view"), "finance")
        fmark = await make_user(db, ("finance.approve", "marketing.edit", "marketing.view"), "fmark")
        await db.commit()
    async with client() as ma, client() as mb, client() as vw, client() as fi, client() as fm, client() as out:
        for c, u in ((ma, p["author"]), (mb, p["approver"]), (vw, viewer), (fi, finance), (fm, fmark), (out, p["outsider"])):
            await login(c, u)

        # ── roles: outsider sees nothing, viewer reads but cannot change anything
        assert (await out.get(base)).status_code == 403
        assert (await vw.get(base)).status_code == 200
        brief = {"summary": "Introduce POVU AllClean 1 L to kiosks in Nairobi.", "key_message": "One bottle for every surface.",
                 "channels": ["email", "social", "ads"], "product_skus": [f"POVU-ALC-1L-{tag}"]}
        assert (await vw.put(f"{base}/brief", json=brief)).status_code == 403
        assert (await vw.post(f"{base}/budget", json={"amount": "100"})).status_code == 403
        assert (await vw.post(f"{base}/links", json={"kind": "AUDIENCE", "ref_id": s["aud"]})).status_code == 403
        v = (await ma.get(base)).json()
        assert [x["done"] for x in v["checklist"]][:1] == [False] and v["brief"]["version"] == 0

        # ── brief (versioned)
        r = await ma.put(f"{base}/brief", json=brief)
        assert r.status_code == 200 and r.json()["brief"]["version"] == 1
        r = await ma.put(f"{base}/brief", json={**brief, "kpi": "Orders attributed"})
        assert r.json()["brief"]["version"] == 2 and r.json()["brief"]["history"][-1]["version"] == 1
        assert (await ma.put(f"{base}/brief", json={**brief, "channels": ["tv"]})).status_code == 422

        # ── creative: only an APPROVED asset can be linked; a newer state is shown, not hidden
        r = await ma.post(f"{base}/links", json={"kind": "DAM_ASSET", "ref_id": str(s["doc"])})
        assert r.status_code == 409 and "APPROVED" in r.json()["detail"]
        await approve_doc(s["doc"])
        r = await ma.post(f"{base}/links", json={"kind": "DAM_ASSET", "ref_id": str(s["doc"])})
        assert r.status_code == 201 and r.json()["usable"] and r.json()["linked_version"] == 1, r.text
        assert (await ma.post(f"{base}/links", json={"kind": "DAM_ASSET", "ref_id": str(s["doc"])})).status_code == 409
        assert (await ma.post(f"{base}/links", json={"kind": "EMAIL_DESIGN", "ref_id": s["design"]})).status_code == 201
        # a new version of the asset appears: the link reports it as outdated
        from app.models.documents import Document
        async with AsyncSessionLocal() as db:
            (await db.get(Document, s["doc"])).is_latest = False
            await db.commit()
        v = (await ma.get(base)).json()
        assert next(i for i in v["creative"] if i["kind"] == "DAM_ASSET")["outdated"] is True
        assert next(c for c in v["checklist"] if c["step"] == "creative")["done"]           # the published design is still usable

        # ── audience: local audience + audience sync draft on the ad account (not a member -> refused)
        assert (await ma.post(f"{base}/links", json={"kind": "AUDIENCE", "ref_id": s["aud"]})).status_code == 201
        r = await ma.post("/api/v1/audience-sync", json={"audience_id": s["aud"], "account_id": p["account"]})
        assert r.status_code == 201, r.text
        sync_id = r.json()["id"]
        assert (await ma.post(f"{base}/links", json={"kind": "AUDIENCE_SYNC", "ref_id": sync_id})).status_code == 201
        assert (await out.post(f"{base}/links", json={"kind": "AUDIENCE_SYNC", "ref_id": sync_id})).status_code == 403

        # ── ads: draft tree -> second-person approval -> local simulated submit, then linked
        r = await ma.post("/api/v1/ads/campaigns", json=campaign_body("meta", p["account"], f"POVU AllClean meta {tag}"))
        assert r.status_code == 201, r.text
        rid = r.json()["id"]
        assert (await ma.post(f"{base}/links", json={"kind": "AD_TREE", "ref_id": rid})).status_code == 201
        before = next(i for i in (await ma.get(base)).json()["channels"]["ads"]["items"])
        assert before["status"] == "DRAFT" and before["submitted"] is False
        await approve(ma, mb, rid, "SUBMIT")
        r = await ma.post(f"/api/v1/ads/campaigns/{rid}/submit")
        assert r.status_code == 200, r.text
        after = next(i for i in (await ma.get(base)).json()["channels"]["ads"]["items"])
        assert after["mode"] == "SIMULATED" and after["submitted"] is True and after["status"] != "DRAFT"

        # ── social: post tagged with the campaign code (native link) + explicit link; second editor approves; exported locally
        r = await ma.post("/api/v1/social/channels", json={"network": "facebook", "external_id": f"povu{tag}", "name": f"POVU page {tag}"})
        assert r.status_code == 201, r.text
        r = await ma.post("/api/v1/social/posts", json={"channel_id": r.json()["id"], "idempotency_key": f"k-{uuid.uuid4().hex[:12]}",
                                                        "text": "POVU AllClean 1 L: one bottle for every surface.",
                                                        "campaign_tag": s["code"]})
        assert r.status_code == 201, r.text
        pid = r.json()["id"]
        social = (await ma.get(base)).json()["channels"]["social"]
        assert social["items"][0]["status"] == "DRAFT" and social["items"][0]["via"] == "campaign_tag" and not social["submitted"]
        assert (await ma.post(f"/api/v1/social/posts/{pid}/request")).status_code == 200
        assert (await ma.post(f"/api/v1/social/posts/{pid}/approve")).status_code == 403          # not the author
        from app.models.crm import SocialPost
        async with AsyncSessionLocal() as db:
            sp = await db.get(SocialPost, uuid.UUID(pid))
            sp.status, sp.approved_version, sp.approved_by = "APPROVED", sp.version, "second-editor"
            await db.commit()
        assert (await ma.post(f"/api/v1/social/posts/{pid}/export")).status_code == 200
        r = await ma.post(f"{base}/links", json={"kind": "SOCIAL_POST", "ref_id": pid})
        assert r.status_code == 201 and r.json()["status"] == "EXPORTED"
        social = (await ma.get(base)).json()["channels"]["social"]
        assert len(social["items"]) == 1 and social["submitted"] is True                            # linked + tagged = one item

        # ── e-mail: the segment campaign that already points at this campaign is shown with its own approval state
        v = (await ma.get(base)).json()
        mail = [i for i in v["channels"]["email"]["items"] if i["kind"] == "EMAIL_CAMPAIGN"]
        assert len(mail) == 1 and mail[0]["approval"] == "APPROVED" and mail[0]["status"] == "QUEUED" and v["channels"]["email"]["submitted"]

        # ── budget: within the cap applies at once; above it needs a finance approver who is not the requester
        r = await ma.post(f"{base}/budget", json={"amount": "40000"})
        assert r.status_code == 201 and r.json()["status"] == "APPLIED"
        assert (await ma.get(base)).json()["budget"]["amount"] == "40000.00"
        r = await ma.post(f"{base}/budget", json={"amount": "90000", "note": "AllClean launch burst"})
        assert r.status_code == 201 and r.json()["status"] == "PENDING"
        rq = r.json()["id"]
        v = (await ma.get(base)).json()
        assert v["budget"]["amount"] == "40000.00" and v["budget"]["pending"]["id"] == rq                # not applied yet
        assert next(c for c in v["checklist"] if c["step"] == "budget")["done"] is False
        assert (await ma.post(f"{base}/budget", json={"amount": "95000"})).status_code == 409            # one open request
        assert (await ma.post(f"{API}/budget-requests/{rq}/decide", json={"ok": True})).status_code == 403   # marketing is not finance
        assert (await mb.post(f"{API}/budget-requests/{rq}/decide", json={"ok": True})).status_code == 403
        assert (await vw.post(f"{API}/budget-requests/{rq}/decide", json={"ok": True})).status_code == 403
        # a finance person who is also an editor cannot approve their own request
        r = await fm.post(f"{base}/budget", json={"amount": "120000"})
        assert r.status_code == 409                                                                       # (ma's request is still open)
        r = await fi.post(f"{API}/budget-requests/{rq}/decide", json={"ok": True})
        assert r.status_code == 200 and r.json()["status"] == "APPROVED" and r.json()["decided_by"] == finance
        assert (await fi.post(f"{API}/budget-requests/{rq}/decide", json={"ok": True})).status_code == 409
        assert (await ma.get(base)).json()["budget"]["amount"] == "90000.00"
        r = await fm.post(f"{base}/budget", json={"amount": "120000"})
        assert r.status_code == 201 and r.json()["status"] == "PENDING"
        assert (await fm.post(f"{API}/budget-requests/{r.json()['id']}/decide", json={"ok": True})).status_code == 403   # self-approval
        r = await fi.post(f"{API}/budget-requests/{r.json()['id']}/decide", json={"ok": False})
        assert r.json()["status"] == "REJECTED" and (await ma.get(base)).json()["budget"]["amount"] == "90000.00"

        # ── analytics: only stored data. Confirmed orders of the campaign, never the cancelled one
        a = (await ma.get(f"{base}/analytics")).json()
        assert a["attribution"]["orders"] == 2 and a["attribution"]["revenue"] == {"KES": "4500.00"}
        assert a["attribution"]["leads"] == 1 and a["attribution"]["leads_by_source"] == {"facebook": 1}
        assert a["channels"]["ads"]["has_data"] is False and a["spend"]["roas"] == {}        # nothing invented
        a = (await ma.get(f"{base}/analytics", params={"company_id": s["co_a"]})).json()      # company filter
        assert a["attribution"]["orders"] == 1 and a["attribution"]["revenue"] == {"KES": "2250.00"}
        a = (await ma.get(f"{base}/analytics", params={"company_id": s["co_b"]})).json()
        assert a["attribution"]["orders"] == 1
        assert (await out.get(f"{base}/analytics")).status_code == 403

        # real ad / spend / social rows feed the report; ROAS only with approved spend in the same currency
        from app.models.m49_social import SocialPostMetric
        from app.models.marketing import AdPerformance, AdPlatform, ApprovalStatus, BrandSpend, BrandSpendCategory
        async with AsyncSessionLocal() as db:
            db.add(AdPerformance(campaign_id=uuid.UUID(cid), platform=list(AdPlatform)[0], ad_date=date(2026, 12, 6),
                                 impressions=1000, clicks=40, spend=Decimal("300"), conversions=2))
            db.add(BrandSpend(campaign_id=uuid.UUID(cid), spend_category=list(BrandSpendCategory)[0], amount=Decimal("1500"),
                              currency="KES", spend_date=date(2026, 12, 6), approval_status=ApprovalStatus.APPROVED))
            db.add(BrandSpend(campaign_id=uuid.UUID(cid), spend_category=list(BrandSpendCategory)[0], amount=Decimal("999"),
                              currency="KES", spend_date=date(2026, 12, 6), approval_status=ApprovalStatus.PENDING))
            db.add(SocialPostMetric(post_id=uuid.UUID(pid), network="facebook", metric="post_impressions", value=Decimal("812"),
                                    source="local fixture"))
            await db.commit()
        a = (await ma.get(f"{base}/analytics")).json()
        assert a["spend"]["approved_brand_spend"] == {"KES": "1500.00"} and a["spend"]["roas"] == {"KES": "3.00"}
        assert a["channels"]["social"]["by_network"] == {"facebook": {"post_impressions": "812.00"}}
        assert next(iter(a["channels"]["ads"]["by_platform"].values()))["clicks"] == 40

        # ── unlink + audit trail of every mutation
        v = (await ma.get(base)).json()
        lid = next(i["link_id"] for i in v["audience"] if i["kind"] == "AUDIENCE")
        assert (await vw.delete(f"{base}/links/{lid}")).status_code == 403
        assert (await ma.delete(f"{base}/links/{lid}")).status_code == 204
        assert all(i["kind"] != "AUDIENCE" for i in (await ma.get(base)).json()["audience"])
        assert [x["step"] for x in v["checklist"]] == ["brief", "creative", "audience", "channels", "budget", "approval"]
        assert s["cid"] in {c["id"] for c in (await ma.get(f"{API}/campaigns")).json()}
        cands = (await ma.get(f"{base}/candidates")).json()
        assert any(x["ref_id"] == s["aud"] for x in cands["AUDIENCE"]) and not [x for x in cands["EMAIL_DESIGN"] if x["ref_id"] == s["design"]]

    from app.models.audit_log import AuditLog
    async with AsyncSessionLocal() as db:
        ev = [e.event_type for e in (await db.execute(select(AuditLog).where(AuditLog.target_id == cid))).scalars()
              if e.event_type.startswith("MARKETING_STUDIO_")]
    for want in ("BRIEF_SAVED", "LINKED", "UNLINKED", "BUDGET_APPLIED", "BUDGET_REQUESTED", "BUDGET_APPROVED", "BUDGET_REJECTED"):
        assert f"MARKETING_STUDIO_{want}" in ev, (want, ev)
    # nothing was sent anywhere: the ad tree is a simulated submission, the post an export
    assert not [e for e in ev if "LIVE" in e]


def test_campaign_budget_above_cap_refused_outside_studio():
    """The plain campaign create/PATCH cannot bypass the finance cap (budget routes through the studio request)."""
    from decimal import Decimal
    from fastapi import HTTPException
    from app.api.v1.endpoints.marketing import _guard_budget_cap
    from app.services.marketing_studio_service import cap
    _guard_budget_cap(None)
    _guard_budget_cap(cap())
    with pytest.raises(HTTPException) as e:
        _guard_budget_cap(cap() + Decimal("0.01"))
    assert e.value.status_code == 409
