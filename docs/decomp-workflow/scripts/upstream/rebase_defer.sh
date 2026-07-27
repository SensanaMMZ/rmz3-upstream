#!/bin/bash
# Rebase a stale branch onto upstream/dev, deferring to upstream on any file
# that conflicts.
#
# A conflict here means upstream has since decompiled the same file itself. Our
# version cannot simply be replayed on top -- upstream re-carved the .inc and
# switched to the flat typedef. Taking upstream's copy drops our contribution
# for that ONE file while preserving the rest of the branch, which for a
# 107-file PR is the difference between 99 usable files and none.
#
# During a rebase --ours is the branch being rebased ONTO (upstream/dev).
set -u
cd "${RMZ3_WT:?set RMZ3_WT to the upstream worktree}"
b="$1"
git checkout -q -B "reb/$(basename $b)" "prfork/contrib/$b" 2>/dev/null
dropped=""
git rebase upstream/dev >/dev/null 2>&1
# In a WORKTREE the rebase state lives under .git/worktrees/<name>/,
# not .git/ -- a literal .git/rebase-merge test is always false there,
# so the resolve loop never runs and the rebase is left half-done.
inrebase() { [ -d "$(git rev-parse --git-path rebase-merge)" ] || \n             [ -d "$(git rev-parse --git-path rebase-apply)" ]; }
while inrebase; do
  U=$(git diff --name-only --diff-filter=U)
  [ -z "$U" ] && { git -c core.editor=true rebase --continue >/dev/null 2>&1 || break; continue; }
  for f in $U; do
    git checkout --ours -- "$f" 2>/dev/null || git rm -q -- "$f" 2>/dev/null
    git add -- "$f" 2>/dev/null
    dropped="$dropped $f"
  done
  git -c core.editor=true rebase --continue >/dev/null 2>&1 || break
done
if inrebase; then
  echo "  rebase stuck"; git rebase --abort 2>/dev/null; exit 1
fi
echo "  rebased; deferred to upstream on:$(echo $dropped | tr ' ' '\n' | sort -u | tr '\n' ' ')"
