#!/usr/bin/env python3
"""Swap AllocEntityFirst <-> AllocEntityLast on lines this branch ADDED.

The fork and upstream disagree: 0x08006f5c is AllocEntityLast in the fork and
AllocEntityFirst upstream, and 0x08006f90 the other way round. Ported code
carries the fork spelling and therefore calls the wrong allocator.

Scoped to added lines only -- pre-existing upstream C already uses the upstream
spelling, and rewriting it would break correct code. The swap must be
simultaneous, hence the placeholder.

usage: swap_alloc.py <file> ...   (files listed by the caller from git diff)
"""
import io
import subprocess
import sys

PLACEHOLDER = '\x00ALLOC\x00'


def added_lines(path):
    d = subprocess.run(['git', 'diff', 'upstream/dev', '--', path],
                       capture_output=True, text=True, errors='replace').stdout
    return {l[1:].rstrip('\r\n') for l in d.split('\n')
            if l.startswith('+') and not l.startswith('+++')}


total = 0
for path in sys.argv[1:]:
    added = added_lines(path)
    lines = io.open(path, encoding='utf-8', newline='').read().split('\n')
    n = 0
    for i, line in enumerate(lines):
        if line.rstrip('\r') not in added:
            continue
        if 'AllocEntityFirst' not in line and 'AllocEntityLast' not in line:
            continue
        new = (line.replace('AllocEntityFirst', PLACEHOLDER)
                   .replace('AllocEntityLast', 'AllocEntityFirst')
                   .replace(PLACEHOLDER, 'AllocEntityLast'))
        if new != line:
            lines[i] = new
            n += 1
    if n:
        io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
        print('  %-44s %d' % (path, n))
        total += n
print('swapped %d call(s)' % total)
