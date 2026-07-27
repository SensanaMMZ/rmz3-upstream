#!/bin/bash
# Hand a source file back to upstream on a branch that should no longer own it.
#
#   do_handoff.sh <branch> <src/path/file.c> [<src/path/file.c> ...]
#
# Reverting the .c alone is NOT enough. Porting also split the file's
# `asm/.../file.inc` into `file_a.inc`, `file_b.inc`, ... and deleted the
# original. Restoring only the C leaves upstream's `INCASM("asm/.../file.inc")`
# pointing at a file the branch removed, and leaves the carved pieces orphaned
# with nothing including them -- so the tree stops building. Restore the whole
# asm group with the C.
set -u
cd "${RMZ3_WT:?set RMZ3_WT to the upstream worktree}"
export PATH="/c/devkitPro/devkitARM/bin:$PATH"
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
b="$1"; shift

git diff --quiet || { echo "  ABORT: dirty tree"; exit 1; }
git checkout -q "$b" 2>/dev/null
[ "$(git rev-parse --abbrev-ref HEAD)" = "$b" ] || { echo "  ABORT: not on $b"; exit 1; }

for c in "$@"; do
  base=$(basename "$c" .c)
  dir=$(dirname "${c#src/}")
  # every asm path this branch touched that belongs to this file's group
  for a in $(git diff upstream/dev --name-only -- "asm/$dir" | \
             grep -E "/${base}(_[a-z0-9]+)*\.inc$"); do
    if git cat-file -e "upstream/dev:$a" 2>/dev/null; then
      git checkout upstream/dev -- "$a"
    else
      git rm -q -f -- "$a" 2>/dev/null
    fi
  done
  # and the original inc, if the branch deleted it
  orig="asm/$dir/$base.inc"
  git cat-file -e "upstream/dev:$orig" 2>/dev/null && git checkout upstream/dev -- "$orig"
  git checkout upstream/dev -- "$c"
  echo "    handed back $c"
done

git add -A asm src
if git diff --cached --quiet; then echo "  nothing changed"; exit 0; fi

rc=0
for f in $(git diff upstream/dev --name-only -- src); do
  bash "$S/cc_check.sh" "$f" >/dev/null 2>&1 || { echo "  BROKEN $f"; rc=1; }
done
python3 "$S/check_carve.py" "$b" | grep LOST && rc=1
# safe_reset.sh snapshots the tree before discarding, so a failed verify cannot
# take a good round of edits with it.
if [ $rc -ne 0 ]; then
  echo "  VERIFY FAILED, reverting"
  bash "$S/safe_reset.sh" >/dev/null
  exit 1
fi
echo "  verified"
