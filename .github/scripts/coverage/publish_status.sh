#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/../common/lib.sh"

SUMMARY="coverage-summary/Summary.json"
if [ ! -f "$SUMMARY" ]; then
  echo "Nema coverage izvestaja (build verovatno nije prosao) — postavljam status 'error'."
  set_commit_status "$HEAD_SHA" coverage error "coverage nije izmeren (build/test)"
  exit 0
fi

LINE_PCT=$(jq -r '.summary.linecoverage // 0' "$SUMMARY")
BRANCH_PCT=$(jq -r '.summary.branchcoverage // 0' "$SUMMARY")
COVERED=$(jq -r '.summary.coveredlines // 0' "$SUMMARY")
VALID=$(jq -r '.summary.coverablelines // 0' "$SUMMARY")

LINE=$(awk "BEGIN{printf \"%.4f\", $LINE_PCT/100}")
BRANCH=$(awk "BEGIN{printf \"%.4f\", $BRANCH_PCT/100}")

DESC="line=$LINE branch=$BRANCH covered=$COVERED valid=$VALID"
echo "Coverage: $DESC"
set_commit_status "$HEAD_SHA" coverage success "$DESC"
