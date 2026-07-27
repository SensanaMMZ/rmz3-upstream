#!/usr/bin/env python3
"""Find functions upstream still keeps in assembly whose body is trivial.

Two shapes qualify:

  * `bx lr` and nothing else (`.byte 0x70, 0x47`) -- an empty function. In C
    that is `void f(T* p) {}`, and agbcc emits exactly `bx lr` for it.
  * a constant return: `mov r0, #N; bx lr` (`0x20 0xNN 0x70 0x47`), i.e.
    `return N;`.

Both are mechanical and carry no judgement, which makes them the right place to
start on the ~2,459 functions neither tree has decompiled. Trailing `0x00 0x00`
is alignment padding to the next 4-byte boundary and is ignored.

Prints `<inc>\\t<function>\\t<kind>` so the result can drive a port directly.
"""
import glob
import re
import sys

START = re.compile(r'^\tthumb_func_start (\S+)\s*$')
BYTES = re.compile(r'^\s*\.byte\s+(.*)$')


def body_bytes(lines):
    """Raw bytes of a function body, or None if it is not a pure .byte blob."""
    out = []
    for l in lines:
        s = l.strip()
        if not s or s.startswith('@') or s.endswith(':'):
            continue
        m = BYTES.match(l)
        if not m:
            return None                     # real instructions, not a blob
        for tok in m.group(1).split(','):
            tok = tok.strip()
            if tok:
                out.append(int(tok, 16))
    return out


def classify(b):
    while b and b[-1] == 0:                 # alignment padding
        b = b[:-1]
    if b == [0x70, 0x47]:
        return 'empty'
    if len(b) == 4 and b[0] == 0x20 and b[2:] == [0x70, 0x47]:
        return 'return-const-%d' % b[1]
    return None


def classify_insns(lines):
    """Same two shapes, but written as instructions rather than a .byte blob.

    Most of these are disassembled, not raw bytes -- scanning only for blobs
    found 1 stub in the whole tree when there are hundreds."""
    insns = []
    for l in lines:
        # Strip the trailing `@ 0x...` comment FIRST. Definitions are written
        # `FUN_0804b900: @ 0x0804B900`, so testing for a trailing ':' before
        # removing the comment never matched and every label counted as an
        # instruction -- which is why only 41 of the hundreds were found.
        s = l.split('@')[0].strip()
        if not s or s.startswith('.') or s.endswith(':'):
            continue
        insns.append(re.sub(r'\s+', ' ', s))
    if insns == ['bx lr']:
        return 'empty'
    if len(insns) == 2 and insns[1] == 'bx lr':
        m = re.match(r'movs? r0, #(?:0x)?([0-9a-fA-F]+)$', insns[0])
        if m:
            return 'return-const-%d' % int(m.group(1), 0)
    return None


def main():
    rows = []
    for path in sorted(glob.glob('asm/**/*.inc', recursive=True)):
        with open(path, encoding='utf-8', errors='replace') as fh:
            lines = fh.read().splitlines()
        marks = [(i, m.group(1)) for i, l in enumerate(lines)
                 for m in [START.match(l)] if m]
        for k, (i, name) in enumerate(marks):
            end = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
            chunk = lines[i + 1:end]
            b = body_bytes(chunk)
            kind = classify(b) if b is not None else classify_insns(chunk)
            if kind:
                rows.append((path, name, kind))

    for p, n, k in rows:
        print('%s\t%s\t%s' % (p, n, k))
    sys.stderr.write('trivial stubs found: %d\n' % len(rows))


if __name__ == '__main__':
    main()
