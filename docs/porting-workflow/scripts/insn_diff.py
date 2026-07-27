#!/usr/bin/env python3
"""Normalized instruction diff: ROM asm (from an .inc) vs compiler output.

Normalizes the cosmetic differences between the disassembler's spelling and
agbcc's (adds/add, movs/mov, decimal/hex immediates, label names) so the diff
shows only REAL codegen divergence.

    insn_diff.py <ref:incpath> <fn> <built.s>
"""
import re
import subprocess
import sys


def norm(line):
    s = line.split('@')[0].strip()
    if not s or s.startswith('.') or s.endswith(':') or s.startswith('thumb_func'):
        return None
    s = re.sub(r'\s+', ' ', s)
    # Unified mnemonics: agbcc writes add/mov/lsl..., the disassembly adds/movs.
    s = re.sub(r'^(add|sub|mov|lsl|lsr|asr|mul|and|orr|eor|bic|neg|mvn)s ',
               r'\1 ', s)
    # Immediates to decimal.
    def dec(m):
        return '#' + str(int(m.group(1), 16))
    s = re.sub(r'#0x([0-9a-fA-F]+)', dec, s)
    # Local labels / literal loads are position-dependent names; canonicalise.
    s = re.sub(r'(\.L\w+|_[0-9A-F]{8})(\+0x[0-9a-f]+)?', 'LBL', s)
    # `add r1, r1, #34` vs `adds r1, #0x22` (2-op vs 3-op same-reg form)
    m = re.match(r'add (r\d+), (r\d+), #(\d+)$', s)
    if m and m.group(1) == m.group(2):
        s = 'add %s, #%s' % (m.group(1), m.group(3))
    return s


def rom(ref, fn):
    inc = subprocess.run(['git', 'show', ref], capture_output=True
                         ).stdout.decode('utf-8', 'replace')
    out, on = [], False
    for ln in inc.splitlines():
        if ln.strip() == 'thumb_func_start ' + fn:
            on = True
            continue
        if on and ln.strip() == 'thumb_func_end ' + fn:
            break
        if on:
            n = norm(ln)
            if n:
                out.append(n)
    return out


def built(path, fn):
    txt = open(path, encoding='utf-8', errors='replace').read()
    m = re.search(r'^%s:\n(.*?)\.size\s+%s' % (re.escape(fn), re.escape(fn)),
                  txt, re.S | re.M)
    if not m:
        return []
    out = []
    for ln in m.group(1).splitlines():
        n = norm(ln)
        if n:
            out.append(n)
    return out


def main():
    ref, fn, s = sys.argv[1], sys.argv[2], sys.argv[3]
    a, b = rom(ref, fn), built(s, fn)
    print('%s: rom %d insn, built %d insn' % (fn, len(a), len(b)))
    import difflib
    for ln in difflib.unified_diff(a, b, 'rom', 'built', lineterm='', n=2):
        print('  ' + ln)


if __name__ == '__main__':
    main()
