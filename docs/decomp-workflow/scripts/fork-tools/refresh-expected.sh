#!/bin/bash
# Copy current build artifacts into expected/ so that future objdiff comparisons
# treat the current state as the matching baseline.
#
# Usage:
#   tools/refresh-expected.sh                # refresh everything (slow, ~26MB)
#   tools/refresh-expected.sh src/foo/bar.o  # refresh one .o (after a match)
#   tools/refresh-expected.sh src/foo/bar.c  # convenience: same .o, .c form
#
# Run after each commit that ends with a confirmed sha1 match. Without this,
# tools/diff.sh will report spurious diffs for any function you've decompiled
# since the last refresh.

set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
SRC="$REPO/build/rmz3"
DST="$REPO/expected/build/rmz3"

# Sanity: make sure we're refreshing from a matching build.
if [ -f "$REPO/rmz3.sha1" ] && [ -f "$REPO/rmz3.gba" ]; then
  if ! (cd "$REPO" && sha1sum -c rmz3.sha1) >/dev/null 2>&1; then
    echo "refusing to refresh: rmz3.gba does not match rmz3.sha1." >&2
    echo "Build a matching ROM first (\`make\`) before refreshing." >&2
    exit 1
  fi
fi

if [ -z "$1" ]; then
  echo "refreshing entire expected/build/rmz3/ from build/rmz3/ ..."
  mkdir -p "$DST"
  cp -ru "$SRC"/. "$DST"/
  echo "done."
  exit 0
fi

# Single-file refresh. Accept either .o or .c form.
arg="$1"
case "$arg" in
  *.c) rel="${arg%.c}.o" ;;
  *.o) rel="$arg" ;;
  *)   echo "error: argument must end in .c or .o (got: $arg)" >&2; exit 1 ;;
esac
rel="${rel#./}"

srcf="$SRC/$rel"
dstf="$DST/$rel"

if [ ! -f "$srcf" ]; then
  echo "error: $srcf not found." >&2
  exit 1
fi
mkdir -p "$(dirname "$dstf")"
cp "$srcf" "$dstf"
echo "refreshed: $rel"
