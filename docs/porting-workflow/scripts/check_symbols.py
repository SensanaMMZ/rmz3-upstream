#!/usr/bin/env python3
"""Check every symbol a ported file calls actually exists upstream.

WHY THIS EXISTS: the byte probe masks BL targets as relocations, so a call to a
function that does not exist upstream produces byte-IDENTICAL output and only
fails at link time. Ten port branches verified green this way and every one of
them failed CI, because the fork's `UpdateMotionGraphic` is called
`UpdateEntityAnim` upstream (same address, 0x0801765C).

Compiling with the project's real CFLAGS (-Wimplicit -Werror) catches it as an
implicit declaration. This script reports the same thing up front, with the
likely upstream name, so a rename can be applied before the round trip.

usage: check_symbols.py <src.c> [<src.c> ...]
"""
import os
import re
import subprocess
import sys

# Confirmed fork -> upstream renames. Verified by matching ROM addresses.
KNOWN = {
    'UpdateMotionGraphic': 'UpdateEntityAnim',   # 0x0801765C
    'gMission': 'gScore',
    'taskCol': 'renderPrio',
}


def upstream_symbols():
    """Everything upstream declares or defines: headers, C, and asm labels."""
    syms = set()
    out = subprocess.run(['git', 'grep', '-h', '-oE',
                          r'\b[A-Za-z_][A-Za-z0-9_]*\s*\(', 'HEAD', '--', 'include'],
                         capture_output=True).stdout.decode('utf-8', 'replace')
    syms |= {m.rstrip('( \t') for m in out.split('\n') if m}
    out = subprocess.run(['git', 'grep', '-h', '-oE',
                          r'^\tthumb_func_start \S+', 'HEAD', '--', 'asm'],
                         capture_output=True).stdout.decode('utf-8', 'replace')
    syms |= {l.split()[-1] for l in out.split('\n') if l.strip()}
    out = subprocess.run(['git', 'grep', '-h', '-oE',
                          r'^[A-Za-z_][\w \*]*\b[A-Za-z_][A-Za-z0-9_]*\(', 'HEAD', '--', 'src'],
                         capture_output=True).stdout.decode('utf-8', 'replace')
    for l in out.split('\n'):
        m = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\($', l.strip())
        if m:
            syms.add(m.group(1))
    return syms


C_KEYWORDS = {'if', 'for', 'while', 'switch', 'return', 'sizeof', 'do', 'else'}


def main():
    known = upstream_symbols()
    bad = 0
    for src in sys.argv[1:]:
        txt = open(src, encoding='utf-8', errors='replace').read()
        called = {m.group(1) for m in re.finditer(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*\(', txt)}
        called -= C_KEYWORDS
        missing = sorted(n for n in called
                         if n not in known and not n.isupper() and
                         not re.search(r'\b%s\s*\([^;{)]*\)\s*[;{]' % re.escape(n), txt))
        for n in missing:
            hint = KNOWN.get(n)
            print('%-34s %-26s %s' % (os.path.basename(src), n,
                                      '-> ' + hint if hint else 'NOT FOUND upstream'))
            bad += 1
    if not bad:
        print('all called symbols resolve upstream')
    return 1 if bad else 0


sys.exit(main())
