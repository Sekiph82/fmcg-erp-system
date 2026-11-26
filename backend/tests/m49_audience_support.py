"""Shared helpers for the M49.S01.T006 / T011 tests: mount the new routers (until the module registry lists them)."""
import importlib
import os

import pytest

M49 = pytest.mark.skipif(os.environ.get("M49_DB") != "1", reason="requires the disposable M49 PostgreSQL (M49_DB=1)")


def mount() -> None:
    from app.main import app
    paths = {getattr(r, "path", "") for r in app.routes}
    for mod, prefix in (("audience_sync", "/api/v1/audience-sync"), ("ads_lifecycle", "/api/v1/ads-lifecycle")):
        if not any(p.startswith(prefix) for p in paths):
            app.include_router(importlib.import_module(f"app.api.v1.endpoints.{mod}").router, prefix=prefix)
