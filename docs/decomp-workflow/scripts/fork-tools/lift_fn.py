#!/usr/bin/env python3
import os
"""Lift verified C from a scratch file into a src file, replacing an INCASM.

Carries EVERYTHING in the scratch after the marker line -- forward declarations
included -- which is what plain function-regex extraction kept dropping.
"""
import sys, os, re

def main():
    if len(sys.argv) < 5:
        print('usage: lift_fn.py <scratch.c> <marker> <src.c> <inc-path> [--keep-inc]')
        return 1
    scratch, marker, src, inc = sys.argv[1:5]
    keep = '--keep-inc' in sys.argv
    s = open(scratch, encoding='utf-8').read()
    if marker not in s:
        print('marker not found in scratch:', marker); return 1
    body = s[s.index(marker):].rstrip() + '\n'
    t = open(src, encoding='utf-8').read()
    line = 'INCASM("%s");\n' % inc
    if line not in t:
        print('INCASM line not found in', src); return 1
    t = t.replace(line, body if not keep else body + '\n' + line)
    open(src, 'w', encoding='utf-8', newline='\n').write(t)
    if not keep and os.path.exists(inc):
        os.remove(inc)
    print('lifted into %s (%d bytes of C); inc %s' % (src, len(body), 'removed' if not keep else 'kept'))
    return 0

sys.exit(main())
