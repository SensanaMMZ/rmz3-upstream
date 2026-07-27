#!/usr/bin/env python3
import os
"""Split an .inc file around multiple empty-stub functions.

Usage: split_inc_multi.py <inc_path> <fn1> [<fn2> ...]
Produces <base>_p1.inc, <base>_p2.inc, ..., <base>_pN+1.inc where stubs
go between consecutive parts. Removes the original. Prints all part paths.
"""
import re
import sys
from pathlib import Path

inc = Path(sys.argv[1])
fns = sys.argv[2:]
text = inc.read_text()
lines = text.split("\n")

cuts = []  # list of (stub_start_idx, stub_end_idx_exclusive)
for fn in fns:
    start = None
    for i, ln in enumerate(lines):
        if re.match(rf"\s*thumb_func_start\s+{fn}\b", ln):
            start = i
            break
    if start is None:
        sys.exit(f"no thumb_func_start {fn}")
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"\s*thumb_func_start\s+\w", lines[j]):
            end = j
            break
    cuts.append((start, end))

cuts.sort()

PRELUDE = [
    '\t.include "asm/macros.inc"',
    "",
    "\t.syntax unified",
    "",
    "\t.text",
    "",
]

parts = []
prev = 0
for start, end in cuts:
    parts.append(lines[prev:start])
    prev = end
parts.append(lines[prev:])

# trim trailing blanks
for p in parts:
    while p and p[-1].strip() == "":
        p.pop()

base = inc.with_suffix("")
out = []
for i, p in enumerate(parts):
    suffix = f"_p{i+1}.inc"
    path = Path(str(base) + suffix)
    if i == 0:
        path.write_text("\n".join(p) + "\n")
    else:
        # add prelude
        content = PRELUDE.copy()
        # skip leading blanks in p
        while p and p[0].strip() == "":
            p.pop(0)
        content.extend(p)
        path.write_text("\n".join(content) + "\n")
    out.append(path)

inc.unlink()
for p in out:
    print(p)
