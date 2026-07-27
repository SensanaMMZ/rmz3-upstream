#!/bin/bash
# Convert ONE branch off OBJECT_HDR, end to end, and verify EVERY file the
# branch touches -- not just the ones that named the macro. Writes results
# atomically: nothing reads a half-written file, because the result only
# appears (via mv) after the run is finished.
#
#   run_conversion.sh <branch> <worktree> <result-file>
#
# Leaves the worktree ON the branch with the conversion COMMITTED when every
# file passes, or fully reset to the branch tip when any file fails.
set -u
b="$1"; WT="$2"; OUT="$3"
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$WT" || exit 1

# EXCLUSIVE LOCK on the worktree. Three conversion runs have now raced each
# other (and foreground edits) in this worktree: a TaskStop'd run whose bash
# tree survived as a zombie, a second run whose end-of-run revert fired UNDER a
# third, and hand-iterations done while a run was still live. Every one of
# those produced numbers that had to be thrown away. mkdir is atomic: if the
# lock exists, another instance is (or died) holding it -- refuse to start and
# say so, never silently share the tree.
LOCK="$WT/.conversion.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "ABORT: $LOCK exists -- another conversion is running (or died holding it)" >> "$OUT.tmp"
  mv "$OUT.tmp" "$OUT"
  exit 1
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
export PATH="/c/devkitPro/devkitARM/bin:$PATH"
TMP="$OUT.tmp"
export CONV_NO_FIELD_RENAMES=1
: > "$TMP"

git checkout -q "$b" 2>/dev/null
[ "$(git rev-parse --abbrev-ref HEAD)" = "$b" ] || { echo "ABORT: checkout $b" >> "$TMP"; mv "$TMP" "$OUT"; exit 1; }
git checkout -q -- . 2>/dev/null
git clean -qfd src include 2>/dev/null
start=$(git rev-parse HEAD)
echo "branch $b tip $start" >> "$TMP"

# Skip branches that never re-add the macro.
if [ "$(git show "$b:include/entity/entity.h" 2>/dev/null | grep -c 'define OBJECT_HDR')" = "0" ]; then
  echo "SKIP: no OBJECT_HDR in entity.h" >> "$TMP"; mv "$TMP" "$OUT"; exit 0
fi

# 1. Upstream headers wholesale, then re-add types the branch genuinely adds.
git checkout upstream/dev -- include/ 2>/dev/null
python3 "$S/preserve_header_additions.py" "$b" >> "$TMP" 2>&1

# 2. Convert every .c the branch touches.
files=$(git diff upstream/dev --name-only -- 'src/*.c')
n=0
for f in $files; do
  [ -f "$f" ] || continue
  python3 "$S/subst_hdr.py" "$f"
  for p in rename_fork_types fix_struct_keyword to_flat flatten_converted \
           fix_common fix_buffer_offsets fix_field_offsets fix_macro_names \
           align_protos fix_nested_access fix_arg_casts fix_arg_casts_n fix_includes; do
    python3 "$S/$p.py" "$f" >/dev/null 2>>"$TMP"
  done
  n=$((n+1))
done
python3 "$S/rename_branch_fields.py" "$b" $files >> "$TMP" 2>&1
python3 "$S/fix_wrapped_defs.py" $files >> "$TMP" 2>&1
python3 "$S/rename_enums.py" "$b" $files >> "$TMP" 2>&1
if grep -qE "Traceback|SyntaxError" "$TMP"; then
  echo "FIXER CRASHED" >> "$TMP"
  git checkout -q -- . ; git clean -qfd src include; mv "$TMP" "$OUT"; exit 1
fi

# 3. Known flattening collisions: a file-local field now shadowed by an
# ENTITY_HDR field of the same name. Applied only where present.
python3 "$S/fix_hdr_collisions.py" $files >> "$TMP" 2>&1

# 4. Verify EVERY file.
bad=0
for f in $files; do
  [ -f "$f" ] || continue
  if ! bash "$S/cc_check.sh" "$f" >/dev/null 2>"$S/conv_one_err.txt"; then
    echo "BROKEN $f" >> "$TMP"; bad=$((bad+1))
    # keep the first real error line per broken file in the result itself
    grep -m2 -E "error|warning|undeclared|incomplete|no member" \
      "$S/conv_one_err.txt" | sed 's/^/    /' >> "$TMP"
  fi
done
echo "converted $n file(s), broken $bad" >> "$TMP"

if [ "$bad" != 0 ]; then
  if [ -n "$KEEP" ]; then
    # leave the failed tree in place for hand-fixing; caller owns cleanup
    echo "RESULT: FAIL (KEEP=1, tree left dirty on $b)" >> "$TMP"
  else
    git checkout -q -- . ; git clean -qfd src include
    echo "RESULT: FAIL (reverted, branch untouched at $start)" >> "$TMP"
  fi
  mv "$TMP" "$OUT"; exit 1
fi

rm -f nul 2>/dev/null
if [ -f tools/check_shared_branch.sh ]; then
  bash tools/check_shared_branch.sh >/dev/null 2>&1 || { echo "RESULT: SCRUB FAIL" >> "$TMP"; mv "$TMP" "$OUT"; exit 1; }
fi
git add -A src include
git -c user.name="SensanaMMZ" \
    -c user.email="305674455+SensanaMMZ@users.noreply.github.com" \
    commit -q -m "Use upstream's COLLISION_OBJECT_HDR instead of OBJECT_HDR" >/dev/null 2>&1
echo "RESULT: OK $(git rev-parse --short HEAD)" >> "$TMP"
mv "$TMP" "$OUT"
