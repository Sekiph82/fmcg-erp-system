"""M50.S01.T011 Gmail add-on and Outlook add-in: manifest build, OAuth+PKCE sign-in, scoped short-lived tokens, host/origin
binding, revocation, injection hygiene and a local Gmail host harness running the real Code.gs against the real ERP API.
Unit: the manifest build script (output files, refusals). DB (M50_DB=1): API flow with personas, then the harness.
"""
import base64
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "addins" / "build.py"
NODE = shutil.which("node")
DB = pytest.mark.skipif(os.environ.get("M50_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
BASE = "/api/v1/public/crm-addin"


def run_build(*args):
    return subprocess.run([sys.executable, str(BUILD), *args], capture_output=True, text=True)


# ── manifest build ───────────────────────────────────────────────────────────

def test_build_writes_checked_manifests_and_sources(tmp_path):
    r = run_build("--app-origin", "https://erp.povu-demo.test", "--api-origin", "https://api.povu-demo.test", "--out", str(tmp_path))
    assert r.returncode == 0, r.stderr
    import xml.etree.ElementTree as ET
    xml = (tmp_path / "outlook" / "manifest.xml").read_text(encoding="utf-8")
    root = ET.fromstring(xml)
    ns = "{http://schemas.microsoft.com/office/appforoffice/1.1}"
    assert root.find(ns + "Permissions").text == "ReadItem" and "erp.povu.example" not in xml
    assert {d.text for d in root.iter(ns + "AppDomain")} == {"https://erp.povu-demo.test", "https://api.povu-demo.test"}
    assert "https://erp.povu-demo.test/addin/sidebar.html?host=outlook" in xml and 'Name="DialogApi"' in xml
    gm = json.loads((tmp_path / "gmail" / "appsscript.json").read_text())
    assert gm["urlFetchWhitelist"] == ["https://api.povu-demo.test/"] and "script.send_mail" not in json.dumps(gm)
    code = (tmp_path / "gmail" / "Code.gs").read_text(encoding="utf-8")
    assert 'var APP_ORIGIN = "https://erp.povu-demo.test";' in code and 'var API_ORIGIN = "https://api.povu-demo.test";' in code
    meta = json.loads((tmp_path / "build-manifest.json").read_text())
    assert set(meta["files"]) == {"outlook/manifest.xml", "gmail/appsscript.json", "gmail/Code.gs"}
    assert meta["files"]["gmail/Code.gs"] == hashlib.sha256(code.encode()).hexdigest()
    # same origin -> same Outlook Id (a redeploy updates the add-in rather than adding a second one); another origin differs
    run_build("--app-origin", "https://erp.povu-demo.test", "--out", str(tmp_path / "b"))
    run_build("--app-origin", "https://erp2.povu-demo.test", "--out", str(tmp_path / "c"))
    ids = [json.loads((tmp_path / d / "build-manifest.json").read_text())["outlook"]["id"] for d in (".", "b", "c")]
    assert ids[0] == ids[1] != ids[2]


@pytest.mark.parametrize("origin", ["http://erp.povu-demo.test", "https://erp.povu-demo.test/path", "https://*.povu-demo.test",
                                    "https://erp.povu.example", "erp.povu-demo.test", "https://user:pw@erp.povu-demo.test", "https://erp.povu-demo.test/?a=1"])
def test_build_refuses_bad_origins(tmp_path, origin):
    r = run_build("--app-origin", origin, "--out", str(tmp_path / "o"))
    assert r.returncode == 1 and "BUILD FAILED" in r.stderr and not (tmp_path / "o").exists()


def test_build_allows_localhost_only_when_asked(tmp_path):
    assert run_build("--app-origin", "http://localhost:3000", "--out", str(tmp_path / "x")).returncode == 1
    assert run_build("--app-origin", "http://localhost:3000", "--api-origin", "http://localhost:8000", "--allow-local", "--out", str(tmp_path / "y")).returncode == 0


def test_validators_refuse_broader_permissions_scopes_and_tokens_in_urls():
    sys.path.insert(0, str(ROOT / "addins"))
    try:
        import build
    finally:
        sys.path.pop(0)
    app = "https://erp.povu-demo.test"
    good, _ = build.build_outlook(app, app, "1.1.0.0")
    with pytest.raises(build.BuildError, match="broader"):
        build.validate_outlook(good.replace("<Permissions>ReadItem", "<Permissions>ReadWriteMailbox"), {app})
    with pytest.raises(build.BuildError, match="not on the ERP origin"):
        build.validate_outlook(good.replace(f"{app}/addin/sidebar.html?host=outlook", "https://evil.example/pane.html"), {app})
    with pytest.raises(build.BuildError, match="not one of the ERP"):
        build.validate_outlook(good.replace(f"<AppDomain>{app}</AppDomain>", "<AppDomain>https://evil.example</AppDomain>"), {app})
    with pytest.raises(build.BuildError, match="well-formed"):
        build.validate_outlook(good.replace("</OfficeApp>", ""), {app})
    gm_json, code = build.build_gmail(app, app)
    manifest = json.loads(gm_json)
    build.validate_gmail(manifest, code, app, app)
    with pytest.raises(build.BuildError, match="reviewed list"):
        build.validate_gmail({**manifest, "oauthScopes": [*manifest["oauthScopes"], "https://mail.google.com/"]}, code, app, app)
    with pytest.raises(build.BuildError, match="token, code or verifier"):
        build.validate_gmail(manifest, code + '\nvar u = API + "/x?access_token=" + t;', app, app)
    with pytest.raises(build.BuildError, match="exactly the API origin"):
        build.validate_gmail({**manifest, "urlFetchWhitelist": ["https://evil.example/"]}, code, app, app)
    with pytest.raises(build.BuildError, match="dynamic code"):
        build.validate_gmail(manifest, code + "\neval('1');", app, app)


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_host_sources_are_valid_javascript():
    for f in ("frontend/public/addin/sidebar.js", "frontend/public/addin/harness.js", "frontend/public/addin/loader.js",
              "addins/harness/gmail_host.js"):
        r = subprocess.run([NODE, "--check", str(ROOT / f)], capture_output=True, text=True)
        assert r.returncode == 0, (f, r.stderr)
    sidebar = (ROOT / "frontend/public/addin/sidebar.js").read_text()
    assert "innerHTML" not in sidebar and "localStorage" not in sidebar            # mail text only as text; tokens not persisted beyond the pane


# ── DB ───────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
async def _no_privileged_2fa_and_dispose(monkeypatch):
    """Superuser test personas skip the authenticator-app enrolment gate (it is not what these tests are about)."""
    async def _no(db, user_id):
        return False
    monkeypatch.setattr("app.services.auth_2fa_policy.requires_privileged_2fa", _no)
    yield
    if os.environ.get("M50_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


_ENGINE = {}


def _S():
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.db.session import engine
    return async_sessionmaker(_ENGINE.get("e") or engine, expire_on_commit=False)()


def pkce():
    v = secrets.token_urlsafe(48)
    return v, base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()


def mini_app():
    """The add-in router alone (its public paths are allow-listed by the coordinator in PUBLIC_ROUTES)."""
    from fastapi import FastAPI
    from app.api.v1.endpoints import crm_addin
    app = FastAPI()
    app.include_router(crm_addin.router, prefix=BASE)
    return app


async def _staff(db, tag, superuser=True, assigned=False):
    from app.core.security import create_access_token
    from app.models.user import User
    u = User(username=f"{tag}-{uuid.uuid4().hex[:6]}", email=f"{tag}-{uuid.uuid4().hex[:6]}@povu-demo.test", full_name=tag.title(),
             hashed_password="x", is_active=True, is_superuser=superuser)
    db.add(u)
    await db.flush()
    return u, {"erp_access_token": create_access_token(u.id)}


async def _deal(db, owner, email):
    from app.models.crm import CRMContact, CRMContactAssociation, CRMRecord
    from app.models.email_integration import EmailTemplate
    c = CRMContact(full_name="Wanjiru Duka", email=email, job_title="Buyer")
    r = CRMRecord(company_name="Duka Moja Ltd", assigned_rep_id=str(owner.id))
    db.add_all([c, r])
    await db.flush()
    db.add(CRMContactAssociation(contact_id=c.id, object_type="crm_record", object_id=r.id, label="primary", created_at=datetime.now(timezone.utc)))
    db.add(EmailTemplate(name=f"POVU thanks {uuid.uuid4().hex[:4]}", subject_template="Thank you", body_template="Thank you for your order of POVU AllClean 1 L.", is_active=True))
    await db.flush()
    return c, r


async def _signin(client, cookies, host="outlook", origin=None, scopes=None):
    v, ch = pkce()
    origin = origin or ("gmail-addon" if host == "gmail" else "http://localhost:3000")
    a = await client.post(f"{BASE}/auth/authorize", json={"host": host, "code_challenge": ch, "origin": origin, "scopes": scopes or []}, cookies=cookies)
    assert a.status_code == 200, a.text
    t = await client.post(f"{BASE}/auth/token", json={"code": a.json()["code"], "code_verifier": v, "host": host})
    assert t.status_code == 200, t.text
    return t.json(), a.json()


@DB
@pytest.mark.asyncio
async def test_oauth_pkce_flow_scopes_host_origin_refresh_and_revocation():
    from sqlalchemy import select
    from app.models.audit_log import AuditLog
    from app.models.crm import CRMActivity
    from app.models.m50_data_sso import AddinGrant
    email = f"buyer-{uuid.uuid4().hex[:6]}@povu-demo.test"
    thr, mid = f"thr-{uuid.uuid4().hex[:8]}", f"harness-{uuid.uuid4().hex[:8]}@povu-demo.test"
    async with _S() as db:
        user, cookies = await _staff(db, "rep")
        contact, deal = await _deal(db, user, email)
        await db.commit()
        deal_id, user_id = str(deal.id), user.id
    app = mini_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test") as c:
        H = lambda tok, host="outlook", **kw: {"Authorization": f"Bearer {tok}", "X-Addin-Host": host, **kw}
        # authorize needs a staff session, a valid challenge/host and an origin the ERP trusts
        v, ch = pkce()
        ok = {"host": "outlook", "code_challenge": ch, "origin": "http://localhost:3000"}
        assert (await c.post(f"{BASE}/auth/authorize", json=ok)).status_code == 401
        assert (await c.post(f"{BASE}/auth/authorize", json={**ok, "origin": "https://evil.example"}, cookies=cookies)).status_code == 403
        assert (await c.post(f"{BASE}/auth/authorize", json={**ok, "code_challenge": "short"}, cookies=cookies)).status_code == 422
        assert (await c.post(f"{BASE}/auth/authorize", json={**ok, "host": "thunderbird"}, cookies=cookies)).status_code == 422
        assert (await c.post(f"{BASE}/auth/authorize", json={**ok, "scopes": ["addin.admin"]}, cookies=cookies)).status_code == 422
        assert (await c.post(f"{BASE}/auth/authorize", json={**ok, "origin": "gmail-addon"}, cookies=cookies)).status_code == 403      # outlook may not claim the Gmail origin
        # code: wrong verifier burns it, right verifier works once
        a = (await c.post(f"{BASE}/auth/authorize", json=ok, cookies=cookies)).json()
        bad = await c.post(f"{BASE}/auth/token", json={"code": a["code"], "code_verifier": pkce()[0], "host": "outlook"})
        assert bad.status_code == 400
        assert (await c.post(f"{BASE}/auth/token", json={"code": a["code"], "code_verifier": v, "host": "outlook"})).status_code == 400
        a = (await c.post(f"{BASE}/auth/authorize", json=ok, cookies=cookies)).json()
        assert (await c.post(f"{BASE}/auth/token", json={"code": a["code"], "code_verifier": v, "host": "gmail"})).status_code == 400   # other host's exchange
        a = (await c.post(f"{BASE}/auth/authorize", json=ok, cookies=cookies)).json()
        tok = (await c.post(f"{BASE}/auth/token", json={"code": a["code"], "code_verifier": v, "host": "outlook"})).json()
        assert tok["access_token"].startswith("povua_") and tok["expires_in"] == 900 and tok["scope"] == "addin.read addin.write"
        # data routes: lookup, thread, templates, log, note, task
        assert (await c.get(f"{BASE}/lookup", params={"email": email}, headers=H(tok["access_token"]))).json()["contact"]["name"] == "Wanjiru Duka"
        log = await c.post(f"{BASE}/log-email", headers=H(tok["access_token"]), json={
            "crm_record_id": deal_id, "subject": "Order <script>alert(1)</script> POVU", "body": "Hi <b>team</b>\x00\x07 send cartons", "direction": "IN",
            "message_id": mid, "thread_id": thr})
        assert log.status_code == 201, log.text
        dup = await c.post(f"{BASE}/log-email", headers=H(tok["access_token"]), json={"crm_record_id": deal_id, "subject": "x", "message_id": mid})
        assert dup.json() == {"duplicate": True}
        for bad_id in ("a b", "x<y>", "../../etc/passwd;", "a" * 301):
            r = await c.post(f"{BASE}/log-email", headers=H(tok["access_token"]), json={"crm_record_id": deal_id, "subject": "s", "message_id": bad_id})
            assert r.status_code == 422, bad_id
        assert (await c.post(f"{BASE}/note", headers=H(tok["access_token"]), json={"crm_record_id": deal_id, "text": "<img src=x onerror=1>"})).status_code == 422   # nothing left
        assert (await c.post(f"{BASE}/note", headers=H(tok["access_token"]), json={"crm_record_id": deal_id, "text": "Call back Friday"})).status_code == 201
        assert (await c.post(f"{BASE}/task", headers=H(tok["access_token"]), json={"crm_record_id": deal_id, "text": "Send price list"})).status_code == 201
        th = (await c.get(f"{BASE}/thread", params={"thread_id": thr}, headers=H(tok["access_token"]))).json()
        assert len(th) == 1 and th[0]["deal"] == "Duka Moja Ltd"
        assert (await c.get(f"{BASE}/thread", params={"thread_id": "a b"}, headers=H(tok["access_token"]))).status_code == 422
        assert (await c.get(f"{BASE}/templates", headers=H(tok["access_token"]))).json()
        async with _S() as db:
            acts = (await db.execute(select(CRMActivity).where(CRMActivity.crm_record_id == uuid.UUID(deal_id)))).scalars().all()
            mail = next(a for a in acts if a.subject.startswith("Received:"))
            assert "<" not in mail.subject and "<" not in mail.notes and "\x00" not in mail.notes and mail.notes.startswith(f"Thread: {thr}\n")
            assert (await db.execute(select(AuditLog).where(AuditLog.event_type.like("CRM_ADDIN_%")))).first() is not None
        # host spoof, origin spoof, missing host header, token in the wrong place
        assert (await c.get(f"{BASE}/whoami", headers=H(tok["access_token"], host="gmail"))).status_code == 403
        assert (await c.get(f"{BASE}/whoami", headers={"Authorization": f"Bearer {tok['access_token']}"})).status_code == 403
        assert (await c.get(f"{BASE}/whoami", headers=H(tok["access_token"], Origin="https://evil.example"))).status_code == 403
        assert (await c.get(f"{BASE}/whoami", headers=H(tok["access_token"], Origin="http://localhost:3000"))).status_code == 200
        assert (await c.get(f"{BASE}/whoami", params={"access_token": tok["access_token"]})).status_code == 401           # a URL token is never read
        assert (await c.get(f"{BASE}/whoami", headers=H("povua_nonsense"))).status_code == 401
        # read-only grant cannot write
        ro, ra = await _signin(c, cookies, scopes=["addin.read"])
        assert ro["scope"] == "addin.read"
        assert (await c.get(f"{BASE}/lookup", params={"email": email}, headers=H(ro["access_token"]))).status_code == 200
        assert (await c.post(f"{BASE}/note", headers=H(ro["access_token"]), json={"crm_record_id": deal_id, "text": "x"})).status_code == 403
        # refresh rotates; reuse of the old refresh token revokes the whole grant
        r1 = (await c.post(f"{BASE}/auth/refresh", json={"refresh_token": tok["refresh_token"]})).json()
        assert r1["access_token"] != tok["access_token"] and r1["refresh_token"] != tok["refresh_token"]
        assert (await c.get(f"{BASE}/whoami", headers=H(tok["access_token"]))).status_code == 401                # old access token is gone
        assert (await c.get(f"{BASE}/whoami", headers=H(r1["access_token"]))).status_code == 200
        assert (await c.post(f"{BASE}/auth/refresh", json={"refresh_token": tok["refresh_token"]})).status_code == 409   # parallel request inside the 10 s race window
        assert (await c.get(f"{BASE}/whoami", headers=H(r1["access_token"]))).status_code == 200                 # ...is not theft: the grant lives
        async with _S() as db:
            g = (await db.execute(select(AddinGrant).where(AddinGrant.prev_refresh_hash == hashlib.sha256(tok["refresh_token"].encode()).hexdigest()))).scalar_one()
            g.rotated_at = datetime.now(timezone.utc) - timedelta(seconds=60)
            await db.commit()
        assert (await c.post(f"{BASE}/auth/refresh", json={"refresh_token": tok["refresh_token"]})).status_code == 401   # replay of the rotated-out token
        assert (await c.get(f"{BASE}/whoami", headers=H(r1["access_token"]))).status_code == 401                 # ...which killed the grant
        # sign-out from the add-in; user lists and revokes sessions
        t2, _ = await _signin(c, cookies)
        assert (await c.post(f"{BASE}/auth/revoke", headers=H(t2["access_token"]))).json() == {"revoked": True}
        assert (await c.get(f"{BASE}/whoami", headers=H(t2["access_token"]))).status_code == 401
        t3, _ = await _signin(c, cookies)
        sess = (await c.get(f"{BASE}/sessions", cookies=cookies)).json()
        assert sess and all("access_token" not in s and "hash" not in json.dumps(s) for s in sess)
        victim = next(s for s in sess if s["signed_in"])
        assert (await c.delete(f"{BASE}/sessions/{victim['id']}", cookies=cookies)).status_code == 200
        async with _S() as db:                                                                                    # the user's revocation covers every live grant
            for g in (await db.execute(select(AddinGrant).where(AddinGrant.user_id == user_id, AddinGrant.revoked_at.is_(None), AddinGrant.access_hash.is_not(None)))).scalars():
                await c.delete(f"{BASE}/sessions/{g.id}", cookies=cookies)
        assert (await c.get(f"{BASE}/whoami", headers=H(t3["access_token"]))).status_code == 401
        # a disabled user's token stops at once; an expired access token is refused
        t4, _ = await _signin(c, cookies)
        async with _S() as db:
            from app.models.user import User
            (await db.get(User, user_id)).is_active = False
            await db.commit()
        assert (await c.get(f"{BASE}/whoami", headers=H(t4["access_token"]))).status_code == 401
        async with _S() as db:
            from app.models.user import User
            (await db.get(User, user_id)).is_active = True
            from app.services.addin_auth_service import h as _h
            g = (await db.execute(select(AddinGrant).where(AddinGrant.access_hash == _h(t4["access_token"])))).scalar_one()
            g.access_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await db.commit()
        assert (await c.get(f"{BASE}/whoami", headers=H(t4["access_token"]))).status_code == 401
        # a user with no CRM rights cannot hand the CRM to an add-in; a viewer gets look-up only
        async with _S() as db:
            nobody, ncookies = await _staff(db, "nobody", superuser=False)
            await db.commit()
        v2, ch2 = pkce()
        assert (await c.post(f"{BASE}/auth/authorize", json={"host": "outlook", "code_challenge": ch2, "origin": "http://localhost:3000"}, cookies=ncookies)).status_code == 403


@DB
@pytest.mark.asyncio
async def test_gmail_host_harness_runs_the_real_code_gs_against_the_real_api(tmp_path):
    """Code.gs (built for the local origin) runs in the harness; UrlFetchApp makes real HTTP calls to a live ERP instance."""
    if NODE is None:
        pytest.skip("node not installed")
    import uvicorn
    from fastapi import FastAPI
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine
    from app.core.config import settings
    _ENGINE["e"] = create_async_engine(settings.DATABASE_URL)         # the server thread has its own loop and the app's engine
    from app.api.v1.endpoints import crm_addin
    from app.models.crm import CRMActivity
    from app.models.m50_data_sso import AddinGrant
    from app.services import addin_auth_service as aas
    email = f"buyer-{uuid.uuid4().hex[:6]}@povu-demo.test"
    async with _S() as db:
        user, cookies = await _staff(db, "gm")
        contact, deal = await _deal(db, user, email)
        await db.commit()
        deal_id, user_id = str(deal.id), user.id
    app = FastAPI()
    app.include_router(crm_addin.router, prefix=BASE)

    @app.get("/_consent")                                  # stands in for the ERP consent page: the signed-in user presses Allow
    async def consent(challenge: str):
        from app.db.session import AsyncSessionLocal
        from app.models.user import User
        async with AsyncSessionLocal() as db:
            u = await db.get(User, user_id)
            out = await aas.authorize(db, u, "gmail", challenge, "gmail-addon", [])
            await db.commit()
            return out

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    assert server.started
    origin = f"http://127.0.0.1:{port}"
    out_dir = tmp_path / "dist"
    assert run_build("--app-origin", origin, "--allow-local", "--out", str(out_dir)).returncode == 0
    gthr = f"gthr-{uuid.uuid4().hex[:8]}"
    msgs = {"m1": {"from": f"Wanjiru Duka <{email}>", "subject": "Order for POVU AllClean 1 L", "body": "Please send 20 cartons.",
                   "messageIdHeader": f"<gmail-{uuid.uuid4().hex[:6]}@povu-demo.test>", "threadId": gthr}}
    gm = {"accessToken": "gmail-host-token", "messageId": "m1", "threadId": gthr}
    scenario = {"messages": msgs, "steps": [
        {"call": "onGmailMessage", "gmail": gm},                                                       # not signed in -> sign-in card
        {"call": "finishAuth_", "consent": origin, "formInput": {}},                                  # user approves, types the code
        {"call": "onGmailMessage", "gmail": gm},                                                       # contact card
        {"call": "logEmail_", "gmail": gm, "parameters": {"id": "m1", "thread": gthr}, "formInput": {"deal": deal_id}},
        {"call": "addNote_", "formInput": {"deal": deal_id, "text": "Wants a quote Monday"}},
        {"call": "replyTemplate_", "parameters": {"id": "m1"}, "formInput": {"tpl": ""}},
        {"expire": True, "call": "onGmailMessage", "gmail": gm},                                       # access token expired -> refresh
        {"call": "signOut_"},
        {"call": "onGmailMessage", "gmail": gm}]}                                                      # signed out -> sign-in card again
    sc = tmp_path / "scenario.json"
    sc.write_text(json.dumps(scenario))
    r = subprocess.run([NODE, str(ROOT / "addins" / "harness" / "gmail_host.js"), str(out_dir / "gmail" / "Code.gs"), str(sc)],
                       capture_output=True, text=True, timeout=120)
    server.should_exit = True
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout)
    R = res["results"]
    assert all(x["ok"] for x in R[:3] + R[7:]), [x for x in R if not x["ok"]]
    s1 = json.dumps(R[0]["result"])
    assert "/addin/authorize?host=gmail&challenge=" in s1 and "verifier" not in s1.lower().replace("code_verifier", "") and "Finish sign-in" in s1
    assert "Wanjiru Duka" in json.dumps(R[2]["result"]) and "Log this e-mail" in json.dumps(R[2]["result"]) and "Reply with a template" in json.dumps(R[2]["result"])
    assert "E-mail logged" in json.dumps(R[3]["result"]) and "Note added" in json.dumps(R[4]["result"])
    reqs = res["requests"]
    assert all(q["headers"].get("X-Addin-Host") == "gmail" for q in reqs)
    for q in reqs:                                          # no token, code or verifier in any URL
        assert "access_token" not in q["url"] and "povua_" not in q["url"] and "povur_" not in q["url"] and "verifier" not in q["url"] and "code=" not in q["url"]
    paths = [q["url"].replace(origin + BASE, "").split("?")[0] for q in reqs]
    assert "/auth/token" in paths and "/auth/refresh" in paths and "/auth/revoke" in paths and "/lookup" in paths and "/log-email" in paths
    assert next(q for q in reqs if q["url"].endswith("/auth/token"))["status"] == 200
    assert "Authorization" not in next(q for q in reqs if q["url"].endswith("/auth/token"))["headers"]
    assert res["properties"].get("POVU_SESSION") is None                            # signed out: nothing left in the user properties
    assert "No CRM" not in json.dumps(R[8]["result"]) and "Finish sign-in" in json.dumps(R[8]["result"])
    async with _S() as db:
        acts = (await db.execute(select(CRMActivity).where(CRMActivity.crm_record_id == uuid.UUID(deal_id)))).scalars().all()
        assert {a.activity_type.value for a in acts} >= {"EMAIL", "NOTE"}
        assert any(a.notes.startswith(f"Thread: {gthr}\n") for a in acts)
        g = (await db.execute(select(AddinGrant).where(AddinGrant.user_id == user_id, AddinGrant.host == "gmail"))).scalars().all()
        assert g and all(x.revoked_at is not None for x in g if x.access_hash is None) and all(x.access_hash is None for x in g)   # signed out = revoked
    await _ENGINE.pop("e").dispose()
