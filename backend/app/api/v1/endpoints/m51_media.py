"""M51.S01.T006/T007/T010 media studio API. Prefix /api/v1/media-studio.

marketing.view reads; marketing.create/edit creates images, jobs and uploads; marketing.approve reviews images and job outputs,
sets quotas, runs cleanup and backup/restore. Every mutation is audited. No unauthenticated routes here (signed URLs are in
m51_media_public.py). There is no company dimension in this schema (single tenant per database); access is by permission."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.models.m51_media import (M51ImageJob, M51ImageUsage, M51MediaJob, M51StorageBackup, M51StorageObject, M51StorageQuota,
                                  M51UploadSession)
from app.services import cms_service as cms
from app.services import m51_image_gen as ig
from app.services import m51_media_tools as mt
from app.services import m51_storage as st

router = APIRouter(dependencies=[Depends(require_any_permission(("marketing.view",)))])
EDIT, APPROVE = ("marketing.create", "marketing.edit"), ("marketing.approve",)


def _need(user, perms) -> None:
    if not (user.is_superuser or has_any_permission(user, perms)):
        raise HTTPException(403, "You do not have permission for this media action.")


def _iso(d):
    return d.isoformat() if d else None


def _img(j: M51ImageJob) -> dict:
    return {"id": str(j.id), "operation": j.operation, "provider": j.provider, "model": j.model, "mode": j.mode, "status": j.status,
            "title": j.title, "prompt": j.prompt, "overlay_text": j.overlay_text, "size": j.size, "document_id": str(j.document_id) if j.document_id else None,
            "findings": j.findings or [], "provenance": j.provenance or {}, "cost_estimate": float(j.cost_estimate or 0), "error": j.error,
            "created_by": j.created_by, "reviewed_by": j.reviewed_by, "review_note": j.review_note, "created_at": _iso(j.created_at)}


def _obj(o: M51StorageObject) -> dict:
    return {"id": str(o.id), "backend": o.backend, "file_name": o.file_name, "mime": o.mime, "size": o.size, "sha256": o.sha256, "status": o.status,
            "scan_status": o.scan_status, "approval": o.approval, "owner_type": o.owner_type, "owner_id": o.owner_id, "meta": o.meta or {},
            "retention_until": _iso(o.retention_until), "created_by": o.created_by, "approved_by": o.approved_by, "created_at": _iso(o.created_at)}


def _job(j: M51MediaJob) -> dict:
    r = dict(j.result or {})
    for big in ("srt", "vtt"):
        r.pop(big, None)
    return {"id": str(j.id), "kind": j.kind, "status": j.status, "progress": j.progress, "params": {k: (v[:200] if isinstance(v, str) else v) for k, v in (j.params or {}).items()},
            "source_object_id": str(j.source_object_id) if j.source_object_id else None, "output_object_id": str(j.output_object_id) if j.output_object_id else None,
            "result": r, "has_captions": bool((j.result or {}).get("vtt")), "error": j.error, "created_by": j.created_by,
            "started_at": _iso(j.started_at), "finished_at": _iso(j.finished_at), "created_at": _iso(j.created_at)}


async def _get(db, model, rid, what):
    row = await db.get(model, rid)
    if row is None:
        raise HTTPException(404, f"{what} not found")
    return row


@router.get("/status")
async def overview(db: AsyncSession = Depends(get_db)):
    month = ig._month()
    u = await db.get(M51ImageUsage, month)
    return {"images": {**ig.status(), "spent_this_month": float(u.spent) if u else 0.0, "calls_this_month": u.calls if u else 0},
            "tools": await mt.tools_status(), "storage": {**st.status(), "used_bytes": await st.used_bytes(db), "quota_bytes": await st.quota_for(db, "*")}}


# ── T006 images ─────────────────────────────────────────────────────────────

class ImageIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=10, max_length=1000)
    operation: str = Field("GENERATE", pattern="^(GENERATE|EDIT)$")
    size: str = "1024x1024"
    overlay_text: Optional[str] = Field(None, max_length=300)
    brand_key: Optional[str] = Field(None, max_length=40)
    product_skus: list[str] = Field(default_factory=list, max_length=5)
    source_document_id: Optional[uuid.UUID] = None
    negative_prompt: Optional[str] = Field(None, max_length=300)
    idempotency_key: Optional[str] = Field(None, max_length=80)


@router.post("/images", status_code=201)
async def create_image(b: ImageIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Gates first (moderation, brand claims, SKUs, budget), then the provider. The result is a DRAFT asset; REJECTED/FAILED jobs are kept as evidence."""
    _need(user, EDIT)
    try:
        j = await ig.create_job(db, user, **b.model_dump())
    except ig.ImageError as e:
        await db.rollback()
        raise HTTPException(e.status, str(e))
    cms.audit(db, user, "media.image.requested", "m51_image_job", j.id, {"status": j.status, "provider": j.provider, "mode": j.mode,
                                                                           "prompt_sha256": j.prompt_sha256, "findings": len(j.findings or [])})
    await db.commit()
    return _img(j)


@router.get("/images")
async def list_images(db: AsyncSession = Depends(get_db)):
    return [_img(j) for j in (await db.execute(select(M51ImageJob).order_by(M51ImageJob.created_at.desc()).limit(100))).scalars()]


class ReviewIn(BaseModel):
    approve: bool
    note: str = Field("", max_length=300)


@router.post("/images/{jid}/review")
async def review_image(jid: uuid.UUID, b: ReviewIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Second-person approval: approved images become usable by e-mail, social, CMS and ads through the DAM; discarded ones are archived."""
    _need(user, APPROVE)
    j = await _get(db, M51ImageJob, jid, "Image job")
    try:
        await ig.review(db, j, user, b.approve, b.note)
    except ig.ReviewError as e:
        raise HTTPException(e.status, str(e))
    cms.audit(db, user, "media.image.approved" if b.approve else "media.image.discarded", "m51_image_job", j.id, {"document": str(j.document_id)})
    await db.commit()
    return _img(j)


# ── T007 jobs ───────────────────────────────────────────────────────────────

class JobIn(BaseModel):
    kind: str
    source_object_id: Optional[uuid.UUID] = None
    params: dict = Field(default_factory=dict)


@router.post("/jobs", status_code=201)
async def create_job(b: JobIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    try:
        j = await mt.create(db, user, b.kind, b.source_object_id, b.params)
    except (mt.MediaError, ValueError, TypeError) as e:
        raise HTTPException(getattr(e, "status", 422), str(e))
    cms.audit(db, user, "media.job.created", "m51_media_job", j.id, {"kind": j.kind, "status": j.status})
    await db.commit()
    if j.status == "QUEUED":
        mt.schedule(j.id)
    return _job(j)


@router.get("/jobs")
async def list_jobs(db: AsyncSession = Depends(get_db)):
    return [_job(j) for j in (await db.execute(select(M51MediaJob).order_by(M51MediaJob.created_at.desc()).limit(100))).scalars()]


@router.get("/jobs/{jid}")
async def get_job(jid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return _job(await _get(db, M51MediaJob, jid, "Job"))


@router.get("/jobs/{jid}/captions")
async def captions(jid: uuid.UUID, format: str = "vtt", db: AsyncSession = Depends(get_db)):
    j = await _get(db, M51MediaJob, jid, "Job")
    text = (j.result or {}).get({"srt": "srt", "vtt": "vtt"}.get(format, "vtt"))
    if j.kind != "CAPTIONS" or not text:
        raise HTTPException(404, "No captions on this job")
    return PlainTextResponse(text, media_type="text/vtt" if format == "vtt" else "application/x-subrip",
                             headers={"Content-Disposition": f'attachment; filename="captions.{"srt" if format == "srt" else "vtt"}"', "X-Content-Type-Options": "nosniff"})


@router.post("/jobs/{jid}/cancel")
async def cancel_job(jid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    j = await _get(db, M51MediaJob, jid, "Job")
    try:
        await mt.cancel(db, j)
    except mt.MediaError as e:
        raise HTTPException(e.status, str(e))
    cms.audit(db, user, "media.job.cancelled", "m51_media_job", j.id, {})
    await db.commit()
    return _job(j)


@router.post("/jobs/run-pending")
async def run_pending(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Recover stale RUNNING jobs and (re)start QUEUED ones (call from a scheduler after a restart)."""
    _need(user, APPROVE)
    stale = await mt.recover_stale(db)
    n = await mt.run_pending(db)
    await db.commit()
    return {"stale_failed": stale, "started": n}


# ── T010 storage ────────────────────────────────────────────────────────────

class UploadIn(BaseModel):
    file_name: str = Field(min_length=1, max_length=200)
    total_size: int = Field(ge=1)
    part_size: Optional[int] = Field(None, ge=1)
    retention_days: Optional[int] = Field(None, ge=1, le=3650)


def _sess(s: M51UploadSession, o: M51StorageObject, have: Optional[list[int]] = None) -> dict:
    return {"id": str(s.id), "object_id": str(o.id), "part_size": s.part_size, "total_size": s.total_size, "status": s.status,
            "parts_total": -(-s.total_size // s.part_size), "received_parts": have if have is not None else sorted(int(n) for n in (s.parts or {})),
            "expires_at": _iso(s.expires_at)}


async def _session(db, sid):
    s = await _get(db, M51UploadSession, sid, "Upload session")
    return s, await db.get(M51StorageObject, s.object_id)


@router.post("/storage/uploads", status_code=201)
async def start_upload(b: UploadIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    try:
        o, s = await st.start_upload(db, user, b.file_name, b.total_size, b.part_size, retention_days=b.retention_days)
    except st.StorageError as e:
        await db.rollback()
        raise HTTPException(e.status, str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(502, f"The storage backend refused the upload: {str(e)[:150]}")
    cms.audit(db, user, "media.upload.started", "m51_storage_object", o.id, {"size": b.total_size, "backend": o.backend})
    await db.commit()
    return _sess(s, o)


@router.get("/storage/uploads/{sid}")
async def upload_state(sid: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """What the backend really holds: a client resumes by sending only the missing parts."""
    s, o = await _session(db, sid)
    return _sess(s, o, await st.received_parts(s, o) if s.status == "OPEN" else None)


@router.put("/storage/uploads/{sid}/parts/{n}")
async def put_part(sid: uuid.UUID, n: int, request: Request, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Raw bytes of one part (Content-Type application/octet-stream), exactly part_size (last part: the remainder). Re-sending a part replaces it."""
    _need(user, EDIT)
    s, o = await _session(db, sid)
    try:
        want = st.expected_part_size(s, n)
        buf = bytearray()
        async for chunk in request.stream():
            buf += chunk
            if len(buf) > want:
                raise st.StorageError(f"Part {n} is over {want} bytes", 413)
        info = await st.put_part(db, s, o, n, bytes(buf))
    except st.StorageError as e:
        raise HTTPException(e.status, str(e))
    await db.commit()
    return {"part": n, **info}


@router.post("/storage/uploads/{sid}/complete")
async def complete_upload(sid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    s, o = await _session(db, sid)
    try:
        await st.complete_upload(db, s, o, user)
    except st.StorageError as e:
        await db.commit()                     # keep the DELETED/ABORTED state of a rejected upload
        raise HTTPException(e.status, str(e))
    if getattr(o, "_m51_already_done", False):   # repeated/concurrent complete: same finished object, no second audit or job
        await db.commit()
        return _obj(o)
    cms.audit(db, user, "media.upload.completed", "m51_storage_object", o.id, {"status": o.status, "scan": o.scan_status, "size": o.size})
    await db.commit()
    for jid in [uuid.UUID(o.meta["poster_job"])] if (o.meta or {}).get("poster_job") else []:
        mt.schedule(jid)
    return _obj(o)


@router.delete("/storage/uploads/{sid}")
async def abort_upload(sid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, EDIT)
    s, o = await _session(db, sid)
    await st.abort_upload(db, s, o)
    cms.audit(db, user, "media.upload.aborted", "m51_storage_object", o.id, {})
    await db.commit()
    return {"ok": True}


@router.get("/storage/objects")
async def objects(owner_type: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(M51StorageObject).where(M51StorageObject.status != "DELETED")
    if owner_type:
        stmt = stmt.where(M51StorageObject.owner_type == owner_type)
    return [_obj(o) for o in (await db.execute(stmt.order_by(M51StorageObject.created_at.desc()).limit(200))).scalars()]


class AccessIn(BaseModel):
    ttl_seconds: int = Field(300, ge=10, le=3600)


@router.post("/storage/objects/{oid}/access-url")
async def access_url(oid: uuid.UUID, b: AccessIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Short-lived staff preview URL (scope 'staff': drafts allowed). Needs a READY, scan-clean object."""
    _need(user, EDIT)
    o = await _get(db, M51StorageObject, oid, "Object")
    if o.status != "READY" or (st.cfg("M51_REQUIRE_SCAN", True) and o.scan_status != "CLEAN"):
        raise HTTPException(409, f"This object is {o.status} (scan {o.scan_status}); it cannot be served")
    token, exp = st.sign_access(o, "staff", b.ttl_seconds, str(user.id))
    cms.audit(db, user, "media.access_url.issued", "m51_storage_object", o.id, {"ttl": b.ttl_seconds})
    await db.commit()
    return {"url": f"{st.settings.PUBLIC_API_URL.rstrip('/')}/api/v1/public/media-files/{token}", "expires_at": exp.isoformat()}


@router.post("/storage/objects/{oid}/approve")
async def approve_object(oid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """A second person approves a job output or upload for member/public use."""
    _need(user, APPROVE)
    o = await _get(db, M51StorageObject, oid, "Object")
    if o.status != "READY":
        raise HTTPException(409, "Only a ready object can be approved")
    if o.created_by == user.username:
        raise HTTPException(403, "A different person must approve this media")
    o.approval, o.approved_by = "APPROVED", user.username
    cms.audit(db, user, "media.object.approved", "m51_storage_object", o.id, {})
    await db.commit()
    return _obj(o)


@router.post("/storage/objects/{oid}/revoke")
async def revoke(oid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Every URL issued so far stops working; new ones can be issued."""
    _need(user, APPROVE)
    o = await _get(db, M51StorageObject, oid, "Object")
    detached = await st.revoke_object(db, o)          # also unpublishes CMS media rows made from this object
    cms.audit(db, user, "media.object.revoked", "m51_storage_object", o.id, {"access_version": o.access_version, "cms_media_detached": detached})
    await db.commit()
    return _obj(o)


@router.delete("/storage/objects/{oid}")
async def delete_object(oid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    o = await _get(db, M51StorageObject, oid, "Object")
    await st.delete_object(db, o)
    cms.audit(db, user, "media.object.deleted", "m51_storage_object", o.id, {"file": o.file_name})
    await db.commit()
    return {"ok": True}


class CmsLinkIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    public: bool = False
    access_list_id: Optional[uuid.UUID] = None


@router.post("/storage/objects/{oid}/to-cms-media", status_code=201)
async def to_cms_media(oid: uuid.UUID, b: CmsLinkIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Register an APPROVED audio/video object as a CMS media item. Local-backend objects are served by the existing CMS routes
    (same file, same access list); S3 objects are served through /public/media-files (signed, member-checked)."""
    from app.models.cms import CmsMedia
    _need(user, APPROVE)
    o = await _get(db, M51StorageObject, oid, "Object")
    if o.status != "READY" or o.approval != "APPROVED" or not o.mime.startswith(("audio/", "video/")):
        raise HTTPException(409, "Only an approved, ready audio or video object can be added to the CMS")
    m = CmsMedia(kind="VIDEO" if o.mime.startswith("video/") else "AUDIO", title=b.title, mime=o.mime, size=o.size, sha256=o.sha256 or "",
                 storage_path=o.key, captions={}, public=b.public, access_list_id=b.access_list_id, created_by=user.username)
    db.add(m)
    await db.flush()
    o.owner_type, o.owner_id = "CMS_MEDIA", str(m.id)
    cms.audit(db, user, "media.object.to_cms", "cms_media", m.id, {"object": str(o.id), "backend": o.backend})
    await db.commit()
    return {"cms_media_id": str(m.id), "served_by": "cms" if o.backend == "local" else "signed-url"}


class QuotaIn(BaseModel):
    max_bytes: int = Field(ge=1)


@router.put("/storage/quotas/{scope}")
async def set_quota(scope: str, b: QuotaIn, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    if scope not in ("*", "MEDIA", "CMS_MEDIA", "DOCUMENT", "JOB_OUTPUT"):
        raise HTTPException(422, "Scope must be * or an owner type")
    q = await db.get(M51StorageQuota, scope) or M51StorageQuota(scope=scope, max_bytes=b.max_bytes)
    q.max_bytes, q.updated_by = b.max_bytes, user.username
    db.add(q)
    cms.audit(db, user, "media.quota.set", "m51_storage_quota", scope, {"max_bytes": b.max_bytes})
    await db.commit()
    return {"scope": scope, "max_bytes": b.max_bytes}


@router.post("/storage/cleanup")
async def cleanup(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    out = await st.cleanup(db)
    cms.audit(db, user, "media.storage.cleanup", "m51_storage", "all", out)
    await db.commit()
    return out


@router.get("/storage/backups")
async def backups(db: AsyncSession = Depends(get_db)):
    return [{"id": str(b.id), "status": b.status, "object_count": b.object_count, "total_bytes": b.total_bytes, "error": b.error,
             "created_at": _iso(b.created_at), "restored_at": _iso(b.restored_at)}
            for b in (await db.execute(select(M51StorageBackup).order_by(M51StorageBackup.created_at.desc()).limit(50))).scalars()]


@router.post("/storage/backups", status_code=201)
async def make_backup(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    b = await st.backup(db, user)
    cms.audit(db, user, "media.backup.created", "m51_storage_backup", b.id, {"status": b.status, "objects": b.object_count})
    await db.commit()
    return {"id": str(b.id), "status": b.status, "object_count": b.object_count, "total_bytes": b.total_bytes, "error": b.error}


@router.post("/storage/backups/{bid}/restore")
async def restore_backup(bid: uuid.UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    _need(user, APPROVE)
    b = await _get(db, M51StorageBackup, bid, "Backup")
    try:
        out = await st.restore(db, b, user)
    except st.StorageError as e:
        raise HTTPException(e.status, str(e))
    cms.audit(db, user, "media.backup.restored", "m51_storage_backup", b.id, {"restored": len(out["restored"]), "failed": len(out["failed"])})
    await db.commit()
    return out
