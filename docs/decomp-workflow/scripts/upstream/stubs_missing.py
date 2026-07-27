#!/usr/bin/env python3
"""Which of the 189 found stubs are NOT defined as C on a given branch.

Checked by CONTENT: a stub counts as shipped only if the branch's .c actually
defines it with a body. Ancestry checks lie here because the PR branch was
assembled by cherry-pick (new commit ids), and commit-message sums lie because
one cluster committed without rewriting its .c (bee_server).

    stubs_missing.py <branch>
"""
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
branch = sys.argv[1]

missing, shipped = [], 0
for ln in io.open(os.path.join(HERE, 'stubs.txt'), encoding='utf-8'):
    inc, fn, kind = ln.strip().split('\t')
    # Find the .c that INCASMs this inc on the branch (or its carved pieces --
    # after a port the marker names <base>_a.inc etc., so match on the base).
    base = os.path.splitext(os.path.basename(inc))[0]
    r = subprocess.run(['git', 'grep', '-l', '-E',
                        r'INCASM\(\"asm/[a-z_]+/%s(_[a-z])?\.inc\"\)' % re.escape(base),
                        branch, '--', 'src'], capture_output=True, text=True)
    defined = False
    for hit in r.stdout.split():
        path = hit.split(':', 1)[1]
        txt = subprocess.run(['git', 'show', '%s:%s' % (branch, path)],
                             capture_output=True).stdout.decode('utf-8', 'replace')
        if re.search(r'^[A-Za-z_][\w \*]*\b%s\s*\([^;{)]*\)\s*\{' % re.escape(fn),
                     txt, re.M):
            defined = True
            break
    if defined:
        shipped += 1
    else:
        missing.append((inc, fn, kind))

print('shipped on %s: %d   missing: %d' % (branch, shipped, len(missing)))
for inc, fn, kind in missing:
    print('  %s\t%s\t%s' % (inc, fn, kind))
