#!/usr/bin/env bash
# Kenya Go-Live ERP Training Manual — PDF Export Script (Linux/Mac/Git Bash)
#
# Usage (from repo root):
#   bash docs/user-manual/pdf-export/export-kenya-go-live.sh
#
# Requirements:
#   - Node.js 18+
#   - frontend/node_modules/playwright installed
#   - frontend/node_modules/marked installed
#   - docs/user-manual/screenshots/captured/ exists with PNG files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo "=== Kenya Go-Live PDF Export ==="
echo "Repo root: $REPO_ROOT"

# 1. Verify screenshots
SCREENSHOTS_DIR="$REPO_ROOT/docs/user-manual/screenshots/captured"
if [ ! -d "$SCREENSHOTS_DIR" ]; then
    echo "ERROR: Screenshots folder missing: $SCREENSHOTS_DIR"
    echo "Regenerate: cd frontend && E2E_SKIP_WEBSERVER=1 npm run test:manual-screenshots"
    exit 1
fi
PNG_COUNT=$(find "$SCREENSHOTS_DIR" -name "*.png" | wc -l | tr -d ' ')
echo "Screenshots: $PNG_COUNT PNGs found"
if [ "$PNG_COUNT" -lt 100 ]; then
    echo "WARNING: Only $PNG_COUNT screenshots found. Expected ~140. PDF may have missing images."
fi

# 2. Verify node_modules
FE_MODULES="$REPO_ROOT/frontend/node_modules"
if [ ! -d "$FE_MODULES/playwright" ]; then
    echo "ERROR: Playwright not found at $FE_MODULES/playwright"
    echo "Fix: cd frontend && npm install"
    exit 1
fi
if [ ! -d "$FE_MODULES/marked" ]; then
    echo "ERROR: marked not found at $FE_MODULES/marked"
    echo "Fix: cd frontend && npm install --save-dev marked"
    exit 1
fi

# 3. Verify chapters
KENYA_DIR="$REPO_ROOT/docs/user-manual/kenya-go-live"
CHAPTERS=(
    "00_GO_LIVE_TRAINING_INDEX.md"
    "01_ADMIN_USER_MANUAL.md"
    "02_PRODUCTION_USER_MANUAL.md"
    "03_WAREHOUSE_INVENTORY_USER_MANUAL.md"
    "04_PROCUREMENT_USER_MANUAL.md"
    "05_QUALITY_CONTROL_USER_MANUAL.md"
    "06_SALES_LOGISTICS_USER_MANUAL.md"
    "07_HR_USER_MANUAL.md"
    "08_MANAGER_DASHBOARD_USER_MANUAL.md"
    "09_COMMON_PROBLEMS_AND_FAQ.md"
)
MISSING=()
for ch in "${CHAPTERS[@]}"; do
    [ -f "$KENYA_DIR/$ch" ] || MISSING+=("$ch")
done
if [ ${#MISSING[@]} -gt 0 ]; then
    echo "ERROR: Missing chapter files: ${MISSING[*]}"
    exit 1
fi
echo "Chapters: ${#CHAPTERS[@]} files verified"

# 4. Create output directory
mkdir -p "$REPO_ROOT/docs/user-manual/pdf-output"

# 5. Generate PDF
echo ""
echo "Running PDF generator..."
node "$SCRIPT_DIR/generate-kenya-pdf.mjs"

# 6. Report
PDF="$REPO_ROOT/docs/user-manual/pdf-output/Kenya-Go-Live-ERP-Training-Manual.pdf"
if [ -f "$PDF" ]; then
    SIZE_BYTES=$(stat -c%s "$PDF" 2>/dev/null || stat -f%z "$PDF" 2>/dev/null || echo 0)
    SIZE_MB=$(echo "scale=1; $SIZE_BYTES / 1048576" | bc 2>/dev/null || echo "?")
    echo ""
    echo "PDF generated successfully!"
    echo "Output: $PDF"
    echo "Size:   ${SIZE_MB} MB"
else
    echo "ERROR: PDF not found at expected path: $PDF"
    exit 1
fi
