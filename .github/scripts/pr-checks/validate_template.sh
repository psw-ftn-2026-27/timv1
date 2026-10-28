#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/../common/lib.sh"

gh api -H "Accept: application/vnd.github.raw" \
  "repos/$REPO/contents/.github/pull_request_template.md?ref=$BASE_SHA" \
  > pr_template.md 2>/dev/null || : > pr_template.md

if [ -n "$FRONTEND_DIR" ]; then
  gh api --paginate "repos/$REPO/pulls/$PR/files?per_page=100" --jq '.[]' | jq -s '.' > files.json || rm -f files.json
fi

python3 "$HERE/validate_template.py"
