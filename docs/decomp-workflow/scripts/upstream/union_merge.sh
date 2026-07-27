#!/bin/bash
# Lift functions the OWNER of a file is still carrying as assembly, so the file
# becomes a true superset and the losing PR can hand it over losslessly.
#
#   union_merge.sh <owner-branch> <src/file.c> <fn> [<fn> ...]
#
# Why this and not a C-body splice: the owner has these functions inside an
# INCASM'd .inc. Pasting the C body without carving that .inc defines the symbol
# twice -- which compiles, and fails only at assembly. So re-carve the inc that
# holds each function and interleave, exactly as the original port did.
#
# Functions may be spread across several already-carved incs (bird_a.inc,
# bird_b.inc), so group by inc and carve each separately.
set -u
cd "${RMZ3_WT:?set RMZ3_WT to the upstream worktree}"
export PATH="/c/devkitPro/devkitARM/bin:$PATH"
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

owner="$1"; src="$2"; shift 2
fns="$*"

git diff --quiet || { echo "  ABORT: dirty tree"; exit 1; }
git checkout -q "$owner" 2>/dev/null
[ "$(git rev-parse --abbrev-ref HEAD)" = "$owner" ] || {
  echo "  ABORT: on $(git rev-parse --abbrev-ref HEAD), not $owner"; exit 1; }

dir="asm/$(dirname "${src#src/}")"
lifted=0
for fn in $fns; do
  # [[:space:]] not a literal tab: a tab typed into a script does not always
  # survive being written out, and the pattern then silently matches nothing --
  # which looked like "already lifted" for all 40 files.
  inc=$(grep -lE "^[[:space:]]*thumb_func_start $fn\$" $dir/*.inc 2>/dev/null | head -1)
  if [ -z "$inc" ]; then
    echo "  $fn: not in any inc under $dir"; continue
  fi
  python3 "$S/port_to_upstream.py" "$inc" "$src" "$src" "$fn" 2>&1 | sed 's/^/    /'
  lifted=$((lifted+1))
done

# Doing nothing is a FAILURE, not a success. Reporting "merged OK" after zero
# lifts is how a broken grep pattern passed 40 times.
if [ "$lifted" -eq 0 ]; then
  echo "  NOTHING LIFTED from $src"; exit 1
fi

# The lifted bodies come from the fork and need the same treatment as any port.
# import_struct FIRST: a body may name a per-entity struct that exists only in
# the fork, and until it is defined every access through it is "dereferencing
# pointer to incomplete type" -- an error that points at the USE, never at the
# missing definition.
python3 "$S/import_struct.py" "$src" 2>&1 | grep -v "no fork definition" || true
python3 "$S/to_flat.py" "$src" >/dev/null 2>&1
python3 "$S/align_protos.py" "$src" >/dev/null 2>&1
python3 "$S/apply_map_renames.py" \
    ${RMZ3_FORK}/build/rmz3/rmz3.map \
    "$S/upstream.map" "$src" >/dev/null 2>&1
python3 "$S/fix_specific.py" "$src" >/dev/null 2>&1
python3 "$S/fix_common.py"   "$src" >/dev/null 2>&1
python3 "$S/fix_includes.py" "$src" >/dev/null 2>&1
python3 "$S/fix_calls.py"    "$src" >/dev/null 2>&1

if ! bash "$S/cc_check.sh" "$src" >/dev/null 2>&1; then
  echo "  BROKEN after merge:"; bash "$S/cc_check.sh" "$src" 2>&1 | sed -n '2,4p' | sed 's/^/    /'
  bash "$S/safe_reset.sh" >/dev/null
  exit 1
fi
v=$(python3 "$S/verify_calls.py" "$src" 2>/dev/null | tail -1)
case "$v" in *", 0 wrong") ;; *) echo "  CALL MISMATCH: $v"; bash "$S/safe_reset.sh" >/dev/null; exit 1 ;; esac
python3 "$S/check_incasm.py" 2>/dev/null | grep -q "^  0 missing" || {
  echo "  INCASM inconsistent"; bash "$S/safe_reset.sh" >/dev/null; exit 1; }

echo "  merged OK: $src (+$(echo $fns | wc -w) fn)"
