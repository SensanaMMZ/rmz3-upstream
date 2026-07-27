#!/usr/bin/env python3
"""Verify a carved .inc set + lifted C tiles its ROM region with no gap/overlap.

The per-function byte probe proves each lifted function is correct but says
nothing about ORDER. A dropped orphan, a mis-sequenced INCASM, or a function
emitted in the wrong slot all still probe green -- a full-ROM build is what
normally catches that, and this branch cannot be built here.

So check the tiling instead: walk the .c in source order and, for each INCASM
and each lifted C function, take its [start, end) ROM extent. Every piece must
begin exactly where the previous one ended. A dropped orphan shows up as a gap;
a misordering shows up as a backwards jump.

usage: verify_layout.py <src.c> <inc-prefix> <fn>:<addr>:<size> ...
"""
import os
import re
import subprocess
import sys


def inc_extent(path):
    """[start, end) of an .inc. ASSEMBLE it to get the true length -- deriving
    the end from the last pool label is wrong whenever the inc ends with code
    after its pool, which under-measures and fakes a gap."""
    txt = open(path, encoding='utf-8', errors='replace').read()
    addrs = [int(m.group(1), 16) & 0xFFFFFF
             for m in re.finditer(r'@ (0x[0-9A-Fa-f]{8})', txt)]
    # Not every function carries an address comment; recover those from the
    # symbol name, or a part made up entirely of such functions looks addressless
    # and the whole layout check bails out.
    addrs += [int(m.group(1), 16) & 0xFFFFFF
              for m in re.finditer(r'^\tthumb_func_start \w*_([0-9a-fA-F]{8})$',
                                   txt, re.M)]
    if not addrs:
        return None
    start = min(addrs)
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upobj')
    os.makedirs(tmp, exist_ok=True)
    o = os.path.join(tmp, os.path.basename(path) + '.o')
    r = subprocess.run(['arm-none-eabi-as', '-mcpu=arm7tdmi', '-mthumb-interwork',
                        '-I', '.', path, '-o', o], capture_output=True)
    if r.returncode:
        print('   !! cannot assemble %s: %s' % (path, r.stderr.decode()[:120]))
        return None
    h = subprocess.run(['arm-none-eabi-objdump', '-h', o],
                       capture_output=True, text=True).stdout
    m = re.search(r'\.text\s+([0-9a-f]+)', h)
    return start, start + int(m.group(1), 16)


def main():
    src, prefix = sys.argv[1], sys.argv[2]
    fns = {}
    for spec in sys.argv[3:]:
        n, a, s = spec.split(':')[:3]
        fns[n] = (int(a, 16) & 0xFFFFFF, int(s, 16))

    text = open(src, encoding='utf-8', errors='replace').read()
    seq = []
    for m in re.finditer(r'INCASM\("([^"]+)"\);|^[A-Za-z_][\w \*]*?\b(\w+)\([^)]*\)\s*\{',
                         text, re.M):
        if m.group(1):
            if m.group(1).startswith(prefix):
                seq.append(('inc', m.group(1)))
        elif m.group(2) in fns:
            seq.append(('fn', m.group(2)))

    if not seq:
        print('%-34s no pieces found' % os.path.basename(src))
        return 1

    pieces = []
    for kind, val in seq:
        if kind == 'inc':
            e = inc_extent(val)
            if e is None:
                print('   !! %s has no address comments' % val)
                return 1
            pieces.append((e[0], e[1], os.path.basename(val)))
        else:
            a, s = fns[val]
            pieces.append((a, a + s, val))

    ok = True
    print('%s' % os.path.basename(src))
    prev_end = None
    for s, e, name in pieces:
        flag = ''
        if prev_end is not None and s != prev_end:
            # a <4-byte forward step is the following object's .align padding
            if 0 < s - prev_end < 4:
                flag = '  (+%dB align)' % (s - prev_end)
            else:
                flag = '  !! expected 0x%06X' % prev_end
                ok = False
        print('   0x%06X..0x%06X  %-44s%s' % (s, e, name, flag))
        prev_end = e
    print('   LAYOUT %s' % ('OK' if ok else 'BROKEN'))
    return 0 if ok else 1


sys.exit(main())
