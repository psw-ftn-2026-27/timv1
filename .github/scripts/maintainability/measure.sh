#!/usr/bin/env bash
set -e
set -o pipefail

REPORT="$PWD/maintainability-report.json"
if [ ! -f .github/analyzers/measure.sh ]; then
  echo "Nedostaje .github/analyzers/measure.sh"; exit 1
fi
OUT=$(bash .github/analyzers/measure.sh "$PWD" "$REPORT" | tail -n1)
[ -f "$REPORT" ] || { echo "Analizator nije napravio izveštaj."; exit 1; }
echo "Metrics: $OUT"
echo "result=$OUT" >> "$GITHUB_OUTPUT"
