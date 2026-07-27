#!/usr/bin/env python3
import os
"""List every positional field rename fix_struct_fields would apply, so the
table can be eyeballed before it rewrites anything."""
import glob
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_struct_fields as F  # noqa: E402

pairs, upnames, skipped = [], set(), 0
for h in sorted(p.replace('\\', '/')
                for p in glob.glob('include/**/*.h', recursive=True)):
    with open(h, encoding='utf-8', errors='replace') as fh:
        up = fh.read()
    r = subprocess.run(['git', 'show', 'main:' + h], capture_output=True)
    if r.returncode:
        continue
    fk = r.stdout.decode('utf-8', errors='replace')
    us, fs = F.structs(up), F.structs(fk)
    for n, ufl in us.items():
        upnames.update(ufl)
        ffl = fs.get(n)
        if ffl is None:
            continue
        if len(ffl) != len(ufl):
            skipped += 1
            continue
        for a, b in zip(ffl, ufl):
            if a != b and '<anon>' not in (a, b):
                pairs.append((n, a, b))

print('%d rename(s), %d struct(s) skipped on count mismatch'
      % (len(pairs), skipped))
for n, a, b in pairs[:40]:
    print('   %-18s %-26s -> %-26s %s'
          % (n, a, b, 'AMBIGUOUS' if a in upnames else ''))
