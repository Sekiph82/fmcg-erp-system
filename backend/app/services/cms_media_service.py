"""M46.S01.T006 memberships, gated content and locally hosted video/audio.

- Access lists name portal accounts (and/or account types); an explicit revocation wins. A members-only page or
  media item is served only to a signed-in portal user (existing portal realm cookie) whose ACTIVE account is on the
  list. Anonymous visitors get 401, signed-in but not listed get 403; nothing of the content leaks in either case.
- Media files are stored under MEDIA_STORAGE_PATH by random key, the type is checked from the file's own bytes
  (MP4/M4A/WebM/Ogg/MP3/WAV), never from the name. Captions are WebVTT, stripped of markup.
- A play by a portal user is recorded (de-duplicated per 30 minutes) and shows on the linked customer's timeline.
- KB access groups: a KB article with an access list is visible on the public KB only to listed portal members.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.cms import CmsAccessList, CmsMedia, CmsMediaView

KINDS = {"video/mp4": "VIDEO", "video/webm": "VIDEO", "audio/mp4": "AUDIO", "audio/mpeg": "AUDIO", "audio/ogg": "AUDIO", "audio/wav": "AUDIO"}
EXT = {".mp4": "video/mp4", ".m4v": "video/mp4", ".webm": "video/webm", ".m4a": "audio/mp4", ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".wav": "audio/wav"}


def sniff(head: bytes, ext: str) -> Optional[str]:
    """MIME from magic bytes; the extension only picks between audio/video for the shared MP4 container."""
    if head[4:8] == b"ftyp":
        return "audio/mp4" if ext == ".m4a" else "video/mp4"
    if head[:4] == b"\x1aE\xdf\xa3":
        return "video/webm"
    if head[:4] == b"OggS":
        return "audio/ogg"
    if head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        return "audio/mpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio/wav"
    return None


def root() -> Path:
    p = Path(settings.MEDIA_STORAGE_PATH).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


async def store(upload: UploadFile) -> tuple[str, str, int, str]:
    ext = Path((upload.filename or "").lower()).suffix
    if ext not in EXT:
        raise HTTPException(422, f"Allowed media: {', '.join(sorted(EXT))}")
    key = uuid.uuid4().hex
    path = root() / key
    h, size, head = hashlib.sha256(), 0, b""
    f = await asyncio.to_thread(path.open, "wb")
    try:
        while chunk := await upload.read(1024 * 1024):
            if not head:
                head = chunk[:16]
            size += len(chunk)
            if size > settings.MEDIA_MAX_UPLOAD_BYTES:
                await asyncio.to_thread(f.close)
                path.unlink(missing_ok=True)
                raise HTTPException(413, f"Media over {settings.MEDIA_MAX_UPLOAD_BYTES // 1048576} MiB")
            h.update(chunk)
            await asyncio.to_thread(f.write, chunk)
    finally:
        if not f.closed:
            await asyncio.to_thread(f.close)
    mime = sniff(head, ext)
    if mime is None or mime != EXT[ext] and not (ext == ".m4v" and mime == "video/mp4"):
        path.unlink(missing_ok=True)
        raise HTTPException(422, "The file content is not the media type its name says")
    return key, mime, size, h.hexdigest()


def file_path(m: CmsMedia) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", m.storage_path):
        raise HTTPException(404, "Not found")
    return root() / m.storage_path


def poster_file(m: CmsMedia) -> Path:
    if not m.poster_path or not re.fullmatch(r"[a-f0-9]{32}", m.poster_path):
        raise HTTPException(404, "No poster")
    return root() / m.poster_path


def store_bytes(data: bytes, mime: str) -> tuple[str, int, str]:
    """Store generated media (narration, trim); the bytes must really be the declared type."""
    ok = data[:8] == b"\x89PNG\r\n\x1a\n" if mime == "image/png" else sniff(data[:16], ".m4a" if mime == "audio/mp4" else "") == mime
    if not ok:
        raise HTTPException(422, "The generated file is not the expected media type")
    if len(data) > settings.MEDIA_MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Generated media is over the size limit")
    key = uuid.uuid4().hex
    (root() / key).write_bytes(data)
    return key, len(data), hashlib.sha256(data).hexdigest()


# ── ffmpeg tools (poster frame, trim) — only when ffmpeg is installed ──────────

FORMATS = {"video/mp4": "mp4", "video/webm": "webm", "audio/mp4": "mp4", "audio/mpeg": "mp3", "audio/ogg": "ogg", "audio/wav": "wav"}


def ffmpeg() -> Optional[str]:
    return shutil.which("ffmpeg")


def not_available() -> HTTPException:
    return HTTPException(409, {"status": "NOT_AVAILABLE", "detail": "ffmpeg is not installed on the server; poster frames and trimming are unavailable."})


async def _ffmpeg(args: list[str]) -> bytes:
    exe = ffmpeg()
    if not exe:
        raise not_available()
    r = await asyncio.to_thread(subprocess.run, [exe, "-hide_banner", "-loglevel", "error", "-nostdin", *args], capture_output=True, timeout=300)
    if r.returncode != 0 or not r.stdout:
        raise HTTPException(422, f"ffmpeg could not process this media: {r.stderr.decode(errors='replace')[:200]}")
    return r.stdout


async def poster_frame(m: CmsMedia, t: float) -> bytes:
    return await _ffmpeg(["-ss", f"{t:.3f}", "-protocol_whitelist", "file", "-i", str(file_path(m)), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1"])


async def trim(m: CmsMedia, start: float, end: float) -> bytes:
    """Stream copy (no re-encode) of [start, end) into the same container; the original file is not touched."""
    fmt = FORMATS[m.mime]
    extra = ["-movflags", "frag_keyframe+empty_moov"] if fmt == "mp4" else []   # mp4 to a pipe needs a fragmented layout
    return await _ffmpeg(["-ss", f"{start:.3f}", "-protocol_whitelist", "file", "-i", str(file_path(m)), "-t", f"{end - start:.3f}", "-c", "copy", *extra, "-f", fmt, "pipe:1"])


VTT_TIME = re.compile(r"^\d{2}:\d{2}(:\d{2})?\.\d{3} --> \d{2}:\d{2}(:\d{2})?\.\d{3}")


def clean_vtt(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").strip()
    if not text.startswith("WEBVTT"):
        raise HTTPException(422, "Captions must be WebVTT (start with WEBVTT)")
    if not any(VTT_TIME.match(line) for line in text.split("\n")):
        raise HTTPException(422, "Captions have no cue timings")
    return re.sub(r"<[^>]*>", "", text)[:200_000]


def on_list(acl: Optional[CmsAccessList], account) -> bool:
    if acl is None or account is None:
        return False
    aid = str(account.id)
    if aid in (acl.revoked_ids or []):
        return False
    atype = getattr(account.account_type, "value", account.account_type)
    return aid in (acl.account_ids or []) or str(atype) in (acl.account_types or [])


async def member_check(db: AsyncSession, access_list_id, portal_user) -> None:
    """Raise 401 without a portal sign-in, 403 when the signed-in account is not on the list."""
    if portal_user is None:
        raise HTTPException(401, "Members only: please sign in to the customer portal.")
    acl = await db.get(CmsAccessList, access_list_id) if access_list_id else None
    if not on_list(acl, portal_user.account):
        raise HTTPException(403, "Your account does not have access to this content.")


async def optional_portal_user(request, db: AsyncSession):
    from app.core.external_auth import get_portal_user
    if not request.cookies.get("erp_portal_token"):
        return None
    try:
        return await get_portal_user(request, db)
    except HTTPException:
        return None


def viewer_hash(raw: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"media:{raw}".encode(), hashlib.sha256).hexdigest()


async def record_view(db: AsyncSession, m: CmsMedia, portal_user, raw_viewer: str, seconds: int) -> bool:
    vh = viewer_hash(str(portal_user.id) if portal_user else raw_viewer[:100])
    since = datetime.now(timezone.utc) - timedelta(minutes=30)
    recent = (await db.execute(select(CmsMediaView).where(CmsMediaView.media_id == m.id, CmsMediaView.viewer_hash == vh,
                                                          CmsMediaView.created_at > since))).scalars().first()
    if recent:
        recent.seconds = max(recent.seconds, max(0, min(int(seconds or 0), 86400)))
        return False
    db.add(CmsMediaView(media_id=m.id, viewer_hash=vh, seconds=max(0, min(int(seconds or 0), 86400)),
                        portal_account_id=portal_user.portal_account_id if portal_user else None,
                        portal_user_id=portal_user.id if portal_user else None))
    return True


async def kb_visible_ids(db: AsyncSession, portal_user) -> set:
    """KB articles behind access groups that this portal member may read."""
    from app.models.knowledge_base import KBArticle
    rows = (await db.execute(select(KBArticle.id, KBArticle.access_list_id).where(KBArticle.access_list_id.isnot(None)))).all()
    if not rows or portal_user is None:
        return set()
    acls = {a.id: a for a in (await db.execute(select(CmsAccessList).where(CmsAccessList.id.in_({r[1] for r in rows})))).scalars()}
    return {aid for aid, lid in rows if on_list(acls.get(lid), portal_user.account)}
