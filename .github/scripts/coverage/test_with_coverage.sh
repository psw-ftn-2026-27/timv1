#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/../common/lib.sh"

select_solution
SETTINGS=""
[ -n "$RUNSETTINGS" ] && SETTINGS="--settings $RUNSETTINGS"
echo "Testiram: ${TARGET:-(cwd)}  settings: ${SETTINGS:-(nema)}"
dotnet test $TARGET $SETTINGS \
  --blame-hang-timeout 5m --blame-hang-dump-type none \
  --collect:"XPlat Code Coverage" --results-directory ./coverage-raw
