#!/usr/bin/env python3
"""Functions upstream/dev has genuinely DECOMPILED -- real C, not a shell.

A plain "is there a definition with this name" test is wrong here and nearly got
five valid PRs closed. Upstream keeps three kinds of placeholder that look like
C definitions but are still assembly:

    NAKED u8 FUN_080e964c(...) { ... }                  raw asm in a C wrapper
    NAKED static void unused_x(void) { INCCODE("..."); } ditto, via INCCODE
    NON_MATCH void FlushOAM(void) { ... }                C that does NOT match

A PR replacing any of those with a real matching body is still worth having.
Only a definition with none of those markers counts as done.
"""
import re
import subprocess
import sys

files = subprocess.run(['git', 'ls-tree', '-r', '--name-only', 'upstream/dev'],
                       capture_output=True, text=True).stdout.split('\n')
srcs = [f for f in files if f.endswith('.c')]
blob = subprocess.run(['git', 'cat-file', '--batch'],
                      input='\n'.join('upstream/dev:%s' % f for f in srcs).encode(),
                      capture_output=True).stdout

DEF = re.compile(r'^(?P<mods>(?:static\s+|NAKED\s+|NON_MATCH\s+|ALIGNED\([^)]*\)\s+)*)'
                 r'[A-Za-z_][\w \*]*?\b(?P<name>\w+)\s*\([^;)]*\)\s*\{(?P<rest>.*)$',
                 re.M)

done, shell = set(), set()
pos, idx = 0, 0
while pos < len(blob) and idx < len(srcs):
    nl = blob.find(b'\n', pos)
    if nl < 0:
        break
    h = blob[pos:nl].split()
    if len(h) < 3:
        pos, idx = nl + 1, idx + 1
        continue
    n = int(h[2])
    txt = blob[nl + 1:nl + 1 + n].decode('utf-8', 'replace')
    pos, idx = nl + 1 + n + 1, idx + 1
    for m in DEF.finditer(txt):
        name, mods, rest = m.group('name'), m.group('mods'), m.group('rest')
        if 'NAKED' in mods or 'NON_MATCH' in mods or 'INCCODE' in rest:
            shell.add(name)
        else:
            done.add(name)
done -= shell
if len(sys.argv) > 1 and sys.argv[1] == '--dump':
    print('\n'.join(sorted(done)))
else:
    print('upstream/dev: %d genuinely decompiled, %d still asm shells'
          % (len(done), len(shell)))
