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
STRATEGY = USER_MANUAL_DIR / "MANUAL_WITH_SCREENSHOTS_STRATEGY.md"
CAPTURE_PLAN = USER_MANUAL_DIR / "SCREENSHOT_CAPTURE_PLAN.md"
CAPTURE_SCRIPT = REPO_ROOT / "frontend" / "e2e" / "manual-screenshots.spec.ts"


def test_full_manual_required_inputs_exist() -> None:
    assert MANUAL_AUDIT.exists(), "MANUAL_AUDIT.md missing"
    assert FULL_MANUAL_AUDIT.exists(), "FULL_MANUAL_GENERATION_AUDIT.md missing"
    assert SCREENSHOT_INDEX.exists(), "screenshots-index.json missing"
    assert ROUTES.exists(), "routes.json missing"


def test_screenshot_strategy_and_plan_exist() -> None:
    assert STRATEGY.exists(), "MANUAL_WITH_SCREENSHOTS_STRATEGY.md missing"
    assert CAPTURE_PLAN.exists(), "SCREENSHOT_CAPTURE_PLAN.md missing"
    assert CAPTURE_SCRIPT.exists(), "manual-screenshots.spec.ts missing"


def test_screenshot_index_is_valid_json() -> None:
    """Index can be empty (pre-capture) or populated (post-capture). Either is valid."""
    index = json.loads(SCREENSHOT_INDEX.read_text(encoding="utf-8"))
    assert isinstance(index, list), "screenshots-index.json must be a JSON array"


def test_routes_json_is_valid_and_workspace_based() -> None:
    """Routes must use real workspace paths, not old redirect paths."""
    routes = json.loads(ROUTES.read_text(encoding="utf-8"))
    assert isinstance(routes, list), "routes.json must be a JSON array"
    assert len(routes) >= 100, f"Expected >= 100 routes, got {len(routes)}"

    # All routes must have required fields
    required_fields = {"id", "title", "path", "capture"}
    for route in routes:
        missing = required_fields - set(route.keys())
        assert not missing, f"Route {route.get('id', '?')} missing fields: {missing}"

    # No old redirect-only paths (routes that are known redirects)
    KNOWN_REDIRECT_PATHS = {
        "/dashboard/van-sales",
        "/dashboard/qms",
        "/dashboard/allergen",
        "/dashboard/shelf-life",
        "/dashboard/fixed-assets",
        "/dashboard/bank-reconciliation",
        "/dashboard/recruitment",
        "/dashboard/mrp",
        "/dashboard/mps",
        "/dashboard/traceability",
    }
    capture_paths = {r["path"] for r in routes if r.get("capture", True)}
    bad = capture_paths & KNOWN_REDIRECT_PATHS
    assert not bad, f"routes.json contains old redirect-only paths with capture=true: {bad}"


def test_kenya_go_live_manuals_exist() -> None:
    go_live_dir = USER_MANUAL_DIR / "kenya-go-live"
    expected = [
        "00_GO_LIVE_TRAINING_INDEX.md",
        "01_ADMIN_USER_MANUAL.md",
        "02_PRODUCTION_USER_MANUAL.md",
        "03_WAREHOUSE_INVENTORY_USER_MANUAL.md",
        "04_PROCUREMENT_USER_MANUAL.md",
        "05_QUALITY_CONTROL_USER_MANUAL.md",
        "06_SALES_LOGISTICS_USER_MANUAL.md",
        "07_HR_USER_MANUAL.md",
        "08_MANAGER_DASHBOARD_USER_MANUAL.md",
        "09_COMMON_PROBLEMS_AND_FAQ.md",
    ]
    for fname in expected:
        path = go_live_dir / fname
        assert path.exists(), f"Kenya go-live manual missing: {fname}"
        assert path.stat().st_size > 500, f"Kenya go-live manual too small: {fname}"


def test_full_reference_manuals_exist() -> None:
    ref_dir = USER_MANUAL_DIR / "full-reference"
    expected = [
        "00_FULL_ERP_MANUAL_INDEX.md",
        "01_DASHBOARD_AND_NAVIGATION.md",
        "02_MASTER_DATA.md",
        "03_PROCUREMENT.md",
        "04_INVENTORY_AND_WAREHOUSE.md",
        "05_PRODUCTION.md",
        "06_QUALITY_AND_COMPLIANCE.md",
        "07_SALES_AND_DISTRIBUTION.md",
        "08_FINANCE.md",
        "09_HR_AND_PAYROLL.md",
        "10_ADMIN_AND_SECURITY.md",
        "11_AI_AND_AUTOMATION.md",
        "12_REPORTS_AND_EXPORTS.md",
        "13_STANDALONE_OPERATIONAL_PAGES.md",
        "14_OLD_ROUTE_COMPATIBILITY.md",
    ]
    for fname in expected:
        path = ref_dir / fname
        assert path.exists(), f"Full reference manual missing: {fname}"
        assert path.stat().st_size > 200, f"Full reference manual too small: {fname}"


def test_manual_template_exists() -> None:
    template = USER_MANUAL_DIR / "templates" / "PAGE_MANUAL_TEMPLATE.md"
    assert template.exists(), "PAGE_MANUAL_TEMPLATE.md missing"
