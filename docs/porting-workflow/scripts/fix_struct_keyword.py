#!/usr/bin/env python3
"""Drop the `struct` keyword for types upstream declares as anonymous typedefs.

`include/boss/omega1.h` says `typedef struct { ... } Omega1;`. There is no tag,
so `struct Omega1` is a *different*, incomplete type -- C happily accepts the
declaration `struct Omega1* p` and then rejects `p->mode[0]` with "dereferencing
pointer to incomplete type". The file included the right header the whole time,
which is why it reads like a missing include and is not one.

So: for every type upstream defines WITHOUT a tag, rewrite `struct X` -> `X`.
Types upstream does give a tag (`struct Entity`, `struct Body`) are left alone.
The set is read from include/ at run time.
"""
import glob
import io
import re
import sys

TAGGED = re.compile(r'(?:typedef\s+)?struct\s+(\w+)\s*\{')
ANON = re.compile(r'typedef\s+struct\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\s*(\w+)\s*;',
                  re.S)


def main():
    src = sys.argv[1]
    anon, tagged = set(), set()
    for h in glob.glob('include/**/*.h', recursive=True):
        with io.open(h, encoding='utf-8', errors='replace') as fh:
            t = fh.read()
        tagged |= set(TAGGED.findall(t))
        anon |= set(ANON.findall(t))
    # A name that also exists as a tag somewhere is fine as `struct X`.
    anon -= tagged
    if not anon:
        print('  struct keyword: no anonymous typedefs')
        return

    with io.open(src, encoding='utf-8', errors='replace') as fh:
        txt = fh.read()

    # A type this file DEFINES with a tag is a real tagged struct here,
    # regardless of what upstream does -- leave it alone.
    anon -= set(TAGGED.findall(txt))

    n = 0
    for name in sorted(anon):
        # Never touch a DEFINITION: `struct BlazinTail {` must not become
        # `BlazinTail {`, which is not a declaration at all and fails as
        # "data definition has no type or storage class".
        txt, k = re.subn(r'\bstruct\s+%s\b(?!\s*\{)' % re.escape(name),
                         name, txt)
        n += k
    if n:
        with io.open(src, 'w', encoding='utf-8', newline='') as fh:
            fh.write(txt)
    print('  struct keyword: %d dropped (%d anonymous typedef(s))'
          % (n, len(anon)))


if __name__ == '__main__':
    main()
