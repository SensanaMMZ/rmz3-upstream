#!/usr/bin/env python3
"""Report a function's ROM address and exact byte size from its .inc.

usage: fnsize.py <fn> [<fn> ...]

Sizes in rom_symbols.txt are unreliable (see notes/backlog-truth.md), and so was
this tool's first version, which tried to add up instruction widths from the .inc
text -- it disagreed with reality on 2 of 5 functions.

The .inc carries absolute addresses, so use those instead and never guess:
  * every literal-pool entry is a line `_XXXXXXXX: .4byte ...`, so the end of the
    function is the LAST such address + 4;
  * a function with no pool ends where the next `@ 0x...` address comment starts;
  * a trailing `_XXXXXXXX:` label followed by `.byte` is an ORPHAN (padding or a
    stray `bx lr` with no thumb_func_start). It is NOT part of the function --
    lifting the function must leave those bytes behind, so report them apart.
"""
import glob
import re
import sys

POOL = re.compile(r'^_([0-9A-Fa-f]{8}): \.4byte', re.M)
ORPHAN = re.compile(r'^_([0-9A-Fa-f]{8}):\n(?:[ \t]*\.byte ([^\n]*)\n?)+', re.M)
ADDR = re.compile(r'@ (0x[0-9A-Fa-f]{8})')


def main():
    want = set(sys.argv[1:])
    for f in sorted(glob.glob('asm/**/*.inc', recursive=True)):
        txt = open(f, encoding='utf-8', errors='replace').read()
        parts = re.split(r'\n\s*thumb_func_start\s+(\S+)\n', txt)
        for i in range(1, len(parts), 2):
            if parts[i] not in want:
                continue
            body = parts[i + 1]
            m = ADDR.search(body)
            if not m:
                print('%-24s ?? no address comment' % parts[i])
                continue
            addr = int(m.group(1), 16)

            pools = [int(a, 16) for a in POOL.findall(body)]
            orphan = ORPHAN.search(body)
            # A pool can sit in the MIDDLE of a function (agbcc dumps one after
            # any unconditional branch). If real instructions follow the last
            # pool entry, "last pool + 4" is NOT the end -- FUN_08071470 and the
            # SET_XFLIP spawners all do this.
            tail_is_code = False
            if pools:
                after_pool = body[body.rindex('.4byte'):]
                tail_is_code = bool(re.search(r'^\t[a-z]', after_pool, re.M))
            if pools and not tail_is_code:
                end = max(pools) + 4
                how = 'last pool'
            elif i + 3 < len(parts) and ADDR.search(parts[i + 3]):
                end = int(ADDR.search(parts[i + 3]).group(1), 16)
                how = 'next symbol'
            else:
                print('%-24s %08X  ?? no pool and no next symbol' % (parts[i], addr))
                continue

            note = ''
            if orphan:
                oaddr = int(orphan.group(1), 16)
                if oaddr >= end:
                    n = len(orphan.group(0).split('.byte')[1].split(','))
                    note = '   + ORPHAN %d bytes at %08X (leave in the .inc)' % (n, oaddr)
            print('%-24s %08X  size 0x%X  (%s)%s'
                  % (parts[i], addr, end - addr, how, note))


main()
