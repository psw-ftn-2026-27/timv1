#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "${1:-.}" && pwd)"
REPORT="${2:-$ROOT/maintainability-report.json}"
KIT="$ROOT/.github/analyzers"
cd "$ROOT"

mapfile -t SLNX < <(find . -maxdepth 1 -name '*.slnx' | sort)
mapfile -t SLN < <(find . -maxdepth 1 -name '*.sln' | sort)
if [ ${#SLNX[@]} -ge 1 ]; then
  TARGET="${SLNX[0]}"
elif [ ${#SLN[@]} -ge 1 ]; then
  TARGET="${SLN[0]}"
else
  TARGET=$(find . \( -name '*.slnx' -o -name '*.sln' \) -not -path './.github/*' | sort | head -1)
fi
[ -n "${TARGET:-}" ] || { echo "Nema .sln/.slnx u repou." >&2; exit 1; }
echo "Merenje: $TARGET" >&2

SARIF="$(mktemp -d)"
dotnet build "$TARGET" -nologo -v q \
  "-p:CustomAfterMicrosoftCommonTargets=$KIT/tt.targets" \
  "-p:TtSarifDir=$SARIF/" \
  "-p:TtRepoRoot=$ROOT" \
  "-p:TtMeasure=true" \
  "-p:TreatWarningsAsErrors=false" >&2

python3 "$KIT/sarif2report.py" "$SARIF" "$ROOT" "$REPORT" "$KIT/tt.globalconfig"
