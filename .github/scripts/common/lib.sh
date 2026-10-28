#!/usr/bin/env bash

REPO="${REPO:-$GITHUB_REPOSITORY}"
RUN_URL="${RUN_URL:-$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID}"

select_solution() {
  local slnx sln
  mapfile -t slnx < <(find . -maxdepth 1 -name '*.slnx' | sort)
  mapfile -t sln < <(find . -maxdepth 1 -name '*.sln' | sort)
  TARGET=""
  SOLUTION_ERROR=""
  if [ ${#slnx[@]} -ge 1 ]; then
    TARGET="${slnx[0]}"
    if [ ${#slnx[@]} -gt 1 ]; then
      SOLUTION_ERROR="U korenu repoa postoji više .slnx solucija (${slnx[*]}) — ostavi jednu."
    fi
  elif [ ${#sln[@]} -ge 1 ]; then
    TARGET="${sln[0]}"
    if [ ${#sln[@]} -gt 1 ]; then
      SOLUTION_ERROR="U korenu repoa postoji više .sln solucija (${sln[*]}) — ostavi jednu."
    fi
  else
    TARGET=$(find . \( -name '*.slnx' -o -name '*.sln' \) -not -path '*/.github/*' | sort | head -1)
    if [ -z "$TARGET" ]; then
      TARGET=$(find . -name '*.csproj' -path '*[Tt]est*' -not -path '*/.github/*' | sort | head -1)
    fi
  fi
  RUNSETTINGS=$(find . -name coverage.runsettings -not -path '*/.github/*' | sort | head -1)
}

find_bot_comment() {
  local marker="$1" id
  id=$(gh api "repos/$REPO/issues/$PR/comments" --paginate \
        --jq ".[] | select(.user.login == \"github-actions[bot]\" and (.body | contains(\"$marker\"))) | .id") || id=""
  echo "${id%%$'\n'*}"
}

upsert_bot_comment() {
  local marker="$1" file="$2" id
  id=$(find_bot_comment "$marker")
  if [ -n "$id" ]; then
    gh api -X PATCH "repos/$REPO/issues/comments/$id" -F body=@"$file" >/dev/null
  else
    gh api -X POST "repos/$REPO/issues/$PR/comments" -F body=@"$file" >/dev/null
  fi
}

repost_bot_comment() {
  local marker="$1" file="$2"
  delete_bot_comment "$marker"
  gh api -X POST "repos/$REPO/issues/$PR/comments" -F body=@"$file" >/dev/null
}

delete_bot_comment() {
  local marker="$1" id
  id=$(find_bot_comment "$marker")
  if [ -n "$id" ]; then
    gh api -X DELETE "repos/$REPO/issues/comments/$id" >/dev/null || true
  fi
}

set_commit_status() {
  local sha="$1" context="$2" state="$3" description="$4"
  gh api -X POST "repos/$REPO/statuses/$sha" \
    -f state="$state" -f context="$context" \
    -f description="$description" -f target_url="$RUN_URL" >/dev/null
}
