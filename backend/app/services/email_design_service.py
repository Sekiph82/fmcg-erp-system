"""Visual e-mail designer: block documents rendered to responsive HTML + plain text (M44.S01.T001).

Blocks (validated, never raw HTML): heading, text (supports **bold** and line breaks), image (https only, alt text
required), button (http/https link; contrast checked), divider, spacer, columns (two columns of simple blocks),
product (POVU product card: name, size, price text), footer (sender address; the unsubscribe link is always added
at send time by the outbox). Every text is HTML-escaped; links must be http(s) — javascript:, data: and the like
are refused. Variables: {contact_name}, {company_name}, {first_name} with "|fallback" support ({first_name|there}).
Output is table-based, inline-styled, max-width 600 px, mobile friendly, with a matching plain-text part.
"""
from __future__ import annotations

import html
import re
from typing import Any, Optional
from urllib.parse import urlsplit

BLOCK_TYPES = ("heading", "text", "image", "button", "divider", "spacer", "columns", "product", "footer")
VAR_RE = re.compile(r"\{(contact_name|company_name|first_name)(?:\|([^{}]{0,60}))?\}")
DEFAULT_THEME = {"brand_color": "#1D4ED8", "text_color": "#111827", "background": "#F3F4F6", "font": "Arial, Helvetica, sans-serif"}
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
MAX_BLOCKS = 80


class DesignError(ValueError):
    pass


def _url(u: Any, *, https_only: bool = False) -> str:
    u = str(u or "").strip()
    parts = urlsplit(u)
    ok = parts.scheme in (("https",) if https_only else ("http", "https")) and bool(parts.netloc)
    if not ok or any(c in u for c in '"<>\\ \n\r'):
        raise DesignError(f"Link must be a full {'https' if https_only else 'http(s)'} address: {u[:80]!r}")
    return u


def _luminance(hex_color: str) -> float:
    def ch(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def validate(doc: dict) -> tuple[dict, list[str]]:
    """Clean a design document; returns (document, accessibility warnings). Raises DesignError when unsafe."""
    theme = {**DEFAULT_THEME, **{k: v for k, v in (doc.get("theme") or {}).items() if k in DEFAULT_THEME}}
    for k in ("brand_color", "text_color", "background"):
        if not HEX.match(str(theme[k])):
            raise DesignError(f"{k} must be a #RRGGBB colour")
    theme["font"] = re.sub(r"[^A-Za-z0-9 ,\-]", "", str(theme["font"]))[:80] or DEFAULT_THEME["font"]
    warnings: list[str] = []

    def clean(block: dict, depth: int = 0) -> dict:
        t = block.get("type")
        if t not in BLOCK_TYPES or (depth and t in ("columns", "footer")):
            raise DesignError(f"Unknown or misplaced block: {t!r}")
        b: dict = {"type": t}
        aud = block.get("audience") or {}
        if aud:   # M44.S01.T012 smart content: show only to these lifecycle stages / customer channels
            b["audience"] = {k: [str(x)[:20] for x in (aud.get(k) or [])][:10] for k in ("lifecycle", "channel", "language") if aud.get(k)}
        if t in ("heading", "text", "footer"):
            b["text"] = str(block.get("text") or "")[:5000]
            if t == "heading":
                b["level"] = 1 if block.get("level") == 1 else 2
        elif t == "image":
            b["url"] = _url(block.get("url"), https_only=True)
            b["alt"] = str(block.get("alt") or "").strip()[:200]
            if not b["alt"]:
                warnings.append("An image has no alternative text; screen readers and blocked-image views show nothing.")
            if block.get("href"):
                b["href"] = _url(block["href"])
        elif t == "button":
            b["label"] = str(block.get("label") or "").strip()[:80] or "Open"
            b["href"] = _url(block.get("href"))
        elif t == "spacer":
            b["height"] = max(4, min(80, int(block.get("height") or 16)))
        elif t == "product":
            b.update({k: str(block.get(k) or "")[:120] for k in ("name", "size", "price")})
            if block.get("image_url"):
                b["image_url"] = _url(block["image_url"], https_only=True)
        elif t == "columns":
            b["left"] = [clean(x, depth + 1) for x in (block.get("left") or [])[:10]]
            b["right"] = [clean(x, depth + 1) for x in (block.get("right") or [])[:10]]
        return b

    blocks = doc.get("blocks") or []
    if not isinstance(blocks, list) or len(blocks) > MAX_BLOCKS:
        raise DesignError(f"A design holds 1–{MAX_BLOCKS} blocks")
    out = [clean(b) for b in blocks]
    if contrast("#FFFFFF", theme["brand_color"]) < 4.5:
        warnings.append("Button text on the brand colour is below WCAG AA contrast (4.5:1).")
    if contrast(theme["text_color"], "#FFFFFF") < 4.5:
        warnings.append("Body text colour is below WCAG AA contrast on white.")
    return {"theme": theme, "blocks": out}, warnings


def fill(text: str, values: dict) -> str:
    def sub(m: re.Match) -> str:
        v = values.get(m.group(1))
        return str(v) if v not in (None, "") else (m.group(2) or "")
    return VAR_RE.sub(sub, text)


def _inline(text: str, values: dict) -> str:
    esc = html.escape(fill(text, values))
    esc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc)
    return esc.replace("\n", "<br>")


def render_html(doc: dict, values: Optional[dict] = None, preheader: str = "") -> str:
    values = values or {}
    th = doc["theme"]

    def one(b: dict) -> str:
        t = b["type"]
        if t == "heading":
            size = 26 if b["level"] == 1 else 20
            return (f'<h{b["level"]} style="margin:0 0 12px;font-size:{size}px;line-height:1.3;color:{th["text_color"]}">'
                    f'{_inline(b["text"], values)}</h{b["level"]}>')
        if t == "text":
            return f'<p style="margin:0 0 14px;font-size:16px;line-height:1.5;color:{th["text_color"]}">{_inline(b["text"], values)}</p>'
        if t == "image":
            img = (f'<img src="{html.escape(b["url"])}" alt="{html.escape(b["alt"])}" width="100%" '
                   f'style="display:block;max-width:100%;height:auto;border:0">')
            return (f'<a href="{html.escape(b["href"])}">{img}</a>' if b.get("href") else img) + '<div style="height:12px"></div>'
        if t == "button":
            return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 16px"><tr>'
                    f'<td style="background:{th["brand_color"]};border-radius:6px">'
                    f'<a href="{html.escape(b["href"])}" style="display:inline-block;padding:12px 22px;color:#FFFFFF;'
                    f'text-decoration:none;font-weight:bold;font-size:16px">{html.escape(b["label"])}</a></td></tr></table>')
        if t == "divider":
            return '<hr style="border:0;border-top:1px solid #E5E7EB;margin:16px 0">'
        if t == "spacer":
            return f'<div style="height:{b["height"]}px;line-height:{b["height"]}px">&nbsp;</div>'
        if t == "product":
            img = (f'<img src="{html.escape(b["image_url"])}" alt="{html.escape(b["name"])}" width="120" '
                   f'style="display:block;max-width:120px;height:auto">') if b.get("image_url") else ""
            return (f'<table role="presentation" width="100%" style="margin:0 0 14px;border:1px solid #E5E7EB;border-radius:6px">'
                    f'<tr><td style="padding:10px;width:130px">{img}</td><td style="padding:10px;color:{th["text_color"]}">'
                    f'<strong>{html.escape(b["name"])}</strong><br>{html.escape(b["size"])}<br>{html.escape(b["price"])}</td></tr></table>')
        if t == "columns":
            col = lambda items: "".join(one(x) for x in items)  # noqa: E731
            return ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
                    f'<td class="col" valign="top" style="width:50%;padding-right:8px">{col(b["left"])}</td>'
                    f'<td class="col" valign="top" style="width:50%;padding-left:8px">{col(b["right"])}</td></tr></table>')
        if t == "footer":
            return f'<p style="margin:24px 0 0;font-size:12px;line-height:1.5;color:#6B7280">{_inline(b["text"], values)}</p>'
        return ""

    body = "".join(one(b) for b in doc["blocks"] if shows(b, values))
    pre = f'<div style="display:none;max-height:0;overflow:hidden">{html.escape(preheader)}</div>' if preheader else ""
    return ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<style>@media (max-width:620px){.wrap{width:100%!important}.col{display:block!important;width:100%!important;'
            'padding:0!important}}</style></head>'
            f'<body style="margin:0;padding:0;background:{th["background"]};font-family:{th["font"]}">{pre}'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{th["background"]}"><tr><td align="center">'
            f'<table role="presentation" class="wrap" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:600px;'
            f'background:#FFFFFF"><tr><td style="padding:24px">{body}</td></tr></table></td></tr></table></body></html>')


def render_text(doc: dict, values: Optional[dict] = None) -> str:
    values = values or {}
    lines: list[str] = []

    def one(b: dict) -> None:
        t = b["type"]
        if t in ("heading", "text", "footer"):
            lines.append(fill(b["text"], values).replace("**", ""))
        elif t == "button":
            lines.append(f'{b["label"]}: {b["href"]}')
        elif t == "image" and b.get("href"):
            lines.append(f'{b["alt"] or "Image"}: {b["href"]}')
        elif t == "product":
            lines.append(" · ".join(x for x in (b["name"], b["size"], b["price"]) if x))
        elif t == "divider":
            lines.append("—" * 20)
        elif t == "columns":
            for x in b["left"] + b["right"]:
                one(x)
    for b in doc["blocks"]:
        if shows(b, values):
            one(b)
    return "\n\n".join(x for x in lines if x)


def shows(block: dict, values: dict) -> bool:
    """Smart content: a block with an audience shows only when the recipient matches (unknown → hidden)."""
    aud = block.get("audience") or {}
    for key in ("lifecycle", "channel", "language"):
        if aud.get(key) and str(values.get(key) or "").upper() not in {x.upper() for x in aud[key]}:
            return False
    return True
