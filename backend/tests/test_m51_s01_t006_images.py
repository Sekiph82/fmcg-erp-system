"""M51.S01.T006 image generation/editing (DB part needs M51_DB=1; adapter/gate unit part runs everywhere).

Unit: moderation, status/NOT_CONFIGURED, OpenAI generation+edit and Stability core request construction against the simulator,
429 retry, 401/402/403 mapping, invalid image, content filter. DB: draft asset with provenance, claim/moderation/SKU rejection
without a provider call, budget exhaustion and release on failure, UNKNOWN outcome keeps the reservation, idempotency, EDIT,
second-person approval making the asset usable in the DAM, discard, RBAC.
"""
import os
import uuid

import httpx
import pytest

from app.services import m51_image_gen as ig
from tests.m51_media_common import (clean_scan, client_for, ensure_tables, setv, sim_calls, sim_control, staff, use_image_sim)

DB = pytest.mark.skipif(os.environ.get("M51_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _cleanup():
    yield
    from app.core import provider_http
    provider_http.set_test_transport(None)
    if os.environ.get("M51_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_moderation_and_status(monkeypatch):
    assert ig.moderate("a nude person")[0]["code"] == "moderation"
    assert not ig.moderate("POVU AllClean 1 L bottle on a kitchen counter")
    setv(monkeypatch, "M51_IMAGE_PROVIDER", "")
    assert ig.status()["status"] == "NOT_CONFIGURED"
    setv(monkeypatch, "M51_IMAGE_PROVIDER", "openai")
    assert ig.status()["status"] == "NOT_CONFIGURED"          # no live flag / key
    setv(monkeypatch, "M51_IMAGE_LIVE_ENABLED", True)
    setv(monkeypatch, "OPENAI_API_KEY", "sk-test")
    assert ig.status()["status"] == "AVAILABLE" and ig.status()["mode"] == "LIVE"
    setv(monkeypatch, "M51_IMAGE_PROVIDER", "simulator")
    assert ig.status()["mode"] == "SIMULATED"


@pytest.mark.asyncio
async def test_openai_contract_and_errors(monkeypatch):
    use_image_sim(monkeypatch)
    setv(monkeypatch, "M51_IMAGE_BACKOFF", 0)
    setv(monkeypatch, "M51_IMAGE_PROVIDER", "simulator")
    img, meta, prov, mode = await ig.call_provider("GENERATE", "Brand: POVU. Clean kitchen counter", "1024x1024", None, None)
    assert img[:8] == b"\x89PNG\r\n\x1a\n" and (prov, mode) == ("simulator", "SIMULATED") and meta["request_id"] == "req_sim_1"
    c = (await sim_calls())[-1]
    assert c["op"] == "generations" and c["model"] == "sim-image-1" and "response_format" not in c["keys"] and "output_format" in c["keys"]
    await sim_control({"faults": {"openai": ["429"]}})
    await ig.call_provider("GENERATE", "retry me please", "1024x1024", None, None)          # 429 → retried → success
    await sim_control({"faults": {"openai": ["moderation"]}})
    with pytest.raises(ig.ImageError) as e:
        await ig.call_provider("GENERATE", "something", "1024x1024", None, None)
    assert e.value.kind == "MODERATION"
    await sim_control({"faults": {"openai": ["bad_image"]}})
    img = (await ig.call_provider("GENERATE", "x" * 12, "1024x1024", None, None))[0]
    assert not ig._png_or_jpeg(img)
    setv(monkeypatch, "M51_IMAGE_SIM_KEY", "wrong")
    with pytest.raises(ig.ImageError) as e:
        await ig.call_provider("GENERATE", "something", "1024x1024", None, None)
    assert e.value.kind == "AUTH"
    setv(monkeypatch, "M51_IMAGE_SIM_KEY", "sim-image-key")
    out = await ig.call_provider("EDIT", "make it brighter", "1024x1024", b"\x89PNG\r\n\x1a\nxx", None)
    assert out[0][:4] == b"\x89PNG" and (await sim_calls())[-1]["op"] == "edits" and (await sim_calls())[-1]["images"] == 1


@pytest.mark.asyncio
async def test_stability_contract(monkeypatch):
    use_image_sim(monkeypatch)
    setv(monkeypatch, "M51_IMAGE_PROVIDER", "stability")
    setv(monkeypatch, "M51_IMAGE_LIVE_ENABLED", True)
    setv(monkeypatch, "STABILITY_API_KEY", "sim-stability-key")
    setv(monkeypatch, "M51_STABILITY_BASE_URL", "http://127.0.0.1:8765")
    img, meta, prov, mode = await ig.call_provider("GENERATE", "POVU hand wash powder pouch", "1536x1024", None, "blurry")
    assert img[:4] == b"\x89PNG" and meta["seed"] == "42" and mode == "LIVE"
    c = (await sim_calls())[-1]
    assert c["aspect_ratio"] == "3:2" and c["accept"] == "image/*"
    await sim_control({"faults": {"stability": ["filtered"]}})
    with pytest.raises(ig.ImageError) as e:
        await ig.call_provider("GENERATE", "something here", "1024x1024", None, None)
    assert e.value.kind == "MODERATION"
    await sim_control({"faults": {"stability": ["403"]}})
    with pytest.raises(ig.ImageError) as e:
        await ig.call_provider("GENERATE", "something here", "1024x1024", None, None)
    assert e.value.kind == "MODERATION"
    with pytest.raises(ig.ImageError, match="not supported"):
        await ig.call_provider("EDIT", "something here", "1024x1024", b"x", None)


@pytest.mark.asyncio
async def test_live_blocked_by_local_egress(monkeypatch):
    """A live provider cannot be reached while PROVIDER_EGRESS=local: nothing is sent."""
    from app.core import provider_http
    provider_http.set_test_transport(None)
    setv(monkeypatch, "PROVIDER_EGRESS", "local")
    setv(monkeypatch, "M51_IMAGE_PROVIDER", "openai")
    setv(monkeypatch, "M51_IMAGE_LIVE_ENABLED", True)
    setv(monkeypatch, "OPENAI_API_KEY", "sk-test")
    with pytest.raises(ig.ImageError) as e:
        await ig.call_provider("GENERATE", "something here", "1024x1024", None, None)
    assert e.value.kind == "BLOCKED"


RUN = uuid.uuid4().hex[:8]
PERMS = ("marketing.view", "marketing.create", "marketing.edit")


async def _setup(monkeypatch, budget=1.0):
    from app.db.session import AsyncSessionLocal
    await ensure_tables()
    use_image_sim(monkeypatch)
    clean_scan(monkeypatch)
    setv(monkeypatch, "M51_IMAGE_PROVIDER", "simulator")
    setv(monkeypatch, "M51_IMAGE_MONTHLY_BUDGET_USD", budget)
    setv(monkeypatch, "M51_IMAGE_BACKOFF", 0)
    setv(monkeypatch, "M51_IMAGE_MAX_BACKOFF", 0)
    async with AsyncSessionLocal() as db:
        # a fresh month ledger for this run
        from sqlalchemy import text
        await db.execute(text("DELETE FROM m51_image_usage"))
        maker, approver, viewer = (await staff(db, "maker", PERMS), await staff(db, "approver", PERMS + ("marketing.approve",)),
                                   await staff(db, "viewer", ("marketing.view",)))
        await db.commit()
    return maker, approver, viewer


@DB
@pytest.mark.asyncio
async def test_image_flow(monkeypatch):
    from sqlalchemy import select
    from app.api.v1.endpoints.marketing_assets import _usable
    from app.db.session import AsyncSessionLocal
    from app.models.documents import Document, DocumentStatus
    maker, approver, viewer = await _setup(monkeypatch)
    async with client_for(maker) as c, client_for(approver) as a, client_for(viewer) as v:
        body = {"title": "AllClean hero", "prompt": "POVU AllClean bottle on a bright kitchen counter, soft light", "product_skus": ["POVU-ALC-1L"], "idempotency_key": "k1-" + RUN}
        r = await c.post("/api/v1/media-studio/images", json=body)
        assert r.status_code == 201, r.text
        j = r.json()
        # unknown SKU only rejects when the product master lacks it; here the seed may or may not have it
        if j["status"] == "REJECTED":
            assert j["findings"][0]["code"] == "unknown_sku"
            body["product_skus"] = []
            body["idempotency_key"] = "k1b-" + RUN
            j = (await c.post("/api/v1/media-studio/images", json=body)).json()
        assert j["status"] == "GENERATED" and j["mode"] == "SIMULATED" and j["provider"] == "simulator"
        p = j["provenance"]
        assert p["provider"] == "simulator" and p["model"] == "sim-image-1" and len(p["prompt_sha256"]) == 64 and p["generated_at"]
        assert "Brand: POVU" in (await sim_calls())[-1]["prompt"]
        n_calls = len(await sim_calls())
        # idempotent repeat: same job, no new provider call
        again = (await c.post("/api/v1/media-studio/images", json=body)).json()
        assert again["id"] == j["id"] and len(await sim_calls()) == n_calls
        async with AsyncSessionLocal() as db:
            d = await db.get(Document, uuid.UUID(j["document_id"]))
            assert d.status == DocumentStatus.DRAFT and d.document_type == "AI_IMAGE" and not _usable(d)   # unusable before approval
        # creator cannot approve; viewer cannot review; second person can
        assert (await c.post(f"/api/v1/media-studio/images/{j['id']}/review", json={"approve": True})).status_code == 403
        assert (await v.post(f"/api/v1/media-studio/images/{j['id']}/review", json={"approve": True})).status_code == 403
        ok = await a.post(f"/api/v1/media-studio/images/{j['id']}/review", json={"approve": True, "note": "on brand"})
        assert ok.status_code == 200 and ok.json()["status"] == "APPROVED"
        async with AsyncSessionLocal() as db:
            d = await db.get(Document, uuid.UUID(j["document_id"]))
            assert _usable(d)                                   # now visible to e-mail/social/CMS/ads via the DAM
        assert (await a.post(f"/api/v1/media-studio/images/{j['id']}/review", json={"approve": False})).status_code == 409
        # EDIT of the approved asset
        e = (await c.post("/api/v1/media-studio/images", json={"title": "AllClean hero v2", "prompt": "make the light warmer please", "operation": "EDIT",
                                                              "source_document_id": j["document_id"]})).json()
        assert e["status"] == "GENERATED" and e["provenance"]["operation"] == "EDIT" and (await sim_calls())[-1]["op"] == "edits"
        bad_edit = (await c.post("/api/v1/media-studio/images", json={"title": "x", "prompt": "make the light warmer please", "operation": "EDIT"})).json()
        assert bad_edit["status"] == "REJECTED"
        # discard
        d2 = (await a.post(f"/api/v1/media-studio/images/{e['id']}/review", json={"approve": False, "note": "no"})).json()
        assert d2["status"] == "DISCARDED"
        assert (await v.post("/api/v1/media-studio/images", json=body)).status_code == 403
        assert any(x["id"] == j["id"] for x in (await v.get("/api/v1/media-studio/images")).json())
    async with AsyncSessionLocal() as db:
        from app.models.audit_log import AuditLog
        ev = {r for r in (await db.execute(select(AuditLog.event_type).where(AuditLog.event_type.like("media.image.%")))).scalars()}
        assert {"media.image.requested", "media.image.approved", "media.image.discarded"} <= ev


@DB
@pytest.mark.asyncio
async def test_gates_budget_and_failures(monkeypatch):
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.cms import CsBrandProfile
    from app.models.m51_media import M51ImageUsage
    maker, approver, _ = await _setup(monkeypatch, budget=0.09)
    async with AsyncSessionLocal() as db:
        if not (await db.execute(select(CsBrandProfile).where(CsBrandProfile.key == "m51-img"))).scalar_one_or_none():
            db.add(CsBrandProfile(key="m51-img", name="M51 image test", banned_terms=["cheap"], evidence=[{"id": "e1", "text": "Tested on tiles.", "source": "lab"}],
                                  claim_terms=["antibacterial"], terminology={}))
            await db.commit()
    async with client_for(maker) as c:
        async def post(**kw):
            r = await c.post("/api/v1/media-studio/images", json={"title": "t", "prompt": "POVU AllClean bottle on a bright kitchen counter", **kw})
            assert r.status_code == 201, r.text
            return r.json()
        before = len(await sim_calls())
        assert (await post(prompt="nude person holding a POVU bottle"))["status"] == "REJECTED"
        j = await post(brand_key="m51-img", prompt="a cheap looking POVU bottle on a counter")
        assert j["status"] == "REJECTED" and any(f["code"] == "banned_term" for f in j["findings"])
        j = await post(brand_key="m51-img", prompt="POVU bottle with the antibacterial effect", overlay_text="Kills 99% of germs")
        assert j["status"] == "REJECTED" and any(f["code"] == "uncited_claim" for f in j["findings"])
        j = await post(prompt="POVU bottle", product_skus=["NOPE-1"])
        assert j["status"] == "REJECTED" and j["findings"][0]["code"] == "unknown_sku"
        assert (await c.post("/api/v1/media-studio/images", json={"title": "t", "prompt": "valid prompt long enough", "size": "10x10"})).status_code == 422
        assert len(await sim_calls()) == before            # none of the above reached the provider
        # provider failure → FAILED, reservation released
        await sim_control({"faults": {"openai": ["500"] * 4}})
        f = await post()
        assert f["status"] == "FAILED" and f["cost_estimate"] == 0 and f["provenance"]["kind"] == "SERVER"
        async with AsyncSessionLocal() as db:
            assert float((await db.get(M51ImageUsage, __import__("app.services.m51_image_gen", fromlist=["x"])._month())).spent) == 0
        # budget 0.09 with 0.04 per image: two succeed, third is refused
        assert (await post(idempotency_key=RUN + "b1"))["status"] == "GENERATED"
        assert (await post(idempotency_key=RUN + "b2"))["status"] == "GENERATED"
        over = await post(idempotency_key=RUN + "b3")
        assert over["status"] == "FAILED" and "budget" in over["error"].lower()
        # unknown outcome (timeout): FAILED, UNKNOWN, reservation kept
        from app.core import provider_http

        class Timeout(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                raise httpx.ReadTimeout("slow", request=request)
        setv(monkeypatch, "M51_IMAGE_MONTHLY_BUDGET_USD", 1.0)
        monkeypatch.setattr(provider_http, "_test_transport", Timeout())
        u = await post(idempotency_key=RUN + "b4")
        assert u["status"] == "FAILED" and u["provenance"]["outcome"] == "UNKNOWN" and u["cost_estimate"] == 0.04
        # provider moderation → REJECTED, nothing stored
        use_image_sim(monkeypatch)
        await sim_control({"faults": {"openai": ["moderation"]}})
        m = await post(idempotency_key=RUN + "b5")
        assert m["status"] == "REJECTED" and m["document_id"] is None
        # provider not configured → 409-style FAILED job, no call
        setv(monkeypatch, "M51_IMAGE_PROVIDER", "")
        n = await post(idempotency_key=RUN + "b6")
        assert n["status"] == "FAILED" and "provider" in n["error"].lower()
