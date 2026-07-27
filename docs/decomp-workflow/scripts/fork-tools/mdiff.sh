#!/bin/bash
# Compile ONE source file with agbcc and show the disassembly diff for ONE
# function vs the expected target.
# Usage: tools/mdiff.sh <src.c> <func> [MODERN]   (MODERN defaults to 1)
# NOTE: use MODERN=0 to test a function whose dual-form has been DROPPED (body
# active in the real build). mdiff GUARDS against empty compiles: if the symbol
# is absent from either object (failed compile), it reports FAIL, not a bogus
# empty "0-diff" match.
cd "$(dirname "$0")/.."; REPO="$PWD"
export PATH=/c/devkitPro/devkitARM/bin:$PATH
AGBCC="$REPO/tools/agbcc/bin/agbcc.exe"
AS="/c/devkitPro/devkitARM/bin/arm-none-eabi-as"
OBJDUMP="/c/devkitPro/devkitARM/bin/arm-none-eabi-objdump"
SRC="$1"; FN="$2"; M="${3:-1}"
CPPFLAGS="-I tools/agbcc -I tools/agbcc/include -iquote include -nostdinc -std=gnu89 -DMODERN=$M"
CFLAGS="-mthumb-interwork -Wimplicit -Wparentheses -O2 -fshort-enums -fhex-asm"
ASFLAGS="-mcpu=arm7tdmi -march=armv4t -mthumb -mthumb-interwork -g"
uniq=$(echo "$SRC" | tr '/.' '__')
s="build/sweep/$uniq.s"; o="build/sweep/$uniq.o"; mkdir -p build/sweep
cpp $CPPFLAGS "$SRC" 2>/dev/null | "$AGBCC" $CFLAGS -o "$s" 2>"build/sweep/$uniq.err" || { echo "COMPILE FAIL (see build/sweep/$uniq.err)"; tail -3 "build/sweep/$uniq.err"; exit 1; }
printf '.text\n\t.align\t2, 0\n' >> "$s"
"$AS" $ASFLAGS "$s" -o "$o" 2>>"build/sweep/$uniq.err" || { echo "AS FAIL"; exit 1; }
exp="expected/build/rmz3/${SRC%.c}.o"; [ -f "$exp" ] || exp="build/rmz3/${SRC%.c}.o"
dis(){ "$OBJDUMP" -d --disassemble="$FN" "$1" 2>/dev/null | grep -E "^\s+[0-9a-f]+:" | sed -E 's/^\s+[0-9a-f]+:\s+[0-9a-f ]+\t//; s/[0-9a-f]+ <([^>]*)>/<\1>/g'; }
nc=$(dis "$o" | wc -l); ne=$(dis "$exp" | wc -l)
if [ "$nc" -eq 0 ] || [ "$ne" -eq 0 ]; then
  echo "SYMBOL MISSING: $FN not found (cur=$nc exp=$ne) — compile likely failed, NOT a match"; exit 2
fi
echo "=== $FN (MODERN=$M) : target(<) vs mine(>)  [cur=$nc exp=$ne instrs] ==="
diff <(dis "$exp") <(dis "$o")
