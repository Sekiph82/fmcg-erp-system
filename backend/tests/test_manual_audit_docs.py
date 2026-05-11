"""Documentation audit regression checks.

These tests make the generated manual audit resumable-workflow friendly:
future runs can quickly detect if the audit file is missing required sections
or was accidentally replaced with a shallow placeholder.
"""
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = REPO_ROOT / "docs" / "user-manual" / "MANUAL_AUDIT.md"


REQUIRED_SECTIONS = [
    "# Manual Audit",
    "## Scope And Method",
    "## Executive Findings",
    "## Frontend Inventory",
    "## Sidebar / Navigation Inventory",
    "## Backend Inventory",
    "## Module Completeness Matrix",
    "## Button / Action Inventory",
    "## Workflow / Status Inventory",
    "## Role / Permission Inventory",
    "## Mock / Stub / Dev-Only Inventory",
    "## Key Gaps For Manual Preparation",
    "## Audit Limitations",
]


def _read_audit() -> str:
    assert AUDIT_PATH.exists(), f"{AUDIT_PATH} does not exist"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_manual_audit_contains_required_sections() -> None:
    audit = _read_audit()

    for section in REQUIRED_SECTIONS:
        assert section in audit


def test_manual_audit_contains_real_inventory_depth() -> None:
    audit = _read_audit()

    assert "Frontend pages scanned:" in audit
    assert "Backend endpoints discovered:" in audit
    assert "Mock/stub/dev-only markers found:" in audit
    assert audit.count("| frontend/src/app/") >= 100
    assert audit.count("| backend/app/api/v1/endpoints/") >= 100
    assert audit.count("Permission enforcement needs review") >= 100


def test_manual_audit_keeps_uncertainty_language() -> None:
    audit = _read_audit()

    assert "Not clearly discoverable" in audit
    assert "Frontend placeholder or partial implementation." in audit
    assert "Backend/API available, frontend screen not clearly found." in audit
