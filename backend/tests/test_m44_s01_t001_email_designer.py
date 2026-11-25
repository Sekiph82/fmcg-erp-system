"""M44.S01.T001 visual e-mail designer (unit; runs at the M44 gate).

Unsafe links refused (javascript:, data:, http images), all text escaped (no HTML/XSS), alt-text and contrast
warnings, variables with fallback, plain-text part, designed mail gets the unsubscribe link and tracked links
(unsubscribe untouched), INVOICE mail never gets an unsubscribe line.
"""
import uuid

import pytest

from app.models.crm import CRMOutboundMessage
from app.services import crm_engagement_service as eng
from app.services import email_design_service as eds


def _doc(**over):
    d = {"theme": {"brand_color": "#1D4ED8"}, "blocks": [
        {"type": "heading", "text": "Hi {first_name|there}", "level": 1},
        {"type": "text", "text": "<script>alert(1)</script> **POVU** offer"},
        {"type": "button", "label": "Order", "href": "https://povu-demo.test/order?a=1&b=2"},
        {"type": "footer", "text": "POVU synthetic"}]}
    d.update(over)
    return d


def test_escape_variables_and_text_part():
    doc, warn = eds.validate(_doc())
    h = eds.render_html(doc, {"first_name": ""})
    assert "<script>" not in h and "&lt;script&gt;" in h and "<strong>POVU</strong>" in h
    assert "Hi there" in h
    t = eds.render_text(doc, {"first_name": "Asha"})
    assert "Hi Asha" in t and "Order: https://povu-demo.test/order?a=1&b=2" in t and "**" not in t


@pytest.mark.parametrize("block", [
    {"type": "button", "label": "x", "href": "javascript:alert(1)"},
    {"type": "image", "url": "http://povu-demo.test/a.png", "alt": "a"},
    {"type": "image", "url": "data:image/png;base64,AAAA", "alt": "a"},
    {"type": "button", "label": "x", "href": 'https://a.test/" onmouseover="x'},
    {"type": "script"},
])
def test_unsafe_blocks_refused(block):
    with pytest.raises(eds.DesignError):
        eds.validate({"blocks": [block]})


def test_accessibility_warnings():
    _, warn = eds.validate({"theme": {"brand_color": "#FFFF00"}, "blocks": [{"type": "image", "url": "https://a.test/x.png", "alt": ""}]})
    assert any("alternative text" in w for w in warn) and any("contrast" in w for w in warn)


def test_designed_mail_unsubscribe_and_tracking():
    doc, _ = eds.validate(_doc())
    msg = CRMOutboundMessage(id=uuid.uuid4(), to_email="buyer@povu-demo.test", purpose="CAMPAIGN")
    html = eng.with_unsubscribe(msg, eds.render_html(doc))
    assert "/unsubscribe?t=" in html
    tracked, links = eng.track_html(msg, html)
    assert links == ["https://povu-demo.test/order?a=1&b=2"]
    assert "/public/t/c/" in tracked and "/public/t/o/" in tracked and "/unsubscribe?t=" in tracked
    inv = CRMOutboundMessage(id=uuid.uuid4(), to_email="buyer@povu-demo.test", purpose="INVOICE")
    assert "/unsubscribe" not in eng.with_unsubscribe(inv, "<html><body>x</body></html>")
