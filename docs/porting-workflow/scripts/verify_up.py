#!/usr/bin/env python3
"""Byte-verify functions in an upstream-style .c against the ROM.

upstream/dev cannot be built on this box (see the upstream-build-blockers note),
so a full-ROM sha1 check is unavailable. This compiles one .c with agbcc against
upstream's headers and compares each named function byte-for-byte with baseimg,
masking only the two halfwords of each unrelocated BL and any pool word holding
a relocation. That verifies the code itself; it does NOT verify link order.

usage: verify_up.py <src.c> <fn>:<addr>:<size>[:relocs,..] ...
"""
import re
import subprocess
import sys
import os

AGBCC = os.path.join(os.environ['RMZ3_FORK'], 'tools/agbcc')
CPPFLAGS = ['-I', AGBCC, '-I', AGBCC + '/include', '-iquote', 'include',
            '-nostdinc', '-undef', '-std=gnu89', '-DMODERN=0']


def fnbytes(obj, sym):
    out = subprocess.run(['arm-none-eabi-objdump', '-d', '-j', '.text', obj],
                         capture_output=True, text=True).stdout
    syms = subprocess.run(['arm-none-eabi-objdump', '-t', obj],
                          capture_output=True, text=True).stdout
    m = re.search(r'^([0-9a-f]{8}) .*\bF \.text\t([0-9a-f]{8}) %s$'
                  % re.escape(sym), syms, re.M)
    if not m:
        return None
    start, size = int(m.group(1), 16), int(m.group(2), 16)
    raw = open(obj, 'rb').read()
    # .text offset inside the object
    sec = subprocess.run(['arm-none-eabi-objdump', '-h', obj],
                         capture_output=True, text=True).stdout
    s = re.search(r'\.text\s+([0-9a-f]+)\s+[0-9a-f]+\s+[0-9a-f]+\s+([0-9a-f]+)', sec)
    off = int(s.group(2), 16)
    return raw[off + start:off + start + size].hex()


def sym_offset(obj, sym):
    out = subprocess.run(['arm-none-eabi-objdump', '-t', obj],
                         capture_output=True, text=True).stdout
    m = re.search(r'^([0-9a-f]{8})\s.*\sF\s+\.text\s+[0-9a-f]{8}\s+%s$' % re.escape(sym),
                  out, re.M)
    return int(m.group(1), 16) if m else None


def relocs_for(obj, start, size):
    """Offsets (relative to the function) of words carrying a relocation.

    Hand-listing pool offsets is error-prone and silently under-masks, which
    reads as a real byte difference. objdump knows exactly which words the
    linker will fill in."""
    out = subprocess.run(['arm-none-eabi-objdump', '-r', obj],
                         capture_output=True, text=True).stdout
    hits = set()
    for m in re.finditer(r'^([0-9a-f]{8})\s+R_ARM_\S+', out, re.M):
        off = int(m.group(1), 16)
        if start <= off < start + size:
            hits.add(off - start)
    return hits


def main():
    src = sys.argv[1]
    base = os.path.basename(src).replace('.c', '')
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upobj')
    os.makedirs(tmp, exist_ok=True)
    i = os.path.join(tmp, base + '.i')
    s = os.path.join(tmp, base + '.s')
    o = os.path.join(tmp, base + '.o')
    # NOT a CRLF hazard despite text mode: subprocess writes raw bytes
    # straight to the file descriptor, bypassing Python's newline
    # translation. Verified. Leave as-is.
    with open(i, 'w') as f:
        r = subprocess.run(['arm-none-eabi-cpp'] + CPPFLAGS + [src],
                           stdout=f, stderr=subprocess.PIPE)
    if r.returncode:
        print('CPP FAIL %s: %s' % (src, r.stderr.decode()[:200]))
        return 1
    with open(i) as f:
        # Use the project's REAL CFLAGS. Omitting -Wimplicit/-Werror made
        # implicit declarations invisible warnings here while the actual build
        # treats them as errors -- every port branch byte-verified green and
        # then failed CI.
        r = subprocess.run([AGBCC + '/bin/agbcc.exe', '-mthumb-interwork',
                            '-Wimplicit', '-Wparentheses', '-Werror', '-O2',
                            '-fshort-enums', '-fhex-asm', '-o', s], stdin=f,
                           capture_output=True)
    if r.returncode:
        print('AGBCC FAIL %s: %s' % (src, r.stderr.decode()[:300]))
        return 1
    r = subprocess.run(['arm-none-eabi-as', '-mcpu=arm7tdmi', '-mthumb-interwork',
                        '-I', '.', s, '-o', o], capture_output=True)
    if r.returncode:
        print('AS FAIL %s: %s' % (src, r.stderr.decode()[:300]))
        return 1

    rom = open('baseimg.gba', 'rb').read()
    bad = 0
    for spec in sys.argv[2:]:
        parts = spec.split(':')
        fn, addr, size = parts[0], int(parts[1], 16) & 0xFFFFFF, int(parts[2], 16)
        relocs = {int(x, 0) for x in parts[3].split(',')} if len(parts) > 3 and parts[3] else set()
        sym_off = sym_offset(o, fn)
        if sym_off is not None:
            relocs |= relocs_for(o, sym_off, size)
        import os as _os
        if _os.environ.get('VDBG'): print('   dbg %s sym_off=%s relocs=%s'%(fn,sym_off,sorted(hex(r) for r in relocs)))
        ours = fnbytes(o, fn)
        if ours is None:
            print('%-22s NO SYMBOL' % fn); bad += 1; continue
        tgt = rom[addr:addr + size].hex()
        pad = ''
        ob, tb = len(ours) // 2, len(tgt) // 2
        if 0 < tb - ob < 4 and (ob + (tb - ob)) % 4 == 0 and set(tgt[ob * 2:]) == {'0'}:
            # slice ran to the next symbol and swept up the following object's
            # `.align 2, 0` padding; only ever zero bytes, only up to a 4-boundary
            pad = ' (+%dB align pad)' % (tb - ob)
            tgt = tgt[:ob * 2]
        if len(ours) != len(tgt):
            print('%-22s SIZE %dB vs rom %dB' % (fn, len(ours)//2, len(tgt)//2))
            bad += 1; continue
        diffs = []
        k = 0
        while k < len(tgt) // 2:
            if ours[k*2:k*2+2] != tgt[k*2:k*2+2]:
                hw = k // 2 * 2
                lo = ours[hw*2:hw*2+4]
                # unrelocated BL pair shows as fff7 feff in our object
                if lo == 'fff7' or (hw >= 2 and ours[(hw-2)*2:(hw-2)*2+4] == 'fff7'):
                    k = hw + 4; continue
                if k // 4 * 4 in relocs:
                    k += 1; continue
                diffs.append(k)
            k += 1
        print('%-22s %3dB  %s%s' % (fn, len(tgt)//2,
                                    'MATCH' if not diffs else 'diffs=%d %s'
                                    % (len(diffs), [hex(d) for d in diffs[:6]]), pad))
        if diffs:
            bad += 1
    return 1 if bad else 0


sys.exit(main())
