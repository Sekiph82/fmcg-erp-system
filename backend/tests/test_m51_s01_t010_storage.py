"""M51.S01.T010 pluggable storage (DB part needs M51_DB=1; the S3 part also needs M51_S3_TEST_ENDPOINT, a local MinIO).

Unit: SigV4 signer equals botocore's, Range parsing, signed token tamper/expiry.
DB, local and S3 backends: multipart/resumable upload with out-of-order parts, resume state, wrong part size, missing parts,
magic-byte check, quota, ClamAV fail-closed quarantine, signed URL + Range/HEAD/416, revoke/delete/expiry, no public listing,
second-person approval, CMS link, cleanup of expired sessions and retention, backup and hash-verified restore.
"""
import hashlib
import io
import os
import time
import uuid
import wave
from datetime import datetime, timedelta, timezone

import pytest

from app.services import m51_storage as st
from tests.m51_media_common import anon_client, client_for, clean_scan, ensure_tables, setv, staff

DB = pytest.mark.skipif(os.environ.get("M51_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
S3 = pytest.mark.skipif(not os.environ.get("M51_S3_TEST_ENDPOINT"), reason="requires a local MinIO (M51_S3_TEST_ENDPOINT)")
BASE = "/api/v1/media-studio"
PERMS = ("marketing.view", "marketing.create", "marketing.edit")


@pytest.fixture(autouse=True)
async def _cleanup():
    yield
    if os.environ.get("M51_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def wav_bytes(n_bytes: int) -> bytes:
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(8000)
        w.writeframes((bytes(range(256)) * (n_bytes // 256 + 1))[:max(0, n_bytes - 44)])
    return b.getvalue()


def test_sigv4_matches_botocore():
    pytest.importorskip("botocore")
    from botocore.auth import S3SigV4Auth
    from botocore.awsrequest import AWSRequest
    from botocore.credentials import Credentials
    from app.services.m51_s3 import sign_headers
    sha = hashlib.sha256(b"hello").hexdigest()
    url = "http://127.0.0.1:29000/m51-test/m51/ab%20cd.bin?partNumber=2&uploadId=x%2By"
    req = AWSRequest(method="PUT", url=url, data=b"hello", headers={"content-type": "application/octet-stream", "x-amz-content-sha256": sha})
    S3SigV4Auth(Credentials("AKID", "SECRET"), "s3", "us-east-1").add_auth(req)
    when = datetime.strptime(req.headers["X-Amz-Date"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)      # sign at botocore's instant
    h = sign_headers("PUT", url, {"content-type": "application/octet-stream"}, sha, "AKID", "SECRET", "us-east-1", when)
    assert h["authorization"] == req.headers["Authorization"]


def test_range_and_tokens(monkeypatch):
    assert st.parse_range(None, 100) is None
    assert st.parse_range("bytes=0-9", 100) == (0, 9)
    assert st.parse_range("bytes=90-", 100) == (90, 99)
    assert st.parse_range("bytes=-10", 100) == (90, 99)
    assert st.parse_range("bytes=50-500", 100) == (50, 99)
    for bad in ("bytes=100-110", "bytes=5-2", "items=1-2", "bytes=-"):
        with pytest.raises(st.StorageError) as e:
            st.parse_range(bad, 100)
        assert e.value.status == 416
    from types import SimpleNamespace
    o = SimpleNamespace(id=uuid.uuid4(), access_version=1)
    tok, _ = st.sign_access(o, "staff", 60, "u1")
    assert st.verify_token(tok)["o"] == str(o.id)
    for bad in (tok[:-2] + "xx", "x." + tok.split(".")[1], "junk", tok.split(".")[0]):
        with pytest.raises(st.StorageError):
            st.verify_token(bad)
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + 3600)
    with pytest.raises(st.StorageError):
        st.verify_token(tok)
    monkeypatch.setattr(time, "time", real)
    assert st.verify_token(tok)                                   # ttl is capped, not extended
    assert st.verify_token(st.sign_access(o, "staff", 99999, "u")[0])["e"] - int(real()) <= 900 + 2


async def _upload(c, name: str, data: bytes, part: int, order=None, drop_after=None):
    r = await c.post(f"{BASE}/storage/uploads", json={"file_name": name, "total_size": len(data), "part_size": part})
    assert r.status_code == 201, r.text
    s = r.json()
    n = s["parts_total"]
    order = order or list(range(1, n + 1))
    for i in order[:drop_after]:
        pr = await c.put(f"{BASE}/storage/uploads/{s['id']}/parts/{i}", content=data[(i - 1) * part:i * part], headers={"content-type": "application/octet-stream"})
        assert pr.status_code == 200, pr.text
    return s


async def _flow(monkeypatch, tmp_path, backend: str, part: int, size: int):
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.audit_log import AuditLog
    from app.models.m51_media import M51StorageObject, M51UploadSession
    await ensure_tables()
    clean_scan(monkeypatch)
    setv(monkeypatch, "MEDIA_STORAGE_PATH", str(tmp_path / "media"))
    setv(monkeypatch, "M51_STORAGE_BACKUP_PATH", str(tmp_path / "backup"))
    setv(monkeypatch, "M51_STORAGE_BACKEND", backend)
    setv(monkeypatch, "M51_STORAGE_PART_BYTES", part)
    setv(monkeypatch, "M51_STORAGE_QUOTA_BYTES", 1 << 40)
    async with AsyncSessionLocal() as db:
        maker, approver, viewer = (await staff(db, "maker", PERMS), await staff(db, "approver", PERMS + ("marketing.approve",)),
                                   await staff(db, "viewer", ("marketing.view",)))
        await db.execute(__import__("sqlalchemy").text("DELETE FROM m51_storage_quotas"))
        await db.commit()
    data = wav_bytes(size)
    async with client_for(maker) as c, client_for(approver) as a, client_for(viewer) as v, anon_client() as anon:
        # --- resumable multipart: parts 1 and 3 arrive, the client "drops", resumes with the missing one
        s = await _upload(c, "sample.wav", data, part, order=[3, 1], drop_after=2) if -(-len(data) // part) == 3 else await _upload(c, "sample.wav", data, part, order=[1], drop_after=1)
        state = (await c.get(f"{BASE}/storage/uploads/{s['id']}")).json()
        assert state["received_parts"] == ([1, 3] if s["parts_total"] == 3 else [1]) and state["status"] == "OPEN"
        assert (await c.post(f"{BASE}/storage/uploads/{s['id']}/complete")).status_code == 409          # missing parts
        wrong = await c.put(f"{BASE}/storage/uploads/{s['id']}/parts/2", content=data[:part - 1])
        assert wrong.status_code == 422
        for i in state_missing(s, state):
            assert (await c.put(f"{BASE}/storage/uploads/{s['id']}/parts/{i}", content=data[(i - 1) * part:i * part])).status_code == 200
        assert (await v.post(f"{BASE}/storage/uploads/{s['id']}/complete")).status_code == 403
        done = await c.post(f"{BASE}/storage/uploads/{s['id']}/complete")
        assert done.status_code == 200, done.text
        o = done.json()
        assert o["status"] == "READY" and o["scan_status"] == "CLEAN" and o["sha256"] == hashlib.sha256(data).hexdigest() and o["size"] == len(data)
        assert o["backend"] == backend and o["approval"] == "DRAFT"
        # --- signed access: Range, HEAD, 416, tamper
        u = (await c.post(f"{BASE}/storage/objects/{o['id']}/access-url", json={"ttl_seconds": 120})).json()
        path = u["url"].split("http://localhost:8000")[1]
        full = await anon.get(path)
        assert full.status_code == 200 and full.content == data and full.headers["accept-ranges"] == "bytes" and full.headers["cache-control"] == "private, no-store"
        r = await anon.get(path, headers={"range": "bytes=10-99"})
        assert r.status_code == 206 and r.content == data[10:100] and r.headers["content-range"] == f"bytes 10-99/{len(data)}"
        r = await anon.get(path, headers={"range": f"bytes={len(data) - 5}-"})
        assert r.status_code == 206 and r.content == data[-5:]
        assert (await anon.get(path, headers={"range": f"bytes={len(data) + 5}-"})).status_code == 416
        h = await anon.head(path)
        assert h.status_code == 200 and h.headers["content-length"] == str(len(data)) and not h.content
        assert (await anon.get(path[:-3] + "abc")).status_code == 404
        assert (await anon.get("/api/v1/public/media-files/")).status_code in (404, 405)
        # --- viewer cannot issue URLs; draft is not member-visible
        assert (await v.post(f"{BASE}/storage/objects/{o['id']}/access-url", json={})).status_code == 403
        # --- revoke ends every issued URL; a fresh one works
        assert (await a.post(f"{BASE}/storage/objects/{o['id']}/revoke")).status_code == 200
        assert (await anon.get(path)).status_code == 404
        path2 = (await c.post(f"{BASE}/storage/objects/{o['id']}/access-url", json={})).json()["url"].split("http://localhost:8000")[1]
        assert (await anon.get(path2)).status_code == 200
        # --- approval needs another person; CMS link needs approval
        assert (await c.post(f"{BASE}/storage/objects/{o['id']}/approve")).status_code == 403
        assert (await a.post(f"{BASE}/storage/objects/{o['id']}/to-cms-media", json={"title": "x"})).status_code == 409
        assert (await a.post(f"{BASE}/storage/objects/{o['id']}/approve")).status_code == 200
        # --- backup, lose the bytes, restore
        bk = (await a.post(f"{BASE}/storage/backups")).json()
        assert bk["status"] in ("COMPLETED", "PARTIAL") and bk["object_count"] >= 1   # PARTIAL = leftover rows of earlier runs whose bytes are gone
        be = st.get_backend(backend)
        await be.delete(await _key(o["id"]))               # the bytes are lost behind the database's back
        rs = (await a.post(f"{BASE}/storage/backups/{bk['id']}/restore")).json()
        assert o["id"] in rs["restored"] and not rs["failed"]
        assert (await anon.get(path2)).status_code == 404                         # restore revokes older URLs
        path3 = (await c.post(f"{BASE}/storage/objects/{o['id']}/access-url", json={})).json()["url"].split("http://localhost:8000")[1]
        assert (await anon.get(path3)).content == data
        # --- delete: URL dead, bytes gone
        assert (await a.delete(f"{BASE}/storage/objects/{o['id']}")).status_code == 200
        assert (await anon.get(path3)).status_code == 404
        assert await be.size(await _key(o["id"])) is None
        # --- failed upload cleanup: abort frees the parts
        s2 = await _upload(c, "partial.wav", data, part, order=[1], drop_after=1)
        assert (await c.delete(f"{BASE}/storage/uploads/{s2['id']}")).status_code == 200
        assert (await c.put(f"{BASE}/storage/uploads/{s2['id']}/parts/1", content=data[:part])).status_code == 409
        assert (await be.list_parts(await _key(s2["object_id"]), "local" if backend == "local" else await _uid(s2["id"]))) == {}
        # --- expired session is swept
        s3 = await _upload(c, "stale.wav", data, part, order=[1], drop_after=1)
        async with AsyncSessionLocal() as db:
            sess = await db.get(M51UploadSession, uuid.UUID(s3["id"]))
            sess.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await db.commit()
        assert (await a.post(f"{BASE}/storage/cleanup")).json()["sessions_expired"] >= 1
        assert (await c.put(f"{BASE}/storage/uploads/{s3['id']}/parts/1", content=data[:part])).status_code == 409
        # --- audit trail
        async with AsyncSessionLocal() as db:
            ev = {r for r in (await db.execute(select(AuditLog.event_type).where(AuditLog.event_type.like("media.%")))).scalars()}
        assert {"media.upload.completed", "media.object.revoked", "media.backup.restored", "media.object.deleted", "media.storage.cleanup"} <= ev


def state_missing(s, state):
    return [i for i in range(1, s["parts_total"] + 1) if i not in state["received_parts"]]


async def _key(oid: str) -> str:
    from app.db.session import AsyncSessionLocal
    from app.models.m51_media import M51StorageObject
    async with AsyncSessionLocal() as db:
        return (await db.get(M51StorageObject, uuid.UUID(oid))).key


async def _uid(sid: str) -> str:
    from app.db.session import AsyncSessionLocal
    from app.models.m51_media import M51UploadSession
    async with AsyncSessionLocal() as db:
        return (await db.get(M51UploadSession, uuid.UUID(sid))).backend_upload_id


@DB
@pytest.mark.asyncio
async def test_local_backend_flow(monkeypatch, tmp_path):
    await _flow(monkeypatch, tmp_path, "local", 2000, 5500)


@DB
@S3
@pytest.mark.asyncio
async def test_s3_backend_flow_minio(monkeypatch, tmp_path):
    from app.services.m51_s3 import S3Client
    ep = os.environ["M51_S3_TEST_ENDPOINT"]
    for k, v in (("M51_S3_ENDPOINT", ep), ("M51_S3_BUCKET", "m51-test"), ("M51_S3_ACCESS_KEY", os.environ["M51_S3_TEST_KEY"]),
                 ("M51_S3_SECRET_KEY", os.environ["M51_S3_TEST_SECRET"]), ("PROVIDER_EGRESS", "local")):
        setv(monkeypatch, k, v)
    await S3Client(ep, "m51-test", os.environ["M51_S3_TEST_KEY"], os.environ["M51_S3_TEST_SECRET"]).create_bucket()
    assert st.status()["status"] == "CONFIGURED"
    await _flow(monkeypatch, tmp_path, "s3", 5 << 20, (11 << 20) + 12345)       # 3 parts: 5 MiB, 5 MiB, remainder


@DB
@pytest.mark.asyncio
async def test_rejections_quota_scan_retention(monkeypatch, tmp_path):
    from app.db.session import AsyncSessionLocal
    from app.models.m51_media import M51StorageObject
    from app.services import document_storage_service as d
    await ensure_tables()
    setv(monkeypatch, "MEDIA_STORAGE_PATH", str(tmp_path / "media"))
    setv(monkeypatch, "M51_STORAGE_BACKEND", "local")
    setv(monkeypatch, "M51_STORAGE_QUOTA_BYTES", 1 << 40)
    async with AsyncSessionLocal() as db:
        maker, approver = await staff(db, "maker", PERMS), await staff(db, "approver", PERMS + ("marketing.approve",))
        from sqlalchemy import text
        await db.execute(text("DELETE FROM m51_storage_quotas"))
        await db.commit()
    data = wav_bytes(3000)
    async with client_for(maker) as c, client_for(approver) as a, anon_client() as anon:
        # bad extension, empty, oversize
        assert (await c.post(f"{BASE}/storage/uploads", json={"file_name": "x.exe", "total_size": 10})).status_code == 422
        assert (await c.post(f"{BASE}/storage/uploads", json={"file_name": "../../etc/x.wav", "total_size": 0})).status_code == 422
        setv(monkeypatch, "M51_STORAGE_MAX_BYTES", 1000)
        assert (await c.post(f"{BASE}/storage/uploads", json={"file_name": "big.wav", "total_size": 2000})).status_code == 413
        setv(monkeypatch, "M51_STORAGE_MAX_BYTES", 1 << 30)
        # content that is not its extension: rejected on completion, bytes removed
        junk = b"MZ" + b"\x00" * 3000
        s = await _upload(c, "fake.mp4", junk, 4000)
        r = await c.post(f"{BASE}/storage/uploads/{s['id']}/complete")
        assert r.status_code == 422 and "media type" in r.text
        async with AsyncSessionLocal() as db:
            o = await db.get(M51StorageObject, uuid.UUID(s["object_id"]))
            assert o.status == "DELETED" and not (tmp_path / "media" / o.key).exists()
        # no scanner configured → fail closed: quarantined and never served
        setv(monkeypatch, "DOCUMENT_CLAMAV_HOST", "")
        s = await _upload(c, "unscanned.wav", data, 4000)
        o = (await c.post(f"{BASE}/storage/uploads/{s['id']}/complete")).json()
        assert o["status"] == "QUARANTINED" and o["scan_status"] == "NOT_SCANNED"
        assert (await c.post(f"{BASE}/storage/objects/{o['id']}/access-url", json={})).status_code == 409
        # infected → quarantined
        async def infected(path):
            return d.ScanResult("INFECTED", "x")
        monkeypatch.setattr(d, "scan_document", infected)
        s = await _upload(c, "eicar.wav", data, 4000)
        o = (await c.post(f"{BASE}/storage/uploads/{s['id']}/complete")).json()
        assert o["status"] == "QUARANTINED" and o["scan_status"] == "INFECTED"
        clean_scan(monkeypatch)
        # quota
        assert (await a.put(f"{BASE}/storage/quotas/MEDIA", json={"max_bytes": 100})).status_code == 200
        assert (await c.put(f"{BASE}/storage/quotas/MEDIA", json={"max_bytes": 1})).status_code == 403
        q = await c.post(f"{BASE}/storage/uploads", json={"file_name": "q.wav", "total_size": 3000})
        assert q.status_code == 507
        assert (await a.put(f"{BASE}/storage/quotas/MEDIA", json={"max_bytes": 1 << 30})).status_code == 200
        # retention: past retention_until → deleted by cleanup, URL dead
        r = await c.post(f"{BASE}/storage/uploads", json={"file_name": "ret.wav", "total_size": len(data), "part_size": 4000, "retention_days": 1})
        s = r.json()
        await c.put(f"{BASE}/storage/uploads/{s['id']}/parts/1", content=data)
        o = (await c.post(f"{BASE}/storage/uploads/{s['id']}/complete")).json()
        url = (await c.post(f"{BASE}/storage/objects/{o['id']}/access-url", json={})).json()["url"].split("http://localhost:8000")[1]
        assert (await anon.get(url)).status_code == 200
        async with AsyncSessionLocal() as db:
            ob = await db.get(M51StorageObject, uuid.UUID(o["id"]))
            ob.retention_until = datetime.now(timezone.utc) - timedelta(minutes=1)
            await db.commit()
        assert (await a.post(f"{BASE}/storage/cleanup")).json()["retention_deleted"] >= 1
        assert (await anon.get(url)).status_code == 404
        # approve → CMS link
        s = await _upload(c, "cms.wav", data, 4000)
        o = (await c.post(f"{BASE}/storage/uploads/{s['id']}/complete")).json()
        assert (await a.post(f"{BASE}/storage/objects/{o['id']}/approve")).status_code == 200
        link = await a.post(f"{BASE}/storage/objects/{o['id']}/to-cms-media", json={"title": "POVU how-to narration", "public": False})
        assert link.status_code == 201 and link.json()["served_by"] == "cms"
        from app.models.cms import CmsMedia
        async with AsyncSessionLocal() as db:
            m = await db.get(CmsMedia, uuid.UUID(link.json()["cms_media_id"]))
            assert m.storage_path == (await _key(o["id"])) and not m.public
        # anonymous visitors get 401 for member-only media, 404 for unknown
        assert (await anon.post(f"/api/v1/public/media-files/member/{link.json()['cms_media_id']}")).status_code == 401
        assert (await anon.post(f"/api/v1/public/media-files/member/{uuid.uuid4()}")).status_code == 404
