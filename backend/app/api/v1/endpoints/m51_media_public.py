"""M51.S01.T010 signed media delivery. Prefix /api/v1/public/media-files (unauthenticated routes; the signed token is the credential).

GET|HEAD /{token}                 stream the object with HTTP Range (206/416). The token is an HMAC over object id, expiry, access version,
                                  purpose and audience; every request re-checks the row (READY, scan CLEAN, same access version, and for
                                  'member' tokens APPROVED), so delete/revoke/quarantine end access at once. Any failure is a plain 404.
POST /member/{cms_media_id}       a signed-in portal member (existing portal cookie) on the media's access list, or anyone for a public item,
                                  gets a 5-minute 'member' URL for the approved object linked to that CMS media. 401 anonymous, 403 not listed.
Private, never cached; nosniff; sandboxed CSP."""
from __future__ import annotations

import re
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models.cms import CmsMedia
from app.models.m51_media import M51StorageObject
from app.services import cms_media_service as media
from app.services import m51_storage as st

router = APIRouter()
HEAD_SAFE = {"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store", "Content-Security-Policy": "default-src 'none'; sandbox",
             "Accept-Ranges": "bytes", "Cross-Origin-Resource-Policy": "same-site"}


@router.api_route("/{token}", methods=["GET", "HEAD"])
async def serve(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        o = await st.load_for_token(db, token)
        rng = st.parse_range(request.headers.get("range"), o.size)
    except st.StorageError as e:
        if e.status == 416:
            raise HTTPException(416, "Range not satisfiable", headers={"Content-Range": "bytes */0"})
        raise HTTPException(404, "Not found")
    name = re.sub(r"[^\w.\-]", "_", o.file_name)[:100]
    h = {**HEAD_SAFE, "Content-Disposition": f"inline; filename*=UTF-8''{quote(name)}"}
    a, b = rng or (0, o.size - 1)
    h["Content-Length"] = str(b - a + 1)
    if rng:
        h["Content-Range"] = f"bytes {a}-{b}/{o.size}"
    code = 206 if rng else 200
    if request.method == "HEAD":
        return Response(status_code=code, headers=h, media_type=o.mime)
    return StreamingResponse(st.get_backend(o.backend).iter_range(o.key, a, b), status_code=code, headers=h, media_type=o.mime)


@router.post("/member/{cms_media_id}")
async def member_url(cms_media_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    m = await db.get(CmsMedia, cms_media_id)
    if m is None or m.storage_path.startswith(st.REVOKED_PREFIX):
        raise HTTPException(404, "Not found")
    user = await media.optional_portal_user(request, db)
    if not m.public:
        await media.member_check(db, m.access_list_id, user)       # 401 / 403
    o = (await db.execute(select(M51StorageObject).where(M51StorageObject.owner_type == "CMS_MEDIA", M51StorageObject.owner_id == str(m.id),
                                                         M51StorageObject.status == "READY", M51StorageObject.approval == "APPROVED"))).scalars().first()
    if o is None or (st.cfg("M51_REQUIRE_SCAN", True) and o.scan_status != "CLEAN"):
        raise HTTPException(404, "Not found")
    token, exp = st.sign_access(o, "member", 300, str(getattr(user, "portal_account_id", "") or "public"))
    return {"url": f"{st.settings.PUBLIC_API_URL.rstrip('/')}/api/v1/public/media-files/{token}", "expires_at": exp.isoformat()}
