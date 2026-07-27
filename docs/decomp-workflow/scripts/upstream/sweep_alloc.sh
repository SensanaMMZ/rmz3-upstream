#!/bin/bash
# Apply the AllocEntityFirst<->Last swap to each branch, one clean checkout at
# a time.
#
# The assertion matters: a failed `git checkout` leaves you on the PREVIOUS
# branch, and running the swap there a second time silently reverts the first
# branch's fix. Verify the checkout actually landed before touching anything.
set -u
cd "${RMZ3_WT:?set RMZ3_WT to the upstream worktree}"
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

for b in "$@"; do
  echo "=== $b"
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "  ABORT: working tree dirty, refusing to switch"; exit 1
  fi
  git checkout -q "$b" 2>&1 | sed 's/^/  /'
  cur=$(git rev-parse --abbrev-ref HEAD)
  if [ "$cur" != "$b" ]; then
    echo "  ABORT: checkout failed, on '$cur' not '$b'"; exit 1
  fi
  FILES=$(git diff upstream/dev --name-only -- src)
  HITS=""
  for f in $FILES; do
    git diff upstream/dev -- "$f" | grep -q "^+.*AllocEntity" && HITS="$HITS $f"
  done
  if [ -z "$HITS" ]; then echo "  (no added AllocEntity calls)"; continue; fi
  python3 "$S/swap_alloc.py" $HITS
done
echo "sweep done, on $(git rev-parse --abbrev-ref HEAD)"
