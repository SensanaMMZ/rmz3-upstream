#!/usr/bin/env python3
import os
"""Preview the value-matched macro rename table before it rewrites anything."""
import glob
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_macro_names as FM  # noqa: E402

ren = {}
for h in sorted(x.replace('\\', '/')
                for x in glob.glob('include/**/*.h', recursive=True)):
    with open(h, encoding='utf-8', errors='replace') as fh:
        up = FM.defines(fh.read())
    r = subprocess.run(['git', 'show', 'main:' + h], capture_output=True)
    if r.returncode:
        continue
    fk = FM.defines(r.stdout.decode('utf-8', errors='replace'))
    for val, fn in fk.items():
        un = up.get(val)
        if not un or len(un) != 1 or len(fn) != 1:
            continue
        if fn[0] != un[0]:
            ren[fn[0]] = un[0]

print('%d pair(s); sample:' % len(ren))
for k, v in list(ren.items())[:12]:
    print('  %-32s -> %s' % (k, v))
print('  METATILE_SOFT_PLATFORM ->', ren.get('METATILE_SOFT_PLATFORM'))
