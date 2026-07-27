#!/bin/bash
# Port one inc's worth of functions from the fork onto current upstream/dev.
#
#   port_cluster.sh <asm/path/file.inc> <fn> [<fn> ...]
#
# Branches from upstream/dev (never rebases an old branch -- dev keeps
# decompiling, so a stale branch's carve no longer lines up), carves the inc,
# lifts the C bodies from the fork's main, runs the fixer chain, and gates on:
#
#   compile + assemble  (assembling catches a symbol defined twice)
#   BL targets          (a call to the wrong existing function is byte-identical)
#   carve               (no function lost in the split)
#   INCASM              (every include resolves, nothing orphaned)
#
# Anything short of all four rolls back. CI still has to confirm the ROM --
# a function that matches in the fork can be a different SIZE once lifted into
# another file, and only the link sees that.
set -u
cd "${RMZ3_WT:?set RMZ3_WT to the upstream worktree}"
export PATH="/c/devkitPro/devkitARM/bin:$PATH"
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
FM=${RMZ3_FORK}/build/rmz3/rmz3.map

inc="$1"; shift
fns="$*"
# Include the inc's DIRECTORY in the branch name. Basenames are not unique
# across asm/ -- asm/boss/baby_elf.inc and asm/projectile/baby_elf.inc are
# different files, and both mapping to `port/baby_elf` meant porting the boss
# one did `checkout -B port/baby_elf upstream/dev` and silently discarded the
# already-CI-verified projectile commit. Same collision class as the earlier
# `ci/<basename>` one; fixing it there did not fix it here.
rel="${inc#asm/}"; name="port/$(dirname "$rel")-$(basename "${rel%.inc}")"
# NAME= overrides the branch, so the same inc can be ported several times with
# different function subsets -- needed to isolate which function in a cluster is
# the one that overflows the ROM, since no local check can see it.
name="${NAME:-$name}"

git diff --quiet || bash "$S/safe_reset.sh" >/dev/null 2>&1
rm -f nul 2>/dev/null
git checkout -q -B "$name" upstream/dev 2>/dev/null
[ "$(git rev-parse --abbrev-ref HEAD)" = "$name" ] || { echo "  ABORT: checkout"; exit 1; }

# Find the .c that INCASMs this inc, rather than assuming the paths mirror.
# They often do not: `asm/boss/blazin_i.inc` is one carved piece of
# `src/boss/blazin.c`, and deriving `src/boss/blazin_i.c` just reports
# "no upstream .c" for every already-split file.
#
# This MUST run after the reset+checkout above. Resolving it first reads a tree
# left dirty by a previous run -- one where this very INCASM had already been
# carved out -- so the grep finds nothing and the port aborts with
# "no src/boss/blazin_k.c" on a file that exists and is fine.
src=$(grep -rl "INCASM(\"$inc\")" src --include=*.c 2>/dev/null | head -1)
if [ -z "$src" ]; then
  src="src/${inc#asm/}"; src="${src%.inc}.c"
fi
[ -f "$src" ] || { echo "  ABORT: no $src"; exit 1; }

# Keep stderr: it reports when a body came from a file other than the mirrored
# path, and the abort reason. Discarding it is what hid the 6 carve failures.
python3 "$S/port_to_upstream.py" "$inc" "$src" "$src" $fns >/dev/null 2>>"$S/port_err.log" || {
  echo "  ABORT: carve failed ($(tail -1 "$S/port_err.log"))"
  bash "$S/safe_reset.sh" >/dev/null 2>&1; exit 1; }

# A fixer that dies on a SyntaxError must not pass silently. Every pass had
# its stderr sent to /dev/null, so when a bad edit left fix_field_offsets
# unparseable it simply stopped doing anything -- and the clusters that needed
# it failed with the very errors it exists to fix, looking like new problems.
: > "$S/fix_err.log"
python3 "$S/import_struct.py"      "$src" 2>>"$S/fix_err.log" | grep -v "no fork definition"
# Offset mappers BEFORE to_flat. The fork distinguishes entity work
# ((p->s).work, 0x10) from a kind-struct's own work (p->work, 0xB4); to_flat
# collapses both to `p->work`, after which the mapper cannot tell them apart
# and rewrote entity stores to buffer[] at 0xB4 (+8 bytes, caught by the
# size gate on projectile/tretista). Before to_flat the spellings are
# unambiguous: `p->work` can only be the kind-struct's own field.
python3 "$S/fix_buffer_offsets.py" "$src" >/dev/null 2>>"$S/fix_err.log"
python3 "$S/fix_field_offsets.py"  "$src" $fns >/dev/null 2>>"$S/fix_err.log"
python3 "$S/to_flat.py"            "$src" >/dev/null 2>>"$S/fix_err.log"
python3 "$S/align_protos.py"       "$src" >/dev/null 2>>"$S/fix_err.log"
python3 "$S/apply_map_renames.py" "$FM" "$S/upstream.map" "$src" >/dev/null 2>>"$S/fix_err.log"
# fix_return_type must run BEFORE the field mappers. It replaces upstream's
# placeholder signature for an INCASM'd function (`u32 f(void* p)`) with the
# fork's real one (`bool8 f(struct Boss* p)`). Running it last meant every
# mapper still saw `void* p`, could not resolve the type, and left the body
# untouched -- reported as an unresolved access rather than a stale signature.
python3 "$S/fix_return_type.py"    "$src" $fns >/dev/null 2>>"$S/fix_err.log"
python3 "$S/fix_specific.py"       "$src" >/dev/null 2>>"$S/fix_err.log"
python3 "$S/fix_common.py"         "$src" >/dev/null 2>>"$S/fix_err.log"
python3 "$S/fix_struct_fields.py"  "$src" $fns >/dev/null 2>>"$S/fix_err.log"
python3 "$S/fix_nested_access.py"  "$src" >/dev/null 2>>"$S/fix_err.log"
python3 "$S/fix_macro_names.py"    "$src" >/dev/null 2>>"$S/fix_err.log"
python3 "$S/fix_includes.py"       "$src" >/dev/null 2>>"$S/fix_err.log"
python3 "$S/fix_calls.py"          "$src" >/dev/null 2>>"$S/fix_err.log"
python3 "$S/fix_init_macro.py"     "$src" >/dev/null 2>>"$S/fix_err.log"
python3 "$S/fix_arg_casts.py"      "$src" >/dev/null 2>>"$S/fix_err.log"

fail=""
if grep -q "Traceback\|SyntaxError" "$S/fix_err.log" 2>/dev/null; then
  echo "  FAIL $(basename "$src") (fixer crashed: $(grep -m1 "Error" "$S/fix_err.log"))"
  [ "${KEEP:-0}" = 1 ] || bash "$S/safe_reset.sh" >/dev/null 2>&1
  exit 1
fi
# Keep the compiler diagnostics. Rolling back and printing only "compile" threw
# away the one thing needed to classify the failure, so every triage pass had to
# re-run the whole port just to see the error again.
bash "$S/cc_check.sh" "$src" > "$S/cc_out.txt" 2>&1 || {
  fail="compile"
  { echo "### $name ($src)"; head -25 "$S/cc_out.txt"; } >> "$S/fail_err.log"; }
[ -z "$fail" ] && { v=$(python3 "$S/verify_calls.py" "$src" 2>/dev/null | tail -1)
  case "$v" in *", 0 wrong") ;; *) fail="BL targets" ;; esac; }
[ -z "$fail" ] && { python3 "$S/check_carve.py" "$name" 2>/dev/null | grep -q LOST && fail="carve"; }
[ -z "$fail" ] && { python3 "$S/check_incasm.py" 2>/dev/null | grep -q "^  0 missing, 0 orphaned" || fail="INCASM"; }
# SIZE. A function that byte-matches in the fork can assemble LONGER once lifted
# into another file (literal pool placement), and every check above still passes
# -- compile, assemble, BL targets and carve are all blind to length. It only
# surfaces at the link, as `region 'rom' overflowed by N bytes`. Two clusters
# burned a CI round-trip on exactly this; the byte counts matched the overflow
# exactly, so this check is what should have run first.
#
# Gate on POSITIVE deltas only. A negative delta means the map boundary used as
# the "rom" size spans more than the function -- it happens whenever the next
# symbol is absent from the map, which is most of them here. Failing on `wrong
# size != 0` rejected a correct blazin port over two -102/-1716 readings.
[ -z "$fail" ] && { over=$(python3 "$S/size_check.py" "$src" 2>/dev/null | grep -c "(+")
  [ "$over" = 0 ] || fail="size: $over function(s) longer than the original"; }

if [ -n "$fail" ]; then
  echo "  FAIL $(basename "$src") ($fail)"
  # KEEP=1 leaves the broken tree in place so the failure can be inspected.
  [ "${KEEP:-0}" = 1 ] || bash "$S/safe_reset.sh" >/dev/null 2>&1
  exit 1
fi

bash tools/check_shared_branch.sh >/dev/null 2>&1 || { echo "  SCRUB FAIL"; exit 1; }
git add -A src asm
before=$(git rev-parse HEAD)
git -c user.name="SensanaMMZ" \
    -c user.email="305674455+SensanaMMZ@users.noreply.github.com" \
    commit -q -m "Match $(echo $fns | wc -w) function(s) in $(basename "$src" .c)" >/dev/null 2>&1
[ "$(git rev-parse HEAD)" = "$before" ] && { echo "  FAIL $(basename "$src") (nothing committed)"; exit 1; }
echo "  OK   $(basename "$src") +$(echo $fns | wc -w) fn  $(git rev-parse --short HEAD)"
