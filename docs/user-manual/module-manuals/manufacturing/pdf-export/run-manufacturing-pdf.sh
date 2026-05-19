#!/usr/bin/env bash
# Manufacturing Module Manual — PDF Generator (Unix/macOS)
# Run from repo root:  bash docs/user-manual/module-manuals/manufacturing/pdf-export/run-manufacturing-pdf.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
FE_DIR="$REPO_ROOT/frontend"
GENERATOR="$SCRIPT_DIR/generate-manufacturing-pdf.mjs"
PDF_PATH="$REPO_ROOT/docs/user-manual/pdf-output/FMCG-ERP-Manufacturing-Manual.pdf"

echo ""
echo "=== Manufacturing Manual PDF — Unix Runner ==="
echo "Repo root: $REPO_ROOT"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found. Install from https://nodejs.org/"
    exit 1
fi
echo "Node: $(node --version)"

# Check frontend node_modules
if [ ! -d "$FE_DIR/node_modules/playwright" ]; then
    echo "Installing frontend dependencies..."
    cd "$FE_DIR" && npm install && cd "$REPO_ROOT"
fi

# Run generator
echo ""
echo "Running PDF generator..."
node "$GENERATOR"

if [ -f "$PDF_PATH" ]; then
    SIZE_MB=$(du -m "$PDF_PATH" | cut -f1)
    echo ""
    echo "✓ Output: $PDF_PATH (${SIZE_MB} MB)"
else
    echo "ERROR: PDF not found at: $PDF_PATH"
    exit 1
fi
