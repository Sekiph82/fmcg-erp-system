"""M51.S01.T001 typed layout validation and render safety (no database).

Every property of the layout model is typed; unknown properties/values are refused and the css handed to the browser
is generated from fixed tables, so no script or style text can travel through any property.
"""
import json
import re

import pytest

from app.services import cms_layout_service as L
from app.services import cms_service as cms

SAFE_CSS = re.compile(r"^[#A-Za-z0-9 ,.\-()/%]*$")
PAYLOADS = ["</style><script>alert(1)</script>", "red;background:url(javascript:alert(1))", "expression(alert(1))", "var(--x)", "#GGGGGG",
            "'; DROP TABLE x;--", "javascript:alert(1)", "{{7*7}}", "\"onmouseover=\"alert(1)", "url(//evil.example.com/x.png)", "", "null",
            99999, -1, 1.5, True, [], {}]


def _doc(**block):
    return {"blocks": [{"type": "section", "children": [{"type": "text", "text": "x", **block}]}]}


def test_nested_layout_roundtrip_and_ids():
    doc, _ = cms.validate_doc({"blocks": [{"type": "section", "as": "aside", "label": "Promo", "style": {"desktop": {"padding_top": "lg", "background": "surface"}},
        "children": [{"type": "row", "style": {"desktop": {"gap": "md", "valign": "center"}}, "children": [
            {"type": "column", "style": {"desktop": {"span": 6}, "mobile": {"span": "12"}}, "children": [{"type": "heading", "text": "POVU AllClean 1 L", "level": 1}]},
            {"type": "column", "style": {"desktop": {"span": 6}}, "hide": ["mobile", "tablet"], "children": [
                {"type": "grid", "style": {"desktop": {"cols": 2}}, "children": [{"type": "product", "name": "POVU AllClean 1 L"}]}]}]}]}]})
    sec = doc["blocks"][0]
    assert sec["as"] == "aside" and sec["label"] == "Promo"
    col2 = sec["children"][0]["children"][1]
    assert col2["hide"] == ["tablet", "mobile"] and sec["children"][0]["children"][0]["style"]["mobile"]["span"] == 12
    assert all(b["id"] for b in cms.flat(doc["blocks"]))


@pytest.mark.parametrize("bad", [
    {"blocks": [{"type": "row", "children": [{"type": "text", "text": "x"}]}]},                 # rows hold columns only
    {"blocks": [{"type": "column", "children": []}]},                                            # column outside a row
    {"blocks": [{"type": "section", "children": [{"type": "columns", "left": [{"type": "columns"}]}]}]},
    {"blocks": [{"type": "section", "style": {"desktop": {"span": 3}}}]},                      # span is column-only
    {"blocks": [{"type": "text", "text": "x", "style": {"desktop": {"cols": 3}}}]},
    {"blocks": [{"type": "text", "text": "x", "style": {"watch": {"color": "brand"}}}]},        # unknown breakpoint
    {"blocks": [{"type": "text", "text": "x", "style": {"desktop": {"position": "fixed"}}}]},   # unknown property
    {"blocks": [{"type": "text", "text": "x", "style": {"desktop": {"color": "#FF0000"}}}]},    # colours are tokens, not hex
    {"blocks": [{"type": "text", "text": "x", "hide": ["watch"]}]},
    {"blocks": [{"type": "component", "key": "Bad Key!"}]},
    {"blocks": [{"type": "component", "key": "promo", "overrides": {"a": {"type": "html"}}}]},  # only listed fields may be overridden
    {"blocks": [{"type": "component", "key": "promo", "overrides": {"a": {"href": "javascript:alert(1)"}}}]},
    {"blocks": [{"type": "text", "text": "x"}], "layout": {"header": "Not A Key"}},
    {"blocks": [{"type": "text", "text": "x"}], "layout": {"sidebar": "none"}},
])
def test_invalid_layout_is_rejected(bad):
    with pytest.raises(cms.CmsError):
        cms.validate_doc(bad)


def test_depth_and_node_limits():
    deep = {"type": "text", "text": "x"}
    for _ in range(L.MAX_DEPTH + 2):
        deep = {"type": "section", "children": [deep]}
    with pytest.raises(cms.CmsError):
        cms.validate_doc({"blocks": [deep]})
    wide = {"blocks": [{"type": "section", "children": [{"type": "section", "children": [{"type": "text", "text": "x"}] * 40}] * 12}] * 2}
    with pytest.raises(cms.CmsError):
        cms.validate_doc(wide)


@pytest.mark.parametrize("prop", sorted(L.STYLE_SPEC))
def test_every_style_property_rejects_payloads_and_accepts_only_allow_list(prop):
    kind = next(iter(L.TYPE_ONLY.get(prop, ("text",))))
    for p in PAYLOADS:
        if not isinstance(p, bool) and isinstance(p, (str, int)) and p in L.STYLE_SPEC[prop]:
            continue
        with pytest.raises(cms.CmsError):
            L.clean_style({"desktop": {prop: p}}, kind)
    for v in L.STYLE_SPEC[prop]:
        assert L.clean_style({"tablet": {prop: v}}, kind) == {"tablet": {prop: v}}


def test_generated_css_contains_only_safe_values_for_every_property():
    tokens, _ = L.validate_tokens({"colors": {"brand": "#0F766E"}, "heading_font": "serif", "radius": 12})
    for btype in ("text", "section", "row", "column", "grid"):
        for prop, allowed in L.STYLE_SPEC.items():
            if prop in L.TYPE_ONLY and btype not in L.TYPE_ONLY[prop]:
                continue
            for v in allowed:
                css = L.css_for({"desktop": {prop: v}}, btype, tokens)
                assert set(css) == set(L.BREAKPOINTS)
                for props in css.values():
                    for k, val in props.items():
                        assert re.fullmatch(r"[a-zA-Z]+", k) and SAFE_CSS.match(str(val)), (btype, prop, v, k, val)


def test_css_cascade_and_mobile_defaults():
    tokens = L.DEFAULT_TOKENS
    css = L.css_for({"desktop": {"span": 6, "padding_top": "lg"}, "tablet": {"padding_top": "md"}}, "column", tokens)
    assert css["desktop"]["gridColumn"] == "span 6 / span 6" and css["desktop"]["paddingTop"] == 24
    assert css["tablet"]["gridColumn"] == "span 6 / span 6" and css["tablet"]["paddingTop"] == 16
    assert css["mobile"]["gridColumn"] == "span 12 / span 12" and css["mobile"]["paddingTop"] == 16      # stacks, keeps tablet spacing
    g = L.css_for({"desktop": {"cols": 3}}, "grid", tokens)
    assert g["desktop"]["gridTemplateColumns"] == "repeat(3, minmax(0, 1fr))" and g["mobile"]["gridTemplateColumns"] == "repeat(1, minmax(0, 1fr))"


def test_text_payloads_stay_data_and_links_are_checked_in_every_container():
    doc, _ = cms.validate_doc(_doc(text="<script>alert(1)</script><style>*{display:none}</style> **b**"))
    assert doc["blocks"][0]["children"][0]["text"].startswith("<script>")      # kept as text; the browser renders it escaped
    for bad in ({"type": "button", "label": "x", "href": "javascript:alert(1)"}, {"type": "image", "url": "http://x.example.com/a.png", "alt": "a"},
                {"type": "text", "text": "[x](javascript:alert(1))"}):
        with pytest.raises(cms.CmsError):
            cms.validate_doc({"blocks": [{"type": "section", "children": [{"type": "row", "children": [{"type": "column", "children": [bad]}]}]}]})


def test_tokens_validation_and_email_reuse():
    t, warn = L.validate_tokens({"colors": {"brand": "#1d4ed8", "text": "#777777", "background": "#888888"}})
    assert t["colors"]["brand"] == "#1D4ED8" and any("contrast" in w for w in warn)
    for bad in ({"colors": {"brand": "red"}}, {"colors": {"sparkle": "#FFFFFF"}}, {"body_font": "Comic; x"}, {"radius": 99}, {"unknown": 1},
                {"colors": {"brand": "#FFFFFF;}</style>"}}):
        with pytest.raises(cms.CmsError):
            L.validate_tokens(bad)
    e = L.email_theme(t)
    assert set(e) == {"brand_color", "text_color", "background", "font"} and e["brand_color"] == "#1D4ED8"
    from app.services.email_design_service import validate
    validate({"theme": e, "blocks": []})                 # the e-mail designer accepts the derived theme unchanged


def test_overrides_apply_only_to_listed_fields_and_known_ids():
    base = [{"type": "section", "id": "s1", "children": [{"type": "text", "id": "t1", "text": "Order POVU AllClean 1 L"}, {"type": "text", "id": "t2", "text": "keep"}]}]
    ov = L.clean_overrides({"t1": {"text": "Order POVU Hand Wash Powder 1 kg Pouch", "style": {"mobile": {"align": "center"}}, "hide": ["tablet"]}, "zz": {"text": "x"}})
    out = L.apply_overrides(base, ov)
    assert out[0]["children"][0]["text"].endswith("1 kg Pouch") and out[0]["children"][0]["style"] == {"mobile": {"align": "center"}}
    assert out[0]["children"][1]["text"] == "keep" and base[0]["children"][0]["text"].endswith("1 L")      # source untouched


def test_every_preset_validates():
    for key, p in L.PRESETS.items():
        content, _ = L.validate_component(p["kind"], p["draft"])
        assert json.dumps(content)
    with pytest.raises(cms.CmsError):
        L.validate_component("SECTION", {"blocks": [{"type": "component", "key": "promo-banner"}]})        # no nested references in the library
