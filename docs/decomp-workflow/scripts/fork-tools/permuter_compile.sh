#!/bin/bash
# Compile a single C file to a .o exactly the way the rmz3 makefile does
# (cpp | agbcc | as), for decomp-permuter. The agbcc flags are fixed here; any
# extra flags in the argument list (e.g. the -I/-D that import.py forwards) are
# ignored — we only scrape the input .c and the -o output path out of the args.
#
# Works both as the permuter's compile.sh AND as a standalone:
#   tools/permuter_compile.sh [flags...] <input.c> [flags...] -o <output.o>
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DKA="C:/devkitPro/devkitARM"
AGBCC="$REPO/tools/agbcc/bin/agbcc"

INPUT=""
OUTPUT=""
prev=""
for a in "$@"; do
  if [ "$prev" = "-o" ]; then OUTPUT="$a"; prev=""; continue; fi
  case "$a" in
    -o) prev="-o" ;;
    *.c) INPUT="$a" ;;
    *) : ;;  # ignore all other flags
  esac
done
[ -z "$INPUT" ]  && { echo "permuter_compile.sh: no .c input in args: $*" >&2; exit 2; }
[ -z "$OUTPUT" ] && { echo "permuter_compile.sh: no -o output in args: $*" >&2; exit 2; }

SFILE="${OUTPUT%.o}.s"
# -Werror dropped: permuter mutations can introduce benign warnings.
cpp -I "$REPO/tools/agbcc" -I "$REPO/tools/agbcc/include" -iquote "$REPO/include" \
    -nostdinc -std=gnu89 -DMODERN=0 "$INPUT" \
  | "$AGBCC" -mthumb-interwork -Wimplicit -Wparentheses -O2 -fshort-enums -fhex-asm -o "$SFILE"
printf '.text\n\t.align\t2, 0\n' >> "$SFILE"
"$DKA/bin/arm-none-eabi-as" -mcpu=arm7tdmi -march=armv4t -mthumb -mthumb-interwork -g "$SFILE" -o "$OUTPUT"
