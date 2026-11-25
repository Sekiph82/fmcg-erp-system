"""Signed webhook fixtures (M43.S00.T004): build provider callbacks exactly as the ERP verifies them."""
import hashlib
import hmac
import json


def body_bytes(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()


def meta_signature(app_secret: str, body: bytes) -> str:
    """X-Hub-Signature-256 as Meta sends it (verified by app.core.callback_security.verify_meta_signature)."""
    return "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()


def hmac_sha256_hex(secret: str, body: bytes) -> str:
    """Generic HMAC-SHA256 hex digest used by the ERP's inbound webhook endpoints."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
