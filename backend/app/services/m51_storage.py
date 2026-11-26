"""M51.S01.T010 pluggable media storage: local disk or S3-compatible (MinIO/Ceph/AWS), behind one interface.

- Objects have opaque random keys; the database row (m51_storage_objects) is the authority, bytes are private. Nothing is
  public: access is by short-lived HMAC-signed URLs (token = object id, expiry, purpose, audience, access_version) that the
  ERP itself serves with bounded streaming and HTTP Range. The token is re-checked against the row on every request, so
  deleting, quarantining or revoking (access_version bump) kills every URL already issued. S3 stays private.
- Uploads are multipart/resumable sessions: parts may arrive in any order and be re-sent; GET session lists received parts so a
  client resumes after a drop. Completion verifies part continuity and total size, computes sha256 by bounded streaming,
  checks the file's magic bytes against its extension, scans with the existing ClamAV integration (fail closed) and only then
  marks the object READY. Quotas are checked at session start and again at completion.
- Retention/cleanup removes expired sessions, never-completed uploads and objects past retention_until.
- Backup copies READY objects to M51_STORAGE_BACKUP_PATH with a sha256 manifest; restore verifies every hash before writing back.
Settings (getattr with defaults): M51_STORAGE_BACKEND local|s3, M51_S3_ENDPOINT/BUCKET/REGION/ACCESS_KEY/SECRET_KEY,
M51_STORAGE_PART_BYTES, M51_STORAGE_MAX_BYTES, M51_STORAGE_QUOTA_BYTES, M51_SIGNED_URL_MAX_SECONDS, M51_UPLOAD_SESSION_HOURS,
M51_REQUIRE_SCAN, M51_STORAGE_BACKUP_PATH, M51_AUTO_POSTER.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncIterator, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.m51_media import M51StorageBackup, M51StorageObject, M51StorageQuota, M51UploadSession

CHUNK = 1 << 20
MIN_S3_PART, MAX_PART = 5 << 20, 64 << 20
EXT = {".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".m4a": "audio/mp4", ".mp3": "audio/mpeg",
       ".ogg": "audio/ogg", ".wav": "audio/wav", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
KEY_RE = re.compile(r"[a-f0-9]{32}")


class StorageError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


def cfg(name: str, default):
    return getattr(settings, name, default)


def sniff(head: bytes, ext: str) -> Optional[str]:
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    from app.services.cms_media_service import sniff as media_sniff
    return media_sniff(head, ext)


# ── backends ────────────────────────────────────────────────────────────────

class LocalBackend:
    name = "local"
    min_part = 1

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root or settings.MEDIA_STORAGE_PATH).resolve()   # same directory the CMS media routes read (32-hex keys)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        if not KEY_RE.fullmatch(key):
            raise StorageError("Not found", 404)
        return self.root / key

    def _parts(self, key: str) -> Path:
        return self.root / ".parts" / key

    async def create_multipart(self, key: str, mime: str) -> str:
        await asyncio.to_thread(self._parts(key).mkdir, parents=True, exist_ok=True)
        return "local"

    async def upload_part(self, key: str, uid: str, n: int, data: bytes) -> str:
        await asyncio.to_thread((self._parts(key) / str(n)).write_bytes, data)
        return hashlib.sha256(data).hexdigest()

    async def list_parts(self, key: str, uid: str) -> dict[int, int]:
        d = self._parts(key)
        return {int(p.name): p.stat().st_size for p in d.iterdir()} if d.is_dir() else {}

    def _assemble(self, key: str, numbers: list[int]) -> None:
        tmp = self.path(key).with_suffix(".tmp")
        with tmp.open("wb") as out:
            for n in numbers:
                with (self._parts(key) / str(n)).open("rb") as f:
                    shutil.copyfileobj(f, out, CHUNK)
        os.replace(tmp, self.path(key))
        shutil.rmtree(self._parts(key), ignore_errors=True)

    async def complete(self, key: str, uid: str, parts: list[tuple[int, str]]) -> None:
        await asyncio.to_thread(self._assemble, key, [n for n, _ in sorted(parts)])

    async def abort(self, key: str, uid: str) -> None:
        await asyncio.to_thread(shutil.rmtree, self._parts(key), True)

    async def size(self, key: str) -> Optional[int]:
        p = self.path(key)
        return p.stat().st_size if p.is_file() else None

    async def iter_range(self, key: str, start: int, end: int) -> AsyncIterator[bytes]:
        f = await asyncio.to_thread(self.path(key).open, "rb")
        try:
            await asyncio.to_thread(f.seek, start)
            left = end - start + 1
            while left > 0:
                b = await asyncio.to_thread(f.read, min(CHUNK, left))
                if not b:
                    break
                left -= len(b)
                yield b
        finally:
            f.close()

    async def put_bytes(self, key: str, data: bytes, mime: str) -> None:
        await asyncio.to_thread(self.path(key).write_bytes, data)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self.path(key).unlink, True)


class S3Backend:
    name = "s3"
    min_part = MIN_S3_PART

    def __init__(self):
        from app.services.m51_s3 import S3Client
        self.c = S3Client(cfg("M51_S3_ENDPOINT", ""), cfg("M51_S3_BUCKET", ""), cfg("M51_S3_ACCESS_KEY", ""),
                          cfg("M51_S3_SECRET_KEY", ""), cfg("M51_S3_REGION", "us-east-1"), backoff=float(cfg("M51_S3_BACKOFF", 0.5)))

    @staticmethod
    def k(key: str) -> str:
        if not KEY_RE.fullmatch(key):
            raise StorageError("Not found", 404)
        return f"m51/{key}"

    async def create_multipart(self, key: str, mime: str) -> str:
        return await self.c.create_multipart(self.k(key), mime)

    async def upload_part(self, key: str, uid: str, n: int, data: bytes) -> str:
        return await self.c.upload_part(self.k(key), uid, n, data)

    async def list_parts(self, key: str, uid: str) -> dict[int, int]:
        return await self.c.list_parts(self.k(key), uid)

    async def complete(self, key: str, uid: str, parts: list[tuple[int, str]]) -> None:
        await self.c.complete_multipart(self.k(key), uid, parts)

    async def abort(self, key: str, uid: str) -> None:
        await self.c.abort_multipart(self.k(key), uid)

    async def size(self, key: str) -> Optional[int]:
        h = await self.c.head(self.k(key))
        return h["size"] if h else None

    def iter_range(self, key: str, start: int, end: int):
        return self.c.iter_range(self.k(key), start, end, CHUNK)

    async def put_bytes(self, key: str, data: bytes, mime: str) -> None:
        await self.c.put(self.k(key), data, mime)

    async def delete(self, key: str) -> None:
        await self.c.delete(self.k(key))


def get_backend(name: Optional[str] = None):
    name = (name or cfg("M51_STORAGE_BACKEND", "local")).lower()
    if name == "s3":
        return S3Backend()
    if name == "local":
        return LocalBackend()
    raise StorageError(f"Unknown storage backend {name}", 503)


def status() -> dict:
    name = cfg("M51_STORAGE_BACKEND", "local").lower()
    out = {"backend": name, "max_object_bytes": int(cfg("M51_STORAGE_MAX_BYTES", 2 << 30)),
           "part_bytes": int(cfg("M51_STORAGE_PART_BYTES", 8 << 20)), "require_scan": bool(cfg("M51_REQUIRE_SCAN", True)),
           "scanner": "clamav" if settings.DOCUMENT_CLAMAV_HOST.strip() else "NOT_CONFIGURED"}
    if name == "s3":
        ok = all(cfg(n, "") for n in ("M51_S3_ENDPOINT", "M51_S3_BUCKET", "M51_S3_ACCESS_KEY", "M51_S3_SECRET_KEY"))
        out["status"] = "CONFIGURED" if ok else "NOT_CONFIGURED"
    else:
        out["status"] = "CONFIGURED"
    return out


# ── signed access ───────────────────────────────────────────────────────────

def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _mac(payload: str) -> str:
    return _b64(hmac.new(settings.SECRET_KEY.encode(), b"m51-media:" + payload.encode(), hashlib.sha256).digest())


def sign_access(obj: M51StorageObject, purpose: str, ttl: int, audience: str) -> tuple[str, datetime]:
    """purpose: 'staff' (preview of a draft by an authorised user) or 'member' (approved content for a portal member)."""
    ttl = max(10, min(int(ttl), int(cfg("M51_SIGNED_URL_MAX_SECONDS", 900))))
    exp = int(time.time()) + ttl
    payload = _b64(json.dumps({"o": str(obj.id), "e": exp, "v": obj.access_version, "p": purpose, "a": audience[:64]},
                              separators=(",", ":")).encode())
    return f"{payload}.{_mac(payload)}", datetime.fromtimestamp(exp, timezone.utc)


def verify_token(token: str) -> dict:
    try:
        payload, mac = token.split(".", 1)
        if not hmac.compare_digest(mac, _mac(payload)):
            raise ValueError
        d = json.loads(_unb64(payload))
        if int(d["e"]) < time.time():
            raise ValueError
        return d
    except Exception:
        raise StorageError("Not found", 404) from None


async def load_for_token(db: AsyncSession, token: str) -> M51StorageObject:
    """Everything is re-checked against the row: a revoked, deleted, quarantined or (for members) unapproved object is 404."""
    d = verify_token(token)
    try:
        obj = await db.get(M51StorageObject, uuid.UUID(d["o"]))
    except ValueError:
        raise StorageError("Not found", 404) from None
    if (obj is None or obj.status != "READY" or obj.access_version != d["v"]
            or (cfg("M51_REQUIRE_SCAN", True) and obj.scan_status != "CLEAN")
            or (d["p"] == "member" and obj.approval != "APPROVED")):
        raise StorageError("Not found", 404)
    return obj


def parse_range(header: Optional[str], size: int) -> Optional[tuple[int, int]]:
    """Single 'bytes=a-b' range; None = whole object; raises 416 StorageError when unsatisfiable."""
    if not header:
        return None
    m = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
    if not m or (not m.group(1) and not m.group(2)):
        raise StorageError("Bad range", 416)
    if m.group(1):
        a, b = int(m.group(1)), int(m.group(2)) if m.group(2) else size - 1
    else:
        n = int(m.group(2))
        a, b = max(0, size - n), size - 1
    b = min(b, size - 1)
    if a > b or a >= size:
        raise StorageError("Range not satisfiable", 416)
    return a, b


# ── lifecycle ───────────────────────────────────────────────────────────────

async def quota_for(db: AsyncSession, owner_type: str) -> int:
    for scope in (owner_type, "*"):
        q = await db.get(M51StorageQuota, scope)
        if q:
            return int(q.max_bytes)
    return int(cfg("M51_STORAGE_QUOTA_BYTES", 10 << 30))


async def used_bytes(db: AsyncSession, owner_type: Optional[str] = None) -> int:
    stmt = select(func.coalesce(func.sum(M51StorageObject.size), 0)).where(M51StorageObject.status.in_(("UPLOADING", "READY", "QUARANTINED")))
    if owner_type:
        stmt = stmt.where(M51StorageObject.owner_type == owner_type)
    return int((await db.execute(stmt)).scalar_one())


async def start_upload(db: AsyncSession, user, file_name: str, total_size: int, part_size: Optional[int] = None,
                       owner_type: str = "MEDIA", owner_id: Optional[str] = None, retention_days: Optional[int] = None) -> tuple[M51StorageObject, M51UploadSession]:
    name = Path((file_name or "").replace("\\", "/")).name
    ext = Path(name.lower()).suffix
    if not name or len(name) > 200 or ext not in EXT:
        raise StorageError(f"Allowed media: {', '.join(sorted(EXT))}")
    cap = int(cfg("M51_STORAGE_MAX_BYTES", 2 << 30))
    if total_size < 1:
        raise StorageError("Empty files are not allowed")
    if total_size > cap:
        raise StorageError(f"Object over {cap // 1048576} MiB", 413)
    be = get_backend()
    ps = int(part_size or cfg("M51_STORAGE_PART_BYTES", 8 << 20))
    if not be.min_part <= ps <= MAX_PART:
        raise StorageError(f"Part size must be {be.min_part // 1048576 or 1} byte(s)–{MAX_PART // 1048576} MiB for the {be.name} backend")
    if -(-total_size // ps) > 10000:
        raise StorageError("Too many parts; use a larger part size")
    for scope in {owner_type, "*"}:
        if scope == "*":
            used, limit = await used_bytes(db), await quota_for(db, "*")
        else:
            used, limit = await used_bytes(db, owner_type), await quota_for(db, owner_type)
        if used + total_size > limit:
            raise StorageError(f"Storage quota exceeded ({scope}): {used + total_size} > {limit} bytes", 507)
    key = uuid.uuid4().hex
    mime = EXT[ext]
    uid = await be.create_multipart(key, mime)
    obj = M51StorageObject(backend=be.name, key=key, owner_type=owner_type, owner_id=owner_id, file_name=name, mime=mime,
                           size=total_size, status="UPLOADING", scan_status="PENDING", created_by=user.username,
                           retention_until=datetime.now(timezone.utc) + timedelta(days=retention_days) if retention_days else None)
    db.add(obj)
    await db.flush()
    sess = M51UploadSession(object_id=obj.id, backend_upload_id=uid, part_size=ps, total_size=total_size, parts={},
                            expires_at=datetime.now(timezone.utc) + timedelta(hours=int(cfg("M51_UPLOAD_SESSION_HOURS", 24))),
                            created_by=user.username)
    db.add(sess)
    await db.flush()
    return obj, sess


def expected_part_size(sess: M51UploadSession, n: int) -> int:
    count = -(-sess.total_size // sess.part_size)
    if not 1 <= n <= count:
        raise StorageError(f"Part number must be 1..{count}")
    return sess.part_size if n < count else sess.total_size - sess.part_size * (count - 1)


async def put_part(db: AsyncSession, sess: M51UploadSession, obj: M51StorageObject, n: int, data: bytes) -> dict:
    if sess.status != "OPEN" or sess.expires_at < datetime.now(timezone.utc):
        raise StorageError("This upload session is closed or expired", 410)
    want = expected_part_size(sess, n)
    if len(data) != want:
        raise StorageError(f"Part {n} must be exactly {want} bytes (got {len(data)})")
    etag = await get_backend(obj.backend).upload_part(obj.key, sess.backend_upload_id, n, data)
    parts = dict(sess.parts or {})
    parts[str(n)] = {"size": len(data), "etag": etag, "sha256": hashlib.sha256(data).hexdigest()}
    sess.parts = parts                       # reassign: JSON column change tracking
    return parts[str(n)]


async def received_parts(sess: M51UploadSession, obj: M51StorageObject) -> list[int]:
    """Parts the backend really holds (not just what we recorded) so a resume never trusts stale state."""
    held = await get_backend(obj.backend).list_parts(obj.key, sess.backend_upload_id)
    return sorted(int(n) for n in (sess.parts or {}) if held.get(int(n)) == sess.parts[n]["size"])


@asynccontextmanager
async def materialize(obj: M51StorageObject):
    """A local file with the object's bytes (the stored file itself for local; a bounded temp copy for S3)."""
    be = get_backend(obj.backend)
    if be.name == "local":
        yield be.path(obj.key)
        return
    d = tempfile.mkdtemp(prefix="m51-")
    try:
        p = Path(d) / "obj"
        with p.open("wb") as f:
            async for chunk in be.iter_range(obj.key, 0, obj.size - 1):
                f.write(chunk)
        yield p
    finally:
        shutil.rmtree(d, ignore_errors=True)


async def _sha_head(obj: M51StorageObject) -> tuple[str, bytes]:
    h, head = hashlib.sha256(), b""
    async for chunk in get_backend(obj.backend).iter_range(obj.key, 0, obj.size - 1):
        if not head:
            head = chunk[:16]
        h.update(chunk)
    return h.hexdigest(), head


async def complete_upload(db: AsyncSession, sess: M51UploadSession, obj: M51StorageObject, user) -> M51StorageObject:
    if sess.status != "OPEN":
        raise StorageError("This upload session is closed", 409)
    if sess.expires_at < datetime.now(timezone.utc):
        raise StorageError("This upload session is expired", 410)
    count = -(-sess.total_size // sess.part_size)
    have = await received_parts(sess, obj)
    if have != list(range(1, count + 1)):
        missing = sorted(set(range(1, count + 1)) - set(have))
        raise StorageError(f"Missing parts: {missing[:20]}", 409)
    be = get_backend(obj.backend)
    be_used = await used_bytes(db)
    await be.complete(obj.key, sess.backend_upload_id, [(int(n), p["etag"]) for n, p in sess.parts.items()])
    actual = await be.size(obj.key)
    sha, head = await _sha_head(obj)
    ext = Path(obj.file_name.lower()).suffix
    mime = sniff(head, ext)
    bad = None
    if actual != sess.total_size:
        bad = "The stored size does not match the declared size"
    elif mime is None or (mime != obj.mime and not (ext == ".m4v" and mime == "video/mp4")):
        bad = "The file content is not the media type its name says"
    elif be_used > await quota_for(db, "*"):
        bad = "Storage quota exceeded"
    if bad:
        await be.delete(obj.key)
        obj.status, sess.status, obj.meta = "DELETED", "ABORTED", {**(obj.meta or {}), "reason": bad}
        obj.deleted_at = datetime.now(timezone.utc)
        raise StorageError(bad, 422)
    obj.sha256, obj.size = sha, actual
    from app.services.document_storage_service import scan_document
    async with materialize(obj) as path:
        scan = await scan_document(path)
    obj.scan_status = scan.status
    obj.status = "READY" if scan.status == "CLEAN" else "QUARANTINED"
    sess.status = "COMPLETED"
    await db.flush()
    if obj.status == "READY":
        await run_hooks(db, obj, user)
    return obj


async def run_hooks(db: AsyncSession, obj: M51StorageObject, user) -> None:
    """Thumbnail/transcode queue hook: a READY video gets a queued POSTER job (needs ffmpeg at run time)."""
    if obj.mime.startswith("video/") and cfg("M51_AUTO_POSTER", True):
        from app.models.m51_media import M51MediaJob
        job = M51MediaJob(kind="POSTER", status="QUEUED", params={"at": 1.0, "width": 640, "auto": True}, source_object_id=obj.id, created_by=getattr(user, "username", None))
        db.add(job)
        await db.flush()
        obj.meta = {**(obj.meta or {}), "hooks": ["POSTER"], "poster_job": str(job.id)}


async def abort_upload(db: AsyncSession, sess: M51UploadSession, obj: M51StorageObject) -> None:
    if sess.status == "OPEN":
        try:
            await get_backend(obj.backend).abort(obj.key, sess.backend_upload_id)
        except Exception:               # cleanup is best effort; the row still goes DELETED and the sweeper retries nothing else
            pass
    sess.status = "ABORTED"
    if obj.status == "UPLOADING":
        obj.status, obj.deleted_at = "DELETED", datetime.now(timezone.utc)


async def delete_object(db: AsyncSession, obj: M51StorageObject) -> None:
    try:
        await get_backend(obj.backend).delete(obj.key)
    finally:
        obj.status, obj.deleted_at = "DELETED", datetime.now(timezone.utc)
        obj.access_version += 1


async def cleanup(db: AsyncSession) -> dict:
    """Expired sessions → aborted (parts freed); objects past retention → deleted."""
    now = datetime.now(timezone.utc)
    out = {"sessions_expired": 0, "retention_deleted": 0}
    for s in (await db.execute(select(M51UploadSession).where(M51UploadSession.status == "OPEN", M51UploadSession.expires_at < now))).scalars():
        obj = await db.get(M51StorageObject, s.object_id)
        await abort_upload(db, s, obj)
        s.status = "EXPIRED"
        out["sessions_expired"] += 1
    for o in (await db.execute(select(M51StorageObject).where(M51StorageObject.status.in_(("READY", "QUARANTINED")),
                                                              M51StorageObject.retention_until.isnot(None), M51StorageObject.retention_until < now))).scalars():
        await delete_object(db, o)
        out["retention_deleted"] += 1
    return out


# ── backup / restore ────────────────────────────────────────────────────────

def backup_root() -> Path:
    p = Path(cfg("M51_STORAGE_BACKUP_PATH", "data/media_backup"))
    p = p if p.is_absolute() else Path(settings.MEDIA_STORAGE_PATH).resolve().parent / p
    p.mkdir(parents=True, exist_ok=True)
    return p


async def backup(db: AsyncSession, user) -> M51StorageBackup:
    b = M51StorageBackup(status="RUNNING", created_by=user.username)
    db.add(b)
    await db.flush()
    dest = backup_root() / str(b.id)
    dest.mkdir(parents=True, exist_ok=True)
    manifest, total, failed = [], 0, []
    for o in (await db.execute(select(M51StorageObject).where(M51StorageObject.status == "READY"))).scalars():
        h = hashlib.sha256()
        try:
            with (dest / o.key).open("wb") as f:
                async for chunk in get_backend(o.backend).iter_range(o.key, 0, o.size - 1):
                    h.update(chunk)
                    f.write(chunk)
            if h.hexdigest() != o.sha256:
                raise StorageError("checksum mismatch")
        except Exception as e:                   # one unreadable object must not hide the rest
            (dest / o.key).unlink(missing_ok=True)
            failed.append(f"{o.id}: {str(e)[:80]}")
            continue
        manifest.append({"id": str(o.id), "key": o.key, "sha256": o.sha256, "size": o.size})
        total += o.size
    b.status, b.manifest, b.object_count, b.total_bytes = ("PARTIAL" if failed else "COMPLETED"), manifest, len(manifest), total
    b.error = ("; ".join(failed))[:400] if failed else None
    return b


async def restore(db: AsyncSession, b: M51StorageBackup, user) -> dict:
    """Put back every manifest object whose bytes are gone from the live backend; each file is hash-verified first."""
    if b.status not in ("COMPLETED", "PARTIAL"):
        raise StorageError("Only a completed backup can be restored", 409)
    src = backup_root() / str(b.id)
    restored, skipped, failed = [], 0, []
    for m in b.manifest:
        obj = await db.get(M51StorageObject, uuid.UUID(m["id"]))
        if obj is None:
            failed.append({"id": m["id"], "reason": "object record is gone"})
            continue
        be = get_backend(obj.backend)
        if obj.status == "READY" and await be.size(obj.key) == m["size"]:
            skipped += 1
            continue
        p = src / m["key"]
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != m["sha256"]:
            failed.append({"id": m["id"], "reason": "backup copy missing or corrupt"})
            continue
        sess_uid = await be.create_multipart(obj.key, obj.mime)
        ps = max(be.min_part, int(cfg("M51_STORAGE_PART_BYTES", 8 << 20)))
        parts, data, n = [], p.read_bytes(), 0
        for off in range(0, len(data), ps):
            n += 1
            parts.append((n, await be.upload_part(obj.key, sess_uid, n, data[off:off + ps])))
        await be.complete(obj.key, sess_uid, parts)
        from app.services.document_storage_service import scan_document
        async with materialize(obj) as path:
            scan = await scan_document(path)
        obj.scan_status, obj.status, obj.deleted_at = scan.status, "READY" if scan.status == "CLEAN" else "QUARANTINED", None
        obj.access_version += 1                     # URLs issued before the loss do not come back
        restored.append(m["id"])
    b.restored_at = datetime.now(timezone.utc)
    return {"restored": restored, "already_present": skipped, "failed": failed}


async def store_file(db: AsyncSession, path: Path, file_name: str, user, owner_type: str = "JOB_OUTPUT", owner_id: Optional[str] = None,
                     approval: str = "DRAFT") -> M51StorageObject:
    """Server-side produced file (job output) → a stored object through the same multipart/scan path as an upload."""
    be = get_backend()
    size = path.stat().st_size
    cap = int(cfg("M51_STORAGE_MAX_BYTES", 2 << 30))
    if size < 1 or size > cap:
        raise StorageError("Output is empty or over the storage size limit", 413)
    if await used_bytes(db) + size > await quota_for(db, "*"):
        raise StorageError("Storage quota exceeded", 507)
    ext = Path(file_name.lower()).suffix
    if ext not in EXT:
        raise StorageError("Unsupported output type")
    key, ps = uuid.uuid4().hex, max(be.min_part, int(cfg("M51_STORAGE_PART_BYTES", 8 << 20)))
    uid = await be.create_multipart(key, EXT[ext])
    obj = M51StorageObject(backend=be.name, key=key, owner_type=owner_type, owner_id=owner_id, file_name=file_name, mime=EXT[ext],
                           size=size, status="UPLOADING", scan_status="PENDING", approval=approval, created_by=getattr(user, "username", None))
    db.add(obj)
    await db.flush()
    parts, h, head = [], hashlib.sha256(), b""
    try:
        with path.open("rb") as f:
            n = 0
            while chunk := await asyncio.to_thread(f.read, ps):
                n += 1
                head = head or chunk[:16]
                h.update(chunk)
                parts.append((n, await be.upload_part(key, uid, n, chunk)))
        await be.complete(key, uid, parts)
    except Exception:
        await be.abort(key, uid)
        obj.status, obj.deleted_at = "DELETED", datetime.now(timezone.utc)
        raise
    mime = sniff(head, ext)
    if mime != EXT[ext] and not (ext == ".m4v" and mime == "video/mp4"):
        await be.delete(key)
        obj.status, obj.deleted_at = "DELETED", datetime.now(timezone.utc)
        raise StorageError("The produced file is not the expected media type")
    obj.sha256 = h.hexdigest()
    from app.services.document_storage_service import scan_document
    async with materialize(obj) as p:
        scan = await scan_document(p)
    obj.scan_status, obj.status = scan.status, "READY" if scan.status == "CLEAN" else "QUARANTINED"
    return obj
