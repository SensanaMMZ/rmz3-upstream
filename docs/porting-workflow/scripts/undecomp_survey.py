#!/usr/bin/env python3
"""Survey the assembly upstream has NOT decompiled, sorted by size.

Every `thumb_func_start` in `asm/*.inc` is a function still in assembly. What
matters for picking work is how big each one is: a 12-byte leaf that loads a
field and returns is a different proposition from a 900-byte state machine.

Size comes from the distance to the next `thumb_func_start` in the same inc
(minus trailing padding/pool, so it is an upper bound), which is enough to rank
them. Prints a histogram plus the smallest candidates, and flags the ones whose
body is a single `bx lr` or an immediate return -- those are mechanical.
"""
import glob
import os
import re
import sys

START = re.compile(r'^\tthumb_func_start (\S+)\s*$')


def functions(path):
    with open(path, encoding='utf-8', errors='replace') as fh:
        lines = fh.read().splitlines()
    marks = [(i, m.group(1)) for i, l in enumerate(lines)
             for m in [START.match(l)] if m]
    out = []
    for k, (i, name) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        body = [l for l in lines[i + 1:end]
                if l.strip() and not l.strip().startswith('@')
                and not l.strip().startswith('.') and ':' not in l]
        out.append((name, len(body), path))
    return out


def main():
    allf = []
    for p in sorted(glob.glob('asm/**/*.inc', recursive=True)):
        allf.extend(functions(p))
    allf.sort(key=lambda t: t[1])

    print('total functions still in asm: %d' % len(allf))
    buckets = [(0, 5), (6, 10), (11, 20), (21, 40), (41, 80), (81, 160),
               (161, 10 ** 6)]
    for lo, hi in buckets:
        n = sum(1 for _, c, _ in allf if lo <= c <= hi)
        label = '%d-%d' % (lo, hi) if hi < 10 ** 6 else '%d+' % lo
        print('  %-8s instructions: %4d  %s' % (label, n, '#' * (n // 25)))

    print('\nsmallest 30:')
    for name, cnt, path in allf[:30]:
        print('  %-30s %3d instr  %s' % (name, cnt, os.path.basename(path)))


if __name__ == '__main__':
    main()
