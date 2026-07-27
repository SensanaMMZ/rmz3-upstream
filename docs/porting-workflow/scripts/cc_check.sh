#!/bin/bash
# Compile one upstream .c with the project's REAL CFLAGS.
# -Wimplicit -Wparentheses -Werror are the ones that matter: omitting them made
# implicit declarations invisible warnings locally while the real build errors.
export PATH="/c/devkitPro/devkitARM/bin:$PATH"
A=${RMZ3_FORK}/tools/agbcc
out=$(arm-none-eabi-cpp -I $A -I $A/include -iquote include -nostdinc -undef \
        -std=gnu89 -DMODERN=0 "$1" 2>&1 \
      | $A/bin/agbcc.exe -mthumb-interwork -Wimplicit -Wparentheses -Werror \
        -O2 -fshort-enums -fhex-asm -o /dev/null 2>&1)
if [ -n "$out" ]; then echo "FAIL $1"; echo "$out" | head -4 | sed 's/^/    /'; exit 1; fi

# ASSEMBLE too. Compiling alone cannot see a duplicate symbol -- if a function
# exists both in the C and in an INCASM'd .inc, only the assembler complains
# ("symbol `foo' is already defined"). Four files shipped that way on
# tail-batch-1 and passed every compile-only check.
tmp=$(mktemp -d)
arm-none-eabi-cpp -I $A -I $A/include -iquote include -nostdinc -undef     -std=gnu89 -DMODERN=0 "$1" 2>/dev/null   | $A/bin/agbcc.exe -mthumb-interwork -Wimplicit -Wparentheses -Werror     -O2 -fshort-enums -fhex-asm -o "$tmp/x.s" 2>/dev/null
asout=$(arm-none-eabi-as -mcpu=arm7tdmi -mthumb-interwork -I . "$tmp/x.s"         -o "$tmp/x.o" 2>&1)
rm -rf "$tmp"
if [ -n "$asout" ]; then echo "AS FAIL $1"; echo "$asout" | head -3 | sed 's/^/    /'; exit 1; fi
exit 0
