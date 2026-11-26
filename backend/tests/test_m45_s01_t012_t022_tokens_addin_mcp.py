"""M45.S01.T012 Outlook/Gmail add-ins and T022 MCP server, both on personal access tokens.

Unit: the Outlook manifest is well-formed and points at the shared sidebar; the Gmail manifest declares the
add-on trigger and only the narrow scopes; the sidebar page exists. DB (M45_DB=1): a local MCP client lists tools
by token scope, read calls respect RBAC, write calls only create approval requests (self-approval refused, a second
person's approval executes it), a revoked token is refused; the add-in API looks up a contact, logs an e-mail once,
and refuses a token without the crm.addin scope.
"""
import json
import os
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_manifests_and_sidebar():
    ns = {"o": "http://schemas.microsoft.com/office/appforoffice/1.1"}
    root = ET.parse(ROOT / "addins/outlook/manifest.xml").getroot()
    assert root.tag.endswith("OfficeApp") and uuid.UUID(root.find("o:Id", ns).text)
    for el in ("Version", "ProviderName", "DefaultLocale", "DisplayName", "Description", "IconUrl", "Hosts", "Requirements",
               "FormSettings", "Permissions"):
        assert root.find(f"o:{el}", ns) is not None, el
    src = root.find("o:FormSettings/o:Form/o:DesktopSettings/o:SourceLocation", ns).get("DefaultValue")
    assert src.endswith("/addin/sidebar.html?host=outlook") and src.startswith("https://")
    g = json.loads((ROOT / "addins/gmail/appsscript.json").read_text(encoding="utf-8"))
    assert g["addOns"]["gmail"]["contextualTriggers"][0]["onTriggerFunction"] == "onGmailMessage"
    assert "https://www.googleapis.com/auth/gmail.addons.current.message.readonly" in g["oauthScopes"]
    assert not any("gmail.modify" in s or "mail.google.com" in s for s in g["oauthScopes"])   # read-only access to mail
    assert "function onGmailMessage" in (ROOT / "addins/gmail/Code.gs").read_text(encoding="utf-8")
    html = (ROOT / "frontend/public/addin/sidebar.html").read_text(encoding="utf-8")
    assert 'src="loader.js"' in html and "Sign in to POVU ERP" in html      # M50.S01.T011: OAuth sign-in replaces the pasted token
    assert (ROOT / "frontend/public/addin/sidebar.js").exists() and root.find("o:Permissions", ns).text == "ReadItem"


async def _user(db, *, superuser=False, perms=()):
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.models.role import Permission, Role
    from app.models.user import User
    u = User(username=f"syn-{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex[:8]}@povu-demo.test", full_name="Synthetic user",
             hashed_password=hash_password(uuid.uuid4().hex), is_active=True, is_superuser=superuser)
    if perms:
        role = Role(name=f"syn-{uuid.uuid4().hex[:6]}", description="synthetic", is_active=True)
        for code in perms:
            p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
            if p is None:
                mod, act = code.split(".", 1)
                p = Permission(code=code, name=code, module=mod, action=act, is_active=True)
                db.add(p)
            role.permissions.append(p)
        db.add(role)
        u.roles.append(role)
    db.add(u)
    await db.flush()
    return u


def _client():
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


async def _rpc(c, token, method, params=None, rid=1):
    r = await c.post("/api/v1/public/mcp", headers={"Authorization": f"Bearer {token}"},
                     json={"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
    return r


@DB
@pytest.mark.asyncio
async def test_mcp_tools_rbac_approval_and_revocation():
    from datetime import date
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMRecord
    from app.models.sales import Customer, SalesOrder, SOStatus
    from app.services import pat_service as pats
    async with AsyncSessionLocal() as db:
        sales = await _user(db, perms=("sales.view", "crm.edit"))
        nobody = await _user(db)
        admin = await _user(db, superuser=True)
        cust = Customer(code=f"SYN-{uuid.uuid4().hex[:6]}", name="POVU MCP Outlet", currency="KES")
        db.add(cust)
        await db.flush()
        so = SalesOrder(order_no=f"SO-MCP-{uuid.uuid4().hex[:6]}", customer_id=cust.id, order_date=date.today(),
                        requested_delivery_date=date.today(), status=SOStatus.CONFIRMED, currency="KES")
        rec = CRMRecord(company_name="POVU MCP Outlet", assigned_rep_id=str(sales.id))
        db.add_all([so, rec])
        await db.flush()
        _, t_read = await pats.create(db, sales.id, "mcp", ["mcp.read"], 30)
        trw, t_rw = await pats.create(db, sales.id, "mcp", ["mcp.read", "mcp.write"], 30)
        _, t_none = await pats.create(db, nobody.id, "mcp", ["mcp.read"], 30)
        _, t_addin = await pats.create(db, sales.id, "addin", ["crm.addin"], 30)
        await db.commit()
        ids = {"so": so.order_no, "rec": str(rec.id), "admin": admin.id, "trw": trw.id}

    async with _client() as c:
        init = (await _rpc(c, t_read, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}})).json()
        assert init["result"]["serverInfo"]["name"] == "fmcg-erp"
        r = await c.post("/api/v1/public/mcp", headers={"Authorization": f"Bearer {t_read}"},
                         json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        assert r.status_code == 202
        names = {t["name"] for t in (await _rpc(c, t_read, "tools/list")).json()["result"]["tools"]}
        assert "order_status" in names and "propose_follow_up_task" not in names          # write tool needs mcp.write
        ok = (await _rpc(c, t_read, "tools/call", {"name": "order_status", "arguments": {"order_no": ids["so"]}})).json()["result"]
        assert not ok["isError"] and ok["structuredContent"]["status"] == "CONFIRMED"
        denied = (await _rpc(c, t_none, "tools/call", {"name": "order_status", "arguments": {"order_no": ids["so"]}})).json()["result"]
        assert denied["isError"] and "permission" in denied["content"][0]["text"]
        stock = (await _rpc(c, t_read, "tools/call", {"name": "stock_level", "arguments": {"sku": "x"}})).json()["result"]
        assert stock["isError"]                                                             # no inventory.view
        assert (await _rpc(c, t_addin, "tools/list")).status_code == 403                    # wrong scope
        prop = (await _rpc(c, t_rw, "tools/call", {"name": "propose_follow_up_task",
                                                    "arguments": {"crm_record_id": ids["rec"], "subject": "Call about POVU 500 ml"}})).json()["result"]
        assert not prop["isError"] and prop["structuredContent"]["status"] == "PENDING"
        req_id = prop["structuredContent"]["approval_request_id"]
        assert (await _rpc(c, t_read, "bogus")).json()["error"]["code"] == -32601

    async with AsyncSessionLocal() as db:
        from sqlalchemy import func, select
        from app.models.ai_hub import AIActionRequest, PersonalAccessToken
        from app.models.audit_log import AuditLog
        from app.models.crm import CRMActivity
        from app.models.user import User
        req = await db.get(AIActionRequest, uuid.UUID(req_id))
        assert req.status == "PENDING"
        assert (await db.execute(select(func.count()).select_from(CRMActivity).where(
            CRMActivity.crm_record_id == uuid.UUID(ids["rec"])))).scalar_one() == 0              # nothing written yet
        requester = await db.get(User, req.requested_by)
        with pytest.raises(PermissionError):
            await pats.decide(db, req, requester, True)                                        # no self-approval
        await pats.decide(db, req, await db.get(User, ids["admin"]), True)
        assert req.status == "DONE" and req.result["activity_id"]
        assert (await db.execute(select(func.count()).select_from(AuditLog).where(AuditLog.event_type == "MCP_TOOL_CALL"))).scalar_one() >= 1
        (await db.get(PersonalAccessToken, ids["trw"])).revoked_at = pats.now()
        await db.commit()
    async with _client() as c:
        assert (await _rpc(c, t_rw, "tools/list")).status_code == 401                         # revoked


@DB
@pytest.mark.asyncio
async def test_addin_api():
    from app.db.session import AsyncSessionLocal
    from app.models.crm import CRMContact, CRMContactAssociation, CRMRecord
    from app.services import pat_service as pats
    from datetime import datetime, timezone
    async with AsyncSessionLocal() as db:
        rep = await _user(db, perms=("crm.view", "crm.edit"))
        other = await _user(db, perms=("crm.view",))
        email = f"buyer-{uuid.uuid4().hex[:6]}@povu-demo.test"
        c = CRMContact(full_name="Buyer Synthetic", email=email, owner_user_id=rep.id)
        rec = CRMRecord(company_name="POVU Addin Outlet", assigned_rep_id=str(rep.id))
        db.add_all([c, rec])
        await db.flush()
        db.add(CRMContactAssociation(contact_id=c.id, object_type="crm_record", object_id=rec.id, label="primary",
                                     created_at=datetime.now(timezone.utc)))
        foreign = CRMRecord(company_name="Another rep's deal", assigned_rep_id=str(other.id))
        db.add(foreign)
        await db.flush()
        db.add(CRMContactAssociation(contact_id=c.id, object_type="crm_record", object_id=foreign.id, label="other",
                                     created_at=datetime.now(timezone.utc)))
        _, tok = await pats.create(db, rep.id, "outlook", ["crm.addin"], 30)
        _, tok_other = await pats.create(db, other.id, "outlook", ["crm.addin"], 30)
        _, tok_mcp = await pats.create(db, rep.id, "mcp", ["mcp.read"], 30)
        await db.commit()
        rid = str(rec.id)
    async with _client() as cl:
        h = {"Authorization": f"Bearer {tok}"}
        d = (await cl.get("/api/v1/public/crm-addin/lookup", params={"email": email}, headers=h)).json()
        assert d["found"] and [x["id"] for x in d["deals"]] == [rid]                         # other rep's deal hidden
        d2 = (await cl.get("/api/v1/public/crm-addin/lookup", params={"email": email},
                           headers={"Authorization": f"Bearer {tok_other}"})).json()
        assert d2["found"] and [x["company"] for x in d2["deals"]] == ["Another rep's deal"]       # only their own deal
        body = {"crm_record_id": rid, "subject": "Order POVU 500 ml", "body": "Please send 20 cartons", "message_id": "m1@povu-demo.test"}
        assert (await cl.post("/api/v1/public/crm-addin/log-email", json=body, headers=h)).status_code == 201
        assert (await cl.post("/api/v1/public/crm-addin/log-email", json=body, headers=h)).json() == {"duplicate": True}
        assert (await cl.post("/api/v1/public/crm-addin/note", json={"crm_record_id": rid, "text": "Prefers Friday"},
                              headers={"Authorization": f"Bearer {tok_other}"})).status_code == 404   # not their deal
        assert (await cl.get("/api/v1/public/crm-addin/templates", headers={"Authorization": f"Bearer {tok_mcp}"})).status_code == 403
        assert (await cl.get("/api/v1/public/crm-addin/templates", headers={"Authorization": "Bearer nope"})).status_code == 401
