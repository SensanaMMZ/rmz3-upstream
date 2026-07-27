#!/usr/bin/env python3
"""Check what fix_nested_access sees: is VFX nested, and does Entity list work?"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_buffer_offsets as BO  # noqa: E402
import fix_struct_fields as FSF  # noqa: E402

src = 'src/vfx/copy_x_reflect_laser.c'
with open(src, encoding='utf-8', errors='replace') as fh:
    txt = fh.read()
print('var_type(p) =', BO.var_type(txt, 'p'))

entity_fields, nested = set(), {}
for h in sorted(p.replace('\\', '/') for p in
                glob.glob('include/**/*.h', recursive=True)) + [src]:
    with open(h, encoding='utf-8', errors='replace') as fh:
        raw = fh.read()
    for nm, body in BO._bodies(FSF.expand_macros(raw)):
        if nm == 'Entity':
            entity_fields.update(FSF.fields(body))
    for nm, body in BO._bodies(raw):
        first = next((l.strip() for l in body.splitlines()
                      if l.strip() and not l.strip().startswith('//')), '')
        if re.match(r'(?:struct\s+)?Entity\s+s\s*;', first):
            nested[nm] = True

print('entity_fields has work?', 'work' in entity_fields,
      '| count', len(entity_fields))
print('sample:', sorted(entity_fields)[:10])
print('nested types:', sorted(nested)[:12])
