#!/bin/bash
# objdiff match%-gate (harness-roadmap #3): compile every NON_MATCH holdout at
# MODERN=1, run objdiff against the expected object, and rank the holdout
# functions by match% (closest first). One pass over the whole backlog.
#
# Usage: tools/objdiff_rank.sh [limit]   ->  build/objdiff-rank.md
set -u
cd "$(dirname "$0")/.."
export PATH=/c/devkitPro/devkitARM/bin:$PATH
AGBCC=tools/agbcc/bin/agbcc.exe
AS=arm-none-eabi-as
OBJDIFF=tools/objdiff-cli.exe
JT="${CLAUDE_JOB_DIR:-/tmp}/tmp"; mkdir -p "$JT" 2>/dev/null || JT=/tmp
LIMIT="${1:-100000}"
OUT=build/objdiff-rank.md; mkdir -p build

# list NON_MATCH/NAKED functions with a MODERN body, by file
mapfile -t rows < <(git grep -n -E '^(NON_MATCH|NAKED)' -- 'src/*.c' 'src/**/*.c' 2>/dev/null)
declare -A seen
> "$JT/rank.tsv"
n=0
for r in "${rows[@]}"; do
  f="${r%%:*}"; rest="${r#*:}"; txt="${rest#*:}"
  fn=$(echo "$txt" | grep -oE '\b[A-Za-z_][A-Za-z_0-9]*\s*\(' | head -1 | tr -d ' (')
  [ -z "$fn" ] && continue
  key="$f"
  [ -n "${seen[$key]:-}" ] && continue
  seen[$key]=1
  exp="expected/build/rmz3/${f%.c}.o"
  [ -f "$exp" ] || continue
  n=$((n+1)); [ $n -gt $LIMIT ] && break
  s="$JT/r.s"; o="$JT/r.o"; rm -f "$s" "$o"
  cpp -I tools/agbcc -I tools/agbcc/include -iquote include -nostdinc -std=gnu89 -DMODERN=1 "$f" 2>/dev/null \
    | "$AGBCC" -mthumb-interwork -O2 -fshort-enums -fhex-asm -o "$s" 2>/dev/null
  [ -s "$s" ] || { echo -e "ERR\t$f\t(compile)" >> "$JT/rank.tsv"; continue; }
  printf '.text\n\t.align\t2, 0\n' >> "$s"
  "$AS" -mcpu=arm7tdmi -march=armv4t -mthumb -mthumb-interwork "$s" -o "$o" 2>/dev/null || continue
  "$OBJDIFF" diff -1 "$exp" -2 "$o" --format json -o "$JT/r.json" >/dev/null 2>&1 || continue
  # extract each NON_MATCH fn's match% for this file
  python3 - "$JT/r.json" "$f" "$JT/rank.tsv" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); f=sys.argv[2]
w=open(sys.argv[3],'a')
for sym in d['left']['symbols']:
    mp=sym.get('match_percent'); nm=sym.get('name')
    if mp is not None and nm and mp < 100.0:
        w.write("%.2f\t%s\t%s\n" % (mp, f, nm))
PY
done
# build ranked report
{
  echo "# objdiff holdout ranking (closest to matching first)"
  echo
  echo "| match% | function | file |"
  echo "|---|---|---|"
  grep -vP '^ERR' "$JT/rank.tsv" | sort -rn | awk -F'\t' '{printf "| %s | %s | %s |\n",$1,$3,$2}'
} > "$OUT"
echo "ranked $(grep -vcP '^ERR' "$JT/rank.tsv") holdout functions -> $OUT"
head -14 "$OUT"
