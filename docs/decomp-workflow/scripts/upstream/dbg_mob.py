#!/usr/bin/env python3
import os
"""Trace fix_field_offsets on mob_npc: does the fork's MobObject parse, and does
the variable resolve to it?"""
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_field_offsets as FO  # noqa: E402
import fix_buffer_offsets as BO  # noqa: E402

FO.SIZES = FO._typedef_sizes()
src = 'src/solid/mob_npc.c'
with open(src, encoding='utf-8', errors='replace') as fh:
    txt = fh.read()

print('var_type(m) =', BO.var_type(txt, 'm'))

r = subprocess.run(['git', 'grep', '-l', '-F', 'struct MobObject {',
                    'main', '--', 'src', 'include'],
                   capture_output=True, text=True)
print('fork files:', r.stdout.split())
for line in r.stdout.splitlines():
    path = line.split(':', 1)[1] if ':' in line else line
    t = subprocess.run(['git', 'show', 'main:' + path], capture_output=True)
    for nm, b in BO._bodies(t.stdout.decode('utf-8', errors='replace')):
        if nm == 'MobObject':
            print('parsed fork MobObject ->', FO.own_fields(b))

up = BO.find_struct('MobObject', src)
print('upstream MobObject ->', FO.own_fields(up) if up else None)
