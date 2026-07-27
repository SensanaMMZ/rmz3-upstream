#!/bin/bash
# Sweep every NON_MATCH function: compile its file with agbcc + -DMODERN=1
# (activating the MODERN body but keeping the byte-matching agbcc toolchain),
# then count real instruction diffs vs the expected target .o.
# Ranks candidates by closeness so single-cause cracks surface first.
set -o pipefail
cd "$(dirname "$0")/.."; REPO="$PWD"
cd "$REPO"
export PATH=/c/devkitPro/devkitARM/bin:$PATH
AGBCC="$REPO/tools/agbcc/bin/agbcc.exe"
AS="/c/devkitPro/devkitARM/bin/arm-none-eabi-as"
OBJDUMP="/c/devkitPro/devkitARM/bin/arm-none-eabi-objdump"
CPPFLAGS="-I tools/agbcc -I tools/agbcc/include -iquote include -nostdinc -std=gnu89 -DMODERN=1"
CFLAGS="-mthumb-interwork -Wimplicit -Wparentheses -O2 -fshort-enums -fhex-asm"
ASFLAGS="-mcpu=arm7tdmi -march=armv4t -mthumb -mthumb-interwork -g"
OUT="$REPO/build/sweep"; mkdir -p "$OUT"

dis(){ "$OBJDUMP" -d --disassemble="$2" "$1" 2>/dev/null | grep -E "^\s+[0-9a-f]+:" | sed -E 's/^[^\t]*\t[0-9a-f ]+\t//; s/[0-9a-f]+ <[^>]*>/<L>/g'; }

# files that contain NON_MATCH
FILES=$(grep -rl "NON_MATCH" src/ --include=*.c | sort -u)
for f in $FILES; do
  base=$(basename "$f" .c)
  s="$OUT/$base.s"; o="$OUT/$base.o"
  if ! cpp $CPPFLAGS "$f" 2>/dev/null | "$AGBCC" $CFLAGS -o "$s" 2>"$OUT/$base.err"; then
    echo "COMPILE_FAIL  $f"
    continue
  fi
  printf '.text\n\t.align\t2, 0\n' >> "$s"
  if ! "$AS" $ASFLAGS "$s" -o "$o" 2>>"$OUT/$base.err"; then
    echo "ASM_FAIL      $f"
    continue
  fi
  exp="$REPO/expected/build/rmz3/${f%.c}.o"
  [ -f "$exp" ] || exp="$REPO/build/rmz3/${f%.c}.o"
  # each NON_MATCH function in this file
  funcs=$(grep -oE "NON_MATCH[^A-Za-z0-9_]+([A-Za-z_0-9]+ )*[A-Za-z_0-9]+\(" "$f" | sed -E 's/.*[^A-Za-z0-9_]([A-Za-z_0-9]+)\($/\1/')
  for fn in $funcs; do
    dis "$o" "$fn" > "$OUT/cur.txt"
    dis "$exp" "$fn" > "$OUT/exp.txt"
    ci=$(wc -l < "$OUT/cur.txt"); ei=$(wc -l < "$OUT/exp.txt")
    if [ "$ci" -eq 0 ] || [ "$ei" -eq 0 ]; then continue; fi
    d=$(diff "$OUT/exp.txt" "$OUT/cur.txt" | grep -cE "^[<>]")
    printf '%4d  %-28s %-30s (cur=%s exp=%s)\n' "$d" "$fn" "$base" "$ci" "$ei"
  done
done
