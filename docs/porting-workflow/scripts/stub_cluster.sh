#!/bin/bash
# Decompile every trivial stub in ONE inc, on a fresh branch off upstream/dev.
#
#   stub_cluster.sh <asm/path/file.inc> <fn>:<kind> [...]
#
# Same gate chain as port_cluster.sh -- compile+assemble, BL targets, carve,
# INCASM, size -- because "the body is obviously right" is exactly the kind of
# confidence that produced a wrong ROM earlier in this work.
set -u
cd "${RMZ3_WT:?set RMZ3_WT to the upstream worktree}"
export PATH="/c/devkitPro/devkitARM/bin:$PATH"
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

inc="$1"; shift
specs="$*"
fns=$(echo "$specs" | tr ' ' '\n' | cut -d: -f1 | tr '\n' ' ')
rel="${inc#asm/}"; name="stub/$(dirname "$rel")-$(basename "${rel%.inc}")"

git diff --quiet || bash "$S/safe_reset.sh" >/dev/null 2>&1
git checkout -q -B "$name" upstream/dev 2>/dev/null
[ "$(git rev-parse --abbrev-ref HEAD)" = "$name" ] || { echo "  ABORT: checkout"; exit 1; }

src=$(grep -rl "INCASM(\"$inc\")" src --include=*.c 2>/dev/null | head -1)
[ -n "$src" ] || { echo "  ABORT: no .c INCASMs $inc"; exit 1; }

python3 "$S/port_stubs.py" "$inc" "$src" $specs >/dev/null 2>>"$S/stub_err.log" || {
  echo "  ABORT $(basename "$src") ($(tail -1 "$S/stub_err.log"))"
  bash "$S/safe_reset.sh" >/dev/null 2>&1; exit 1; }

fail=""
bash "$S/cc_check.sh" "$src" > "$S/cc_out.txt" 2>&1 || {
  fail="compile"; { echo "### $name ($src)"; head -12 "$S/cc_out.txt"; } >> "$S/fail_err.log"; }
[ -z "$fail" ] && { python3 "$S/check_carve.py" "$name" 2>/dev/null | grep -q LOST && fail="carve"; }
[ -z "$fail" ] && { python3 "$S/check_incasm.py" 2>/dev/null | grep -q "^  0 missing, 0 orphaned" || fail="INCASM"; }
[ -z "$fail" ] && { over=$(python3 "$S/size_check.py" "$src" 2>/dev/null | grep -c "(+")
  [ "$over" = 0 ] || fail="size: $over longer"; }

if [ -n "$fail" ]; then
  echo "  FAIL $(basename "$src") ($fail)"
  [ "${KEEP:-0}" = 1 ] || bash "$S/safe_reset.sh" >/dev/null 2>&1
  exit 1
fi

bash tools/check_shared_branch.sh >/dev/null 2>&1 || { echo "  SCRUB FAIL"; exit 1; }
git add -A src asm
before=$(git rev-parse HEAD)
git -c user.name="SensanaMMZ" \
    -c user.email="305674455+SensanaMMZ@users.noreply.github.com" \
    commit -q -m "Match $(echo $fns | wc -w) stub(s) in $(basename "$src" .c)" >/dev/null 2>&1
[ "$(git rev-parse HEAD)" = "$before" ] && { echo "  FAIL (nothing committed)"; exit 1; }
echo "  OK   $(basename "$src") +$(echo $fns | wc -w) stub(s)  $(git rev-parse --short HEAD)"
