"""M36.S04.T001 AI sales copilot on disposable PostgreSQL with a fake model: evidence from the permitted
timeline only, unsupported claims dropped, PII redacted before the prompt, provider-off and provider-error
fallbacks, permission checks, and nothing sent."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1.endpoints import crm_pipeline as api
from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMOutboundMessage
from app.models.helpdesk import HelpdeskTicket
from app.models.quotation import Quotation, QuoteStatus
from app.models.sales import Customer, CustomerChannel
from app.services import ai_provider

TASK_DB_ENV = "M36_S04_T001_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S04_T001_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s04_t001_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(*codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=None, is_superuser=False, access_scopes=[], email="rep@povu.example",
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


class FakeModel:
    def __init__(self, answer=None, error=None):
        self.answer, self.error, self.prompts = answer, error, []

    async def generate_structured_output(self, prompt, system=None, schema_hint=None):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.answer, SimpleNamespace(prompt_tokens=10, completion_tokens=20, latency_ms=5)


@pytest.mark.asyncio
async def test_copilot_grounding_pii_fallbacks(monkeypatch):
    # the AI rate limiter must not count against a reachable dev Redis (the synthetic users have id=None,
    # so earlier runs would share one key): keep it in this process
    monkeypatch.setattr("app.core.ai_rate_limiter._get_redis", lambda: None)
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        cust = Customer(code=f"CP-{s}", name="Mama Duka", channel=CustomerChannel.RETAIL, currency="KES")
        db.add(cust)
        await db.flush()
        db.add_all([
            HelpdeskTicket(ticket_no=f"TKT-{s}", subject="Broken caps, call 0712 345 678 or mama@duka.example", customer_id=cust.id),
            Quotation(quote_no=f"QT-{s}", customer_id=cust.id, status=QuoteStatus.SENT, quote_date=date(2026, 11, 18),
                      currency="KES", grand_total=Decimal("4200")),
        ])
        await db.commit()
        cid = str(cust.id)
        outbox_before = (await db.execute(select(func.count()).select_from(CRMOutboundMessage))).scalar_one()

    rep = _user("crm.view_all", "sales.view_all", "quality.view_all")
    body = api.CopilotIn(note="What should I do this week?")

    # provider off: rule-based brief from the same evidence
    monkeypatch.setattr(ai_provider, "get_ai_provider", lambda: ai_provider.MockProvider())
    async with AsyncSessionLocal() as db:
        r = await api.customer_copilot(cid, body, db, rep)
        assert r["mode"] == "rule_based" and r["evidence"]
        actions = " ".join(f["action"] for f in r["follow_ups"])
        assert f"TKT-{s}" in actions and f"QT-{s}" in actions
        flat = str(r["evidence"])
        assert "0712" not in flat and "mama@duka.example" not in flat and "[phone]" in flat and "[email]" in flat

    # AI: an unsupported follow-up (E99) and an uncited one are dropped; a cited one kept; PII never in the prompt
    good = {"summary": "Open quality ticket and a quotation waiting for an answer.", "summary_evidence": ["E1", "E2"],
            "follow_ups": [{"action": "Reply to the broken caps ticket", "due_in_days": 0, "evidence": ["E1"]},
                           {"action": "Offer 20% discount", "due_in_days": 1, "evidence": ["E99"]},
                           {"action": "Invite to a golf day", "due_in_days": 5, "evidence": []}],
            "draft": {"subject": "Your broken caps", "body": "Hello, we are replacing the cartons."}}
    model = FakeModel(good)
    monkeypatch.setattr(ai_provider, "get_ai_provider", lambda: model)
    async with AsyncSessionLocal() as db:
        r = await api.customer_copilot(cid, body, db, rep)
        assert r["mode"] == "ai" and r["dropped_unsupported"] == 2
        assert [f["action"] for f in r["follow_ups"]] == ["Reply to the broken caps ticket"]
        assert r["draft"]["subject"] == "Your broken caps"
        prompt = model.prompts[-1]
        assert "0712" not in prompt and "mama@duka.example" not in prompt and "E1" in prompt

    # uncited summary: replaced by the rule-based one
    model.answer = {**good, "summary": "They love us and will order 500 cartons.", "summary_evidence": ["E42"]}
    async with AsyncSessionLocal() as db:
        r = await api.customer_copilot(cid, body, db, rep)
        assert "500 cartons" not in r["summary"] and r["note"]

    # malformed answer and provider failure: rule-based with a note
    for m in (FakeModel({"nonsense": True}), FakeModel(error=TimeoutError("slow"))):
        monkeypatch.setattr(ai_provider, "get_ai_provider", lambda m=m: m)
        async with AsyncSessionLocal() as db:
            r = await api.customer_copilot(cid, body, db, rep)
            assert r["mode"] == "rule_based" and "note" in r

    # evidence follows permissions: without quality access the ticket is not evidence and is reported hidden
    model = FakeModel(good)
    monkeypatch.setattr(ai_provider, "get_ai_provider", lambda: model)
    async with AsyncSessionLocal() as db:
        r = await api.customer_copilot(cid, body, db, _user("crm.view_all", "sales.view_all"))
        assert "tickets" in r["hidden_sources"] and "Broken caps" not in model.prompts[-1]
        with pytest.raises(HTTPException) as e:
            await api.customer_copilot(cid, body, db, _user("hr.view"))
        assert e.value.status_code == 403
        # nothing was sent
        assert (await db.execute(select(func.count()).select_from(CRMOutboundMessage))).scalar_one() == outbox_before
