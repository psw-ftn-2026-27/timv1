#!/usr/bin/env bash
set -e
set -o pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/../common/lib.sh"

MARKER="<!-- review-template-valid -->"

gh api --paginate "repos/$REPO/pulls/$PR/reviews?per_page=100" --jq '.[]' | jq -s '.' > reviews.json
gh api -H "Accept: application/vnd.github.raw" \
  "repos/$REPO/contents/review_template.md?ref=$BASE_SHA" > template.md 2>/dev/null || : > template.md

python3 "$HERE/validate_reviews.py" > verdict.txt

echo "--- rezultat ---"; cat verdict.txt
STATUS=$(head -n1 verdict.txt)
tail -n +2 verdict.txt >> "$GITHUB_STEP_SUMMARY"

if [ "$STATUS" = "OK" ]; then
  delete_bot_comment "$MARKER"
  set_commit_status "$HEAD_SHA" review-template success "$(sed -n 2p verdict.txt | cut -c1-140)"
  exit 0
fi

if [ "$STATUS" = "WAIT" ]; then
  set_commit_status "$HEAD_SHA" review-template pending "Čeka se revizija recenzenta"
  exit 0
fi

{
  echo "$MARKER"
  echo "## Šablon revizije"
  echo ""
  echo "❌ **Revizija ne prati šablon, spajanje je blokirano.**"
  echo ""
  echo "Revizija mora da pokrije sva tri aspekta kvaliteta (funkcionalnu pogodnost, besprekornost"
  echo "i lakoću održavanja), sa odgovorom na svako pitanje i popunjenim obrazloženjem, zatim sekciju"
  echo "Frontend (ili „NIJE RELEVANTNO ZA OVAJ PR”) i zaključak:"
  echo ""
  tail -n +2 verdict.txt | sed 's/^/- /'
  echo ""
  echo "> Nalepi \`review_template.md\` u polje za reviziju, popuni ga i ponovo predaj reviziju."
  echo "> Aspekte koje si već ispravno pokrio u ranijoj reviziji ne moraš ponavljati."
} > rt.md
if [ "$GITHUB_EVENT_NAME" = "pull_request_review" ]; then
  repost_bot_comment "$MARKER" rt.md || true
else
  upsert_bot_comment "$MARKER" rt.md || true
fi
COUNT=$(tail -n +2 verdict.txt | wc -l)
set_commit_status "$HEAD_SHA" review-template failure "Revizija ne prati šablon, nedostataka: $COUNT (detalji u komentaru)"
