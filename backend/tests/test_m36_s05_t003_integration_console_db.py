"""M36.S05.T003 integration console on disposable PostgreSQL: no fake SYNCED, backoff, secrets handling and
provider-unavailable behaviour."""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select, update

from app.db.session import AsyncSessionLocal, engine
from app.models.email_integration import EmailAccount, EmailProvider
from app.models.integrations import IntegrationLog
from app.services import integration_console_service as console

TASK_DB_ENV = "M36_S05_T003_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S05_T003_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s05_t003_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def test_scrub_and_backoff_pure():
    assert "hunter2" not in console.scrub("login failed password=hunter2 for x")
    assert "s3cr3t" not in console.scrub("GET https://user:s3cr3t@shop.example/api failed")
    assert "abc123" not in console.scrub("Authorization: Bearer abc123")
    t = datetime(2026, 11, 21, tzinfo=timezone.utc)
    assert console.backoff_until(0, t) is None
    assert console.backoff_until(1, t) == t + timedelta(minutes=1)
    assert console.backoff_until(3, t) == t + timedelta(minutes=4)
    assert console.backoff_until(30, t) == t + timedelta(hours=6)          # capped


@pytest.mark.asyncio
async def test_console_health_sync_refusals_backoff(monkeypatch):
    s = uuid4().hex[:8]
    user = SimpleNamespace(id=None, is_superuser=True)
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]

        rows = {r["provider"]: r for r in (await console.overview(db))["connectors"]}
        # nothing connected and nothing run: never reported as working
        assert rows["EMAIL_SYNC"]["health"] == "NOT_CONNECTED" and rows["EMAIL_SYNC"]["credentials"] == "NOT_SET"
        assert rows["CRM_SYNC"]["health"] == "STUB_ONLY" and rows["MARKETING_SYNC"]["health"] == "STUB_ONLY"
        assert not any(r["health"] == "HEALTHY" for r in rows.values())
        assert all("secret" not in str(r).lower() or r["notes"] for r in rows.values())

        for key, code in (("CRM_SYNC", 501), ("EMAIL_SYNC", 409), ("MPESA_DARAJA", 409), ("NOPE", 404)):
            with pytest.raises(console.SyncRefused) as e:
                await console.run_sync(db, key, user)
            assert e.value.status == code, key
        assert (await db.execute(select(func.count()).select_from(IntegrationLog))).scalar_one() == 0   # refusals log nothing

        # a connected mailbox whose sync fails: FAILED run recorded, error scrubbed, then backoff refuses
        db.add(EmailAccount(provider=EmailProvider.SMTP, email_address=f"sales-{s}@povu.example", imap_host="mail.povu.example",
                            imap_port=993, username="sales", secret_enc="x"))
        await db.commit()

        async def failing(_db):
            return {"accounts": 1, "imported": 0, "failed": 1}
        monkeypatch.setattr("app.services.email_mailbox_service.sync_all", failing)
        out = await console.run_sync(db, "EMAIL_SYNC", user)
        assert out["status"] == "FAILED"
        row = {r["provider"]: r for r in (await console.overview(db))["connectors"]}["EMAIL_SYNC"]
        assert row["health"] == "FAILING" and row["consecutive_failures"] == 1 and row["next_retry_at"] is not None
        with pytest.raises(console.SyncRefused) as e:
            await console.run_sync(db, "EMAIL_SYNC", user)
        assert e.value.status == 429 and e.value.retry_at is not None

        # after the wait a successful run makes it HEALTHY; the streak resets
        await db.execute(update(IntegrationLog).values(created_at=datetime.now(timezone.utc) - timedelta(minutes=5)))
        await db.commit()

        async def working(_db):
            return {"accounts": 1, "imported": 3, "failed": 0}
        monkeypatch.setattr("app.services.email_mailbox_service.sync_all", working)
        out = await console.run_sync(db, "EMAIL_SYNC", user)
        assert out == {**out, "status": "SUCCESS", "result": {"accounts": 1, "imported": 3, "failed": 0}}
        row = {r["provider"]: r for r in (await console.overview(db))["connectors"]}["EMAIL_SYNC"]
        assert row["health"] == "HEALTHY" and row["consecutive_failures"] == 0 and row["next_retry_at"] is None

        # a provider exception is recorded as FAILED with the secret scrubbed — never as synced
        async def boom(_db):
            raise RuntimeError("IMAP login failed password=hunter2")
        monkeypatch.setattr("app.services.email_mailbox_service.sync_all", boom)
        out = await console.run_sync(db, "EMAIL_SYNC", user)
        assert out["status"] == "FAILED" and "hunter2" not in out["error"]
        logged = (await db.execute(select(IntegrationLog).order_by(IntegrationLog.created_at.desc()).limit(1))).scalar_one()
        assert "hunter2" not in (logged.error_message or "")

        # the Shopify import is unavailable without its credentials
        with pytest.raises(console.SyncRefused) as e:
            await console.run_sync(db, "ECOMMERCE_SYNC", user)
        assert e.value.status == 409
