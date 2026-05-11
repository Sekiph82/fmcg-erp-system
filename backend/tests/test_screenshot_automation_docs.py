"""Regression checks for the user-manual screenshot automation contract."""
from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_PACKAGE = REPO_ROOT / "frontend" / "package.json"
CAPTURE_SCRIPT = REPO_ROOT / "frontend" / "scripts" / "capture-user-manual-screenshots.mjs"
SCREENSHOT_ROOT = REPO_ROOT / "docs" / "user-manual" / "screenshots"
ROUTES_PATH = SCREENSHOT_ROOT / "routes.json"
INDEX_PATH = SCREENSHOT_ROOT / "screenshots-index.json"
README_PATH = SCREENSHOT_ROOT / "README.md"


def test_screenshot_package_script_and_dependency_exist() -> None:
    package = json.loads(FRONTEND_PACKAGE.read_text(encoding="utf-8"))

    assert package["scripts"]["manual:screenshots"] == "node scripts/capture-user-manual-screenshots.mjs"
    assert "playwright" in package["devDependencies"]


def test_screenshot_capture_script_uses_env_credentials_and_is_read_only() -> None:
    script = CAPTURE_SCRIPT.read_text(encoding="utf-8")

    for env_name in ["MANUAL_TEST_BASE_URL", "MANUAL_TEST_USERNAME", "MANUAL_TEST_PASSWORD"]:
        assert env_name in script

    assert "page.click('button[type=\"submit\"]')" in script
    assert "page.screenshot" in script
    assert "screenshots-index.json" in script

    forbidden_mutations = [
        "approve(",
        "reject(",
        "delete(",
        "submitForm(",
        "createRecord(",
        "sendPayment(",
        "runRecall(",
    ]
    for forbidden in forbidden_mutations:
        assert forbidden not in script


def test_screenshot_routes_manifest_shape() -> None:
    routes = json.loads(ROUTES_PATH.read_text(encoding="utf-8"))

    assert isinstance(routes, list)
    assert len(routes) >= 100
    assert any(route["path"] == "/dashboard" for route in routes)

    required_keys = {"id", "title", "module", "path", "priority", "capture"}
    for route in routes[:25]:
        assert required_keys.issubset(route)
        assert route["path"].startswith("/dashboard")


def test_screenshot_index_and_readme_exist() -> None:
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    readme = README_PATH.read_text(encoding="utf-8")

    assert index == []
    assert "MANUAL_TEST_USERNAME" in readme
    assert "npm run manual:screenshots" in readme
    assert "Read-Only Safety Rules" in readme
