from __future__ import annotations


def clamp_limit(limit: int | None, default: int = 100, maximum: int = 1000) -> int:
    if limit is None:
        return default
    return max(1, min(limit, maximum))


def normalize_offset(offset: int | None) -> int:
    if offset is None:
        return 0
    return max(0, offset)
