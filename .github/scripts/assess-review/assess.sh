#!/usr/bin/env bash
set -eo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HERE/../common/lib.sh"

[ -n "$LLM_MODEL" ] || LLM_MODEL="claude-opus-5-5"
export LLM_MODEL
MARKER="<!-- teamtracker-review-assessment -->"

upsert_comment() {
  repost_bot_comment "$MARKER" "$1"
}

fail_assessment() {
  echo "PROCENA NIJE IZVRŠENA: $1"
  {
    echo "$MARKER"
    echo "## Automatska procena revizije"
    echo ""
    echo "⚠️ **Procena nije izvršena:** $1"
    echo ""
    echo "<sub>Ovo nije ocena revizije, nego kvar u merenju. Pokreni ponovo: Actions → assess-review → Re-run failed jobs.</sub>"
  } > fail.md
  upsert_comment fail.md || true
  exit 1
}

[ -n "$ANTHROPIC_API_KEY" ] || fail_assessment "nije podešen ANTHROPIC_API_KEY."

# 1) Sačekaj merenja istog commit-a: najnoviji run svakog workflow-a koji nije preskočen
#    (preskočeni su oni sa autorovih revizija) mora da se završi uspešno (max ~8 min).
sleep 15
latest() { jq -c --arg n "$1" '[.workflow_runs[] | select(.name==$n and .conclusion!="skipped")][0] // {}' runs.json; }
MST=""; CST=""; MCON=""; CCON=""; MRUN=""; CRUN=""
for i in $(seq 1 48); do
  gh api "repos/$REPO/actions/runs?head_sha=$SHA&per_page=100" > runs.json || { sleep 10; continue; }
  M=$(latest maintainability); C=$(latest coverage)
  MST=$(jq -r '.status // ""' <<< "$M"); MCON=$(jq -r '.conclusion // ""' <<< "$M"); MRUN=$(jq -r '.id // ""' <<< "$M")
  CST=$(jq -r '.status // ""' <<< "$C"); CCON=$(jq -r '.conclusion // ""' <<< "$C"); CRUN=$(jq -r '.id // ""' <<< "$C")
  echo "čekam merenja… maintainability=$MST/$MCON coverage=$CST/$CCON"
  [ "$MST" = "completed" ] && [ "$CST" = "completed" ] && break
  sleep 10
done
[ "$MST" = "completed" ] && [ "$CST" = "completed" ] || fail_assessment "merenja nisu završena na vreme."
[ "$MCON" = "success" ] || fail_assessment "lakoća održavanja nije izmerena (workflow **maintainability** nije uspeo)."
[ "$CCON" = "success" ] || fail_assessment "pokrivenost nije izmerena (workflow **coverage** nije uspeo, najčešće build ili testovi ne prolaze)."

# 2) Preuzmi artefakte preko REST-a.
art_id() { gh api "repos/$REPO/actions/runs/$1/artifacts" --jq "[.artifacts[] | select(.name==\"$2\")][0].id // empty"; }
MAID=$(art_id "$MRUN" maintainability-report)
CAID=$(art_id "$CRUN" coverage-report)
[ -n "$MAID" ] && [ -n "$CAID" ] || fail_assessment "artefakti merenja nisu pronađeni."
gh api "repos/$REPO/actions/artifacts/$MAID/zip" > m.zip && unzip -o m.zip -d _m >/dev/null
gh api "repos/$REPO/actions/artifacts/$CAID/zip" > c.zip && unzip -o c.zip -d _c >/dev/null
MFILE=$(find _m -name maintainability-report.json -print -quit)
CFILE=$(find _c -name Cobertura.xml -print -quit)
[ -n "$MFILE" ] && [ -n "$CFILE" ] || fail_assessment "artefakti merenja su prazni."
cp "$MFILE" maintainability-report.json
cp "$CFILE" Cobertura.xml
echo "merenja: maintainability run $MRUN, coverage run $CRUN"

# 3) Diff, komentari, revizije i šablon revizije sa base grane.
gh api --paginate "repos/$REPO/pulls/$PR/files?per_page=100" --jq '.[]' | jq -s '.' > files.json
gh api --paginate "repos/$REPO/pulls/$PR/comments?per_page=100" --jq '.[]' | jq -s '.' > comments.json
gh api --paginate "repos/$REPO/issues/$PR/comments?per_page=100" --jq '.[]' | jq -s '.' > issue_comments.json
gh api --paginate "repos/$REPO/pulls/$PR/reviews?per_page=100" --jq '.[]' | jq -s '.' > reviews.json
gh api -H "Accept: application/vnd.github.raw" \
  "repos/$REPO/contents/review_template.md?ref=$BASE_SHA" > template.md 2>/dev/null || : > template.md

# 3b) Ranije procene istog PRa: problem koji je recenzent uočio ranije, a više ne postoji,
#     prikazuje se kao rešen umesto da nestane iz procene.
mkdir -p prev
gh api --paginate "repos/$REPO/pulls/$PR/commits?per_page=100" --jq '.[].sha' > pr_shas.txt
while read -r COMMIT_SHA; do
  gh api "repos/$REPO/actions/runs?head_sha=$COMMIT_SHA&per_page=100" \
    --jq ".workflow_runs[] | select(.name==\"assess-review\" and .conclusion==\"success\" and .id != $RUN_ID) | .id" || true
done < pr_shas.txt | sort -un > prev_runs.txt
while read -r PREV_RUN; do
  PAID=$(gh api "repos/$REPO/actions/runs/$PREV_RUN/artifacts" \
    --jq '[.artifacts[] | select(.name=="review-assessment" and .expired==false)][0].id // empty') || PAID=""
  [ -n "$PAID" ] || continue
  gh api "repos/$REPO/actions/artifacts/$PAID/zip" > "prev/$PREV_RUN.zip" \
    && unzip -o -q "prev/$PREV_RUN.zip" -d "prev/$PREV_RUN" || true
done < prev_runs.txt
echo "ranije procene ovog PRa: $(find prev -name review-assessment.json | wc -l)"

# 4) Izmereni problemi + prompt.
python3 "$HERE/assess_review.py" build || fail_assessment "ulazni podaci za procenu nisu potpuni."

# 5) LLM ukrštanje: temperatura 0, do 3 pokušaja, odgovor mora da pokrije SVE probleme i komentare.
python3 "$HERE/llm_assess.py" || fail_assessment "LLM nije vratio ispravnu procenu ni posle 3 pokušaja."

# 6) Sastavi rezultat (review-assessment.json + comment.md).
HEAD_SHA="$SHA" python3 "$HERE/assess_review.py" assemble || fail_assessment "sastavljanje procene nije uspelo."

# 6b) Sažetak za nastavnika: priča kroz ceo PR (uočeno ili promašeno, rešeno ili otvoreno), iz konačne liste.
#     Ako ne uspe, ostaje sažetak iz koraka 5 i procena se ipak objavljuje.
python3 "$HERE/summarize.py" || echo "sažetak nije napisan, ostaje sažetak iz procene"

# 7) Postavi/ažuriraj komentar na PRu.
upsert_comment comment.md
echo "Komentar postavljen."
