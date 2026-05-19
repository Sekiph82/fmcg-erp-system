#!/usr/bin/env bash
# FMCG ERP Full Reference Manual — PDF Export Script (Linux/Mac/Git Bash)
#
# Usage (from repo root):
#   bash docs/user-manual/pdf-export/export-full-reference.sh
#
# Requirements:
#   - Node.js 18+
#   - frontend/node_modules/playwright installed
#   - frontend/node_modules/marked installed
#   - docs/user-manual/screenshots/captured/ exists with PNG files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo "=== FMCG ERP Full Reference Manual — PDF Export ==="
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
FULL_REF_DIR="$REPO_ROOT/docs/user-manual/full-reference"
CHAPTERS=(
    "00_FULL_ERP_MANUAL_INDEX.md"
    "01_DASHBOARD_AND_NAVIGATION.md"
    "02_MASTER_DATA.md"
    "03_PROCUREMENT.md"
    "04_INVENTORY_AND_WAREHOUSE.md"
    "05_PRODUCTION.md"
    "06_QUALITY_AND_COMPLIANCE.md"
    "07_SALES_AND_DISTRIBUTION.md"
    "08_FINANCE.md"
    "09_HR_AND_PAYROLL.md"
    "10_ADMIN_AND_SECURITY.md"
    "11_AI_AND_AUTOMATION.md"
    "12_REPORTS_AND_EXPORTS.md"
    "13_STANDALONE_OPERATIONAL_PAGES.md"
    "14_OLD_ROUTE_COMPATIBILITY.md"
)
MISSING=()
for ch in "${CHAPTERS[@]}"; do
    [ -f "$FULL_REF_DIR/$ch" ] || MISSING+=("$ch")
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
node "$SCRIPT_DIR/generate-full-reference-pdf.mjs"

# 6. Report
PDF="$REPO_ROOT/docs/user-manual/pdf-output/FMCG-ERP-Full-Reference-Manual.pdf"
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
