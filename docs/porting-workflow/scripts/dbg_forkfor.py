#!/usr/bin/env python3
import os
"""Reproduce fix_field_offsets.fork_for('MobObject') exactly as main() runs it."""
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_field_offsets as FO  # noqa: E402
import fix_buffer_offsets as BO  # noqa: E402

FO.SIZES = FO._typedef_sizes()
ty = 'MobObject'
r = subprocess.run(['git', 'grep', '-l', '-F', 'struct %s {' % ty,
                    'main', '--', 'src', 'include'],
                   capture_output=True, text=True)
print('rc', r.returncode, 'out', repr(r.stdout))
for line in r.stdout.splitlines():
    path = line.split(':', 1)[1] if ':' in line else line
    print('path', repr(path))
    t = subprocess.run(['git', 'show', 'main:' + path], capture_output=True)
    print('  show rc', t.returncode, 'len', len(t.stdout))
    names = [nm for nm, _ in
             BO._bodies(t.stdout.decode('utf-8', errors='replace'))]
    print('  bodies:', names[:12])
    for nm, b in BO._bodies(t.stdout.decode('utf-8', errors='replace')):
        if nm == ty:
            print('  own_fields ->', FO.own_fields(b))
            break
