#!/usr/bin/env python3
"""Emit `<fn>:<addr>` specs for every C function in a ported file that carries a
`// 0x........` address comment. Feeds verify_calls.py."""
import re, sys
lines = open(sys.argv[1], encoding='utf-8', errors='replace').readlines()
out = []
for i, l in enumerate(lines):
    m = re.match(r'^\s*//\s*0x([0-9A-Fa-f]{8})\s*$', l)
    if not m:
        continue
    for j in range(i + 1, min(i + 8, len(lines))):
        n = lines[j].strip()
        if not n or n.startswith('//'):
            continue
        d = re.match(r'^[A-Za-z_][\w \*]*?\b(\w+)\s*\([^;]*$', n)
        if d and n.rstrip().endswith(('{', ')')):
            out.append('%s:%s' % (d.group(1), m.group(1)))
        break
print(' '.join(out))
