#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/../common/lib.sh"

if [ -z "$METRICS" ]; then
  set_commit_status "$HEAD_SHA" maintainability error "metrike nisu izmerene"
  exit 0
fi
set_commit_status "$HEAD_SHA" maintainability success "$METRICS"
