#!/bin/bash
# Bring one rebased branch up to standard: map-driven renames, the recurring
# element-effect / function-table defects, missing declarations -- then verify
# every file the branch changes compiles under the REAL CFLAGS.
#
# Checks ALL branch files, not just the ones a fixer touched: checking only the
# touched set let two files reach CI with implicit declarations.
set -u
cd "${RMZ3_WT:?set RMZ3_WT to the upstream worktree}"
export PATH="/c/devkitPro/devkitARM/bin:$PATH"
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
FM=${RMZ3_FORK}/build/rmz3/rmz3.map
b="$1"

git diff --quiet || { echo "  ABORT: dirty"; exit 1; }
git checkout -q "$b" 2>&1 | sed 's/^/  /'
[ "$(git rev-parse --abbrev-ref HEAD)" = "$b" ] || { echo "  ABORT: checkout failed"; exit 1; }

FILES=$(git diff upstream/dev --name-only -- src | tr '\n' ' ')
[ -z "$FILES" ] && { echo "  no src changes"; exit 0; }

# Upstream flattened Boss/Projectile/Weapon/CyberElf/Pickup after these
# branches were written, so `(p->s).x` on those is now a hard error.
for f in $FILES; do python3 "$S/to_flat.py" "$f" | grep -v "no nested-style"; done
# Upstream declares handlers with the file's own flat typedef (SaverWave*,
# Seagulls*) while ported definitions still say struct Weapon*/struct Solid*.
# Retype the parameter AND flatten the body together -- doing either alone
# just swaps "conflicting types" for "no member named s".
python3 "$S/align_protos.py" $FILES | grep -v "^aligned 0"
python3 "$S/apply_map_renames.py" "$FM" "$S/upstream.map" $FILES | tail -6
python3 "$S/fix_common.py"   $FILES
python3 "$S/fix_includes.py" $FILES

# Correct any BL that points at the wrong function, taking the right name from
# the ROM. Needed because these branches were ALREADY written against upstream
# names, so re-applying the fork->upstream rename above can flip a correct call
# (AllocEntityFirst/Last exist on both sides, so nothing else catches it).
python3 "$S/fix_calls.py" $FILES | grep -v '^corrected 0'

rc=0; bad=""
for f in $FILES; do
  bash "$S/cc_check.sh" "$f" >/dev/null 2>&1 || { bad="$bad $f"; rc=1; }
done
# Gate: every BL must resolve to the function the ROM actually calls.
for f in $FILES; do
  v=$(python3 "$S/verify_calls.py" "$f" 2>/dev/null | tail -1)
  case "$v" in *", 0 wrong"|*"0 BL target(s) checked, 0 wrong") ;;
    *) echo "  CALL MISMATCH in $f: $v"; rc=1 ;;
  esac
done
if [ $rc -ne 0 ]; then
  echo "  STILL BROKEN:$bad"
  for f in $bad; do bash "$S/cc_check.sh" "$f" 2>&1 | head -4 | sed 's/^/    /'; done
  # Leave the tree CLEAN so the caller's loop can carry on to the next branch.
  # Without this one failure strands uncommitted edits and every later branch
  # aborts on "dirty tree" -- 20 branches skipped for one bad file.
  bash "$S/safe_reset.sh" >/dev/null   # snapshots before discarding
  exit 1
fi
echo "  all $(echo $FILES | wc -w) file(s) compile clean"
git diff --quiet && { echo "  no changes needed"; exit 0; }
git -c user.name="SensanaMMZ" \
    -c user.email="305674455+SensanaMMZ@users.noreply.github.com" \
    commit -q -am "Rebase on dev and use this repo's names

Symbols resolved against the ROM addresses in the linker map rather than by
spelling. ApplyElementEffect returns struct Entity* and takes a
CollisionObject* here, and the handler tables need the same cast this repo
uses for DeleteEntity."
echo "  committed $(git rev-parse --short HEAD)"
