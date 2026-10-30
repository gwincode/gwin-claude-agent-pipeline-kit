#!/usr/bin/env bash
# Test suite for scripts/check-handoff-freshness.py.
#
# Builds throwaway git repos in a temp dir and asserts the gate's exit code for
# each scenario, including the real cases from the original project's history that motivated
# the gate. Run it before trusting any change to the checker:
#
#   bash scripts/test-handoff-freshness.sh
#
# No network, no fixtures, no dependencies beyond git and python3.

set -u
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/check-handoff-freshness.py"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PASS=0; FAIL=0

mkrepo() {
  rm -rf "$WORK/r"; mkdir -p "$WORK/r"; cd "$WORK/r" || exit 1
  git init -q -b main
  git config user.email t@example.com; git config user.name Test
  mkdir -p .github
  printf '%s\n' "${1:-\{\}}" > .github/handoff-freshness.json
}

commit_at() { GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git commit -q -m "$2"; }

check() { HANDOFF_BASE_SHA="$1" HANDOFF_HEAD_SHA=HEAD python3 "$SCRIPT" >"$WORK/out.txt" 2>&1; echo $?; }

assert() {
  if [ "$2" = "$3" ]; then printf '  ok   %s\n' "$1"; PASS=$((PASS+1))
  else printf '  FAIL %s (expected exit %s, got %s)\n' "$1" "$2" "$3"; FAIL=$((FAIL+1))
       sed 's/^/       | /' "$WORK/out.txt"; fi
}

# One-substantive-commit scenario: handoff date, base date, commit date, expected exit.
simple() {
  mkrepo '{"timezone":"America/New_York"}'
  printf '# HANDOFF\n\n**Last updated:** %s\n' "$2" > HANDOFF.md
  echo base > app.ts; git add -A; commit_at "$3" base
  local b; b=$(git rev-parse HEAD)
  echo changed > result.md; git add -A; commit_at "$4" "a result landed"
  assert "$1" "$5" "$(check "$b")"
}

echo "== Freshness =="
simple "docs-only commit 2 days after the handoff fails"            2026-09-04 2026-09-04T10:00:00Z 2026-09-06T14:28:43Z 1
simple "handoff written the same day passes"                        2026-09-08 2026-09-01T10:00:00Z 2026-09-08T18:00:00Z 0
simple "handoff newer than the commit passes"                       2026-09-09 2026-09-01T10:00:00Z 2026-09-08T18:00:00Z 0

mkrepo '{"timezone":"America/New_York"}'
printf '# HANDOFF\n\n**Last updated:** 2026-08-01\n' > HANDOFF.md
echo base > app.ts; git add -A; commit_at 2026-08-01T10:00:00Z base
B=$(git rev-parse HEAD)
printf '# HANDOFF\n\n**Last updated:** 2026-08-01\n\nmore prose\n' > HANDOFF.md
git add -A; commit_at 2026-09-08T10:00:00Z "handoff only"
assert "a handoff-only PR passes even with an old date" 0 "$(check "$B")"

mkrepo '{"timezone":"America/New_York"}'
printf '# HANDOFF\n\n**Last updated:** 2026-08-01\n' > HANDOFF.md
echo base > app.ts; git add -A; commit_at 2026-08-01T10:00:00Z base
B=$(git rev-parse HEAD)
mkdir -p scripts .github/workflows
cp "$SCRIPT" scripts/check-handoff-freshness.py
echo "name: x" > .github/workflows/handoff-freshness.yml
git add -A; commit_at 2026-09-08T10:00:00Z "install the gate itself"
assert "the gate's own files are exempt (bootstrap install)" 0 "$(check "$B")"

echo "== Malformed input =="
mkrepo '{"timezone":"America/New_York"}'
echo base > app.ts; git add -A; commit_at 2026-09-01T10:00:00Z base
B=$(git rev-parse HEAD)
echo more > app.ts; git add -A; commit_at 2026-09-08T10:00:00Z work
assert "a missing HANDOFF.md fails" 1 "$(check "$B")"

simple "an unparseable Last updated line fails"  "yesterday-ish"  2026-09-01T10:00:00Z 2026-09-08T10:00:00Z 1

echo "== Last updated formatting variants =="
for v in '**Last updated:** 2026-09-08' \
         '_Last updated: 2026-09-08_' \
         'Last updated 2026-09-08' \
         '- **Last updated:** 2026-09-08 (with trailing prose)'; do
  simple "variant: $v" "$v" 2026-09-01T10:00:00Z 2026-09-08T10:00:00Z 0
done

echo "== Timezone (real cases from the original projects) =="
# Project A staging commit: committed 02:09:46Z on the 18th, which is
# 22:09 on the 17th in America/New_York (EDT). The handoff correctly says the 17th.
simple "evening-local session is not a false positive (project A)" \
       2026-08-17 2026-08-17T10:00:00Z 2026-08-18T02:09:46Z 0
# Project B: a genuine two-day gap, must still fail.
simple "genuine multi-day staleness still fails (project B)" \
       2026-09-04 2026-09-04T10:00:00Z 2026-09-06T14:28:43Z 1
# Project B, 2026-09-04: promoted by another session hours later, same day.
simple "same-day author-not-promoter race does not fire" \
       2026-09-04 2026-09-04T09:00:00Z 2026-09-04T20:16:26Z 0
simple "23:59 local on the previous day passes" \
       2026-09-07 2026-09-06T10:00:00Z 2026-09-08T03:59:00Z 0
simple "00:01 local on the following day fails" \
       2026-09-07 2026-09-06T10:00:00Z 2026-09-08T04:01:00Z 1

echo "== Divergence =="
div_setup() { # $1 = divergenceMode, $2 = extra handoff line
  rm -rf "$WORK/bare" "$WORK/r"; mkdir -p "$WORK/bare"
  git init -q --bare -b main "$WORK/bare"
  git clone -q "$WORK/bare" "$WORK/r" 2>/dev/null; cd "$WORK/r" || exit 1
  git config user.email t@example.com; git config user.name Test
  mkdir -p .github
  printf '{"workingBranch":"staging","compareBranch":"main","divergenceMode":"%s","timezone":"America/New_York"}\n' "$1" \
    > .github/handoff-freshness.json
  printf '# HANDOFF\n\n**Last updated:** 2026-09-08\n%s\n' "$2" > HANDOFF.md
  echo base > app.ts; git add -A; commit_at 2026-09-08T10:00:00Z base
  git push -q origin main 2>/dev/null
  git checkout -q -b staging; git push -q origin staging 2>/dev/null
}
main_ahead() {
  git checkout -q main; echo hotfix > hotfix.ts; git add -A
  commit_at 2026-09-08T11:00:00Z "hotfix straight to main"
  git push -q origin main 2>/dev/null; git checkout -q staging; git fetch -q origin
}
pr_commit() {
  B=$(git rev-parse origin/staging); echo feat > feature.ts; git add -A
  commit_at 2026-09-08T12:00:00Z "a feature"
}

div_setup warn ""; main_ahead; pr_commit
assert "warn mode: untracked divergence stays green" 0 "$(check "$B")"
grep -q 'Warning' "$WORK/out.txt" && printf '       (warning was emitted)\n'

div_setup fail ""; main_ahead; pr_commit
assert "fail mode: untracked divergence goes red" 1 "$(check "$B")"

div_setup warn '**Divergence:** main is 1 ahead of staging (hotfix); repair pending.'
main_ahead; pr_commit
assert "a Divergence: line marks it tracked" 0 "$(check "$B")"

div_setup warn ""; git fetch -q origin; pr_commit
assert "staging merely ahead is not divergence" 0 "$(check "$B")"

echo "== Size ceiling (maxLines) =="
# $1 name, $2 config json, $3 total HANDOFF.md lines, $4 expected exit.
# Handoff-only PR, so freshness can never be what fails: only size can.
sized() {
  mkrepo "$2"
  { printf '**Last updated:** 2026-09-08\n'; for _ in $(seq 2 "$3"); do echo filler; done; } > HANDOFF.md
  echo base > app.ts; git add -A; commit_at 2026-09-08T10:00:00Z base
  local b; b=$(git rev-parse HEAD)
  sed -i '2s/.*/edited/' HANDOFF.md; git add -A; commit_at 2026-09-08T11:00:00Z "handoff-only edit"
  assert "$1" "$4" "$(check "$b")"
}
sized "over the ceiling fails (251 > 250)"       '{"maxLines":250}' 251 1
sized "at the ceiling passes (250 = 250)"        '{"maxLines":250}' 250 0
sized "under the ceiling passes (10 < 250)"      '{"maxLines":250}' 10  0
sized "key absent: a 1,445-line file still passes" '{}'             1445 0
grep -q 'size check is disabled' "$WORK/out.txt" && printf '       (disabled-check warning was emitted)\n' \
  || { printf '  FAIL key absent: no disabled-check warning\n'; FAIL=$((FAIL+1)); }
sized "maxLines as a string is misconfiguration" '{"maxLines":"250"}' 10 2
sized "maxLines of 0 is misconfiguration"        '{"maxLines":0}'    10 2

mkrepo '{"timezone":"America/New_York","maxLines":5}'
printf '**Last updated:** 2026-09-08\n1\n2\n3\n4\n5\n' > HANDOFF.md
echo base > app.ts; git add -A; commit_at 2026-09-01T10:00:00Z base
B=$(git rev-parse HEAD)
echo more > app.ts; git add -A; commit_at 2026-09-08T10:00:00Z work
assert "fresh handoff over the ceiling still fails" 1 "$(check "$B")"

echo
printf 'RESULTS: %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
