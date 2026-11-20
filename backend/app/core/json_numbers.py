"""Money and quantities leave the API as JSON numbers, not text (owner decision 2026-11-20).

Pydantic v2 writes Decimal as a string in JSON mode, so every response model with Decimal fields (~80 money/quantity
sites) sent "1250.5000" instead of 1250.5 and clients had to Number() each value. FastAPI's own encoder for plain
dict responses (jsonable_encoder) already turns Decimal into a number; this makes response models do the same:
serialize in Python mode (field serializers still run) and encode with jsonable_encoder. Database values stay Decimal.
"""
from __future__ import annotations

import json
import math
from typing import Any

from fastapi._compat import ModelField
from fastapi.encoders import jsonable_encoder

_installed = False


def _finite(v: Any) -> Any:
    """NaN / Infinity become null (as Pydantic's JSON mode does): JSON.parse rejects them."""
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, list):
        return [_finite(x) for x in v]
    if isinstance(v, dict):
        return {k: _finite(x) for k, x in v.items()}
    return v


def install() -> None:
    global _installed
    if _installed:
        return
    original = ModelField.serialize

    def serialize(self: ModelField, value: Any, *, mode: str = "json", **kw: Any) -> Any:
        if mode != "json":
            return original(self, value, mode=mode, **kw)
        return _finite(jsonable_encoder(original(self, value, mode="python", **kw)))

    def serialize_json(self: ModelField, value: Any, **kw: Any) -> bytes:
        return json.dumps(serialize(self, value, **kw), ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")

    ModelField.serialize = serialize  # type: ignore[method-assign]
    ModelField.serialize_json = serialize_json  # type: ignore[method-assign]
    _installed = True
