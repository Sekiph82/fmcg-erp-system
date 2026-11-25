"""M45.S01.T004–T006 intent, churn and health (unit; DB part needs M45_DB=1).

Unit: decay and explanation, missing-data handling, logistic fit / AUC / calibration on a synthetic separable set,
rule baseline. DB: synthetic cohorts (steady vs lapsing outlets) → features ignore orders on/after the cut-off
(leakage), cold start says "insufficient history", time-aware training reports validation metrics and beats nothing
it cannot show, health labels "not enough data", alerts are deduplicated and scoped to the owner.
"""
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import numpy as np
import pytest

from app.services import customer_intel_service as ci

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
NOW = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_intent_decay_and_explanation():
    cfg = ci.DEFAULTS["intent"]
    sigs = [ci.Signal("QUOTE_VIEW", NOW, "opened quote QT-1"), ci.Signal("QUOTE_VIEW", NOW - timedelta(days=7), "old view"),
            ci.Signal("PAGE", NOW, "PAGE /about"), ci.Signal("UNKNOWN", NOW, "ignored")]
    total, ranked = ci.score_signals(sigs, cfg, NOW)
    assert ranked[0].points == 6 and ranked[1].points == 3.0        # one half-life later: half the points
    assert total == 10.0 and all(s.kind != "UNKNOWN" for s in ranked)


def test_health_missing_data():
    f = ci.Features()
    comp = ci.health_components(f, date(2026, 11, 26))
    assert comp["ordering"] is None and comp["nps"] is None and comp["engagement"] is None
    score, missing = ci.combine(comp, ci.DEFAULTS["health"]["weights"])
    assert score is None and "ordering" in missing                   # only tickets known → not enough data
    f = ci.Features(orders_total=5, last_order=date(2026, 11, 20), orders_90=3, typical_gap=14.0,
                    revenue_90=1000.0, overdue_amount=0.0, nps_last=9)
    score, missing = ci.combine(ci.health_components(f, date(2026, 11, 26)), ci.DEFAULTS["health"]["weights"])
    assert score >= 90 and missing == ["engagement"]


def test_logistic_auc_calibration_and_rule():
    rng = np.random.default_rng(7)
    X = rng.normal(size=(400, 2)); y = (X[:, 0] + 0.3 * rng.normal(size=400) > 0).astype(float)
    p = ci.predict(ci.fit_logistic(X[:300], y[:300]), X[300:])
    assert ci.auc(y[300:], p) > 0.9
    assert sum(b["n"] for b in ci.calibration(y[300:], p)) == 100
    assert ci.auc(np.array([1.0, 1.0]), np.array([0.2, 0.3])) is None  # one class only → no AUC claimed
    f = ci.Features(orders_total=4, last_order=date(2026, 10, 1), typical_gap=10.0)
    assert ci.rule_risk(f, date(2026, 11, 26)) == 1.0 and ci.rule_risk(ci.Features(), date(2026, 11, 26)) == 1.0


async def _cohort(db, n_steady=12, n_lapsing=12, today=date(2026, 11, 26)):
    from app.models.sales import Customer, SalesOrder, SOStatus
    ids = {"steady": [], "lapsing": []}
    for kind, n in (("steady", n_steady), ("lapsing", n_lapsing)):
        for i in range(n):
            c = Customer(code=f"SYN-{uuid.uuid4().hex[:8]}", name=f"POVU {kind} outlet {i}", currency="KES",
                         email=f"{kind}{i}-{uuid.uuid4().hex[:4]}@povu-demo.test")
            db.add(c)
            await db.flush()
            ids[kind].append(c.id)
            start = today - timedelta(days=420)
            stop = today if kind == "steady" else today - timedelta(days=150 + 20 * (i % 8))
            d, k = start + timedelta(days=i % 5), 0
            while d < stop:
                db.add(SalesOrder(order_no=f"SO-SYN-{uuid.uuid4().hex[:10]}", customer_id=c.id, order_date=d,
                                  requested_delivery_date=d, status=SOStatus.INVOICED, currency="KES"))
                d += timedelta(days=14 + (k % 3))
                k += 1
    await db.flush()
    return ids


@DB
@pytest.mark.asyncio
async def test_churn_health_intent_on_synthetic_cohorts():
    from sqlalchemy import func, select
    from app.db.session import AsyncSessionLocal
    from app.models.customer_intel import CIAlert
    from app.models.sales import Customer, SalesOrder, SOStatus
    today = date(2026, 11, 26)
    async with AsyncSessionLocal() as db:
        ids = await _cohort(db)
        steady = ids["steady"][0]
        # leakage: an order on/after the cut-off never changes the features at that cut-off
        cut = today - timedelta(days=60)
        before = (await ci.features(db, [steady], cut))[steady]
        db.add(SalesOrder(order_no=f"SO-SYN-{uuid.uuid4().hex[:10]}", customer_id=steady, order_date=cut,
                          requested_delivery_date=cut, status=SOStatus.INVOICED, currency="KES"))
        await db.flush()
        after = (await ci.features(db, [steady], cut))[steady]
        assert (before.orders_total, before.last_order) == (after.orders_total, after.last_order)
        # cold start
        new = Customer(code=f"SYN-{uuid.uuid4().hex[:8]}", name="POVU new outlet", currency="KES")
        db.add(new)
        await db.flush()
        cold = (await ci.churn(db, [new.id], today))[new.id]
        assert cold["probability"] is None and "Insufficient history" in cold["reason"]
        assert (await ci.health(db, [new.id], today))[new.id]["label"] == "not enough data"
        # rule fallback before training, then a time-aware model
        assert (await ci.churn(db, [ids["lapsing"][0]], today))[ids["lapsing"][0]]["method"] == "rule"
        out = await ci.train_churn(db, "tester", today=today)
        assert out["trained"], out
        m = out["metrics"]
        assert m["split_date"] > m["train_until"] or m["train_until"] < m["split_date"]
        assert m["n_valid"] > 0 and m["auc"] is not None and m["auc"] >= 0.7 and "synthetic" in m["note"]
        risk = await ci.churn(db, [steady, ids["lapsing"][0]], today)
        assert risk[steady]["method"] == "model" and risk[steady]["probability"] < risk[ids["lapsing"][0]]["probability"]
        assert len(risk[steady]["factors"]) == 3
        hs = await ci.health(db, [steady, ids["lapsing"][0]], today)
        assert hs[steady]["score"] > (hs[ids["lapsing"][0]]["score"] or 0)
        # alerts: once per cool-down
        first = await ci.run_daily(db, now=NOW)
        again = await ci.run_daily(db, now=NOW + timedelta(hours=1))
        assert first["alerts"] > 0 and again["alerts"] == 0
        n = (await db.execute(select(func.count()).select_from(CIAlert).where(CIAlert.customer_id == ids["lapsing"][0]))).scalar_one()
        assert n >= 1
        # scope: a rep without CRM-wide rights sees only owned customers
        rep = SimpleNamespace(id=uuid.uuid4(), is_superuser=False, roles=[])
        assert await ci.visible_customer_ids(db, rep) == set()
        await db.rollback()


@DB
@pytest.mark.asyncio
async def test_intent_from_quote_views_and_orders():
    from app.db.session import AsyncSessionLocal
    from app.models.sales import Customer, SalesOrder, SOStatus
    async with AsyncSessionLocal() as db:
        c = Customer(code=f"SYN-{uuid.uuid4().hex[:8]}", name="POVU intent outlet", currency="KES")
        db.add(c)
        await db.flush()
        d = date.today()
        db.add(SalesOrder(order_no=f"SO-SYN-{uuid.uuid4().hex[:10]}", customer_id=c.id, order_date=d,
                          requested_delivery_date=d, status=SOStatus.CONFIRMED, currency="KES"))
        await db.flush()
        out = await ci.intent(db, c.id)
        assert out["score"] > 0 and out["explanation"][0]["kind"] == "ORDER" and out["external_feed"] == "NOT_CONFIGURED"
        await db.rollback()
