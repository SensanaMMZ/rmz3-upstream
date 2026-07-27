#!/usr/bin/env python3
import os
"""Show how fix_struct_fields parses StageLayer on each side, to see why the
anon-position guard rejects it."""
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_struct_fields as F  # noqa: E402

h = 'include/overworld_layer.h'
with open(h, encoding='utf-8', errors='replace') as fh:
    up = F.structs(fh.read())
fk = F.structs(subprocess.run(['git', 'show', 'main:' + h],
                              capture_output=True).stdout
               .decode('utf-8', errors='replace'))
a, b = fk.get('StageLayer'), up.get('StageLayer')
print('fork  %d:' % len(a), a)
print('upst  %d:' % len(b), b)
print('anon fork:', [i for i, x in enumerate(a) if x == '<anon>'])
print('anon upst:', [i for i, x in enumerate(b) if x == '<anon>'])
