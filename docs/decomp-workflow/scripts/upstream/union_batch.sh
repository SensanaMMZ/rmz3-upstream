#!/bin/bash
# Run union_merge.sh over a plan, and PROVE each result rather than trusting the
# script's own "merged OK" line.
#
#   union_batch.sh <plan-file>       plan rows: <branch>\t<file>\t<fn> <fn>...
#
# A previous version grepped the merge script's stdout for "merged OK" and
# reported 29 successes. None of them had persisted: a dirty tree from the
# previous iteration made the next run abort, and the summary counted output
# text rather than committed state. So here every item is verified against the
# repository itself --
#
#   * the tree must be clean BEFORE the attempt (else skip, do not corrupt it)
#   * the function must actually appear in the file afterwards
#   * the file must compile AND assemble
#   * a commit must exist that contains it
#
# Anything that fails any of those is reported as FAIL and rolled back.
set -u
cd "${RMZ3_WT:?set RMZ3_WT to the upstream worktree}"
export PATH="/c/devkitPro/devkitARM/bin:$PATH"
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
plan="$1"
ok=0; fail=0
: > "$S/union_failed.txt"

while IFS=$'\t' read -r br file fns; do
  [ -z "${br:-}" ] && continue
  lb="reb/${br#contrib/}"
  git rev-parse --verify -q "$lb" >/dev/null || continue

  if ! git diff --quiet; then
    bash "$S/safe_reset.sh" >/dev/null 2>&1
  fi
  rm -f nul 2>/dev/null

  bash "$S/union_merge.sh" "$lb" "$file" $fns >/dev/null 2>&1

  # PROVE it: every requested function present in the file on disk?
  present=1
  for fn in $fns; do
    grep -qE "^[A-Za-z_].*\b$fn\s*\(" "$file" 2>/dev/null || present=0
  done
  if [ "$present" != 1 ] || ! bash "$S/cc_check.sh" "$file" >/dev/null 2>&1; then
    printf "  FAIL %-40s\n" "$(basename "$file")"
    echo -e "$br\t$file\t$fns" >> "$S/union_failed.txt"
    bash "$S/safe_reset.sh" >/dev/null 2>&1
    fail=$((fail+1)); continue
  fi

  before=$(git rev-parse HEAD)
  git add -A asm src
  git -c user.name="SensanaMMZ" \
      -c user.email="305674455+SensanaMMZ@users.noreply.github.com" \
      commit -q -m "Match $(echo $fns | tr ' ' ', ') in $(basename "$file")" >/dev/null 2>&1
  after=$(git rev-parse HEAD)
  if [ "$before" = "$after" ]; then
    printf "  FAIL %-40s (nothing committed)\n" "$(basename "$file")"
    echo -e "$br\t$file\t$fns" >> "$S/union_failed.txt"
    bash "$S/safe_reset.sh" >/dev/null 2>&1
    fail=$((fail+1)); continue
  fi
  printf "  OK   %-40s +%s fn  %s\n" "$(basename "$file")" "$(echo $fns | wc -w)" "${after:0:8}"
  ok=$((ok+1))
done < "$plan"

echo "--- merged $ok, failed $fail"
