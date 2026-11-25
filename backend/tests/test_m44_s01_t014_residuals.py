"""M44.S01.T014 M43 review residuals (unit + DB part with M44_DB=1).

Unit: the access-log filter masks ?token= in a uvicorn access record.
DB: unknown foreign keys return 422 (not 500): team member, saved-view team, deal split user, dialer record/customer.
"""
import logging
import os
import uuid

import pytest

from app.core.log_redaction import RedactQuerySecrets, redact


def test_access_log_redacts_callback_token():
    rec = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
                            ("10.0.0.1:5000", "POST", "/api/v1/calls/provider/callback?token=s3cr3t-value&x=1", "1.1", 200), None)
    assert RedactQuerySecrets().filter(rec)
    line = rec.getMessage()
    assert "s3cr3t-value" not in line and "token=[REDACTED]&x=1" in line
    assert redact("/a?access_token=abc") == "/a?access_token=[REDACTED]" and redact("/a?page=2") == "/a?page=2"


DB = pytest.mark.skipif(os.environ.get("M44_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M44_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


@DB
@pytest.mark.asyncio
async def test_unknown_foreign_keys_are_422():
    from httpx import ASGITransport, AsyncClient

    from app.core.deps import get_current_user
    from app.db.session import AsyncSessionLocal
    from app.main import app
    from app.models.crm import CRMRecord, CRMTeam
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        admin = User(id=uuid.uuid4(), email=f"adm-{uuid.uuid4().hex[:6]}@povu-demo.test", username=f"syn-{uuid.uuid4().hex[:12]}",
                     hashed_password="x", full_name="Admin", is_active=True, is_superuser=True)
        team = CRMTeam(code=f"T-{uuid.uuid4().hex[:6]}", name="POVU North")
        rec = CRMRecord(company_name="POVU Synthetic Outlet")
        db.add_all([admin, team, rec])
        await db.commit()
        admin_id, team_id, rec_id = admin.id, team.id, rec.id
    ghost = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: admin
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.put(f"/api/v1/crm-teams/teams/{team_id}/members", json={"user_id": ghost})
            assert r.status_code == 422, r.text
            r = await c.post("/api/v1/crm-teams/views", json={"name": "Mine", "team_id": ghost})
            assert r.status_code == 422, r.text
            r = await c.put(f"/api/v1/crm-routing/records/{rec_id}/splits", json=[{"user_id": ghost, "share_pct": "100"}])
            assert r.status_code == 422, r.text
            for item in ({"crm_record_id": ghost}, {"customer_id": ghost}):
                r = await c.post("/api/v1/calls/dialer", json={"name": "POVU calls", "items": [{"phone": "+254700000001", **item}]})
                assert r.status_code == 422 and ghost in r.text, r.text
            ok = await c.put(f"/api/v1/crm-teams/teams/{team_id}/members", json={"user_id": str(admin_id)})
            assert ok.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)
