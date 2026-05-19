#!/usr/bin/env bash
# FMCG ERP Supply Chain Module Manual — PDF Generator (bash)
# Run from repo root:
#   bash docs/user-manual/module-manuals/supply-chain/pdf-export/run-supply-chain-pdf.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
GENERATOR="$SCRIPT_DIR/generate-supply-chain-pdf.mjs"
FRONTEND_DIR="$REPO_ROOT/frontend"

echo ""
echo "=== Supply Chain PDF Generator ==="
echo "Repo root: $REPO_ROOT"
echo "Generator: $GENERATOR"
echo ""

# Ensure frontend dependencies are installed
if [ ! -d "$FRONTEND_DIR/node_modules/playwright" ]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND_DIR" && npm install)
fi

# Run generator
echo "Running PDF generator..."
node "$GENERATOR"

echo ""
echo "Output: docs/user-manual/pdf-output/FMCG-ERP-Supply-Chain-Manual.pdf"
