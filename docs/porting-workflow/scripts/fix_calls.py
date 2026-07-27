#!/usr/bin/env python3
"""Correct wrong BL targets using the ROM as the source of truth.

`apply_map_renames.py` translates fork spellings to upstream ones. That is right
for freshly ported code, but WRONG for a branch already written against upstream
names -- re-applying the AllocEntityFirst/AllocEntityLast swap there flips a
correct call into an incorrect one. Both names exist, so it still compiles,
links, and byte-verifies; the only evidence is one wrong byte in the ROM.

So don't reason about which spelling the source "came from". Ask the ROM: decode
the BL at the call site's ROM address, look up which symbol actually lives at
that target, and make the source say that.

    verify_calls.py  reports    "AllocEntityFirst is 0x08006F5C, rom calls 0x08006F90 == AllocEntityLast"
    fix_calls.py     rewrites   AllocEntityFirst( -> AllocEntityLast(   in that function

usage: fix_calls.py <file.c> ...
"""
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LINE = re.compile(r'^(\S+)\s+(\S+)\s+WRONG: is 0x[0-9A-F]+, rom calls '
                  r'0x[0-9A-F]+\s+==\s+(\S+)$')
DEF = re.compile(r'^[A-Za-z_][\w \*]*?\b(?P<name>\w+)\s*\([^;)]*\)\s*\{')


def func_range(lines, name):
    for i, l in enumerate(lines):
        m = DEF.match(l)
        if m and m.group('name') == name:
            depth, j = 0, i
            while j < len(lines):
                depth += lines[j].count('{') - lines[j].count('}')
                if depth <= 0 and j > i:
                    break
                j += 1
            return i, j
    return None


def main():
    total = 0
    for path in sys.argv[1:]:
        for _ in range(4):
            out = subprocess.run(
                [sys.executable, os.path.join(HERE, 'verify_calls.py'), path],
                capture_output=True, text=True).stdout
            fixes = []
            for line in out.split('\n'):
                m = LINE.match(line.strip())
                if m:
                    fixes.append(m.groups())      # (caller, wrong, right)
            if not fixes:
                break
            lines = io.open(path, encoding='utf-8', newline='').read().split('\n')
            done = 0
            for caller, wrong, right in fixes:
                r = func_range(lines, caller)
                if not r:
                    print('  %s: no source for %s' % (path, caller))
                    continue
                a, b = r
                for k in range(a, min(b + 1, len(lines))):
                    new = re.sub(r'\b%s\s*\(' % re.escape(wrong),
                                 right + '(', lines[k])
                    if new != lines[k]:
                        lines[k] = new
                        done += 1
                        print('  %-30s %s: %s -> %s'
                              % (os.path.basename(path), caller, wrong, right))
            if not done:
                break
            io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
            total += done
    print('corrected %d call(s)' % total)
    return 0


sys.exit(main())
