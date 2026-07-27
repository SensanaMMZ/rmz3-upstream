#!/bin/bash
# Generate one preprocessed context file for decomp.me / cexplore scratches.
#
# Modeled on tmc's genctx.sh. Every header in include/ is concatenated and
# run through the preprocessor at the matching configuration (MODERN=0), so
# a scratch gets the same struct layouts and macros the build sees. Paste
# build/ctx.c into the scratch's context pane (or feed it to m2c).
#
# Usage: tools/genctx.sh [extra -D/-I flags...]
set -eu
cd "$(dirname "$0")/.."
mkdir -p build
{
  echo '#include "global.h"'
  find include -name '*.h' -print | LC_ALL=C sort \
    | sed 's|^include/||; s|.*|#include "&"|'
} | gcc -E -P -x c -nostdinc -undef -Iinclude -Itools/agbcc/include \
      -DMODERN=0 "$@" - > build/ctx.c
echo "$(wc -l < build/ctx.c) lines -> build/ctx.c"
