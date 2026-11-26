"""M47.S01.T007 AI image generation adapter for marketing creatives.

No image provider is connected (accountless build): get_generator() returns None and callers answer NOT_CONFIGURED.
A provider is plugged in here at activation; tests substitute a mock. Whatever a generator returns becomes a DRAFT
MARKETING_CREATIVE document that is unusable publicly until approved in the DAM.
"""
from __future__ import annotations

from typing import Optional, Protocol


class ImageGenerator(Protocol):
    name: str

    async def generate(self, prompt: str) -> bytes:   # PNG bytes
        ...


def get_generator() -> Optional[ImageGenerator]:
    return None


def status() -> dict:
    g = get_generator()
    if g is None:
        return {"status": "NOT_CONFIGURED", "detail": "No image generation provider is connected; upload artwork to the asset library instead."}
    return {"status": "AVAILABLE", "engine": g.name}
