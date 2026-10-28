#!/usr/bin/env bash
set -e
RAW_DIR="$1"
OUT_DIR="$2"
REPORT_TYPES="$3"

dotnet tool install --global dotnet-reportgenerator-globaltool --version 5.5.11
export PATH="$PATH:$HOME/.dotnet/tools"
reportgenerator \
  -reports:"$RAW_DIR/**/coverage.cobertura.xml" \
  -targetdir:"$OUT_DIR" \
  -reporttypes:"$REPORT_TYPES"
