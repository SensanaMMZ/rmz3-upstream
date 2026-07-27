#!/usr/bin/env python3
"""Count REAL structure-policy violations in a branch.

`(p->s).mode[1]` is only wrong when `p`'s type is FLAT upstream. Enemy, VFX and
Solid are genuinely nested upstream, so nested access on those is correct style
and must not be "fixed" -- a raw grep for `->s.` massively overcounts.

Flat upstream: ONLY file-local typedefs built on COLLISION_OBJECT_HDR
(Childre, PantheonFist, ...). The global struct tags are all nested.

usage: audit_policy.py <ref>
"""
import re
import subprocess
import sys

# NOT Boss/Projectile/Enemy/etc: entity.h defines all of them with OBJECT_HDR,
# which is literally `struct Entity s; struct Body body;`. So `(p->s).mode[3]`
# is the CORRECT spelling for every one of those struct tags, and `Boss` is just
# a typedef of `struct Boss`. Only a file-local typedef built on
# COLLISION_OBJECT_HDR is flat.
FLAT_GLOBAL = set()
ref = sys.argv[1]

files = subprocess.run(['git', 'diff', '--name-only', 'upstream/dev...' + ref,
                        '--', 'src'], capture_output=True, text=True).stdout.split()
total, detail = 0, []
for f in files:
    txt = subprocess.run(['git', 'show', '%s:%s' % (ref, f)],
                         capture_output=True, text=True, errors='replace').stdout
    if not txt:
        continue
    local_flat = set(re.findall(
        r'typedef\s+struct\s*\{[^}]*COLLISION_OBJECT_HDR[^}]*\}\s*(\w+)\s*;',
        txt, re.S))
    flat = FLAT_GLOBAL | local_flat
    lines = txt.split('\n')
    i, n = 0, 0
    while i < len(lines):
        m = re.match(r'^[A-Za-z_][\w \*]*?\b\w+\s*\((.*)\)\s*\{\s*$', lines[i])
        if m:
            pm = re.search(r'(?:struct\s+)?(\w+)\s*\*\s*(\w+)\s*[,)]',
                           m.group(1) + ')')
            if pm and pm.group(1) in flat:
                var, depth, j = pm.group(2), 0, i
                while j < len(lines):
                    depth += lines[j].count('{') - lines[j].count('}')
                    if re.search(r'\b%s->s\b' % re.escape(var), lines[j]):
                        n += 1
                    if depth <= 0 and j > i:
                        break
                    j += 1
                i = j
        i += 1
    if n:
        detail.append((f, n))
        total += n
for f, n in sorted(detail, key=lambda x: -x[1]):
    print('    %-52s %d' % (f, n))
print('  TOTAL %d' % total)
