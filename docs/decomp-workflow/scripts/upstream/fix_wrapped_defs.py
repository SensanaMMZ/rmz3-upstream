#!/usr/bin/env python3
"""Rename function DEFINITIONS that dev's headers wrap in a same-named macro.

Dev's motion.h:
    void _ForceEntityPalette(struct Entity* p, u8 palID);
    #define ForceEntityPalette(enti, palID) (_ForceEntityPalette(...))

The branch defines `void ForceEntityPalette(struct Entity* p, u8 palID) {...}`.
Under dev's headers the definition line gets macro-expanded into garbage
("declared as function returning a function"). The fix is dev's own
convention: the function is NAMED `_ForceEntityPalette`; callers keep using
the macro. Renaming the definition (and any branch-local declaration) is
codegen-neutral apart from the symbol name, which dev's declaration pins.

The macro->target table is read from the working-tree headers at run time:
    #define NAME(args) (TARGET(...))  where TARGET is `_NAME` or similar.
Only definitions whose name exactly matches a wrapped macro are touched.
"""
import glob
import io
import re
import sys


def wrapped():
    out = {}
    for h in glob.glob('include/**/*.h', recursive=True):
        txt = io.open(h, encoding='utf-8', errors='replace').read()
        for m in re.finditer(
                r'#define\s+(\w+)\s*\([^)]*\)\s+\(\s*(_\w+)\s*\(', txt):
            out[m.group(1)] = m.group(2)
    return out


def main():
    table = wrapped()
    total = 0
    for f in sys.argv[1:]:
        try:
            txt = io.open(f, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        n = 0
        for name, target in table.items():
            # Definition or file-local prototype of the unwrapped name.
            pat = r'^((?:[A-Za-z_][\w \*]*\s)?)%s(\s*\([^;{)]*\)\s*[;{])' \
                  % re.escape(name)
            txt, k = re.subn(pat, lambda m: m.group(1) + target + m.group(2),
                             txt, flags=re.M)
            n += k
        if n:
            io.open(f, 'w', encoding='utf-8', newline='').write(txt)
            total += n
    print('  wrapped defs: %d renamed' % total)


if __name__ == '__main__':
    main()
