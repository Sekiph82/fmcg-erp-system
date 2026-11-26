"""Multilingual transcription with review (M49.S01.T005). Extends transcription_service (M43); does not replace it.

Provider adapter: OpenAI Audio Transcriptions, POST {base}/audio/transcriptions, multipart/form-data, Bearer auth
(https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create, read 2026-11-26):
- whisper-1 + response_format=verbose_json -> {language, duration, text, segments[{start, end, text, avg_logprob,
  no_speech_prob, ...}]}; segment timestamps, NO speaker labels.
- gpt-4o-transcribe-diarize + response_format=diarized_json + chunking_strategy=auto (required above 30 s) ->
  {duration, text, segments[{type, id, start, end, text, speaker}]}; speakers are "A", "B", ...; this model has no
  timestamp_granularities, no prompt and returns no detected language. Language support of the diarize model for sw/tr
  is not stated on the page: the job carries a warning (UNVERIFIED), never a claim.
- language is an ISO-639-1 code (en / sw / tr here); "auto" omits it. Upload limit 25 MB is the commonly documented
  figure and was not on the fetched page (UNVERIFIED); it is enforced client-side as a safe cap.
- Errors follow the OpenAI error object {"error": {"message", "type", "code"}} (not shown on that page: UNVERIFIED).
  429/5xx are retried with backoff (Retry-After honoured, capped); 400/401/403/413 are never retried.
Optional local engine: faster-whisper (not installed here -> NOT_AVAILABLE with an install note; nothing is pip-installed).

Honesty rules: every segment is passed through crm_copilot_service.redact BEFORE it is stored (raw text never kept);
"quality" holds only what the provider returned (mean avg_logprob / max no_speech_prob) plus deterministic flags - no
accuracy or word-error rate is ever computed or shown. A transcript is a machine draft until a person approves it; only
approved text feeds call/meeting coaching. Retention: TRANSCRIPT_RETENTION_DAYS (default 90).
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlsplit

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked, provider_client
from app.models.m49_voice import TranscriptEdit, TranscriptJob
from app.models.voip import CallLog
from app.services import transcription_service as legacy

log = logging.getLogger(__name__)
LANGS = ("en", "sw", "tr")
LANG_NAMES = {"english": "en", "swahili": "sw", "turkish": "tr"}
MAX_ATTEMPTS = 3
_BACKOFF = 1.0                                   # seconds, doubled per retry (tests patch it to 0)
OPENAI_MAX_BYTES = 25 * 1024 * 1024
LOW_LOGPROB = -1.0                               # the open-source Whisper default threshold; a heuristic flag, not accuracy
LOCAL_NOTE = ("faster-whisper is not installed. Install it on the server (pip install faster-whisper; the model downloads "
              "once into a local cache) and set TRANSCRIPTION_PROVIDER=local. Nothing was installed automatically.")


class TxError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 502, retryable: bool = False):
        super().__init__(message)
        self.code, self.status_code, self.retryable = code, status_code, retryable


def _cfg(name: str, default: str = "") -> str:
    return str(getattr(settings, name, default) or default)


def engines() -> list[dict]:
    """Every engine with an honest state; the UI shows these as they are."""
    try:
        import faster_whisper  # noqa: F401
        local = {"state": "AVAILABLE", "note": "Runs on this server; no speaker labels."}
    except ImportError:
        local = {"state": "NOT_AVAILABLE", "note": LOCAL_NOTE}
    has_key = bool(_cfg("TRANSCRIPTION_OPENAI_API_KEY"))
    return [
        {"key": "openai", "label": "OpenAI Whisper API", "state": "AVAILABLE" if has_key else "NOT_CONFIGURED",
         "note": None if has_key else "Set TRANSCRIPTION_OPENAI_API_KEY to enable (owner activation).",
         "languages": {"en": "SUPPORTED", "sw": "SUPPORTED", "tr": "SUPPORTED"},
         "timestamps": True, "speaker_labels": "diarize model only (gpt-4o-transcribe-diarize); sw/tr diarization UNVERIFIED"},
        {"key": "local", "label": "faster-whisper (local)", "timestamps": True, "speaker_labels": False,
         "languages": {"en": "SUPPORTED", "sw": "SUPPORTED", "tr": "SUPPORTED"}, **local},
        {"key": "http", "label": "Generic HTTP endpoint (M43)", "state": "AVAILABLE" if legacy.adapter() == "http" else "NOT_CONFIGURED",
         "note": None, "timestamps": True, "speaker_labels": "if the endpoint returns them", "languages": {}},
    ]


def _state(key: str) -> str:
    return next(e["state"] for e in engines() if e["key"] == key)


def default_engine() -> Optional[str]:
    return next((e["key"] for e in engines() if e["state"] == "AVAILABLE"), None)


# ── provider calls ────────────────────────────────────────────────────────────

def _ext(url: str) -> str:
    suffix = urlsplit(url).path.rsplit(".", 1)[-1].lower() if "." in urlsplit(url).path else ""
    return suffix if suffix in ("flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm") else "wav"


async def _openai(audio: bytes, ext: str, language: str, diarize: bool) -> dict:
    if len(audio) > OPENAI_MAX_BYTES:
        raise TxError("AUDIO_TOO_LARGE", "The recording is larger than the 25 MB upload cap.", 422)
    model = "gpt-4o-transcribe-diarize" if diarize else "whisper-1"
    data = {"model": model, "response_format": "diarized_json" if diarize else "verbose_json"}
    if language != "auto":
        data["language"] = language
    if diarize:
        data["chunking_strategy"] = "auto"
    for attempt in range(MAX_ATTEMPTS):
        wait = None
        try:
            async with provider_client(timeout=300) as c:
                r = await c.post(_cfg("TRANSCRIPTION_OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/audio/transcriptions",
                                 data=data, files={"file": (f"audio.{ext}", audio, "application/octet-stream")},
                                 headers={"Authorization": f"Bearer {_cfg('TRANSCRIPTION_OPENAI_API_KEY')}"})
        except EgressBlocked as e:
            raise TxError("EGRESS_BLOCKED", str(e), 503) from None
        except httpx.HTTPError:
            err = TxError("PROVIDER_UNAVAILABLE", "The transcription provider could not be reached.", 503, True)
        else:
            if r.status_code == 200:
                body = r.json()
                body["_model"] = model
                return body
            try:
                msg = str((r.json().get("error") or {}).get("message") or "")[:150]
            except ValueError:
                msg = ""
            if r.status_code in (401, 403):
                raise TxError("PROVIDER_AUTH", f"The transcription provider refused the credentials. {msg}".strip(), 424)
            if r.status_code == 413:
                raise TxError("AUDIO_TOO_LARGE", "The provider says the recording is too large.", 422)
            if r.status_code in (400, 404, 422):
                raise TxError("PROVIDER_REJECTED", f"The provider rejected the request. {msg}".strip(), 502)
            err = TxError("RATE_LIMITED" if r.status_code == 429 else "PROVIDER_UNAVAILABLE",
                          f"The transcription provider answered {r.status_code}.", 503, True)
            try:
                wait = min(float(r.headers.get("Retry-After", "")), 5.0)
            except ValueError:
                pass
        if attempt == MAX_ATTEMPTS - 1:
            raise err
        await asyncio.sleep(wait if wait is not None else _BACKOFF * (2 ** attempt))
    raise err   # pragma: no cover


def _norm_openai(body: dict, requested: str) -> dict:
    lang = LANG_NAMES.get(str(body.get("language") or "").lower(), str(body.get("language") or "")[:10] or None)
    segs = [{"start": s.get("start"), "end": s.get("end"), "speaker": s.get("speaker"), "text": s.get("text") or "",
             "avg_logprob": s.get("avg_logprob"), "no_speech_prob": s.get("no_speech_prob")} for s in body.get("segments") or []]
    return {"language": lang or (requested if requested != "auto" else None), "segments": segs, "model": body.get("_model")}


def _local_run(audio: bytes, language: str) -> dict:
    from faster_whisper import WhisperModel
    with tempfile.NamedTemporaryFile(suffix=".audio") as f:
        f.write(audio)
        f.flush()
        segments, info = WhisperModel("small", device="cpu", compute_type="int8").transcribe(
            f.name, language=None if language == "auto" else language)
        return {"language": info.language, "model": "faster-whisper-small",
                "segments": [{"start": s.start, "end": s.end, "speaker": None, "text": s.text.strip(),
                              "avg_logprob": s.avg_logprob, "no_speech_prob": s.no_speech_prob} for s in segments]}


async def _run_engine(engine: str, audio: bytes, url: str, language: str, diarize: bool) -> dict:
    if engine == "openai":
        return _norm_openai(await _openai(audio, _ext(url), language, diarize), language)
    if engine == "local":
        return await asyncio.to_thread(_local_run, audio, language)
    try:
        r = await legacy._http(audio)
    except (legacy.TranscriptionError, httpx.HTTPError, EgressBlocked) as e:
        raise TxError("PROVIDER_UNAVAILABLE", str(e)[:150], 503, True) from None
    return {"language": r.get("language"), "segments": r.get("segments") or [], "model": None}


# ── building the stored transcript ────────────────────────────────────────────

def _quality(segs: list[dict], res: dict, job: TranscriptJob) -> tuple[dict, list[str]]:
    lp = [s["avg_logprob"] for s in res["segments"] if isinstance(s.get("avg_logprob"), (int, float))]
    ns = [s["no_speech_prob"] for s in res["segments"] if isinstance(s.get("no_speech_prob"), (int, float))]
    flags, warnings = [], []
    if not any(s["text"].strip() for s in segs):
        flags.append("EMPTY")
    det = res.get("language")
    if job.language_requested != "auto" and det and det != job.language_requested:
        flags.append("LANGUAGE_MISMATCH")
    if lp and min(lp) < LOW_LOGPROB:
        flags.append("LOW_CONFIDENCE_SEGMENTS")
    if ns and max(ns) > 0.6:
        flags.append("POSSIBLE_NON_SPEECH")
    speakers = sorted({s["speaker"] for s in segs if s["speaker"]})
    if job.diarize and not speakers:
        flags.append("NO_SPEAKER_LABELS")
        warnings.append("Speaker labels were requested but the engine returned none.")
    if job.diarize and job.engine == "openai" and job.language_requested in ("sw", "tr", "auto"):
        warnings.append("Speaker-label quality for this language is UNVERIFIED (not stated by the provider).")
    q = {"segments": len(segs), "speakers": speakers, "flags": flags,
         "provider_signals": {"mean_avg_logprob": round(sum(lp) / len(lp), 3) if lp else None,
                              "max_no_speech_prob": round(max(ns), 3) if ns else None},
         "note": "Provider signals only; no accuracy or word-error rate is measured."}
    return q, warnings


def build(job: TranscriptJob, res: dict) -> None:
    from app.services.crm_copilot_service import redact
    segs, changed = [], 0
    for s in res["segments"][:5000]:
        raw = str(s.get("text") or "")[:4000]
        text = redact(raw) or ""
        changed += text != raw
        segs.append({"start": _f(s.get("start")), "end": _f(s.get("end")),
                     "speaker": str(s["speaker"])[:20] if s.get("speaker") else None, "text": text, "edited": False})
    job.segments, job.redacted_segments = segs, changed
    job.language_detected = (res.get("language") or None) and str(res["language"])[:10]
    job.model = res.get("model")
    job.quality, warns = _quality(segs, res, job)
    job.warnings = warns or None
    job.status, job.error, job.error_code = "DONE", None, None
    job.expires_at = datetime.now(timezone.utc) + timedelta(days=int(getattr(settings, "TRANSCRIPT_RETENTION_DAYS", 90) or 90))


def _f(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def text_of(job: TranscriptJob) -> str:
    return "\n".join((f"{s['speaker']}: " if s.get("speaker") else "") + s["text"] for s in job.segments or [])


# ── job lifecycle ─────────────────────────────────────────────────────────────

async def _audio_for(db: AsyncSession, job: TranscriptJob) -> tuple[bytes, str]:
    if job.source_type == "call":
        call = await db.get(CallLog, job.source_id)
        if call is None or not call.recording_consent or not (call.recording_url or "").startswith("https://"):
            raise TxError("NO_CONSENTED_RECORDING", "Only a consented https recording can be transcribed.", 422)
        if call.recording_expires_at and call.recording_expires_at < datetime.now(timezone.utc):
            raise TxError("RECORDING_EXPIRED", "The recording is past its retention date.", 422)
        url = call.recording_url
        auth = None
        if call.provider == "twilio" and url.startswith(_cfg("VOICE_TWILIO_BASE_URL", "https://api.twilio.com")):
            auth = (_cfg("VOICE_TWILIO_ACCOUNT_SID"), _cfg("VOICE_TWILIO_AUTH_TOKEN"))
    else:
        from app.models.meetings import MeetingRecord
        m = await db.get(MeetingRecord, job.source_id)
        if m is None or not (m.recording_url or "").startswith("https://") or not job.participants_consented:
            raise TxError("NO_CONSENTED_RECORDING", "A meeting recording and every participant's consent are required.", 422)
        url, auth = m.recording_url, None
    try:
        return await legacy._download(url, auth), url
    except legacy.TranscriptionError as e:
        raise TxError("DOWNLOAD_FAILED", str(e), e.status_code) from None
    except (EgressBlocked, httpx.HTTPError):
        raise TxError("DOWNLOAD_FAILED", "The recording could not be downloaded.", 502) from None


async def process(db: AsyncSession, job: TranscriptJob) -> TranscriptJob:
    """Run the job once (the provider adapter retries 429/5xx itself). On a retryable failure another available engine is tried."""
    try:
        audio, url = await _audio_for(db, job)
    except TxError as e:
        job.status, job.error_code, job.error = "FAILED", e.code, str(e)[:300]
        return job
    chain = [job.engine] + [e["key"] for e in engines() if e["state"] == "AVAILABLE" and e["key"] != job.engine and e["key"] != "openai"]
    for i, eng in enumerate(chain):
        job.attempts += 1
        try:
            if _state(eng) != "AVAILABLE":
                raise TxError("ENGINE_NOT_AVAILABLE", LOCAL_NOTE if eng == "local" else f"Engine {eng} is not configured.", 409)
            res = await _run_engine(eng, audio, url, job.language_requested, job.diarize)
        except TxError as e:
            job.status, job.error_code, job.error = "FAILED", e.code, str(e)[:300]
            if not e.retryable:
                return job
            continue
        if eng != job.engine:
            job.engine = eng
        build(job, res)
        if i:
            job.warnings = (job.warnings or []) + [f"Primary engine failed ({job.error_code}); fell back to {eng}."]
        return job
    return job


def manual(job: TranscriptJob, text: str) -> None:
    """Fallback when no engine works: a person types or pastes the transcript (no timestamps, no speakers)."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    build(job, {"language": None if job.language_requested == "auto" else job.language_requested, "model": None,
                "segments": [{"text": ln} for ln in lines]})
    job.engine, job.diarize = "manual", False
    job.quality = {**(job.quality or {}), "flags": [], "note": "Typed by a person; no engine produced this text."}
    job.warnings = None


# ── review, feed into coaching, withdraw ──────────────────────────────────────

async def edit_segment(db: AsyncSession, job: TranscriptJob, idx: int, text: Optional[str], speaker: Optional[str], user_id) -> dict:
    from app.services.crm_copilot_service import redact
    segs = [dict(s) for s in job.segments or []]
    if not 0 <= idx < len(segs):
        raise TxError("NO_SUCH_SEGMENT", "Segment not found.", 404)
    s = segs[idx]
    old_t, old_s = s["text"], s["speaker"]
    new_t = redact(text) if text is not None else old_t
    new_s = (speaker.strip()[:20] or None) if speaker is not None else old_s
    if (new_t, new_s) == (old_t, old_s):
        return s
    db.add(TranscriptEdit(job_id=job.id, segment_index=idx, old_text=old_t, new_text=new_t or "", old_speaker=old_s,
                          new_speaker=new_s, editor_id=user_id, edited_at=datetime.now(timezone.utc)))
    s.update(text=new_t or "", speaker=new_s, edited=True)
    job.segments = segs                                      # new list object so the JSONB change is detected
    if job.review_status == "REVIEWED":
        await feed(db, job)
    return s


async def feed(db: AsyncSession, job: TranscriptJob) -> Optional[str]:
    """Approved text becomes the call transcript (conversation intelligence / coaching) or the meeting recap draft."""
    text = text_of(job)
    if job.source_type == "call":
        call = await db.get(CallLog, job.source_id)
        if call is not None and call.recording_consent:
            call.transcript, call.transcript_segments = text[:200000], [{k: s[k] for k in ("start", "end", "speaker", "text")} for s in job.segments]
            call.transcript_language, call.transcription_status = job.language_detected, "DONE"
        return None
    from app.models.m47_sales_depth import MeetingRecap
    from app.services import meeting_service as ms
    r = await db.get(MeetingRecap, job.source_id)
    if r is not None and r.approved_at:
        return "The meeting recap was already approved; the corrected transcript was not applied to it."
    if len(text) < 20:
        return None
    recap, engine = await ms.build_recap(db, text[:200000], use_ai=False)
    consent = {"participants_consented": True, "attested_by": "transcription_job", "attested_at": datetime.now(timezone.utc).isoformat()}
    if r is None:
        r = MeetingRecap(meeting_id=job.source_id, transcript="", source="TRANSCRIPTION")
        db.add(r)
    r.transcript, r.source, r.recap, r.engine = text[:200000], "TRANSCRIPTION", {**recap, "consent": consent}, engine
    return None


async def withdraw(db: AsyncSession, job: TranscriptJob) -> None:
    """Delete the transcript, its edits, and what was fed from it (call text + quotes + clips; unapproved meeting recap)."""
    if job.source_type == "meeting":
        from app.models.m47_sales_depth import MeetingRecap
        r = await db.get(MeetingRecap, job.source_id)
        if r is not None and r.approved_at:
            raise TxError("RECAP_APPROVED", "The meeting recap was approved and its tasks exist; withdraw is blocked.", 409)
        if r is not None:
            await db.delete(r)
    else:
        call = await db.get(CallLog, job.source_id)
        if call is not None:
            call.transcript, call.transcript_segments, call.transcript_language = None, None, None
            call.transcription_status = "WITHDRAWN"
            from app.models.crm import CRMConversationInsight
            from app.models.voip import CoachingClip
            await db.execute(delete(CRMConversationInsight).where(CRMConversationInsight.source_type == "call",
                                                                  CRMConversationInsight.source_id == call.id))
            await db.execute(delete(CoachingClip).where(CoachingClip.call_id == call.id))
    await db.execute(delete(TranscriptEdit).where(TranscriptEdit.job_id == job.id))
    job.segments, job.quality, job.warnings, job.status = None, None, None, "WITHDRAWN"
    job.review_status, job.expires_at = "UNREVIEWED", None
