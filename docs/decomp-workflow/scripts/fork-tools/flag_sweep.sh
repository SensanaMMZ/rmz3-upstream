#!/bin/bash
# Flag archaeology (holdout-playbook 2a): compile ONE TU with each GCC2
# optimization switch appended; report the holdout fn's diff count AND whether
# control (already-matched) fns in the same TU stay matched.
# Usage: tools/flag_sweep.sh <src.c> <holdout_fn> <control_fn> [control_fn2]
cd "$(dirname "$0")/.."; REPO="$PWD"
export PATH=/c/devkitPro/devkitARM/bin:$PATH
AGBCC="$REPO/tools/agbcc/bin/agbcc.exe"
AS="/c/devkitPro/devkitARM/bin/arm-none-eabi-as"
OBJDUMP="/c/devkitPro/devkitARM/bin/arm-none-eabi-objdump"
SRC="$1"; HFN="$2"; C1="$3"; C2="${4:-}"
CPPFLAGS="-I tools/agbcc -I tools/agbcc/include -iquote include -nostdinc -std=gnu89 -DMODERN=1"
BASECF="-mthumb-interwork -Wimplicit -Wparentheses -O2 -fshort-enums -fhex-asm"
ASFLAGS="-mcpu=arm7tdmi -march=armv4t -mthumb -mthumb-interwork -g"
EXP="expected/build/rmz3/${SRC%.c}.o"
mkdir -p build/flagsweep

dis(){ "$OBJDUMP" -d --disassemble="$2" "$1" 2>/dev/null | grep -E "^\s+[0-9a-f]+:" | sed -E 's/^\s+[0-9a-f]+:\s+//; s/[0-9a-f]+ <([^>]*)>/<L>/g; s/f7ff fffe/BL/; s/f[0-9a-f]{3} f[0-9a-f]{3}(\s+bl)/BL\1/'; }
count(){ local o=$1 fn=$2; local c=$(dis "$o" "$fn" | wc -l); local d=$(diff <(dis "$EXP" "$fn") <(dis "$o" "$fn") | grep -cE '^[<>]'); echo "$c/$d"; }

FLAGS=(
  ""                      # baseline
  "-fno-thread-jumps"
  "-fno-cse-follow-jumps"
  "-fno-cse-skip-blocks"
  "-fno-expensive-optimizations"
  "-fno-strength-reduce"
  "-fno-rerun-cse-after-loop"
  "-fno-schedule-insns"
  "-fno-schedule-insns2"
  "-fno-function-cse"
  "-fno-peephole"
  "-fno-caller-saves"
  "-fno-force-mem"
  "-fno-omit-frame-pointer"
  "-fno-defer-pop"
  "-O1"
)
printf "%-32s %-16s %-14s %-14s\n" "flag" "$HFN(n/diff)" "$C1" "${C2:-—}"
for F in "${FLAGS[@]}"; do
  CF="$BASECF $F"
  [ "$F" = "-O1" ] && CF="${BASECF/-O2/-O1}"
  s=build/flagsweep/t.s; o=build/flagsweep/t.o
  rm -f "$s" "$o"
  cpp $CPPFLAGS "$SRC" 2>/dev/null | "$AGBCC" $CF -o "$s" 2>/dev/null
  [ -s "$s" ] || { printf "%-32s COMPILE-FAIL\n" "${F:-<base>}"; continue; }
  printf '.text\n\t.align\t2, 0\n' >> "$s"
  "$AS" $ASFLAGS "$s" -o "$o" 2>/dev/null || { printf "%-32s AS-FAIL\n" "${F:-<base>}"; continue; }
  r1=$(count "$o" "$HFN"); r2=$(count "$o" "$C1"); r3="—"
  [ -n "$C2" ] && r3=$(count "$o" "$C2")
  printf "%-32s %-16s %-14s %-14s\n" "${F:-<base>}" "$r1" "$r2" "$r3"
done
echo "(format: instrs/diff-lines vs expected — want holdout diff DOWN with controls staying at 0)"
