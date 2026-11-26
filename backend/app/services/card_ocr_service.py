"""M50.S01.T010 business-card text recognition with review and consent.

Engine: RapidOCR 3.x (Apache-2.0) on ONNX Runtime (MIT) with the PP-OCR detection/recognition models bundled in the wheel
(Apache-2.0). Pure pip, no system binary, no network call at run time; runs on CPU in a worker thread.
The picture is read in memory and thrown away: only the recognised text and the fields suggested from it are stored,
as a DRAFT owned by the person who scanned. Nothing becomes a contact until that person reviews every field and
confirms they may keep the card holder's details; confirming records the consent time and an audit row. A draft nobody
confirms is deleted after 7 days.
"""
from __future__ import annotations

import io
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_PIXELS = 12_000_000
DRAFT_TTL = timedelta(days=7)
_engine = None
_lock = threading.Lock()


class OcrError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def status() -> dict:
    try:
        import onnxruntime
        import rapidocr
        return {"available": True, "engine": f"rapidocr {getattr(rapidocr, '__version__', '')} + onnxruntime {onnxruntime.__version__}",
                "installs_with": "pip only (models bundled)"}
    except Exception as e:
        return {"available": False, "engine": None, "reason": f"{type(e).__name__}: {e}"}


def _validate(data: bytes):
    from PIL import Image
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise OcrError(413, f"The picture must be 1 byte to {MAX_IMAGE_BYTES // (1024 * 1024)} MB.")
    if not (data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG\r\n\x1a\n")):
        raise OcrError(415, "The card picture must be a JPEG or PNG.")
    try:
        im = Image.open(io.BytesIO(data))
        w, h = im.size
        im.verify()
    except Exception:
        raise OcrError(415, "The picture is damaged or not a picture.")
    if w * h > MAX_PIXELS:
        raise OcrError(413, "The picture is too large (over 12 megapixels); take a smaller photo.")
    return Image.open(io.BytesIO(data)).convert("RGB")


def read_text(data: bytes) -> tuple[str, list[dict]]:
    """→ (text one recognised line per line, [{text, confidence}]). Blocking: call from a worker thread."""
    global _engine
    import numpy as np
    img = _validate(data)
    with _lock:
        if _engine is None:
            from rapidocr import RapidOCR
            _engine = RapidOCR()
        res = _engine(np.asarray(img)[:, :, ::-1])
    txts = list(res.txts or ())
    scores = [round(float(s), 3) for s in (res.scores or ())]
    lines = [{"text": t, "confidence": scores[i] if i < len(scores) else None} for i, t in enumerate(txts)]
    return "\n".join(txts), lines


def suggest(text: str, lines: list[dict]) -> dict:
    """Field suggestions with the OCR line confidence blended into the parser's own confidence."""
    from app.services.customer_data_service import parse_card
    fields = parse_card(text)["fields"]
    conf = {l["text"].strip(): l["confidence"] for l in lines if l.get("confidence") is not None}
    out = {}
    for k, v in fields.items():
        line_conf = next((c for t, c in conf.items() if str(v["value"]).lower() in t.lower() or t.lower() in str(v["value"]).lower()), None)
        out[k] = {"value": v["value"], "confidence": round(min(v["confidence"], line_conf) if line_conf is not None else v["confidence"], 3)}
    return out


async def create_draft(db, user, data: bytes):
    from starlette.concurrency import run_in_threadpool
    from app.models.m50_data_sso import OcrCardDraft
    try:
        text, lines = await run_in_threadpool(read_text, data)
    except OcrError:
        raise
    except Exception as e:
        raise OcrError(503, f"Text recognition is not available ({type(e).__name__}).")
    if not text.strip():
        raise OcrError(422, "No text could be read from this picture; try a sharper, well-lit photo.")
    await db.execute(OcrCardDraft.__table__.delete().where(OcrCardDraft.status == "DRAFT",
                                                           OcrCardDraft.created_at < datetime.now(timezone.utc) - DRAFT_TTL))
    d = OcrCardDraft(created_by=user.username, engine=status()["engine"][:40], text=text[:3000], fields=suggest(text, lines))
    db.add(d)
    await db.flush()
    return d


async def confirm(db, draft, user, fields: dict, consent: bool):
    """Create the contact from the reviewed fields. Needs explicit consent; an existing e-mail is never overwritten."""
    from app.models.crm import CRMContact
    from app.services import crm_contact_service as cs
    from app.services import pat_service as pats
    if draft.status != "DRAFT":
        raise OcrError(409, f"This card is already {draft.status.lower()}.")
    if draft.created_by != user.username and not user.is_superuser:
        raise OcrError(404, "Card not found")
    if not consent:
        raise OcrError(422, "Confirm that the card holder gave you their card for business contact and that you may keep these details.")
    name = (fields.get("full_name") or "").strip()
    if not name:
        raise OcrError(422, "A name is required: type it in from the card.")
    email = cs.norm_email(fields.get("email")) if fields.get("email") else None
    if fields.get("email") and not email:
        raise OcrError(422, "The e-mail address is not valid.")
    if email and (dup := await cs.find_by_email(db, email)) is not None:
        raise OcrError(409, f"A contact with {email} already exists (id {dup.id}); open it instead of creating a second one.")
    c = CRMContact(full_name=name[:200], email=email, phone=(fields.get("phone") or None), job_title=(fields.get("job_title") or None),
                   owner_user_id=user.id, source="business-card-ocr", notes=("Company on card: " + fields["company"][:150]) if fields.get("company") else None)
    db.add(c)
    await db.flush()
    await cs.set_lifecycle(db, c, "LEAD", "ocr:card", user.id)
    draft.status, draft.consent_at, draft.contact_id = "CONFIRMED", datetime.now(timezone.utc), c.id
    draft.fields = {k: {"value": v, "confidence": 1.0, "reviewed": True} for k, v in fields.items() if v}
    pats.audit(db, user, "CARD_OCR_CONTACT_CREATED", "crm_contact", str(c.id), {"draft": str(draft.id), "consent": True})
    return c
