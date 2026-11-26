"""Local Slack simulator (M47.S01.T010): incoming webhooks (POST /services/T/B/X → "ok") and request signing like Slack
does for interactivity callbacks (v0 HMAC-SHA256 over "v0:{timestamp}:{body}"). Synthetic, local only."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse


def create_slack_app() -> FastAPI:
    app = FastAPI(title="POVU Slack simulator (synthetic, local only)")
    app.state.posts = []

    @app.post("/services/{team}/{bot}/{key}")
    async def webhook(team: str, bot: str, key: str, request: Request):
        app.state.posts.append({"path": f"/services/{team}/{bot}/{key}", "body": await request.json()})
        return PlainTextResponse("ok")

    return app


def signed_interaction(secret: str, slack_user: str, value: str, ts: int | None = None) -> tuple[bytes, dict]:
    """Body + headers of a block_actions callback as Slack would send it."""
    ts = int(time.time()) if ts is None else ts
    payload = {"type": "block_actions", "user": {"id": slack_user, "team_id": "TPOVU"},
               "actions": [{"action_id": value.split(":")[0], "value": value}], "response_url": "https://hooks.slack.com/actions/x"}
    body = urlencode({"payload": json.dumps(payload)}).encode()
    sig = "v0=" + hmac.new(secret.encode(), f"v0:{ts}:".encode() + body, hashlib.sha256).hexdigest()
    return body, {"X-Slack-Request-Timestamp": str(ts), "X-Slack-Signature": sig,
                  "Content-Type": "application/x-www-form-urlencoded"}
