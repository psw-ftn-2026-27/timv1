#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/../common/lib.sh"

select_solution
SETTINGS=""
[ -n "$RUNSETTINGS" ] && SETTINGS="--settings $RUNSETTINGS"
echo "Cilj: ${TARGET:-(nije izabran)}"

set +e
BUILD_RC=0
TEST_RC=0
if [ -n "$SOLUTION_ERROR" ]; then
  echo "$SOLUTION_ERROR" > build.log
  BUILD_RC=1
else
  dotnet build $TARGET > build.log 2>&1
  BUILD_RC=$?
fi
if [ $BUILD_RC -eq 0 ]; then
  dotnet test $TARGET $SETTINGS --no-build \
    --blame-hang-timeout 5m --blame-hang-dump-type none \
    --collect:"XPlat Code Coverage" --results-directory ./cov-raw > test.log 2>&1
  TEST_RC=$?
fi
set -e

tail -n 200 build.log
[ -f test.log ] && tail -n 200 test.log

BUILD_RC=$BUILD_RC TEST_RC=$TEST_RC SOLUTION_ERROR="$SOLUTION_ERROR" python3 "$HERE/build_report.py"
