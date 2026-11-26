"""M51.S01.T007 media processing queue: narration (local TTS), captions, poster/thumbnail, trim, transcode with progress.

Tools (all local, run as separate processes; nothing is linked into the app):
- ffmpeg: M51_FFMPEG_PATH, else `ffmpeg` on PATH (Debian `apt install ffmpeg`, the backend Dockerfiles install it), else the
  imageio-ffmpeg wheel's binary if that package is installed. https://ffmpeg.org/ffmpeg.html (LGPL/GPL by build; process boundary).
- TTS: tts_adapter (espeak-ng or piper). Unsupported languages are reported, never faked.
Missing tool or encoder → job status UNAVAILABLE with the reason; nothing is produced.
Safe limits: source size (M51_MEDIA_PROCESS_MAX_BYTES), duration (M51_MEDIA_MAX_SECONDS), wall-clock (M51_MEDIA_JOB_TIMEOUT, process
killed → TIMEOUT), output size (-fs M51_MEDIA_OUTPUT_MAX_BYTES), text length. Outputs are DRAFT storage objects until a second person approves.
Captions are NOT speech recognition: cue times are the script's sentences spread over the media duration in proportion to length.
"""
from __future__ import annotations

import asyncio
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.m51_media import M51MediaJob, M51StorageObject
from app.services import m51_storage as st
from app.services import tts_adapter as tts

KINDS = ("NARRATION", "CAPTIONS", "POSTER", "TRIM", "TRANSCODE")
# preset → (container extension, output mime, encoder args, required encoders)
PRESETS = {
    "MP4_H264": (".mp4", ["-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-pix_fmt", "yuv420p"], ("libx264", "aac")),
    "WEBM_VP8": (".webm", ["-c:v", "libvpx", "-b:v", "1M", "-c:a", "libvorbis"], ("libvpx", "libvorbis")),
    "MP3": (".mp3", ["-vn", "-c:a", "libmp3lame", "-b:a", "128k"], ("libmp3lame",)),
    "OGG": (".ogg", ["-vn", "-c:a", "libvorbis", "-q:a", "4"], ("libvorbis",)),
    "WAV": (".wav", ["-vn", "-c:a", "pcm_s16le"], ("pcm_s16le",)),
}
_procs: dict[str, asyncio.subprocess.Process] = {}
_tasks: set = set()
_sem: Optional[asyncio.Semaphore] = None


def cfg(name, default):
    return getattr(settings, name, default)


class MediaError(Exception):
    def __init__(self, message: str, status: int = 422, unavailable: bool = False):
        super().__init__(message)
        self.status, self.unavailable = status, unavailable


def ffmpeg() -> Optional[str]:
    p = cfg("M51_FFMPEG_PATH", "") or shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


_enc_cache: dict[str, set] = {}


async def encoders() -> set:
    exe = ffmpeg()
    if not exe:
        return set()
    if exe not in _enc_cache:
        p = await asyncio.create_subprocess_exec(exe, "-hide_banner", "-encoders", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(p.communicate(), 20)
        _enc_cache[exe] = {m.group(1) for m in re.finditer(r"^\s[VAS][\w.]{5}\s(\S+)", out.decode(errors="replace"), re.M)}
    return _enc_cache[exe]


async def tools_status() -> dict:
    exe, enc = ffmpeg(), await encoders()
    return {"ffmpeg": {"status": "AVAILABLE" if exe else "UNAVAILABLE", "path_configured": bool(exe),
                       "detail": None if exe else "ffmpeg not found: install it (apt install ffmpeg) or set M51_FFMPEG_PATH"},
            "presets": {k: {"available": all(e in enc for e in v[2]), "needs": list(v[2])} for k, v in PRESETS.items()},
            "tts": tts.status(),
            "limits": {"max_seconds": int(cfg("M51_MEDIA_MAX_SECONDS", 1800)), "timeout_seconds": int(cfg("M51_MEDIA_JOB_TIMEOUT", 300)),
                       "max_source_bytes": int(cfg("M51_MEDIA_PROCESS_MAX_BYTES", 500 << 20)), "max_text_chars": int(cfg("M51_TTS_MAX_CHARS", 5000))}}


# ── ffmpeg helpers ──────────────────────────────────────────────────────────

async def probe_duration(path: Path) -> float:
    exe = ffmpeg()
    p = await asyncio.create_subprocess_exec(exe, "-hide_banner", "-nostdin", "-i", str(path), stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    _, err = await asyncio.wait_for(p.communicate(), 30)
    m = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", err.decode(errors="replace"))
    if not m:
        raise MediaError("Cannot read the media duration (not a playable media file)")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


async def run_ffmpeg(job_id: str, args: list[str], total: float, on_progress) -> None:
    """Run ffmpeg with -progress, enforce the wall-clock timeout, report progress 0..1."""
    exe = ffmpeg()
    timeout = int(cfg("M51_MEDIA_JOB_TIMEOUT", 300))
    p = await asyncio.create_subprocess_exec(exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-progress", "pipe:1", "-nostats",
                                             *args[:-1], "-fs", str(int(cfg("M51_MEDIA_OUTPUT_MAX_BYTES", 1 << 30))), args[-1],   # -fs is an output option
                                             stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _procs[job_id] = p
    err_task = asyncio.create_task(p.stderr.read())

    async def pump():
        async for line in p.stdout:
            m = re.match(rb"out_time_us=(\d+)", line)
            if m and total > 0:
                await on_progress(min(0.99, int(m.group(1)) / 1e6 / total))
        await p.wait()
    try:
        await asyncio.wait_for(pump(), timeout)
    except asyncio.TimeoutError:
        p.kill()
        await p.wait()
        raise MediaError(f"ffmpeg exceeded the {timeout}s limit and was stopped", 504)
    finally:
        _procs.pop(job_id, None)
    err = (await err_task).decode(errors="replace")[:300]
    if p.returncode != 0:
        if p.returncode in (-9, -15, 137, 143):
            raise MediaError("The job was cancelled", 409)
        raise MediaError(f"ffmpeg could not process this media: {err}")


# ── captions ────────────────────────────────────────────────────────────────

def _ts(sec: float, comma: bool) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02}{',' if comma else '.'}{ms:03}"


def make_captions(text: str, duration: float) -> tuple[str, str, int]:
    """(srt, vtt, cue count): sentences share the duration in proportion to their length."""
    clean = re.sub(r"<[^>]*>", "", text or "")
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", clean) if s.strip()]
    if not sents or duration <= 0:
        raise MediaError("Captions need a script and a media with a duration")
    cues, total, t = [], sum(len(s) for s in sents), 0.0
    for s in sents:
        d = duration * len(s) / total
        cues.append((t, t + d, s))
        t += d
    srt = "\n".join(f"{i}\n{_ts(a, True)} --> {_ts(b, True)}\n{s}\n" for i, (a, b, s) in enumerate(cues, 1))
    vtt = "WEBVTT\n\n" + "\n".join(f"{_ts(a, False)} --> {_ts(b, False)}\n{s}\n" for a, b, s in cues)
    return srt, vtt, len(cues)


# ── queue ───────────────────────────────────────────────────────────────────

async def create(db: AsyncSession, user, kind: str, source_object_id: Optional[uuid.UUID], params: dict) -> M51MediaJob:
    if kind not in KINDS:
        raise MediaError("Unknown job kind")
    src = None
    if kind != "NARRATION":
        src = await db.get(M51StorageObject, source_object_id) if source_object_id else None
        if src is None or src.status != "READY":
            raise MediaError("The source media was not found or is not ready", 404)
        if src.size > int(cfg("M51_MEDIA_PROCESS_MAX_BYTES", 500 << 20)):
            raise MediaError("The source is over the processing size limit", 413)
    if kind == "NARRATION":
        text_ = (params.get("text") or "").strip()
        if len(text_) < 3 or len(text_) > int(cfg("M51_TTS_MAX_CHARS", 5000)):
            raise MediaError(f"Narration text must be 3–{int(cfg('M51_TTS_MAX_CHARS', 5000))} characters")
        if params.get("locale", "en") not in tts.LOCALES:
            raise MediaError(f"Narration languages: {', '.join(tts.LOCALES)}")
        params = {"text": text_, "locale": params.get("locale", "en")}
    elif kind == "CAPTIONS":
        if len((params.get("text") or "").strip()) < 3 or len(params["text"]) > 20000 or params.get("locale", "en") not in tts.LOCALES:
            raise MediaError("Captions need a script (≤20000 chars) and a locale en, sw or tr")
        params = {"text": params["text"].strip(), "locale": params.get("locale", "en")}
    elif kind == "POSTER":
        if not (src.mime.startswith("video/")):
            raise MediaError("A poster needs a video")
        params = {"at": max(0.0, float(params.get("at", 1.0))), "width": max(64, min(int(params.get("width", 640)), 1920)), "auto": bool(params.get("auto"))}
    elif kind == "TRIM":
        a, b = float(params.get("start", 0)), float(params.get("end", 0))
        if not (src.mime.startswith(("video/", "audio/"))) or a < 0 or b <= a:
            raise MediaError("Trim needs audio/video and 0 <= start < end")
        if b - a > int(cfg("M51_MEDIA_MAX_SECONDS", 1800)):
            raise MediaError("The trimmed length is over the duration limit")
        params = {"start": a, "end": b, "reencode": bool(params.get("reencode"))}
    elif kind == "TRANSCODE":
        if params.get("preset") not in PRESETS or not src.mime.startswith(("video/", "audio/")):
            raise MediaError(f"Transcode needs audio/video and a preset: {', '.join(PRESETS)}")
        params = {"preset": params["preset"]}
    job = M51MediaJob(kind=kind, status="QUEUED", params=params, source_object_id=src.id if src else None, created_by=user.username, result={})
    # missing tool → visible UNAVAILABLE job, nothing queued
    miss = None
    if kind == "NARRATION" and not tts.engine():
        miss = tts.status()["detail"]
    elif kind == "NARRATION" and not tts.voices()[params["locale"]]["supported"]:
        miss = tts.voices()[params["locale"]]["note"]
    elif kind != "NARRATION" and not ffmpeg():
        miss = "ffmpeg is not installed on the server"
    elif kind == "TRANSCODE":
        need = [e for e in PRESETS[params["preset"]][2] if e not in await encoders()]
        miss = f"This ffmpeg build lacks the encoder(s): {', '.join(need)}" if need else None
    if miss:
        job.status, job.error = "UNAVAILABLE", miss
    db.add(job)
    await db.flush()
    return job


def schedule(job_id: uuid.UUID) -> None:
    t = asyncio.get_running_loop().create_task(run_job(job_id))
    _tasks.add(t)
    t.add_done_callback(_tasks.discard)


async def _progress_writer(job_id):
    from app.db.session import AsyncSessionLocal
    last = [0.0]

    async def w(p: float):
        now = asyncio.get_running_loop().time()
        if now - last[0] < 0.4:
            return
        last[0] = now
        async with AsyncSessionLocal() as s:
            await s.execute(update(M51MediaJob).where(M51MediaJob.id == job_id, M51MediaJob.status == "RUNNING")
                            .values(progress=round(p, 3), heartbeat_at=datetime.now(timezone.utc)))
            await s.commit()
    return w


async def run_job(job_id: uuid.UUID) -> str:
    """Claim and run one job. Returns the final status."""
    global _sem
    from app.db.session import AsyncSessionLocal
    _sem = _sem or asyncio.Semaphore(int(cfg("M51_MEDIA_WORKERS", 2)))
    async with _sem:
        async with AsyncSessionLocal() as db:
            got = (await db.execute(update(M51MediaJob).where(M51MediaJob.id == job_id, M51MediaJob.status == "QUEUED")
                                    .values(status="RUNNING", started_at=datetime.now(timezone.utc), heartbeat_at=datetime.now(timezone.utc)).returning(M51MediaJob.id))).first()
            await db.commit()
            if not got:
                return "SKIPPED"
            job = await db.get(M51MediaJob, job_id)
            status, err, result, out_id = "SUCCEEDED", None, {}, None
            try:
                with tempfile.TemporaryDirectory(prefix="m51job-") as tmp:
                    result, out_id = await _execute(db, job, Path(tmp), await _progress_writer(job_id))
            except MediaError as e:
                status = "TIMEOUT" if e.status == 504 else "CANCELLED" if e.status == 409 and "cancelled" in str(e) else "FAILED"
                err = str(e)[:400]
            except tts.TtsUnsupported as e:
                status, err = "UNAVAILABLE", str(e)[:400]
            except (tts.TtsUnavailable, st.StorageError) as e:
                status, err = "FAILED", str(e)[:400]
            except Exception as e:                  # never leave a job RUNNING
                status, err = "FAILED", f"{type(e).__name__}: {str(e)[:300]}"
            await db.refresh(job)
            if job.status == "CANCELLED":
                status = "CANCELLED"
            job.status, job.error, job.result, job.finished_at = status, err, result, datetime.now(timezone.utc)
            job.output_object_id = out_id
            if status == "SUCCEEDED":
                job.progress = 1.0
            await db.commit()
            return status


async def _execute(db: AsyncSession, job: M51MediaJob, tmp: Path, progress) -> tuple[dict, Optional[uuid.UUID]]:
    p, jid = job.params, str(job.id)
    who = SimpleNamespace(username=job.created_by)
    if job.kind == "NARRATION":
        wav = await tts.synthesize(p["text"], p["locale"], int(cfg("M51_MEDIA_JOB_TIMEOUT", 300)))
        f = tmp / "narration.wav"
        f.write_bytes(wav)
        out = await st.store_file(db, f, f"narration-{p['locale']}-{jid[:8]}.wav", who, "JOB_OUTPUT", jid)
        v = tts.voices()[p["locale"]]
        return {"engine": tts.engine(), "voice": v.get("voice"), "locale": p["locale"], "chars": len(p["text"])}, out.id
    src = await db.get(M51StorageObject, job.source_object_id)
    async with st.materialize(src) as path:
        dur = await probe_duration(path)
        if dur > int(cfg("M51_MEDIA_MAX_SECONDS", 1800)) and job.kind != "TRIM":
            raise MediaError(f"The media is {dur:.0f}s; the limit is {int(cfg('M51_MEDIA_MAX_SECONDS', 1800))}s")
        if job.kind == "CAPTIONS":
            srt, vtt, n = make_captions(p["text"], dur)
            return {"srt": srt, "vtt": vtt, "cues": n, "locale": p["locale"], "timing": "estimated from sentence length, not speech recognition"}, None
        if job.kind == "POSTER":
            if p["at"] >= dur:
                raise MediaError(f"The poster time is past the end ({dur:.1f}s)")
            f = tmp / "poster.png"
            await run_ffmpeg(jid, ["-ss", f"{p['at']:.3f}", "-i", str(path), "-frames:v", "1", "-vf", f"scale={p['width']}:-2", "-y", str(f)], 1, progress)
            out = await st.store_file(db, f, f"poster-{jid[:8]}.png", who, "JOB_OUTPUT", jid)
            return {"at": p["at"], "width": p["width"]}, out.id
        if job.kind == "TRIM":
            if p["start"] >= dur:
                raise MediaError(f"The start is past the end ({dur:.1f}s)")
            ext = Path(src.file_name).suffix.lower() or ".mp4"
            f = tmp / f"trim{ext}"
            codec = [] if p["reencode"] else ["-c", "copy"]
            await run_ffmpeg(jid, ["-ss", f"{p['start']:.3f}", "-i", str(path), "-t", f"{p['end'] - p['start']:.3f}", *codec, "-y", str(f)], min(p["end"] - p["start"], dur), progress)
            out = await st.store_file(db, f, f"trim-{jid[:8]}{ext}", who, "JOB_OUTPUT", jid)
            return {"start": p["start"], "end": p["end"], "mode": "re-encode" if p["reencode"] else "stream copy (cuts on keyframes)"}, out.id
        ext, args, _ = PRESETS[p["preset"]]
        f = tmp / f"out{ext}"
        await run_ffmpeg(jid, ["-i", str(path), *args, "-y", str(f)], dur, progress)
        out = await st.store_file(db, f, f"transcode-{jid[:8]}{ext}", who, "JOB_OUTPUT", jid)
        return {"preset": p["preset"], "source_seconds": round(dur, 2)}, out.id


async def cancel(db: AsyncSession, job: M51MediaJob) -> None:
    if job.status == "QUEUED":
        job.status, job.finished_at = "CANCELLED", datetime.now(timezone.utc)
    elif job.status == "RUNNING":
        job.status = "CANCELLED"
        proc = _procs.get(str(job.id))
        if proc:
            proc.kill()
    else:
        raise MediaError(f"A {job.status} job cannot be cancelled", 409)


async def recover_stale(db: AsyncSession) -> int:
    """RUNNING jobs whose worker died (no heartbeat for timeout + 60 s) become FAILED; QUEUED jobs are returned for re-scheduling."""
    cut = datetime.now(timezone.utc) - timedelta(seconds=int(cfg("M51_MEDIA_JOB_TIMEOUT", 300)) + 60)
    r = await db.execute(update(M51MediaJob).where(M51MediaJob.status == "RUNNING", M51MediaJob.heartbeat_at < cut)
                         .values(status="FAILED", error="The worker stopped before this job finished", finished_at=datetime.now(timezone.utc)))
    return r.rowcount or 0


async def run_pending(db: AsyncSession) -> int:
    ids = (await db.execute(select(M51MediaJob.id).where(M51MediaJob.status == "QUEUED").order_by(M51MediaJob.created_at).limit(50))).scalars().all()
    for i in ids:
        schedule(i)
    return len(ids)
