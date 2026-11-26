"""M47.S01.T007 / M51.S01.T007 local text-to-speech for narration. No cloud voice, no fake audio.

Engines (TTS_ENGINE): espeak / espeak-ng (system binary, GPL-3.0, called as a separate process) or piper (piper-tts, GPL-3.0,
neural voices from https://github.com/OHF-Voice/piper1-gpl ; voice models are separate .onnx files in PIPER_VOICES_DIR named
<lang>_<REGION>-<name>-<quality>.onnx with their .onnx.json, e.g. en_US-lessac-medium, sw_CD-lanfrica-medium, tr_TR-fahrettin-medium).
Voice selection: EN/SW/TR. espeak-ng ships voices for all three (robotic quality). piper uses a voice only when its model file
is installed for that language; a language without an installed voice is reported UNSUPPORTED (never read in another language).
Without an engine the adapter reports NOT_AVAILABLE. Text goes in on stdin, never as an argument.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from app.core.config import settings

ENGINES = ("espeak", "espeak-ng", "piper")
LOCALES = ("en", "sw", "tr")
VOICES = {"en": "en", "sw": "sw", "tr": "tr"}      # espeak-ng language codes
MAX_CHARS = 20000


class TtsUnavailable(RuntimeError):
    pass


class TtsUnsupported(TtsUnavailable):
    """The engine works but has no voice for this language."""


def _voices_dir() -> Path:
    return Path(getattr(settings, "PIPER_VOICES_DIR", "") or os.environ.get("PIPER_VOICES_DIR", "") or "data/voices")


def _piper_cmd() -> Optional[list[str]]:
    py = getattr(settings, "PIPER_PYTHON", "") or os.environ.get("PIPER_PYTHON", "")     # an interpreter that has piper-tts installed
    if py and Path(py).is_file():
        return [py, "-m", "piper"]
    exe = shutil.which("piper")
    if exe:
        return [exe]
    try:
        import importlib.util
        if importlib.util.find_spec("piper") is not None:
            return [sys.executable, "-m", "piper"]
    except Exception:
        pass
    return None


def piper_voice(locale: str) -> Optional[Path]:
    d = _voices_dir()
    hits = sorted(d.glob(f"{locale}_*.onnx")) if d.is_dir() else []
    return hits[0] if hits else None


def engine() -> Optional[str]:
    name = (os.environ.get("TTS_ENGINE", "") or getattr(settings, "TTS_ENGINE", "") or "").strip().lower()
    if name == "piper":
        return name if _piper_cmd() and any(piper_voice(l) for l in LOCALES) else None
    return name if name in ENGINES and shutil.which(name) else None


def voices() -> dict:
    """Per-language support for the configured engine."""
    e = engine()
    out = {}
    for l in LOCALES:
        if not e:
            out[l] = {"supported": False, "note": "No TTS engine available"}
        elif e == "piper":
            v = piper_voice(l)
            out[l] = {"supported": bool(v), "voice": v.stem if v else None,
                      "note": None if v else f"No piper voice installed for '{l}' in {_voices_dir()} (download one from the piper voices list)"}
        else:
            out[l] = {"supported": True, "voice": VOICES[l], "note": "espeak-ng formant voice (robotic)"}
    return out


def status() -> dict:
    e = engine()
    if e:
        return {"status": "AVAILABLE", "engine": e, "voices": voices()}
    return {"status": "NOT_AVAILABLE", "detail": "No local text-to-speech engine: set TTS_ENGINE=espeak-ng (and install it) or TTS_ENGINE=piper with piper-tts and a voice model in PIPER_VOICES_DIR.",
            "voices": voices()}


def _run(cmd: list[str], text: str, timeout: int) -> bytes:
    r = subprocess.run(cmd, input=text[:MAX_CHARS].encode("utf-8"), capture_output=True, timeout=timeout)
    if r.returncode != 0 or not r.stdout:
        raise TtsUnavailable(f"{Path(cmd[0]).name} failed: {r.stderr.decode(errors='replace')[:200]}")
    return r.stdout


def _piper(text: str, model: Path, timeout: int) -> bytes:
    cmd = _piper_cmd()
    with tempfile.TemporaryDirectory(prefix="piper-") as d:
        out = Path(d) / "out.wav"
        r = subprocess.run([*cmd, "-m", str(model), "-f", str(out)], input=text[:MAX_CHARS].encode("utf-8"), capture_output=True, timeout=timeout)
        if r.returncode != 0 or not out.is_file():
            raise TtsUnavailable(f"piper failed: {r.stderr.decode(errors='replace')[-200:]}")
        return out.read_bytes()


async def synthesize(text: str, locale: str, timeout: int = 300) -> bytes:
    """WAV bytes of the text read by the local engine in the page language."""
    e = engine()
    if not e:
        raise TtsUnavailable(status()["detail"])
    if locale not in LOCALES:
        raise TtsUnsupported(f"Language '{locale}' is not supported; narration supports {', '.join(LOCALES)}")
    if e == "piper":
        model = piper_voice(locale)
        if not model:
            raise TtsUnsupported(voices()[locale]["note"])
        return await asyncio.to_thread(_piper, text, model, timeout)
    return await asyncio.to_thread(_run, [shutil.which(e), "-v", VOICES[locale], "--stdin", "--stdout"], text, timeout)
