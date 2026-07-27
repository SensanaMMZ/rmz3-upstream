#!/bin/bash
# Convert one branch off the fork's OBJECT_HDR and onto upstream's
# COLLISION_OBJECT_HDR.
#
#   convert_object_hdr.sh <branch>
#
# The two describe the same 0xB4 bytes, but OBJECT_HDR is NESTED
# (`struct Entity s; struct Body body;`) so accesses read `p->s.coord`, while
# COLLISION_OBJECT_HDR splices the entity fields in flat so the same access is
# `p->coord`. Upstream REMOVED OBJECT_HDR; these branches build only because
# they patch it back into include/entity/entity.h, which is the structural
# divergence that makes them unmergeable.
#
# So: drop the header change, switch each struct to the flat macro, and flatten
# the accesses with the existing to_flat pass. Every touched file must still
# compile+assemble afterwards, and the branch is left untouched if any of them
# does not -- a half-converted branch is worse than an unconverted one.
set -u
cd ${RMZ3_WT:?set RMZ3_WT to the upstream worktree}
export PATH="/c/devkitPro/devkitARM/bin:$PATH"
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

b="$1"
git diff --quiet || bash "$S/safe_reset.sh" >/dev/null 2>&1
git checkout -q "$b" 2>/dev/null
[ "$(git rev-parse --abbrev-ref HEAD)" = "$b" ] || { echo "  ABORT $b: checkout"; exit 1; }

start=$(git rev-parse HEAD)

# 1. Take upstream's headers, then copy back any type the branch adds that
# upstream genuinely lacks (e.g. struct Omega1) -- a plain revert deletes
# real contributions.
git checkout upstream/dev -- include/ 2>/dev/null
python3 "$S/preserve_header_additions.py" "$b" >/dev/null 2>&1

# 2. Every file that used it.
files=$(git diff upstream/dev --name-only -- "src/*.c")
[ -z "$files" ] && { echo "  $b: nothing to convert"; git checkout -q -- include 2>/dev/null; exit 0; }

for f in $files; do
  python3 - "$f" <<'PY'
import io, re, sys
p = sys.argv[1]
s = io.open(p, encoding='utf-8', errors='replace').read()
s = re.sub(r'^(\s*)OBJECT_HDR;', r'\1COLLISION_OBJECT_HDR;', s, flags=re.M)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
PY
  python3 "$S/rename_fork_types.py" "$f" >/dev/null 2>&1
  python3 "$S/fix_struct_keyword.py" "$f" >/dev/null 2>&1
  python3 "$S/to_flat.py" "$f" >/dev/null 2>&1
  python3 "$S/flatten_converted.py" "$f" >/dev/null 2>&1
  python3 "$S/fix_common.py" "$f" >/dev/null 2>&1
  python3 "$S/fix_buffer_offsets.py" "$f" >/dev/null 2>&1
  python3 "$S/fix_field_offsets.py" "$f" >/dev/null 2>&1
  python3 "$S/fix_macro_names.py" "$f" >/dev/null 2>&1
  python3 "$S/fix_arg_casts.py" "$f" >/dev/null 2>&1
  python3 "$S/fix_arg_casts_n.py" "$f" >/dev/null 2>&1
  python3 "$S/fix_includes.py" "$f" >/dev/null 2>&1
done

# 3. Prove every converted file still builds.
bad=0
for f in $files; do
  bash "$S/cc_check.sh" "$f" >/dev/null 2>&1 || { echo "    BROKEN $f"; bad=$((bad+1)); }
done
if [ "$bad" != 0 ]; then
  echo "  $b: $bad file(s) broken -- reverting, branch untouched"
  git checkout -q -- src include 2>/dev/null
  git reset -q --hard "$start" 2>/dev/null
  exit 1
fi

bash tools/check_shared_branch.sh >/dev/null 2>&1 || { echo "  $b: SCRUB FAIL"; exit 1; }
git add -A src include
git -c user.name="SensanaMMZ" \
    -c user.email="305674455+SensanaMMZ@users.noreply.github.com" \
    commit -q -m "Use upstream's COLLISION_OBJECT_HDR instead of OBJECT_HDR" >/dev/null 2>&1
echo "  $b: converted $(echo "$files" | wc -w) file(s)  $(git rev-parse --short HEAD)"
