"""Print the exact .text bytes of one function in an object file, as hex.

Byte comparison is the final arbiter for a match: disassembly framing lies
(pool compression, functions stored as raw data when they came from an
INCCODE'd .inc, truncated windows), and all three have produced false
verdicts on this project before.

Usage:
  python3 tools/fnbytes.py <obj> <function>          # hex, one line
  python3 tools/fnbytes.py <obj> <fn> --words        # halfword columns
  python3 tools/fnbytes.py <a.o> <b.o> <fn> --diff   # compare two objects

Exit status is 1 when --diff finds a difference, so it can gate a script.
"""
import re, subprocess, sys

OBJDUMP = 'arm-none-eabi-objdump'
SYM = re.compile(r'^([0-9a-f]{8}) .*\bF \.text\t([0-9a-f]{8}) (\S+)\s*$')
ROW = re.compile(r'^ ([0-9a-f]+) ((?:[0-9a-f]{2,8} ){1,4})')


def span(obj, name):
    t = subprocess.run([OBJDUMP, '-t', obj], capture_output=True, text=True).stdout
    for l in t.split('\n'):
        m = SYM.match(l)
        if m and m.group(3) == name:
            return int(m.group(1), 16), int(m.group(2), 16)
    return None


def text(obj):
    out = subprocess.run([OBJDUMP, '-s', '-j', '.text', obj],
                         capture_output=True, text=True).stdout
    b = bytearray()
    for l in out.split('\n'):
        m = ROW.match(l)
        if m:
            b += bytes.fromhex(''.join(m.group(2).split()))
    return bytes(b)


def fn_bytes(obj, name):
    s = span(obj, name)
    if s is None:
        return None
    return text(obj)[s[0]:s[0] + s[1]]


def words(b):
    return ' '.join(b[i:i + 2].hex() for i in range(0, len(b), 2))


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    flags = set(x for x in sys.argv[1:] if x.startswith('--'))
    if '--diff' in flags:
        if len(a) != 3:
            sys.exit('usage: fnbytes.py <a.o> <b.o> <fn> --diff')
        x, y = fn_bytes(a[0], a[2]), fn_bytes(a[1], a[2])
        if x is None or y is None:
            print('%s not found in %s' % (a[2], a[0] if x is None else a[1]))
            sys.exit(1)
        if x == y:
            print('IDENTICAL  %s  (%d bytes)' % (a[2], len(x)))
            sys.exit(0)
        i = next((k for k, (p, q) in enumerate(zip(x, y)) if p != q), min(len(x), len(y)))
        print('DIFFERS    %s  ours %d B, want %d B, first diff at byte %d'
              % (a[2], len(x), len(y), i))
        print('  ours %s' % words(x))
        print('  want %s' % words(y))
        sys.exit(1)
    if len(a) != 2:
        sys.exit(__doc__)
    b = fn_bytes(a[0], a[1])
    if b is None:
        sys.exit('%s not found in %s' % (a[1], a[0]))
    print(words(b) if '--words' in flags else b.hex())


main()
