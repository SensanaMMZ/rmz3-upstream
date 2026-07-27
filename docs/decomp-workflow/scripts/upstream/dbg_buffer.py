#!/usr/bin/env python3
import os
"""Trace fix_buffer_offsets on one file: what each access resolves to and where
it gives up."""
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_buffer_offsets as B  # noqa: E402

src = sys.argv[1]
with open(src, encoding='utf-8', errors='replace') as fh:
    txt = fh.read()

for m in B.ACCESS.finditer(txt):
    var, idx = m.group(1), int(m.group(2), 0)
    ty = B.var_type(txt, var)
    body = B.find_struct(ty, src) if ty else None
    flds = B.fields(body) if body else None
    print('  %-28s var=%-4s type=%-10s struct=%-5s fields=%s'
          % (m.group(0)[:28], var, ty, 'yes' if body else 'NO',
             flds if flds is None else [f[1] for f in flds][:4]))
