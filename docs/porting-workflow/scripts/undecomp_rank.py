#!/usr/bin/env python3
"""Rank the still-in-assembly functions by EXACT byte size.

The first survey counted source lines, which is meaningless here: half these
bodies are `.byte` blobs whose line count says nothing, and it reported 234
functions as "0 instructions" purely because `.byte` lines start with a dot.

Sizes come from ROM addresses instead. Upstream annotates most definitions with
`name: @ 0x0805F54C`, and the auto-named ones carry the address in the name
(`FUN_0805f52c`). Sorting every known address across the ROM and taking the gap
to the next one gives each function's true length.

Usage: undecomp_rank.py [max_bytes]   (default 64)
"""
import glob
import re
import sys

START = re.compile(r'^\tthumb_func_start (\S+)\s*$')
ADDR = re.compile(r'^(\S+):\s*@\s*0x([0-9A-Fa-f]{8})')
NAMED = re.compile(r'^(?:FUN|nop|sub)_([0-9a-f]{8})$')


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 64
    found = {}                       # addr -> (name, inc)
    for path in sorted(glob.glob('asm/**/*.inc', recursive=True)):
        with open(path, encoding='utf-8', errors='replace') as fh:
            lines = fh.read().splitlines()
        for i, l in enumerate(lines):
            m = START.match(l)
            if not m:
                continue
            name = m.group(1)
            addr = None
            if i + 1 < len(lines):
                a = ADDR.match(lines[i + 1])
                if a and a.group(1) == name:
                    addr = int(a.group(2), 16)
            if addr is None:
                n = NAMED.match(name)
                if n:
                    addr = int(n.group(1), 16)
            if addr is not None:
                found[addr] = (name, path)

    order = sorted(found)
    rows = []
    for k, a in enumerate(order):
        if k + 1 < len(order):
            size = order[k + 1] - a
        else:
            continue
        if 0 < size <= limit:
            rows.append((size, found[a][0], found[a][1], a))
    rows.sort()

    print('functions still in asm with a known address: %d' % len(order))
    print('of those, <= %d bytes: %d\n' % (limit, len(rows)))
    for size, name, path, a in rows[:40]:
        print('  %3d B  %-28s 0x%08X  %s' % (size, name, a, path))


if __name__ == '__main__':
    main()
