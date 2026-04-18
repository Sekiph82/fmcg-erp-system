#!/bin/bash
# Usage:  ./commit.sh "Your commit message"
#         ./commit.sh          (auto-message: "Auto-commit YYYY-MM-DD HH:MM")
#
# Stages ALL tracked + untracked files (excluding .gitignore entries),
# commits, and the post-commit hook pushes automatically.

set -e
REPO=$(git rev-parse --show-toplevel)
cd "$REPO"

MSG="${1:-Auto-commit $(date '+%Y-%m-%d %H:%M')}"

echo "Staging all changes..."
git add -A

STAGED=$(git diff --cached --name-only | wc -l)
if [ "$STAGED" -eq 0 ]; then
  echo "Nothing to commit."
  exit 0
fi

echo "Committing $STAGED file(s): $MSG"
git commit -m "$MSG"
# post-commit hook handles the push automatically
