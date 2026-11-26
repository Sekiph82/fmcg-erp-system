"""Startup warnings for deployment settings that weaken public-route protections (M48.S01.T023, M36 audit F10).

Per-IP limits on the public lead form, landing page, chat and similar routes key on `request.client.host`. The
server (gunicorn/uvicorn) rewrites that from X-Forwarded-For only for proxies listed in FORWARDED_ALLOW_IPS:
- unset: the Dockerfiles default to 127.0.0.1, so behind a proxy container every visitor shares the proxy's address
  and one abuser exhausts the limit for everybody;
- "*": any client can send its own X-Forwarded-For and pick a fresh address per request, bypassing the limits.
Several of these limits are also per-worker memory windows (see docs/DEPLOYMENT.md).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def proxy_warning(environment: str, forwarded_allow_ips: Optional[str]) -> Optional[str]:
    if environment != "production":
        return None
    value = (forwarded_allow_ips or "").strip()
    if not value:
        return ("FORWARDED_ALLOW_IPS is not set: behind a reverse proxy all visitors share one address, so per-IP "
                "limits on public forms, landing pages and chat apply to everyone together. Set it to the proxy address.")
    if "*" in [p.strip() for p in value.split(",")]:
        return ("FORWARDED_ALLOW_IPS is '*': any client can forge X-Forwarded-For and bypass per-IP limits on public "
                "routes. Set it to the reverse proxy address only.")
    return None


def warn_on_startup() -> None:
    from app.core.config import settings
    msg = proxy_warning(getattr(settings, "ENVIRONMENT", "development"), os.environ.get("FORWARDED_ALLOW_IPS"))
    if msg:
        logger.warning("%s Per-IP public-route limits are also kept per worker process (see docs/DEPLOYMENT.md).", msg)
