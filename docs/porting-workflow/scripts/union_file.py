#!/usr/bin/env python3
"""Merge one contested source file so NO matched function is lost.

Two PRs porting the same .c independently both re-carve its INCASM boundaries,
so they conflict even when their function sets are disjoint. The fix is to give
the file a single owner -- but a plain revert in the loser throws away real,
byte-verified work (61 functions across 40 files, measured 2026-07-26).

So: take the owner's version, splice in the functions only the loser has, and
then the loser can revert the file with nothing lost.

Splicing is only safe where the owner still has that function as assembly. The
owner's file is a sequence of C bodies and `INCASM("asm/...inc")` lines; a
function the owner lacks is inside one of those incs. This reports what has to
move and where, and writes the merged file when the placement is unambiguous.

usage: union_file.py <file> <owner-ref> <loser-ref> [--write]
"""
import re
import subprocess
import sys


def show(ref, path):
    r = subprocess.run(['git', 'show', '%s:%s' % (ref, path)],
                       capture_output=True, text=True, errors='replace')
    return r.stdout if r.returncode == 0 else None


DEF = re.compile(r'^(?P<sig>(?:static\s+)?(?:NAKED\s+|NON_MATCH\s+)?'
                 r'[A-Za-z_][\w \*]*?\b(?P<name>\w+)\s*\([^;)]*\))\s*\{')


def functions(text):
    """name -> (start, end) line indices of each definition, by brace depth."""
    lines, out = text.split('\n'), {}
    i = 0
    while i < len(lines):
        m = DEF.match(lines[i])
        if m:
            depth, j = 0, i
            while j < len(lines):
                depth += lines[j].count('{') - lines[j].count('}')
                if depth <= 0 and j > i:
                    break
                j += 1
            out[m.group('name')] = (i, j)
            i = j
        i += 1
    return out


def main():
    path, owner, loser = sys.argv[1], sys.argv[2], sys.argv[3]
    write = '--write' in sys.argv
    o, l = show(owner, path), show(loser, path)
    if o is None or l is None:
        print('  %s: missing on one side' % path)
        return 1
    of, lf = functions(o), functions(l)
    extra = [n for n in lf if n not in of]
    if not extra:
        print('  %-44s clean superset, loser can revert' % path)
        return 0

    ol = o.split('\n')
    llines = l.split('\n')
    # Anchor each transplant after the owner's last function that precedes it in
    # the loser's file, so ROM order is preserved.
    order = sorted(lf, key=lambda n: lf[n][0])
    inserts = []
    for n in extra:
        idx = order.index(n)
        prev = next((order[k] for k in range(idx - 1, -1, -1) if order[k] in of), None)
        body = '\n'.join(llines[lf[n][0]:lf[n][1] + 1])
        inserts.append((of[prev][1] + 1 if prev else None, n, body))
    if any(a is None for a, _, _ in inserts):
        print('  %-44s %d extra fn(s), no anchor: %s'
              % (path, len(extra), ' '.join(n for a, n, _ in inserts if a is None)))
        return 2
    print('  %-44s splice %d fn(s): %s'
          % (path, len(extra), ' '.join(sorted(extra))))
    if write:
        for at, _, body in sorted(inserts, key=lambda x: -x[0]):
            ol[at:at] = ['', body]
        open(path, 'w', encoding='utf-8', newline='').write('\n'.join(ol))
    return 0


sys.exit(main())
