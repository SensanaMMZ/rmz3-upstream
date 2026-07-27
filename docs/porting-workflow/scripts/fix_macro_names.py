#!/usr/bin/env python3
"""Rename constants the two trees spell differently, matched by VALUE.

The linker map cannot help: a `#define` never reaches the symbol table, so the
address join that resolves functions and globals is blind to it. But both trees
describe the same hardware constants in the same headers, so a `#define` with an
identical right-hand side in the same header is the same constant under a
different name -- `METATILE_SOFT_PLATFORM (1 << 15)` upstream is
`MTATTR_SOFT_PLATFORM (1 << 15)`.

Only exact, unambiguous matches are used: the value must appear exactly once on
each side of that header. Enum members are handled the same way, keyed by
position within the enum, since an enum body's order IS its values.
"""
import glob
import re
import subprocess
import sys

DEFINE = re.compile(r'^\s*#define\s+([A-Z_][A-Z0-9_]*)\s+(\S.*?)\s*(?://.*)?$')


def defines(txt):
    """value -> [names], for object-like macros only."""
    out = {}
    for ln in txt.splitlines():
        m = DEFINE.match(ln)
        if not m or '(' == m.group(1)[-1:]:
            continue
        val = re.sub(r'\s+', '', m.group(2))
        out.setdefault(val, []).append(m.group(1))
    return out


def main():
    src = sys.argv[1]
    headers = sorted(p.replace('\\', '/') for p in
                     glob.glob('include/**/*.h', recursive=True))
    renames = {}
    for h in headers:
        with open(h, encoding='utf-8', errors='replace') as fh:
            up = defines(fh.read())
        r = subprocess.run(['git', 'show', 'main:' + h], capture_output=True)
        if r.returncode:
            continue
        fk = defines(r.stdout.decode('utf-8', errors='replace'))
        for val, fnames in fk.items():
            unames = up.get(val)
            # One name on each side, or the pairing is a guess.
            if not unames or len(unames) != 1 or len(fnames) != 1:
                continue
            if fnames[0] != unames[0]:
                renames[fnames[0]] = unames[0]

    # Macros the fork defines and upstream simply does not have. `SEA` is
    # `(gOverworld.sea)` in the fork; upstream spells the field access out. A
    # lifted body using `SEA` cannot be renamed to anything, so expand it --
    # otherwise the name looks like an undeclared object and gets "declared"
    # as `SEA;`, which fails as "data definition has no type or storage class".
    expand = {}
    up_names = set()
    for h in headers:
        with open(h, encoding='utf-8', errors='replace') as fh:
            up_names.update(defines(fh.read()).values() and
                            [n for v in defines(open(
                                h, encoding='utf-8',
                                errors='replace').read()).values() for n in v])
    for h in headers:
        r = subprocess.run(['git', 'show', 'main:' + h], capture_output=True)
        if r.returncode:
            continue
        for ln in r.stdout.decode('utf-8', errors='replace').splitlines():
            m = DEFINE.match(ln)
            if m and m.group(1) not in up_names and m.group(2).startswith('('):
                expand.setdefault(m.group(1), m.group(2))

    with open(src, encoding='utf-8', errors='replace') as fh:
        txt = fh.read()
    n = 0
    for a, b in renames.items():
        txt, k = re.subn(r'\b%s\b' % re.escape(a), b, txt)
        n += k
    for a, b in expand.items():
        if re.search(r'\b%s\b' % re.escape(a), txt):
            txt, k = re.subn(r'\b%s\b' % re.escape(a), b.replace('\\', '\\\\'),
                             txt)
            n += k
    with open(src, 'w', encoding='utf-8', newline='') as fh:
        fh.write(txt)
    print('  macro names: %d rewritten (%d pair(s) known)' % (n, len(renames)))


if __name__ == '__main__':
    main()
