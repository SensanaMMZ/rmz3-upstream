#!/usr/bin/env python3
import os
"""Compare a compiled function against the ROM.

Fails loudly on a SIZE MISMATCH. The old ad-hoc comparison used
min(len(ours), len(target)) and therefore reported "diffs=0" for a function that
was several bytes short -- which silently deleted orphan bytes from an .inc and
shifted the whole ROM (see notes/backlog-truth.md, seimeran_p1).

usage: probe_fn.py <obj> <symbol> <rom_addr_hex> <size_hex> [reloc_off,...]
"""
import subprocess, sys, os

OBJDUMP = os.environ.get('OBJDUMP', 'arm-none-eabi-objdump')
BL_HI = ('fff7', '80f7', '81f7', 'fef7', 'fdf7', 'fcf7', 'fbf7', 'f0f7',
         'f5f7', 'f2f7', 'eef7', 'b0f7', '95f7', '92f7', '8bf7', '73f7',
         '77f7', '86f7', '67f7', '66f7', '57f7', '65f7', '64f7', 'a5f7',
         'd8f7', 'b7f7', 'bcf7', '9cf7', '7ef7', 'aff7', 'e5f7', 'c3f7',
         'a8f7', '98f7', 'bef7', 'bdf7', '9ef7', 'd0f7', '5cf7', '53f7',
         '75f7', '87f7', '80f0', '43f0', '9ff7', 'a9f7', '84f7', '763f7')

def main():
    obj, sym, addr, size = sys.argv[1:5]
    reloc = set()
    if len(sys.argv) > 5 and sys.argv[5]:
        reloc = {int(x, 0) for x in sys.argv[5].split(',')}
    base, size = int(addr, 16) & 0xFFFFFF, int(size, 16)
    ours = subprocess.run([sys.executable, 'tools/fnbytes.py', obj, sym],
                          capture_output=True, text=True).stdout.strip()
    rom = open('baseimg.gba', 'rb').read()
    tgt = rom[base:base + size].hex()
    ob, tb = len(ours) // 2, len(tgt) // 2
    pad = ''
    if 0 < tb - ob < 4 and (ob + (tb - ob)) % 4 == 0 \
            and set(tgt[ob * 2:]) == {'0'}:
        # The ROM slice runs to the NEXT symbol, so it can include 1-3 bytes of
        # zero alignment padding that the following object's `.align 2, 0`
        # regenerates. Trim it -- but only zero bytes, only up to a 4-boundary.
        # The seimeran orphan was 4 bytes of NONZERO `bx lr`, so it still trips
        # the check below.
        pad = ' (+%dB rom align padding)' % (tb - ob)
        tgt, tb = tgt[:ob * 2], ob
    if ob != tb:
        print('%s: SIZE MISMATCH ours=%dB rom=%dB  (delta %+d) -- NOT a match; '
              'check for orphan bytes after the final pool' % (sym, ob, tb, ob - tb))
        return 1
    d, i, n = [], 0, len(tgt)
    while i < n:
        if ours[i:i+2] != tgt[i:i+2]:
            hw = (i // 2) // 2 * 2
            if ours[hw*2:hw*2+4] in BL_HI:
                i = (hw + 4) * 2; continue
            if hw >= 2 and ours[(hw-2)*2:(hw-2)*2+4] in BL_HI:
                i = (hw + 2) * 2; continue
            if (i // 2) // 4 * 4 in reloc:
                i += 2; continue
            d.append(i // 2)
        i += 2
    print('%s: %dB/%dB diffs=%d %s%s' % (sym, ob, tb, len(d),
          [hex(x) for x in d[:8]] if d else '<< MATCH', pad))
    return 0

sys.exit(main())
