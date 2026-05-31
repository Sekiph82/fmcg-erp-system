"""
Tests for WhatsApp live send path.

Verifies:
- _meta_send_text calls Meta Cloud API with correct payload and returns msg_id on success
- _meta_send_text returns (None, error_msg) on Meta API error
- _meta_send_text returns (None, error_msg) on network error
- _meta_send_template includes template components when variables provided
- _meta_send_template sends no components when variables empty
- phone number has '+' stripped before sending to Meta
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.endpoints.whatsapp import _meta_send_text, _meta_send_template


@pytest.mark.asyncio
async def test_meta_send_text_success():
    """On 2xx response, returns (msg_id, None)."""
    mock_resp = MagicMock()
    mock_resp.is_success = True
    mock_resp.json.return_value = {
        "messaging_product": "whatsapp",
        "messages": [{"id": "wamid.TEST_MSG_ID_001"}],
    }

    with patch(
        "app.api.v1.endpoints.whatsapp.httpx.AsyncClient",
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=AsyncMock(post=AsyncMock(return_value=mock_resp))),
                               __aexit__=AsyncMock(return_value=False)),
    ):
        msg_id, error = await _meta_send_text(
            phone_number_id="12345678901",
            api_token="test_token",
            to="+254700000001",
            body="Hello from ERP",
        )

    assert msg_id == "wamid.TEST_MSG_ID_001"
    assert error is None


@pytest.mark.asyncio
async def test_meta_send_text_strips_plus_from_phone():
    """Meta API requires phone without leading '+'. Verify it is stripped."""
    captured_payload: dict = {}

    async def fake_post(url, *, json, headers):
        captured_payload.update(json)
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.json.return_value = {"messages": [{"id": "wamid.X"}]}
        return mock_resp

    with patch(
        "app.api.v1.endpoints.whatsapp.httpx.AsyncClient",
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=AsyncMock(post=fake_post)),
            __aexit__=AsyncMock(return_value=False),
        ),
    ):
        await _meta_send_text("pid", "tok", "+254700000001", "hi")

    assert captured_payload["to"] == "254700000001"


@pytest.mark.asyncio
async def test_meta_send_text_meta_error():
    """On non-2xx Meta response, returns (None, error_message)."""
    mock_resp = MagicMock()
    mock_resp.is_success = False
    mock_resp.text = "Unauthorized"
    mock_resp.json.return_value = {"error": {"message": "Invalid OAuth access token"}}

    with patch(
        "app.api.v1.endpoints.whatsapp.httpx.AsyncClient",
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=AsyncMock(post=AsyncMock(return_value=mock_resp))),
            __aexit__=AsyncMock(return_value=False),
        ),
    ):
        msg_id, error = await _meta_send_text("pid", "bad_token", "+254700000001", "hi")

    assert msg_id is None
    assert error == "Invalid OAuth access token"


@pytest.mark.asyncio
async def test_meta_send_text_network_error():
    """On httpx.RequestError, returns (None, 'Network error: ...')."""
    import httpx

    with patch(
        "app.api.v1.endpoints.whatsapp.httpx.AsyncClient",
        return_value=AsyncMock(
            __aenter__=AsyncMock(side_effect=httpx.ConnectError("Connection refused")),
            __aexit__=AsyncMock(return_value=False),
        ),
    ):
        msg_id, error = await _meta_send_text("pid", "tok", "+254711000001", "hi")

    assert msg_id is None
    assert error is not None
    assert "Network error" in error


@pytest.mark.asyncio
async def test_meta_send_template_with_variables():
    """Template with variables sends body components."""
    captured_payload: dict = {}

    async def fake_post(url, *, json, headers):
        captured_payload.update(json)
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.json.return_value = {"messages": [{"id": "wamid.TMPL_001"}]}
        return mock_resp

    with patch(
        "app.api.v1.endpoints.whatsapp.httpx.AsyncClient",
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=AsyncMock(post=fake_post)),
            __aexit__=AsyncMock(return_value=False),
        ),
    ):
        msg_id, error = await _meta_send_template(
            phone_number_id="pid", api_token="tok",
            to="+254700000001", template_name="order_confirmation",
            language="en", variables=["Alice", "SO-001"],
        )

    assert msg_id == "wamid.TMPL_001"
    assert error is None
    tmpl = captured_payload["template"]
    assert tmpl["name"] == "order_confirmation"
    assert tmpl["language"]["code"] == "en"
    assert tmpl["components"][0]["type"] == "body"
    params = tmpl["components"][0]["parameters"]
    assert params[0]["text"] == "Alice"
    assert params[1]["text"] == "SO-001"


@pytest.mark.asyncio
async def test_meta_send_template_no_variables_no_components():
    """Template without variables sends no components key."""
    captured_payload: dict = {}

    async def fake_post(url, *, json, headers):
        captured_payload.update(json)
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.json.return_value = {"messages": [{"id": "wamid.TMPL_002"}]}
        return mock_resp

    with patch(
        "app.api.v1.endpoints.whatsapp.httpx.AsyncClient",
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=AsyncMock(post=fake_post)),
            __aexit__=AsyncMock(return_value=False),
        ),
    ):
        await _meta_send_template("pid", "tok", "+254700000001", "welcome", "en", [])

    assert "components" not in captured_payload["template"]
