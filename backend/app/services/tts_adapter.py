"""M47.S01.T007 text-to-speech adapter for post narration.

Only a local engine is supported: TTS_ENGINE=espeak or espeak-ng with that binary on PATH. Without it the adapter
reports NOT_AVAILABLE and nothing is synthesized (no cloud voice, no fake audio).
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from typing import Optional

ENGINES = ("espeak", "espeak-ng")
VOICES = {"en": "en", "sw": "sw", "tr": "tr"}
MAX_CHARS = 20000


class TtsUnavailable(RuntimeError):
    pass


def engine() -> Optional[str]:
    """The configured local engine, or None when it is not configured or its binary is missing."""
    name = os.environ.get("TTS_ENGINE", "").strip().lower()
    return name if name in ENGINES and shutil.which(name) else None


def status() -> dict:
    e = engine()
    if e:
        return {"status": "AVAILABLE", "engine": e}
    return {"status": "NOT_AVAILABLE", "detail": "No local text-to-speech engine: set TTS_ENGINE=espeak-ng and install it on the server."}


async def synthesize(text: str, locale: str) -> bytes:
    """WAV bytes of the text read by the local engine. Text goes in on stdin (never as an argument)."""
    e = engine()
    if not e:
        raise TtsUnavailable(status()["detail"])
    r = await asyncio.to_thread(subprocess.run, [shutil.which(e), "-v", VOICES.get(locale, "en"), "--stdin", "--stdout"],
                                input=text[:MAX_CHARS].encode("utf-8"), capture_output=True, timeout=300)
    if r.returncode != 0 or not r.stdout:
        raise TtsUnavailable(f"{e} failed: {r.stderr.decode(errors='replace')[:200]}")
    return r.stdout
