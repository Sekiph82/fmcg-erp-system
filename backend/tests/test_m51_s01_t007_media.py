"""M51.S01.T007 TTS and media processing queue (DB part needs M51_DB=1; ffmpeg must be installed for the media jobs).

Unit: caption timing, tool status, TTS voice reporting incl. unsupported language. DB: poster (auto hook after upload), trim,
transcode, captions SRT/VTT, narration through a stand-in espeak-ng, UNAVAILABLE when a tool is missing, duration/size/timeout
limits, corrupt source, cancel, stale-job recovery, progress writer, RBAC and second-person approval of outputs.
"""
import asyncio
import os
import shutil
import subprocess
import sys
import uuid
import wave
from datetime import datetime, timedelta, timezone

import pytest

from app.services import m51_media_tools as mt
from app.services import tts_adapter as tts
from tests.m51_media_common import client_for, clean_scan, ensure_tables, setv, staff

DB = pytest.mark.skipif(os.environ.get("M51_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
FF = pytest.mark.skipif(not mt.ffmpeg(), reason="ffmpeg is not installed")
BASE = "/api/v1/media-studio"
PERMS = ("marketing.view", "marketing.create", "marketing.edit")


@pytest.fixture(autouse=True)
async def _cleanup():
    yield
    if os.environ.get("M51_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_captions_timing():
    srt, vtt, n = mt.make_captions("First sentence here. Second one is a bit longer than the first! Third?", 10)
    assert n == 3 and vtt.startswith("WEBVTT") and "00:00:00,000 --> " in srt and vtt.rstrip().endswith("Third?")
    assert "00:00:10.000" in vtt                                   # the last cue ends at the media duration
    assert "<b>" not in mt.make_captions("<b>Bold</b> text.", 2)[1]
    with pytest.raises(mt.MediaError):
        mt.make_captions("", 5)
    from app.services.cms_media_service import clean_vtt
    assert clean_vtt(vtt)                                          # the CMS accepts what we produce


FAKE_PY = ("import sys, wave\nsys.stdin.buffer.read()\nw = wave.open(sys.stdout.buffer, 'wb')\n"
           "w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b'\\x01\\x02' * 8000); w.close()\n")


def fake_engine(monkeypatch, tmp_path):
    """A stand-in espeak-ng (reads text on stdin, writes a 1 s WAV to stdout) so the adapter's process handling is exercised."""
    py = tmp_path / "fake_espeak.py"
    py.write_text(FAKE_PY)
    if os.name == "nt":
        launcher = tmp_path / "espeak-ng.cmd"
        launcher.write_text(f'@"{sys.executable}" "{py}" %*\n')
    else:
        launcher = tmp_path / "espeak-ng"
        launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{py}" "$@"\n')
        launcher.chmod(0o755)
    real = shutil.which
    monkeypatch.setattr(tts.shutil, "which", lambda n, *a, **k: str(launcher) if n == "espeak-ng" else real(n, *a, **k))
    monkeypatch.setenv("TTS_ENGINE", "espeak-ng")


@pytest.mark.asyncio
async def test_tts_adapter(monkeypatch, tmp_path):
    monkeypatch.setenv("TTS_ENGINE", "")
    assert tts.status()["status"] == "NOT_AVAILABLE" and not tts.voices()["en"]["supported"]
    with pytest.raises(tts.TtsUnavailable):
        await tts.synthesize("hello", "en")
    fake_engine(monkeypatch, tmp_path)
    assert tts.status()["status"] == "AVAILABLE" and all(tts.voices()[l]["supported"] for l in ("en", "sw", "tr"))
    wav = await tts.synthesize("Habari ya asubuhi", "sw")
    assert wav[:4] == b"RIFF"
    with pytest.raises(tts.TtsUnsupported):
        await tts.synthesize("bonjour", "fr")
    # piper without an installed voice for a language: honest UNSUPPORTED, no fallback to another language
    monkeypatch.setenv("TTS_ENGINE", "piper")
    monkeypatch.setattr(tts, "_piper_cmd", lambda: ["piper"])
    voices = tmp_path / "voices"
    voices.mkdir()
    (voices / "en_US-lessac-medium.onnx").write_bytes(b"x")
    setv(monkeypatch, "PIPER_VOICES_DIR", str(voices))
    v = tts.voices()
    assert v["en"]["supported"] and v["en"]["voice"] == "en_US-lessac-medium" and not v["sw"]["supported"] and "No piper voice" in v["sw"]["note"]
    with pytest.raises(tts.TtsUnsupported):
        await tts.synthesize("Habari", "sw")


def make_video(path, seconds=4):
    subprocess.run([mt.ffmpeg(), "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size=320x240:rate=15",
                    "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-c:v", "mpeg4", "-c:a", "aac", "-shortest", "-y", str(path)], check=True)


async def upload(c, name, data, part=1 << 20):
    s = (await c.post(f"{BASE}/storage/uploads", json={"file_name": name, "total_size": len(data), "part_size": part})).json()
    for i in range(1, s["parts_total"] + 1):
        assert (await c.put(f"{BASE}/storage/uploads/{s['id']}/parts/{i}", content=data[(i - 1) * part:i * part])).status_code == 200
    r = await c.post(f"{BASE}/storage/uploads/{s['id']}/complete")
    assert r.status_code == 200, r.text
    return r.json()


async def run(c, kind, source=None, **params):
    r = await c.post(f"{BASE}/jobs", json={"kind": kind, "source_object_id": source, "params": params})
    assert r.status_code == 201, r.text
    j = r.json()
    if j["status"] == "QUEUED":
        await mt.run_job(uuid.UUID(j["id"]))
        j = (await c.get(f"{BASE}/jobs/{j['id']}")).json()
    return j


@DB
@FF
@pytest.mark.asyncio
async def test_media_jobs(monkeypatch, tmp_path):
    from sqlalchemy import select, text
    from app.db.session import AsyncSessionLocal
    from app.models.m51_media import M51MediaJob, M51StorageObject
    await ensure_tables()
    clean_scan(monkeypatch)
    setv(monkeypatch, "MEDIA_STORAGE_PATH", str(tmp_path / "media"))
    setv(monkeypatch, "M51_STORAGE_BACKEND", "local")
    setv(monkeypatch, "M51_STORAGE_QUOTA_BYTES", 1 << 40)
    queued = []
    monkeypatch.setattr(mt, "schedule", lambda jid: queued.append(jid))      # the test runs jobs itself, deterministically
    fake_engine(monkeypatch, tmp_path)
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM m51_storage_quotas"))
        maker, approver, viewer = (await staff(db, "maker", PERMS), await staff(db, "approver", PERMS + ("marketing.approve",)),
                                   await staff(db, "viewer", ("marketing.view",)))
        await db.commit()
    vid = tmp_path / "sample.mp4"
    make_video(vid)
    data = vid.read_bytes()
    async with client_for(maker) as c, client_for(approver) as a, client_for(viewer) as v:
        st = (await c.get(f"{BASE}/status")).json()
        assert st["tools"]["ffmpeg"]["status"] == "AVAILABLE" and st["tools"]["presets"]["WAV"]["available"] and st["tools"]["tts"]["status"] == "AVAILABLE"
        o = await upload(c, "sample.mp4", data)
        assert o["mime"] == "video/mp4" and o["meta"]["hooks"] == ["POSTER"]
        # auto poster hook queued a job after upload
        auto = [q for q in queued if str(q) == o["meta"]["poster_job"]]
        assert auto
        j = (await c.get(f"{BASE}/jobs/{o['meta']['poster_job']}")).json()
        assert j["status"] == "QUEUED" and j["params"]["auto"]
        res = await mt.run_job(uuid.UUID(j["id"]))
        assert res == "SUCCEEDED", (await c.get(f"{BASE}/jobs/{j['id']}")).json()["error"]
        j = (await c.get(f"{BASE}/jobs/{j['id']}")).json()
        poster = next(x for x in (await c.get(f"{BASE}/storage/objects")).json() if x["id"] == j["output_object_id"])
        assert j["progress"] == 1.0 and poster["mime"] == "image/png" and poster["approval"] == "DRAFT" and poster["status"] == "READY"
        # trim 1..3 s: a ~2 s output
        t = await run(c, "TRIM", o["id"], start=1, end=3, reencode=True)
        assert t["status"] == "SUCCEEDED", t
        out = next(x for x in (await c.get(f"{BASE}/storage/objects")).json() if x["id"] == t["output_object_id"])
        async with AsyncSessionLocal() as db:
            ob = await db.get(M51StorageObject, uuid.UUID(out["id"]))
            from app.services import m51_storage as st_
            async with st_.materialize(ob) as p:
                assert 1.5 < await mt.probe_duration(p) < 2.6
        # transcode to WAV (always available); MP4 preset must match the reported availability
        w = await run(c, "TRANSCODE", o["id"], preset="WAV")
        assert w["status"] == "SUCCEEDED" and w["result"]["preset"] == "WAV"
        mp4 = await run(c, "TRANSCODE", o["id"], preset="MP4_H264")
        assert mp4["status"] == ("SUCCEEDED" if st["tools"]["presets"]["MP4_H264"]["available"] else "UNAVAILABLE")
        assert (await c.post(f"{BASE}/jobs", json={"kind": "TRANSCODE", "source_object_id": o["id"], "params": {"preset": "EXE"}})).status_code == 422
        # captions: estimated timing, SRT + VTT downloads
        cap = await run(c, "CAPTIONS", o["id"], text="Karibu POVU. Safi kwa kila nyumba. Asante sana!", locale="sw")
        assert cap["status"] == "SUCCEEDED" and cap["result"]["cues"] == 3 and "not speech recognition" in cap["result"]["timing"] and cap["has_captions"]
        vtt = await c.get(f"{BASE}/jobs/{cap['id']}/captions?format=vtt")
        srt = await c.get(f"{BASE}/jobs/{cap['id']}/captions?format=srt")
        assert vtt.text.startswith("WEBVTT") and "-->" in srt.text and "," in srt.text.split("\n")[1]
        # narration through the stand-in engine, per language; unsupported language refused at creation
        n = await run(c, "NARRATION", None, text="Habari ya asubuhi, karibu.", locale="sw")
        assert n["status"] == "SUCCEEDED" and n["result"]["engine"] == "espeak-ng" and n["result"]["locale"] == "sw"
        nobj = next(x for x in (await c.get(f"{BASE}/storage/objects")).json() if x["id"] == n["output_object_id"])
        assert nobj["mime"] == "audio/wav"
        assert (await c.post(f"{BASE}/jobs", json={"kind": "NARRATION", "params": {"text": "bonjour tout le monde", "locale": "fr"}})).status_code == 422
        # outputs are drafts; a second person approves
        assert (await c.post(f"{BASE}/storage/objects/{nobj['id']}/approve")).status_code == 403
        assert (await a.post(f"{BASE}/storage/objects/{nobj['id']}/approve")).json()["approval"] == "APPROVED"
        # missing tools are reported, nothing produced
        monkeypatch.setenv("TTS_ENGINE", "")
        un = (await c.post(f"{BASE}/jobs", json={"kind": "NARRATION", "params": {"text": "Hello there", "locale": "en"}})).json()
        assert un["status"] == "UNAVAILABLE" and "engine" in un["error"]
        fake_engine(monkeypatch, tmp_path)
        real_ff = mt.ffmpeg
        monkeypatch.setattr(mt, "ffmpeg", lambda: None)
        un = (await c.post(f"{BASE}/jobs", json={"kind": "TRIM", "source_object_id": o["id"], "params": {"start": 0, "end": 1}})).json()
        assert un["status"] == "UNAVAILABLE" and "ffmpeg" in un["error"]
        assert (await c.get(f"{BASE}/status")).json()["tools"]["ffmpeg"]["status"] == "UNAVAILABLE"
        monkeypatch.setattr(mt, "ffmpeg", real_ff)
        # limits: duration, source size, timeout
        setv(monkeypatch, "M51_MEDIA_MAX_SECONDS", 2)
        f = await run(c, "TRANSCODE", o["id"], preset="WAV")
        assert f["status"] == "FAILED" and "limit" in f["error"]
        assert (await c.post(f"{BASE}/jobs", json={"kind": "TRIM", "source_object_id": o["id"], "params": {"start": 0, "end": 3}})).status_code == 422
        setv(monkeypatch, "M51_MEDIA_MAX_SECONDS", 1800)
        setv(monkeypatch, "M51_MEDIA_PROCESS_MAX_BYTES", 100)
        assert (await c.post(f"{BASE}/jobs", json={"kind": "TRANSCODE", "source_object_id": o["id"], "params": {"preset": "WAV"}})).status_code == 413
        setv(monkeypatch, "M51_MEDIA_PROCESS_MAX_BYTES", 500 << 20)
        setv(monkeypatch, "M51_MEDIA_JOB_TIMEOUT", 0)
        to = await run(c, "TRANSCODE", o["id"], preset="WAV")
        assert to["status"] == "TIMEOUT" and "limit" in to["error"] and to["output_object_id"] is None
        setv(monkeypatch, "M51_MEDIA_JOB_TIMEOUT", 300)
        # corrupt source (valid container magic, no media)
        bad = await upload(c, "broken.mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200)
        fb = await run(c, "TRIM", bad["id"], start=0, end=1)
        assert fb["status"] == "FAILED" and "duration" in fb["error"].lower()
        # cancel a queued job; a cancelled job is never run
        q = (await c.post(f"{BASE}/jobs", json={"kind": "TRANSCODE", "source_object_id": o["id"], "params": {"preset": "WAV"}})).json()
        assert (await c.post(f"{BASE}/jobs/{q['id']}/cancel")).json()["status"] == "CANCELLED"
        assert await mt.run_job(uuid.UUID(q["id"])) == "SKIPPED"
        assert (await c.post(f"{BASE}/jobs/{q['id']}/cancel")).status_code == 409
        # progress writer persists, stale RUNNING jobs are recovered, RBAC
        async with AsyncSessionLocal() as db:
            sj = M51MediaJob(kind="TRIM", status="RUNNING", params={}, heartbeat_at=datetime.now(timezone.utc) - timedelta(hours=1), created_by="x")
            pj = M51MediaJob(kind="TRIM", status="RUNNING", params={}, heartbeat_at=datetime.now(timezone.utc), created_by="x")
            db.add_all([sj, pj])
            await db.commit()
        await (await mt._progress_writer(pj.id))(0.5)
        assert (await c.get(f"{BASE}/jobs/{pj.id}")).json()["progress"] == 0.5
        assert (await c.post(f"{BASE}/jobs/run-pending")).status_code == 403
        assert (await a.post(f"{BASE}/jobs/run-pending")).json()["stale_failed"] >= 1
        assert (await c.get(f"{BASE}/jobs/{sj.id}")).json()["status"] == "FAILED"
        assert (await v.post(f"{BASE}/jobs", json={"kind": "POSTER", "source_object_id": o["id"], "params": {}})).status_code == 403
        assert (await v.get(f"{BASE}/jobs")).status_code == 200
        async with AsyncSessionLocal() as db:
            await db.execute(text("UPDATE m51_media_jobs SET status='FAILED' WHERE status='RUNNING'"))
            await db.commit()
