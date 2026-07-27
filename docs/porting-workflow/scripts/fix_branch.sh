#!/bin/bash
# Per-branch: clean checkout (asserted) -> map-driven renames -> compile-check
# every changed file -> commit. Push is left to the caller.
set -u
cd "${RMZ3_WT:?set RMZ3_WT to the upstream worktree}"
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
FM=${RMZ3_FORK}/build/rmz3/rmz3.map
b="$1"

git diff --quiet || { echo "  ABORT: dirty tree"; exit 1; }
git checkout -q "$b" 2>&1 | sed 's/^/  /'
cur=$(git rev-parse --abbrev-ref HEAD)
[ "$cur" = "$b" ] || { echo "  ABORT: on '$cur' not '$b'"; exit 1; }

FILES=$(git diff upstream/dev --name-only -- src | tr '\n' ' ')
[ -z "$FILES" ] && { echo "  no src changes"; exit 0; }
python3 "$S/apply_map_renames.py" "$FM" "$S/upstream.map" $FILES | tail -30

if git diff --quiet; then echo "  nothing to change"; exit 0; fi

# Check EVERY file the branch changes vs upstream/dev, not just the ones the
# rename pass happened to touch. Checking only the touched set let
# capsule_cannon.c and beetank.c reach CI with implicit declarations.
rc=0
for f in $FILES; do
  bash "$S/cc_check.sh" "$f" || rc=1
done
[ $rc -ne 0 ] && { echo "  COMPILE FAILED -- leaving changes uncommitted"; exit 1; }
echo "  all changed files compile clean"

git -c user.name="SensanaMMZ" \
    -c user.email="305674455+SensanaMMZ@users.noreply.github.com" \
    commit -q -am "Use this repo's symbol names

Names resolved against the ROM addresses in the linker map rather than by
spelling. AllocEntityFirst and AllocEntityLast are the other way round here
compared to the fork I ported from, so those calls were going to the wrong
function even though they compiled and linked."
echo "  committed $(git rev-parse --short HEAD)"
