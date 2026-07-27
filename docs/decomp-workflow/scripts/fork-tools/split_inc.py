#!/usr/bin/env python3
import os
"""Split an .inc file around a single empty-stub function.

Usage: split_inc.py <inc_path> <fn_name>
Writes <inc_basename>_pre.inc and <inc_basename>_post.inc next to it,
removes the original, and prints the two new paths.
"""
import re
import sys
from pathlib import Path

inc = Path(sys.argv[1])
fn = sys.argv[2]
text = inc.read_text()
lines = text.split("\n")

# find the stub block: thumb_func_start FN ... up through bx lr (and trailing .align if any)
start = None
for i, ln in enumerate(lines):
    if re.match(rf"\s*thumb_func_start\s+{fn}\b", ln):
        start = i
        break
if start is None:
    sys.exit(f"no thumb_func_start {fn}")

# end is just before the next thumb_func_start
end = len(lines)
for j in range(start + 1, len(lines)):
    if re.match(r"\s*thumb_func_start\s+\w", lines[j]):
        end = j
        break

# trim trailing blank lines in pre
pre = lines[:start]
while pre and pre[-1].strip() == "":
    pre.pop()

post = lines[end:]
while post and post[0].strip() == "":
    post.pop(0)

PRELUDE = [
    '\t.include "asm/macros.inc"',
    "",
    "\t.syntax unified",
    "",
    "\t.text",
    "",
]

base = inc.with_suffix("")
pre_p = Path(str(base) + "_pre.inc")
post_p = Path(str(base) + "_post.inc")
pre_p.write_text("\n".join(pre) + "\n")
post_p.write_text("\n".join(PRELUDE + post) + "\n")
inc.unlink()
print(pre_p)
print(post_p)
