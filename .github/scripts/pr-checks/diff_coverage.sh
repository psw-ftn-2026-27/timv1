#!/usr/bin/env bash
set -e
set -o pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/../common/lib.sh"

gh api --paginate "repos/$REPO/pulls/$PR/files?per_page=100" --jq '.[]' | jq -s '.' > files.json
python3 "$HERE/diff_coverage.py"
