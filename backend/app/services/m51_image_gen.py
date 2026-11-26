"""M51.S01.T006 AI image generation and editing: provider adapters, brand/claim/moderation gates, budget, DRAFT assets.

Official contracts (docs fetched 2026-11-26):
- OpenAI Images API  https://developers.openai.com/api/reference/resources/images  (REST v1)
    POST https://api.openai.com/v1/images/generations  JSON {model, prompt, n, size, quality, output_format, moderation}
    POST https://api.openai.com/v1/images/edits        multipart {model, prompt, image[]}   (a multipart `mask` field is NOT documented, so
                                                      masks are not sent; edits are prompt-guided only)
    Header Authorization: Bearer <key>. GPT image models always answer data[0].b64_json (response_format is not sent);
    usage = token counts. 401 bad key, 429 rate limit (Retry-After), 5xx retry, 400 with error.code moderation_blocked.
    The doc page lists gpt-image-1 as shut down on 2026-10-23: the model name is a setting (M51_OPENAI_IMAGE_MODEL, default gpt-image-2).
- Stability AI Stable Image Core  https://docs.stability.ai/api-reference  (v2beta)
    POST https://api.stability.ai/v2beta/stable-image/generate/core  multipart {prompt, negative_prompt, aspect_ratio, seed, output_format}
    Authorization: Bearer <key>; Accept: image/* (bytes) ; response headers `finish-reason` (CONTENT_FILTERED = moderated, blurred) and `seed`.
    Errors 400/401/402/403 (content moderation)/413/422/429/500. The fetched page documents no edit endpoint: EDIT is OpenAI only.
    (negative_prompt / aspect_ratio / seed / output_format are the v2beta Core form fields; the fetched page did not list them.)
- "simulator" provider = the OpenAI contract served by tests/provider_sim/image_m51_app.py (PROVIDER_EGRESS=local).
Live providers also need M51_IMAGE_LIVE_ENABLED=true, a key, PROVIDER_EGRESS=live and a monthly budget > 0 (owner activation).

Outcome handling: 429/5xx are retried with backoff (Retry-After honoured). A timeout after the request was sent is an UNKNOWN
outcome: neither OpenAI nor Stability offers an image lookup, so the job is FAILED with provenance.outcome=UNKNOWN, the budget
reservation is kept (the provider may have charged) and nothing is retried automatically. Provider failures never produce a stock image.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked, provider_client
from app.models.m51_media import M51ImageJob

SIZES = {"1024x1024": "1:1", "1536x1024": "3:2", "1024x1536": "2:3"}
PROVIDERS = ("simulator", "openai", "stability")
MODERATION = {
    "sexual content": re.compile(r"\b(nude|naked|nsfw|porn\w*|erotic|sexual\w*)\b", re.I),
    "graphic violence": re.compile(r"\b(gore|bloody|mutilat\w*|corpse|beheading|torture)\b", re.I),
    "hate or harassment": re.compile(r"\b(nazi|racial slur|hate symbol|genocide)\b", re.I),
    "weapons or drugs": re.compile(r"\b(firearm|assault rifle|bomb|cocaine|heroin|meth)\b", re.I),
    "minors in unsafe context": re.compile(r"\b(child|minor|kid)\w*\b.*\b(nude|naked|sexual\w*)\b", re.I),
    "real person likeness": re.compile(r"\b(photo of|portrait of|looks like)\s+(president|prime minister|celebrity)\b", re.I),
}


def cfg(name, default):
    return getattr(settings, name, default)


class ImageError(Exception):
    def __init__(self, message: str, status: int = 502, kind: str = "SERVER"):
        super().__init__(message)
        self.status, self.kind = status, kind


def provider_name() -> str:
    return (cfg("M51_IMAGE_PROVIDER", "") or "").strip().lower()


def status() -> dict:
    p = provider_name()
    budget = float(cfg("M51_IMAGE_MONTHLY_BUDGET_USD", 0))
    base = {"budget_usd": budget, "operations": ["GENERATE"], "sizes": list(SIZES)}
    if p not in PROVIDERS:
        return {**base, "status": "NOT_CONFIGURED", "detail": "No image provider is configured (set M51_IMAGE_PROVIDER). Upload artwork to the asset library instead."}
    if p == "openai":
        base["operations"] = ["GENERATE", "EDIT"]
    if p == "simulator":
        return {**base, "status": "AVAILABLE", "provider": p, "mode": "SIMULATED", "operations": ["GENERATE", "EDIT"]}
    live = bool(cfg("M51_IMAGE_LIVE_ENABLED", False))
    key = cfg("OPENAI_API_KEY", "") if p == "openai" else cfg("STABILITY_API_KEY", "")
    if not (live and key):
        return {**base, "status": "NOT_CONFIGURED", "provider": p, "mode": "LIVE",
                "detail": "Needs M51_IMAGE_LIVE_ENABLED=true and the provider API key (owner activation)."}
    return {**base, "status": "AVAILABLE", "provider": p, "mode": "LIVE"}


# ── gates ───────────────────────────────────────────────────────────────────

def moderate(*texts: str) -> list[dict]:
    out = []
    for t in texts:
        for label, pat in MODERATION.items():
            if t and pat.search(t):
                out.append({"level": "error", "code": "moderation", "message": f"Blocked by moderation: {label}."})
    return out


async def brand_profile(db: AsyncSession, key: Optional[str]):
    from app.models.cms import CsBrandProfile
    if key:
        return (await db.execute(select(CsBrandProfile).where(CsBrandProfile.key == key))).scalar_one_or_none()
    p = (await db.execute(select(CsBrandProfile).order_by(CsBrandProfile.key).limit(1))).scalar_one_or_none()
    return p or SimpleNamespace(key=None, terminology={}, banned_terms=[], evidence=[], claim_terms=[])


def claim_check(profile, prompt: str, overlay: Optional[str]) -> list[dict]:
    """Same rules as the content studio: banned terms and claims without approved evidence [E:id] are errors."""
    from app.services import content_studio_service as cs
    f = cs.review(profile, prompt, "web")[1] + (cs.review(profile, overlay, "web")[1] if overlay else [])
    return [x for x in f if x["level"] == "error"]


async def build_prompt(db: AsyncSession, prompt: str, product_skus: list[str]) -> tuple[str, list[dict]]:
    """Brand reference: brand name and the named POVU products from the M48 brand context are added to the prompt."""
    from app.services.brand_context_service import context
    ctx = await context(db)
    known = {p["sku"]: p["name"] for ln in ctx["lines"] for p in ln["products"]}
    bad = [s for s in product_skus if s not in known]
    findings = [{"level": "error", "code": "unknown_sku", "message": f"SKU {s} is not an active product."} for s in bad]
    names = ", ".join(known[s] for s in product_skus if s in known)
    pre = f"Brand: {ctx['brand']}." + (f" Products shown: {names}." if names else "") + " "
    return pre + prompt.strip(), findings


# ── budget ──────────────────────────────────────────────────────────────────

def _month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


async def reserve(db: AsyncSession, est: float, budget: float) -> bool:
    await db.execute(text("INSERT INTO m51_image_usage (month, spent, calls) VALUES (:m, 0, 0) ON CONFLICT (month) DO NOTHING"), {"m": _month()})
    got = (await db.execute(text("UPDATE m51_image_usage SET spent = spent + :e, calls = calls + 1 WHERE month = :m AND spent + :e <= :b RETURNING month"),
                            {"e": est, "m": _month(), "b": budget})).first()
    return got is not None


async def release(db: AsyncSession, est: float) -> None:
    await db.execute(text("UPDATE m51_image_usage SET spent = GREATEST(0, spent - :e) WHERE month = :m"), {"e": est, "m": _month()})


# ── provider adapters ───────────────────────────────────────────────────────

def _png_or_jpeg(b: bytes) -> bool:
    return b[:8] == b"\x89PNG\r\n\x1a\n" or b[:3] == b"\xff\xd8\xff"


async def _send(method_url: tuple[str, str], retries: int = 3, **kw) -> httpx.Response:
    method, url = method_url
    for attempt in range(retries + 1):
        try:
            async with provider_client(timeout=float(cfg("M51_IMAGE_TIMEOUT", 120))) as c:
                r = await c.request(method, url, **kw)
        except EgressBlocked as e:
            raise ImageError(str(e), 503, "BLOCKED")
        except httpx.TimeoutException:
            raise ImageError("The provider did not answer in time; the outcome is unknown", 504, "UNKNOWN")
        except httpx.HTTPError as e:
            raise ImageError(f"Network error: {type(e).__name__}", 502, "SERVER")
        if (r.status_code == 429 or r.status_code >= 500) and attempt < retries:
            await asyncio.sleep(min(float(r.headers.get("Retry-After", 0.5 * 2 ** attempt)), float(cfg("M51_IMAGE_MAX_BACKOFF", 8))))
            continue
        return r
    return r


def _map_error(r: httpx.Response) -> ImageError:
    code = ""
    try:
        e = r.json().get("error") or {}
        code = (e.get("code") or e.get("type") or "") if isinstance(e, dict) else str(e)
    except Exception:
        pass
    s = r.status_code
    if s == 401:
        return ImageError("The provider rejected the API key", 502, "AUTH")
    if s == 402:
        return ImageError("The provider account has no credits", 502, "CREDITS")
    if s == 403 or "moderation" in code or "content_policy" in code:
        return ImageError("The provider's own moderation blocked this request", 422, "MODERATION")
    if s == 429:
        return ImageError("Provider rate limit; try again later", 503, "RATE")
    if 400 <= s < 500:
        return ImageError(f"The provider refused the request ({s} {code})"[:200], 422, "CLIENT")
    return ImageError(f"Provider error {s}", 502, "SERVER")


async def _openai_like(base: str, key: str, model: str, op: str, prompt: str, size: str, source: Optional[bytes]) -> tuple[bytes, dict]:
    h = {"Authorization": f"Bearer {key}"}
    if op == "EDIT":
        r = await _send(("POST", f"{base}/images/edits"), headers=h, data={"model": model, "prompt": prompt, "size": size},
                        files=[("image[]", ("source.png", source, "image/png"))])
    else:
        r = await _send(("POST", f"{base}/images/generations"), headers=h,
                        json={"model": model, "prompt": prompt, "n": 1, "size": size, "output_format": "png", "moderation": "auto"})
    if r.status_code != 200:
        raise _map_error(r)
    try:
        d = r.json()
        item = d["data"][0]
        img = base64.b64decode(item["b64_json"], validate=True)
    except Exception:
        raise ImageError("The provider answered with something that is not an image", 502, "BAD_RESPONSE")
    return img, {"model": model, "request_id": r.headers.get("x-request-id"), "revised_prompt": item.get("revised_prompt"),
                 "usage": d.get("usage")}


async def _stability(base: str, key: str, prompt: str, size: str, negative: Optional[str]) -> tuple[bytes, dict]:
    data = {"prompt": prompt, "aspect_ratio": SIZES[size], "output_format": "png"}
    if negative:
        data["negative_prompt"] = negative
    r = await _send(("POST", f"{base}/v2beta/stable-image/generate/core"), headers={"Authorization": f"Bearer {key}", "Accept": "image/*"},
                    data=data, files={"none": ("", b"")})       # the endpoint requires multipart/form-data
    if r.status_code != 200:
        raise _map_error(r)
    if r.headers.get("finish-reason") == "CONTENT_FILTERED":
        raise ImageError("The provider's own moderation filtered the output", 422, "MODERATION")
    return r.content, {"model": "stable-image-core", "request_id": r.headers.get("x-request-id"), "seed": r.headers.get("seed")}


async def call_provider(op: str, prompt: str, size: str, source: Optional[bytes], negative: Optional[str]) -> tuple[bytes, dict, str, str]:
    """Returns (image bytes, provider meta, provider, mode)."""
    p, st = provider_name(), status()
    if st["status"] != "AVAILABLE":
        raise ImageError(st.get("detail", "Image provider is not configured"), 409, "NOT_CONFIGURED")
    if p == "simulator":
        img, meta = await _openai_like(cfg("M51_IMAGE_SIM_BASE_URL", "http://127.0.0.1:8765/v1"), cfg("M51_IMAGE_SIM_KEY", "sim-image-key"),
                                       "sim-image-1", op, prompt, size, source)
        return img, meta, p, "SIMULATED"
    if p == "openai":
        img, meta = await _openai_like(cfg("M51_OPENAI_IMAGE_BASE_URL", "https://api.openai.com/v1"), cfg("OPENAI_API_KEY", ""),
                                       cfg("M51_OPENAI_IMAGE_MODEL", "gpt-image-2"), op, prompt, size, source)
        return img, meta, p, "LIVE"
    if op == "EDIT":
        raise ImageError("Stability AI editing is not supported by this adapter (no documented edit endpoint was verified)", 422, "UNSUPPORTED")
    img, meta = await _stability(cfg("M51_STABILITY_BASE_URL", "https://api.stability.ai"), cfg("STABILITY_API_KEY", ""), prompt, size, negative)
    return img, meta, p, "LIVE"


# ── job flow ────────────────────────────────────────────────────────────────

async def create_job(db: AsyncSession, user, *, title: str, prompt: str, operation: str = "GENERATE", size: str = "1024x1024",
                     overlay_text: Optional[str] = None, brand_key: Optional[str] = None, product_skus: Optional[list[str]] = None,
                     source_document_id: Optional[uuid.UUID] = None, negative_prompt: Optional[str] = None,
                     idempotency_key: Optional[str] = None) -> M51ImageJob:
    from app.models.documents import Document, DocumentCategory, DocumentStatus
    from app.services.document_storage_service import get_document_storage, scan_document
    if idempotency_key:
        prev = (await db.execute(select(M51ImageJob).where(M51ImageJob.idempotency_key == idempotency_key))).scalar_one_or_none()
        if prev:
            return prev
    if size not in SIZES:
        raise ImageError(f"Size must be one of {', '.join(SIZES)}", 422, "CLIENT")
    p = provider_name()
    job = M51ImageJob(operation=operation, provider=p or "none", mode="SIMULATED" if p == "simulator" else "LIVE", status="REJECTED",
                      title=title.strip(), prompt=prompt.strip(), prompt_sha256=hashlib.sha256(prompt.strip().encode()).hexdigest(),
                      overlay_text=overlay_text, size=size, brand_key=brand_key, source_document_id=source_document_id,
                      findings=[], provenance={}, idempotency_key=idempotency_key, created_by=user.username, created_by_id=user.id)
    db.add(job)
    # 1. gates that need no provider call
    profile = await brand_profile(db, brand_key)
    if brand_key and profile is None:
        raise ImageError("Brand profile not found", 404, "CLIENT")
    full_prompt, findings = await build_prompt(db, job.prompt, product_skus or [])
    findings += moderate(job.prompt, overlay_text or "", negative_prompt or "") + claim_check(profile, job.prompt, overlay_text)
    job.findings = findings
    if findings:
        job.error = "Rejected before any provider call: " + findings[0]["message"]
        await db.flush()
        return job
    source = None
    if operation == "EDIT":
        src = await db.get(Document, source_document_id) if source_document_id else None
        if src is None or src.category != DocumentCategory.MARKETING_CREATIVE or (src.mime_type or "") not in ("image/png", "image/jpeg") or not src.storage_key:
            job.error = "Editing needs an existing marketing image (PNG or JPEG) from the asset library"
            job.findings = [{"level": "error", "code": "bad_source", "message": job.error}]
            await db.flush()
            return job
        source = await asyncio.to_thread(get_document_storage().path_for(src.storage_key).read_bytes)
    # 2. budget
    est = float(cfg("M51_IMAGE_COST_USD", 0.04))
    budget = float(cfg("M51_IMAGE_MONTHLY_BUDGET_USD", 0))
    job.status = "FAILED"
    if provider_name() not in PROVIDERS or status()["status"] != "AVAILABLE":
        job.error = status().get("detail", "Image provider not configured")
        await db.flush()
        return job
    if not await reserve(db, est, budget):
        job.error = "Monthly image budget exhausted (or not set)"
        job.findings = [{"level": "error", "code": "budget", "message": job.error}]
        await db.flush()
        return job
    job.cost_estimate = Decimal(str(est))
    await db.flush()
    await db.commit()                       # keep the reservation durable before the paid call
    # 3. provider call
    try:
        img, meta, prov, mode = await call_provider(operation, full_prompt, size, source, negative_prompt)
    except ImageError as e:
        job.status, job.error = ("REJECTED" if e.kind == "MODERATION" else "FAILED"), str(e)[:400]
        job.provenance = {"provider": p, "outcome": "UNKNOWN" if e.kind == "UNKNOWN" else "NO_IMAGE", "kind": e.kind}
        if e.kind != "UNKNOWN":             # nothing was produced: give the reservation back
            await release(db, est)
            job.cost_estimate = Decimal(0)
        if e.kind == "MODERATION":
            job.findings = [{"level": "error", "code": "provider_moderation", "message": str(e)}]
        await db.flush()
        return job
    # 4. validate + store as a DRAFT document
    if not _png_or_jpeg(img) or len(img) > int(cfg("M51_IMAGE_MAX_BYTES", 10 << 20)):
        await release(db, est)
        job.cost_estimate = Decimal(0)
        job.error = "The provider returned an invalid or oversized image"
        await db.flush()
        return job
    revised = meta.get("revised_prompt") or ""
    rf = moderate(revised) + claim_check(profile, revised, None) if revised else []
    from fastapi import UploadFile
    from starlette.datastructures import Headers
    mime = "image/png" if img[:4] == b"\x89PNG" else "image/jpeg"
    storage = get_document_storage()
    stored = await storage.store_upload(UploadFile(io.BytesIO(img), filename="generated.png" if mime == "image/png" else "generated.jpg",
                                                   headers=Headers({"content-type": mime})))
    scan = await scan_document(storage.path_for(stored.storage_key))
    prov_info = {"provider": prov, "model": meta.get("model"), "mode": mode, "prompt_sha256": job.prompt_sha256,
                 "generated_at": datetime.now(timezone.utc).isoformat(), "request_id": meta.get("request_id"),
                 "revised_prompt_sha256": hashlib.sha256(revised.encode()).hexdigest() if revised else None, "operation": operation}
    doc = Document(title=job.title, category=DocumentCategory.MARKETING_CREATIVE, status=DocumentStatus.DRAFT,
                   description=f"AI image ({mode}) via {prov}/{meta.get('model')}; prompt sha256 {job.prompt_sha256[:16]}; generated {prov_info['generated_at']}. DRAFT: approve before use.",
                   document_type="AI_IMAGE", file_name=stored.file_name, file_size_bytes=stored.file_size_bytes, mime_type=stored.mime_type,
                   storage_provider="local", storage_key=stored.storage_key, file_checksum_sha256=stored.sha256,
                   file_scan_status=scan.status, file_scan_result=scan.result, owner_user_id=user.id, created_by_id=user.id, updated_by_id=user.id)
    db.add(doc)
    await db.flush()
    job.document_id, job.provenance, job.provider, job.mode, job.model = doc.id, prov_info, prov, mode, meta.get("model")
    job.findings, job.status, job.error = rf, "GENERATED", None
    if any(f["level"] == "error" for f in rf):     # provider's revised prompt introduced a claim or banned content: keep as draft, flagged
        job.error = "Review needed: " + rf[0]["message"]
    await db.flush()
    return job


class ReviewError(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


async def review(db: AsyncSession, job: M51ImageJob, user, approve: bool, note: str = "") -> M51ImageJob:
    """A second person approves or discards. Approval flips the DAM document to APPROVED, which is what makes it usable by
    e-mail, social, CMS and ads (they read approved + scan-clean MARKETING_CREATIVE images only)."""
    from app.models.documents import Document, DocumentStatus
    if job.status != "GENERATED":
        raise ReviewError(f"A job in {job.status} cannot be reviewed")
    if job.created_by_id == user.id:
        raise ReviewError("A different person must review this image", 403)
    doc = await db.get(Document, job.document_id)
    now = datetime.now(timezone.utc)
    if approve:
        if any(f["level"] == "error" for f in job.findings or []):
            raise ReviewError("This draft has unresolved findings; discard it and regenerate")
        if doc.file_scan_status != "CLEAN":
            raise ReviewError("An unscanned or infected image cannot be approved")
        doc.status, doc.approved_by_id, doc.approved_at, job.status = DocumentStatus.APPROVED, user.id, now, "APPROVED"
    else:
        doc.status, doc.archived_at, job.status = DocumentStatus.ARCHIVED, now, "DISCARDED"
    job.reviewed_by, job.reviewed_at, job.review_note = user.username, now, note[:300]
    return job
