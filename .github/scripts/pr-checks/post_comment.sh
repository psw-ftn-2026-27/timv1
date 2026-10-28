#!/usr/bin/env bash
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/../common/lib.sh"

upsert_bot_comment "<!-- teamtracker-pr-checks -->" comment.md
echo "Komentar objavljen."
