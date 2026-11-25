"""M44.S01.T010 dynamic audiences (unit; DB part needs M44_DB=1). Runs at the M44 gate.

Unit: rule validation refuses unknown fields/ops and non-numeric numbers; matching incl. exclude; SHA-256 of the
normalised e-mail. DB: unconsented matching customers are blocked (counted, not members); recompute follows data
changes; export refused by default; upload refused without a provider; similarity is labelled local.
"""
import os
import uuid

import pytest

from app.services import audience_service as aus


def test_rules_and_hash():
    with pytest.raises(aus.AudienceError):
        aus.validate({"all": [{"field": "password", "op": "eq", "value": "x"}]})
    with pytest.raises(aus.AudienceError):
        aus.validate({"all": [{"field": "orders_90d", "op": "gte", "value": "many"}]})
    r = aus.validate({"all": [{"field": "channel", "op": "in", "value": ["RETAIL", "ONLINE"]},
                              {"field": "orders_90d", "op": "gte", "value": "2"}],
                      "exclude": [{"field": "city", "op": "eq", "value": "Mombasa"}]})
    assert aus.matches(r, {"channel": "retail", "orders_90d": 3.0, "city": "Nairobi"})
    assert not aus.matches(r, {"channel": "RETAIL", "orders_90d": 3.0, "city": "Mombasa"})
    assert not aus.matches(r, {"channel": "WHOLESALE", "orders_90d": 9.0, "city": "Nairobi"})
    assert aus.sha256_email("  Buyer@POVU-demo.test ") == aus.sha256_email("buyer@povu-demo.test")


DB = pytest.mark.skipif(os.environ.get("M44_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M44_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@DB
@pytest.mark.asyncio
async def test_consent_blocking_recompute_and_export_gates():
    from fastapi import HTTPException
    from types import SimpleNamespace
    from app.api.v1.endpoints import audiences as ep
    from app.db.session import AsyncSessionLocal
    from app.models.crm import MarketingAudience
    from app.models.sales import Customer, CustomerChannel
    from app.services import crm_outbound_service as outbound
    tag = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        yes = Customer(code=f"AUD-Y-{tag}", name="POVU Outlet Consented", email=f"yes-{tag}@povu-demo.test",
                       channel=CustomerChannel.RETAIL, segment=f"aud-{tag}")
        no = Customer(code=f"AUD-N-{tag}", name="POVU Outlet No Consent", email=f"no-{tag}@povu-demo.test",
                      channel=CustomerChannel.RETAIL, segment=f"aud-{tag}")
        db.add_all([yes, no])
        await db.flush()
        await outbound.record_consent(db, yes.email, "SUBSCRIBED", "test")
        a = MarketingAudience(name=f"aud-{tag}", rules=aus.validate({"all": [{"field": "segment", "op": "eq", "value": f"aud-{tag}"}]}))
        db.add(a)
        await db.flush()
        await aus.recompute(db, a)
        assert (a.member_count, a.blocked_count) == (1, 1)
        await outbound.record_consent(db, no.email, "SUBSCRIBED", "test")
        await db.flush()
        await aus.recompute(db, a)
        assert a.member_count == 2
        csv = await aus.hashed_export(db, a)
        assert yes.email not in csv and aus.sha256_email(yes.email) in csv
        # unsubscribed after the last recompute: left out of the export at once (review fix)
        await outbound.record_consent(db, no.email, "UNSUBSCRIBED", "test")
        await db.flush()
        csv = await aus.hashed_export(db, a)
        assert aus.sha256_email(no.email) not in csv and aus.sha256_email(yes.email) in csv
        editor = SimpleNamespace(is_superuser=True, id=None)
        with pytest.raises(HTTPException) as e:
            await ep.export(a.id, db, editor)
        assert e.value.status_code == 403
        with pytest.raises(HTTPException) as e:
            await ep.upload(a.id, "meta", editor)
        assert e.value.status_code == 503
        assert "not an ad-platform lookalike" in (await aus.similar(db, a))["label"]
        await db.rollback()
