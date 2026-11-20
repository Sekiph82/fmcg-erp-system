"""M36.S03.T001 sales document engagement on disposable PostgreSQL: share link creation and permissions,
customer-safe public view (no internal notes), view-event dedupe without storing IP/UA, expiry and
revocation, and that one link never reveals another quotation."""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select
from starlette.requests import Request

from app.api.v1.endpoints import documents_public as public
from app.api.v1.endpoints import quotation as api
from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMDocumentLink, CRMDocumentView
from app.models.quotation import Quotation, QuotationLine, QuoteStatus
from app.models.sales import Customer, CustomerChannel
from app.models.user import User

TASK_DB_ENV = "M36_S03_T001_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S03_T001_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s03_t001_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(uid, *codes, superuser=False):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uid, is_superuser=superuser, access_scopes=[], username="u", full_name="U",
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


def _request(ip: str, ua: str) -> Request:
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [(b"user-agent", ua.encode())],
                    "client": (ip, 5000)})


def _token(url: str) -> str:
    return url.rsplit("/d/", 1)[1]


@pytest.mark.asyncio
async def test_share_view_dedupe_expiry_revoke():
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        cust = Customer(code=f"DL-{s}", name="Mama Duka", channel=CustomerChannel.RETAIL, currency="KES")
        rep_row = User(email=f"dl-{s}@povu.example", username=f"dl{s}", full_name="Rep", hashed_password="x")
        db.add_all([cust, rep_row])
        await db.flush()
        quotes = []
        for n, status in ((1, QuoteStatus.SENT), (2, QuoteStatus.SENT), (3, QuoteStatus.REJECTED)):
            q = Quotation(quote_no=f"QT-{s}-{n}", customer_id=cust.id, status=status, quote_date=date(2026, 11, 20),
                          valid_until=date(2026, 12, 20), currency="KES", grand_total=Decimal("4200"),
                          notes="Delivery Friday", internal_notes="margin 31% - do not go below 4,000")
            db.add(q)
            await db.flush()
            db.add(QuotationLine(quote_id=q.id, line_no=1, description="POVU AllClean 1 L carton", qty=Decimal("20"),
                                 unit="CTN", unit_price=Decimal("210"), line_total=Decimal("4200")))
            quotes.append(q.id)
        await db.commit()

        rep, nobody = _user(rep_row.id, "sales.view", "sales.edit_all"), _user(uuid4(), "sales.view_all")
        with pytest.raises(HTTPException) as e:
            await api.create_share_link(quotes[0], api.ShareLinkIn(), db, nobody)
        assert e.value.status_code == 403
        with pytest.raises(HTTPException) as e:
            await api.create_share_link(quotes[2], api.ShareLinkIn(), db, rep)            # rejected quote
        assert e.value.status_code == 422
        await db.rollback()

        made = await api.create_share_link(quotes[0], api.ShareLinkIn(expires_in_days=7, label="Mama Duka buyer"), db, rep)
        tok = _token(made["url"])
        from uuid import UUID
        stored = (await db.execute(select(CRMDocumentLink.token_hash))).scalars().all()
        assert tok not in stored and made["state"] == "ACTIVE"

        doc = await public.shared_document(tok, db)
        flat = str(doc)
        assert doc["number"] == f"QT-{s}-1" and doc["lines"][0]["description"] == "POVU AllClean 1 L carton"
        assert "margin" not in flat and "4,000" not in flat and doc["notes"] == "Delivery Friday"
        assert f"QT-{s}-2" not in flat                                                   # only its own quote

        # GET alone (mail scanner prefetch) records nothing; the page's POST does, deduped per visitor
        assert (await api.list_share_links(quotes[0], db, rep))[0]["views"] == 0
        assert (await public.shared_document_viewed(tok, _request("41.90.1.1", "Safari"), db))["recorded"] is True
        assert (await public.shared_document_viewed(tok, _request("41.90.1.1", "Safari"), db))["recorded"] is False
        assert (await public.shared_document_viewed(tok, _request("102.2.2.2", "Chrome"), db))["recorded"] is True
        links = await api.list_share_links(quotes[0], db, rep)
        assert links[0]["views"] == 2 and links[0]["first_viewed_at"]
        hashes = (await db.execute(select(CRMDocumentView.viewer_hash).where(
            CRMDocumentView.link_id == UUID(made["id"])))).scalars().all()
        assert all("41.90" not in h and "Safari" not in h and len(h) == 64 for h in hashes)  # no raw IP/UA

        # expiry: same 'not available' answer as an unknown token
        link = await db.get(CRMDocumentLink, UUID(made["id"]))
        link.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await db.commit()
        for bad in (tok, "x" * 32):
            with pytest.raises(HTTPException) as e:
                await public.shared_document(bad, db)
            assert e.value.status_code == 404

        # a quote withdrawn later (expired / rejected) is no longer shown, even through a valid link
        q2_link = await api.create_share_link(quotes[1], api.ShareLinkIn(), db, rep)
        await public.shared_document(_token(q2_link["url"]), db)
        (await db.get(Quotation, quotes[1])).status = QuoteStatus.EXPIRED
        await db.commit()
        with pytest.raises(HTTPException):
            await public.shared_document(_token(q2_link["url"]), db)

        # revoke a fresh link: stops at once, and only an editor may revoke
        fresh = await api.create_share_link(quotes[0], api.ShareLinkIn(), db, rep)
        await public.shared_document(_token(fresh["url"]), db)
        with pytest.raises(HTTPException):
            await api.revoke_share_link(UUID(fresh["id"]), db, nobody)
        assert (await api.revoke_share_link(UUID(fresh["id"]), db, rep))["state"] == "REVOKED"
        with pytest.raises(HTTPException):
            await public.shared_document(_token(fresh["url"]), db)
        with pytest.raises(HTTPException):
            await public.shared_document_viewed(_token(fresh["url"]), _request("1.1.1.1", "x"), db)
