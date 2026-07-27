#!/usr/bin/env python3
import os
"""Show the qualified (struct, field) rename table and the member-type map that
drives it, to see why a two-level access was not rewritten."""
import glob
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_struct_fields as F  # noqa: E402

headers = sorted(p.replace('\\', '/')
                 for p in glob.glob('include/**/*.h', recursive=True))
all_us, all_fs, up_texts = {}, {}, []
for h in headers:
    with open(h, encoding='utf-8', errors='replace') as fh:
        up = fh.read()
    up_texts.append(up)
    all_us.update(F.structs(up))
for h in subprocess.run(['git', 'ls-tree', '-r', '--name-only', 'main',
                         'include/'], capture_output=True, text=True
                        ).stdout.split():
    if h.endswith('.h'):
        all_fs.update(F.structs(subprocess.run(
            ['git', 'show', 'main:' + h], capture_output=True).stdout
            .decode('utf-8', errors='replace')))

print('Entity in upstream:', 'Entity' in all_us, 'len',
      len(all_us.get('Entity') or []))
print('Entity in fork:    ', 'Entity' in all_fs, 'len',
      len(all_fs.get('Entity') or []))

inv = {v: k for k, v in F.ALIASES.items()}
qualified = {}
for name, ufl in all_us.items():
    ffl = all_fs.get(name) or all_fs.get(inv.get(name))
    if ffl is not None and len(ffl) == len(ufl):
        for a, b in zip(ffl, ufl):
            if a != b:
                qualified[(name, a)] = b

member_type = {}
for up in up_texts:
    for ln in up.splitlines():
        d = re.match(r'\s*(?:struct\s+)?(\w+)\s+(\w+)\s*;', ln)
        if d and d.group(1) in all_us:
            member_type.setdefault(d.group(2), set()).add(d.group(1))

print("qualified[('Entity','hazardAttr')] =",
      qualified.get(('Entity', 'hazardAttr')))
print("member_type['s'] =", member_type.get('s'))
print('qualified entries:', len(qualified))
