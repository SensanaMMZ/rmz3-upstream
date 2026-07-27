#!/bin/bash
# Re-check notes/objdiff-ranking.md against the REAL build config (MODERN=0).
#
# Two traps this exists to avoid:
#
#  1. objdiff_rank.sh compiles at MODERN=1, and MODERN swaps shared macros --
#     SET_ENTITY_ROUTINE has a different expansion that schedules the routine
#     store against the fn-table load differently. So functions that already
#     match byte-for-byte in the shipped ROM show up in the ranking as 90-97%
#     near-misses. Those are noise, not work.
#
#  2. For a function actually declared NON_MATCH/NAKED, MODERN=0 emits the
#     INCCODE'd assembly verbatim, so "matches expected" is trivially true and
#     says nothing. For those the MODERN=1 match% IS the real signal (it
#     measures how close the reconstructed C body is).
#
# So the verdict depends on which population a function is in, and the report
# labels both.
#
# Usage: tools/verify_rank.sh   ->  notes/rank-verified.md
set -u
cd "$(dirname "$0")/.."
export PATH=/c/devkitPro/devkitARM/bin:$PATH
AGBCC=tools/agbcc/bin/agbcc.exe
OBJ=build/rankobj; mkdir -p "$OBJ" build
OUT=notes/rank-verified.md

norm() {  # mnemonics only: drop addresses and symbolic branch targets
  arm-none-eabi-objdump -d --no-show-raw-insn "$1" \
    | awk -v f="<$2>:" '$0 ~ f,/^$/' | sed 's/^ *[0-9a-f]*:\t//;s/<.*//;s/ *$//'
}

declare -A files
rows=()
while IFS='|' read -r _lead pct fn f _rest; do
  pct=$(echo "$pct" | tr -d ' %'); fn=$(echo "$fn" | tr -d ' '); f=$(echo "$f" | tr -d ' ')
  [ -f "$f" ] || continue
  rows+=("$pct|$fn|$f"); files[$f]=1
done < <(grep -E '^\| *[0-9]+\.[0-9]+%' notes/objdiff-ranking.md)

for f in "${!files[@]}"; do
  o="$OBJ/$(echo "${f%.c}" | tr '/' '_').o"; s="${o%.o}.s"
  [ "$o" -nt "$f" ] && continue          # cached; compiles dominate the runtime
  cpp -I tools/agbcc -I tools/agbcc/include -iquote include -nostdinc -std=gnu89 \
      -DMODERN=0 "$f" 2>/dev/null \
    | "$AGBCC" -mthumb-interwork -O2 -fshort-enums -fhex-asm -o "$s" 2>/dev/null
  [ -s "$s" ] || { echo "compile failed: $f" >&2; continue; }
  printf '.text\n\t.align\t2, 0\n' >> "$s"
  arm-none-eabi-as -mcpu=arm7tdmi -march=armv4t -mthumb -mthumb-interwork "$s" -o "$o" 2>/dev/null
done

noise=0; open=0
{
  echo "# objdiff ranking, re-verified against the real build (MODERN=0)"
  echo
  echo "\`objdiff_rank.sh\` compiles at MODERN=1, which swaps shared macros"
  echo "(\`SET_ENTITY_ROUTINE\`), so its match% is only meaningful for functions"
  echo "that are actually declared \`NON_MATCH\`/\`NAKED\`. Everything else in the"
  echo "ranking is an artifact of the harness, not open work."
  echo
  echo "| rank% | function | file | declared holdout | verdict |"
  echo "|---|---|---|---|---|"
  for r in "${rows[@]}"; do
    pct="${r%%|*}"; rest="${r#*|}"; fn="${rest%%|*}"; f="${rest#*|}"
    o="$OBJ/$(echo "${f%.c}" | tr '/' '_').o"
    exp="expected/build/rmz3/${f%.c}.o"
    if grep -qE "^(NON_MATCH|NAKED)\b.*\b$fn\b" "$f"; then
      echo "| $pct | $fn | $f | yes | **open** -- rank% is the real signal |"
      open=$((open+1)); continue
    fi
    if [ ! -f "$o" ] || [ ! -f "$exp" ]; then
      echo "| $pct | $fn | $f | no | (no object) |"; continue
    fi
    a=$(norm "$o" "$fn"); b=$(norm "$exp" "$fn")
    if [ -z "$a" ]; then
      echo "| $pct | $fn | $f | no | not emitted from C |"; open=$((open+1))
    elif [ "$a" = "$b" ]; then
      echo "| $pct | $fn | $f | no | already matches -- ranking artifact |"; noise=$((noise+1))
    else
      echo "| $pct | $fn | $f | no | **really differs** |"; open=$((open+1))
    fi
  done
} > "$OUT"
echo "ranking artifacts (already matching): $noise    genuinely open: $open"
echo "-> $OUT"
