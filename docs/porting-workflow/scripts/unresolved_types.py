#!/usr/bin/env python3
"""List struct names a branch references that upstream's headers do not define.

After taking upstream's include/ wholesale, any `struct X` the sources still
mention that upstream never declares is a fork-only spelling -- `struct Elf`
where upstream says `CyberElf`. Those show up as "incomplete type" or a negative
static_assert array, which reads like a size problem rather than a naming one.

Definitions are gathered from upstream's headers AND from each .c (files declare
their own entity structs), so the output is only the genuinely unresolved names.
Everything is read from the tree, never from notes.
"""
import glob
import io
import re
import subprocess
import sys
from collections import Counter

DEFINED = re.compile(r'(?:typedef\s+)?struct\s+(\w+)\s*\{')
TYPEDEF = re.compile(r'\}\s*(\w+)\s*;')
USED = re.compile(r'\bstruct\s+(\w+)\b')


def defined_in(txt):
    return set(DEFINED.findall(txt)) | set(TYPEDEF.findall(txt))


def main():
    known = set()
    for h in glob.glob('include/**/*.h', recursive=True):
        with io.open(h, encoding='utf-8', errors='replace') as fh:
            known |= defined_in(fh.read())

    missing = Counter()
    where = {}
    files = subprocess.run(['git', 'diff', '--name-only', 'upstream/dev',
                            '--', 'src'], capture_output=True, text=True
                           ).stdout.split()
    for f in files:
        if not f.endswith('.c'):
            continue
        try:
            with io.open(f, encoding='utf-8', errors='replace') as fh:
                txt = fh.read()
        except OSError:
            continue
        local = defined_in(txt)
        for name in USED.findall(txt):
            if name not in known and name not in local:
                missing[name] += 1
                where.setdefault(name, f)

    print('unresolved struct names: %d' % len(missing))
    for name, n in missing.most_common(20):
        print('  %-28s %4d use(s)   e.g. %s' % (name, n, where[name]))


if __name__ == '__main__':
    main()
