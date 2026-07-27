#!/bin/bash
# Discard working-tree changes, but SNAPSHOT them first so nothing is lost.
#
# Use this instead of a bare `git checkout -- .`.
#
# Why: a bare reset silently destroyed a full round of fixes on
# reb/enemy-batch-3 -- the chain had been run, the files were correct, and
# nothing had been committed yet. The work looked like a tooling regression on
# the next run rather than a reset, which cost more time than the rerun did.
#
# `git stash create` writes a dangling commit without touching the index or the
# stash list, so the snapshot cannot itself disturb whatever is in flight. The
# sha is printed; recover with `git checkout <sha> -- .`.
#
#   safe_reset.sh [<pathspec> ...]     (default: everything)
set -u
cd "${RMZ3_WT:?set RMZ3_WT to the upstream worktree}"

if git diff --quiet && git diff --cached --quiet; then
  echo "  tree already clean, nothing to reset"
  exit 0
fi

snap=$(git stash create "safe_reset snapshot on $(git rev-parse --abbrev-ref HEAD)")
if [ -n "$snap" ]; then
  # Keep it reachable so gc cannot collect it.
  git tag -f "safe-reset-$(git rev-parse --short "$snap")" "$snap" >/dev/null 2>&1
  echo "  snapshot: $snap  (recover: git checkout $snap -- .)"
fi

# Clear the INDEX first, then restore the worktree. The other order leaves
# staged deletions in place -- `git checkout -- .` will not resurrect a file the
# index says is deleted -- so the tree stays dirty and every following branch
# aborts on "dirty tree". Twelve hand-offs were skipped that way.
git reset -q
if [ $# -gt 0 ]; then
  git checkout -q -- "$@"
else
  git checkout -q -- .
fi
git clean -qfd asm src 2>/dev/null
echo "  reset done on $(git rev-parse --abbrev-ref HEAD)"
