"""Readiness checks for final user manual generation."""
from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
USER_MANUAL_DIR = REPO_ROOT / "docs" / "user-manual"
MANUAL_AUDIT = USER_MANUAL_DIR / "MANUAL_AUDIT.md"
FULL_MANUAL_AUDIT = USER_MANUAL_DIR / "FULL_MANUAL_GENERATION_AUDIT.md"
SCREENSHOT_INDEX = USER_MANUAL_DIR / "screenshots" / "screenshots-index.json"
ROUTES = USER_MANUAL_DIR / "screenshots" / "routes.json"


def test_full_manual_required_inputs_exist() -> None:
    assert MANUAL_AUDIT.exists()
    assert FULL_MANUAL_AUDIT.exists()
    assert SCREENSHOT_INDEX.exists()
    assert ROUTES.exists()


def test_full_manual_audit_records_screenshot_blocker() -> None:
    audit = FULL_MANUAL_AUDIT.read_text(encoding="utf-8")

    assert "Screenshot capture index" in audit
    assert "Existing but empty" in audit
    assert "No screenshot captured for this module yet." in audit
    assert "NEEDS_USER_REVIEW" in audit


def test_screenshot_index_is_valid_json_even_when_empty() -> None:
    index = json.loads(SCREENSHOT_INDEX.read_text(encoding="utf-8"))
    routes = json.loads(ROUTES.read_text(encoding="utf-8"))

    assert index == []
    assert isinstance(routes, list)
    assert len(routes) >= 100
