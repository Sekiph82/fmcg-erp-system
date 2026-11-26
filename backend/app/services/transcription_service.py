"""Call transcription and coaching (M43.S01.T009).

A consented recording (call.recording_consent, https link, within retention) is transcribed by the configured
adapter when CALL_TRANSCRIPTION_ENABLED is on:
- "local": an offline engine on this server (faster-whisper if installed). Not installed → NOT_AVAILABLE; the
  ERP never pretends a transcript exists.
- "http": a configured transcription endpoint with a simple documented contract — multipart POST
  (file=audio, language=auto|en|sw) with "Authorization: Bearer <key>" → {"language": "sw", "segments": [{"start":
  0.0, "end": 2.5, "speaker": "A", "text": "..."}]}. Any provider can sit behind it; tests use the local simulator.
Timestamps and speaker labels are stored when the engine returns them. Up to 3 attempts with backoff; the error is
kept. Withdrawing consent deletes the recording link, transcript and its coaching insights at once. Coaching reuses
conversation intelligence (every finding carries a verbatim quote from the transcript); the call recap lists only
quoted next steps and questions — nothing is invented.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked, provider_client
from app.models.voip import CallLog

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
MAX_AUDIO_BYTES = 50 * 1024 * 1024


class TranscriptionError(Exception):
    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


def adapter() -> Optional[str]:
    p = (settings.TRANSCRIPTION_PROVIDER or "").strip().lower()
    if p == "http" and settings.TRANSCRIPTION_HTTP_URL:
        return "http"
    if p == "local":
        try:
            import faster_whisper  # noqa: F401
            return "local"
        except ImportError:
            return None
    return None


def _eligible(call: CallLog) -> None:
    if not settings.CALL_TRANSCRIPTION_ENABLED:
        raise TranscriptionError("Call transcription is not enabled for this company.")
    if not call.recording_consent or not call.recording_url or not call.recording_url.startswith("https://"):
        raise TranscriptionError("Only a consented https recording can be transcribed.", 422)
    if call.recording_expires_at and call.recording_expires_at < datetime.now(timezone.utc):
        raise TranscriptionError("The recording is past its retention date.", 422)
    if adapter() is None:
        raise TranscriptionError("No transcription engine is configured (NOT_AVAILABLE).", 409)


async def request(db: AsyncSession, call: CallLog) -> CallLog:
    _eligible(call)
    if call.transcription_status not in ("PENDING",):
        call.transcription_status, call.transcription_error, call.transcription_attempts = "PENDING", None, 0
    return call


async def _download(url: str, auth: Optional[tuple] = None) -> bytes:
    """Streamed with a byte cap so a huge or endless body never fills memory (review M43 #7)."""
    async with provider_client(timeout=60) as c:
        async with c.stream("GET", url, auth=auth) as r:
            if r.status_code != 200:
                raise TranscriptionError(f"Recording download failed ({r.status_code}).", 502)
            buf = bytearray()
            async for chunk in r.aiter_bytes():
                buf += chunk
                if len(buf) > MAX_AUDIO_BYTES:
                    raise TranscriptionError("Recording is too large to transcribe.", 422)
    return bytes(buf)


async def _http(audio: bytes) -> dict:
    headers = {"Authorization": f"Bearer {settings.TRANSCRIPTION_HTTP_KEY}"} if settings.TRANSCRIPTION_HTTP_KEY else {}
    async with provider_client(timeout=300) as c:
        r = await c.post(settings.TRANSCRIPTION_HTTP_URL, files={"file": ("call.audio", audio)},
                         data={"language": "auto"}, headers=headers)
    if r.status_code != 200:
        raise TranscriptionError(f"Transcription service refused ({r.status_code}).", 502)
    return r.json()


def _local(audio: bytes) -> dict:
    from faster_whisper import WhisperModel
    with tempfile.NamedTemporaryFile(suffix=".audio") as f:
        f.write(audio)
        f.flush()
        segments, info = WhisperModel("small", device="cpu", compute_type="int8").transcribe(f.name)
        return {"language": info.language,
                "segments": [{"start": s.start, "end": s.end, "speaker": None, "text": s.text.strip()} for s in segments]}


async def process(db: AsyncSession, call: CallLog) -> CallLog:
    """Run one transcription attempt for a PENDING call. Caller commits."""
    try:
        _eligible(call)
        audio = await _download(call.recording_url)
        result = await _http(audio) if adapter() == "http" else await asyncio.to_thread(_local, audio)
    except (TranscriptionError, EgressBlocked, httpx.HTTPError, ValueError) as e:
        call.transcription_attempts = (call.transcription_attempts or 0) + 1
        call.transcription_error = str(e)[:300] or e.__class__.__name__
        if call.transcription_attempts >= MAX_ATTEMPTS or isinstance(e, TranscriptionError) and e.status_code == 422:
            call.transcription_status = "FAILED"
        return call
    segs = [{"start": float(s.get("start") or 0), "end": float(s.get("end") or 0),
             "speaker": (str(s["speaker"])[:20] if s.get("speaker") else None), "text": str(s.get("text") or "")[:4000]}
            for s in (result.get("segments") or [])][:5000]
    call.transcript_segments = segs
    call.transcript = "\n".join((f"{s['speaker']}: " if s["speaker"] else "") + s["text"] for s in segs)[:200000]
    call.transcript_language = str(result.get("language") or "")[:10] or None
    call.transcription_status, call.transcription_error = "DONE", None
    return call


async def withdraw_consent(db: AsyncSession, call: CallLog) -> None:
    """Delete recording, transcript and the insights quoted from it. Caller commits."""
    from app.models.crm import CRMConversationInsight
    call.recording_consent, call.recording_url, call.recording_expires_at = False, None, None
    call.transcript, call.transcript_segments, call.transcript_language = None, None, None
    call.transcription_status, call.transcription_error = "WITHDRAWN", None
    await db.execute(delete(CRMConversationInsight).where(CRMConversationInsight.source_type == "call",
                                                          CRMConversationInsight.source_id == call.id))
    from app.models.voip import CoachingClip           # M43.S01.T017: clips quoting this call go too
    await db.execute(delete(CoachingClip).where(CoachingClip.call_id == call.id))


def recap(insight_findings: list[dict]) -> dict:
    """Call recap from coaching findings: only quoted next steps and questions."""
    pick = lambda kind: [f.get("quote") for f in insight_findings if f.get("kind") == kind and f.get("quote")]  # noqa: E731
    return {"next_steps": pick("next_step"), "questions": pick("question"), "objections": pick("objection")}


async def run_pending(interval: float = 60.0) -> None:
    from app.db.session import AsyncSessionLocal

    while True:
        try:
            async with AsyncSessionLocal() as db:
                due = (await db.execute(select(CallLog).where(CallLog.transcription_status == "PENDING").limit(5)
                                        .with_for_update(skip_locked=True))).scalars().all()
                for call in due:
                    await process(db, call)
                    await db.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("transcription tick failed")
        await asyncio.sleep(interval)
