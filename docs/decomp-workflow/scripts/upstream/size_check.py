#!/usr/bin/env python3
"""Every lifted function must be the SAME SIZE as the assembly it replaced.

This is the gate that was missing. A ported function can compile, assemble, and
have every BL target correct, and still be a few bytes longer than the original
-- literal-pool placement and alignment depend on surrounding code, so a body
that matches in the fork need not match once lifted into a different file. The
only symptom is `region 'rom' overflowed by N bytes` at LINK time, which says
nothing about which function is at fault.

Sizes come from a linker map of a known-good build (`upstream.map`, from any
green CI run): the span from a symbol to the next one is what the ROM allots it.
Compare that against the function's size in the freshly compiled object.

Caveats worth knowing:
  * The next symbol may be data rather than code; the span is still the budget.
  * Trailing alignment padding of up to 3 zero bytes is normal, so a compiled
    size within (span-3, span] passes.
  * Functions with no map entry (static, or newly named) cannot be checked and
    are reported separately rather than silently passing.

usage: size_check.py <file.c> [<file.c> ...]
"""
import bisect
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = os.path.join(HERE, 'upstream.map')
AGBCC = os.path.join(os.environ['RMZ3_FORK'], 'tools/agbcc')


def rom_symbols():
    """name -> ROM address, from the linker map AND upstream's asm annotations.

    The map alone is not enough to SIZE a function: it omits static symbols, so
    the gap to the next map entry can span several functions and a too-large
    body hides inside it. Upstream's incs annotate EVERY function
    (`FUN_08050090: @ 0x08050090`), including statics, so consecutive addresses
    there give exact extents. Merging both gives a boundary set dense enough to
    size against.
    """
    addr = {}
    with open(MAP, encoding='utf-8', errors='replace') as f:
        for line in f:
            m = re.match(r'^\s+0x0([0-9a-f]{7})\s+([A-Za-z_]\w*)\s*$', line)
            if m:
                a = int(m.group(1), 16)
                if 0x8000000 <= a < 0x9000000:
                    addr.setdefault(m.group(2), a)
    files = [f for f in subprocess.run(
        ['git', 'ls-tree', '-r', '--name-only', 'upstream/dev', '--', 'asm'],
        capture_output=True, text=True).stdout.split('\n')
        if f.endswith(('.inc', '.s'))]
    blob = subprocess.run(['git', 'cat-file', '--batch'],
                          input='\n'.join('upstream/dev:%s' % f for f in files).encode(),
                          capture_output=True).stdout
    pos, idx = 0, 0
    while pos < len(blob) and idx < len(files):
        nl = blob.find(b'\n', pos)
        if nl < 0:
            break
        h = blob[pos:nl].split()
        if len(h) < 3:
            pos, idx = nl + 1, idx + 1
            continue
        n = int(h[2])
        txt = blob[nl + 1:nl + 1 + n].decode('utf-8', 'replace')
        pos, idx = nl + 1 + n + 1, idx + 1
        for m in re.finditer(r'^(\w+):\s*@\s*0x([0-9A-Fa-f]{8})\s*$', txt, re.M):
            addr.setdefault(m.group(1), int(m.group(2), 16))
    return addr


def compile_syms(src):
    """name -> size, from the compiled object."""
    tmp = os.path.join(HERE, 'upobj')
    os.makedirs(tmp, exist_ok=True)
    base = os.path.basename(src)[:-2]
    i, s, o = (os.path.join(tmp, base + e) for e in ('.i', '.s', '.o'))
    with open(i, 'w') as f:
        subprocess.run(['arm-none-eabi-cpp', '-I', AGBCC, '-I', AGBCC + '/include',
                        '-iquote', 'include', '-nostdinc', '-undef', '-std=gnu89',
                        '-DMODERN=0', src], stdout=f, stderr=subprocess.DEVNULL)
    with open(i) as f:
        r = subprocess.run([AGBCC + '/bin/agbcc.exe', '-mthumb-interwork',
                            '-Wimplicit', '-Wparentheses', '-Werror', '-O2',
                            '-fshort-enums', '-fhex-asm', '-o', s],
                           stdin=f, capture_output=True)
    if r.returncode:
        return None
    if subprocess.run(['arm-none-eabi-as', '-mcpu=arm7tdmi', '-mthumb-interwork',
                       '-I', '.', s, '-o', o], capture_output=True).returncode:
        return None
    out = subprocess.run(['arm-none-eabi-objdump', '-t', o],
                         capture_output=True, text=True).stdout
    return {m.group(3): int(m.group(2), 16) for m in re.finditer(
        r'^([0-9a-f]{8})\s.*\sF\s+\.text\s+([0-9a-f]{8})\s+(\S+)$', out, re.M)}


def main():
    rom = rom_symbols()
    order = sorted(rom.values())
    bad = unknown = checked = 0
    for src in sys.argv[1:]:
        syms = compile_syms(src)
        if syms is None:
            print('  %s: does not build' % src)
            bad += 1
            continue
        for name, size in sorted(syms.items()):
            # size 0 means the object only REFERENCES the symbol -- the body is
            # still in an INCASM'd .inc. Only functions this file actually
            # defines have a size to compare.
            if size == 0:
                continue
            a = rom.get(name)
            if a is None:
                unknown += 1
                continue
            k = bisect.bisect_right(order, a)
            if k >= len(order):
                continue
            span = order[k] - a
            checked += 1
            if not (span - 4 < size <= span):
                print('  %-26s %-28s rom %3d  built %3d  (%+d)'
                      % (os.path.basename(src), name, span, size, size - span))
                bad += 1
    print('  %d checked, %d wrong size, %d not in the map' % (checked, bad, unknown))
    return 1 if bad else 0


sys.exit(main())
