#!/usr/bin/env python3
"""Fix functions whose body returns a value but whose signature says `void`.

Upstream carries a forward declaration for every function still in asm, and for
an INCASM'd function that declaration is a placeholder -- nothing checks it,
because nothing compiles the body. `hellbat_0804cbe4` is declared `void` there
while the fork's matching body ends `return TRUE;` and is typed `bool8`.

align_protos aligns a lifted definition to the declaration already in the file,
which is right when the declaration is real and wrong here: it stamped `void`
onto a body that returns a value, giving `'return' with a value, in function
returning void`.

The body is the artifact that byte-matches the ROM, so it wins. This rewrites
the DECLARATION (and the definition) to the fork's return type. Callers are
checked first: if any of them uses the result, the file is left alone, since
then the void declaration may be load-bearing for someone else's codegen.
"""
import re
import subprocess
import sys


def fork_return_type(fn):
    """The return type the fork gives `fn`, from its definition."""
    r = subprocess.run(['git', 'grep', '-h', '-E',
                        r'^[A-Za-z_].*\b%s\s*\(' % fn, 'main', '--', 'src'],
                       capture_output=True, text=True)
    for ln in r.stdout.splitlines():
        m = re.match(r'^((?:struct\s+|unsigned\s+|const\s+)*\w+\s*\**)\s*%s\s*\('
                     % re.escape(fn), ln)
        if m and m.group(1).strip() not in ('void',):
            return m.group(1).strip()
    return None


def main():
    src = sys.argv[1]
    # Only the functions being LIFTED. Without this the passes below rewrite
    # upstream's own `static bool32 nop_0804b6b4(void* _ UNUSED)` too, and since
    # the declaration spells the parameter `void* _ UNUSED` while the definition
    # spells it `void* _`, only one of the two got retyped -- "conflicting types
    # for 'nop_0804b6b4'", in a function this port never touched.
    only = set(sys.argv[2:])
    with open(src, encoding='utf-8', errors='replace') as fh:
        txt = fh.read()

    fixed = 0
    for m in re.finditer(r'^void\s+(\w+)\s*\(([^;{)]*)\)\s*\{', txt, re.M):
        fn, args = m.group(1), m.group(2)
        if only and fn not in only:
            continue
        # Body extent.
        depth, start = 0, txt.index('{', m.start())
        end = start
        for j in range(start, len(txt)):
            if txt[j] == '{':
                depth += 1
            elif txt[j] == '}':
                depth -= 1
                if depth == 0:
                    end = j
                    break
        body = txt[start:end]
        if not re.search(r'\breturn\s+[^;\s]', body):
            continue
        ty = fork_return_type(fn)
        if not ty:
            continue
        # A caller that consumes the value would be relying on the declaration
        # as it stands; leave those for a human.
        if re.search(r'[=(,]\s*%s\s*\(' % re.escape(fn), txt):
            sys.stderr.write('    %s: result is used by a caller, left alone\n'
                             % fn)
            continue
        txt = re.sub(r'^void(\s+%s\s*\()' % re.escape(fn), ty + r'\1',
                     txt, flags=re.M)
        fixed += 1

    # Same story for the PARAMETER. `u32 blazin_0803fed8(void* p);` is
    # upstream's placeholder for a function still in asm; the fork's matching
    # definition takes a `struct Boss*` and dereferences it, so the lifted body
    # fails with "dereferencing 'void *' pointer". The body is the artifact that
    # matches the ROM, so its parameter type wins and the declaration follows.
    params = 0
    for m in re.finditer(r'^([\w \*]+?)\b(\w+)\s*\(\s*void\s*\*\s*(\w+)\s*\)\s*\{',
                         txt, re.M):
        fn, arg = m.group(2), m.group(3)
        if only and fn not in only:
            continue
        r = subprocess.run(['git', 'grep', '-h', '-E',
                            r'^[A-Za-z_].*\b%s\s*\(' % fn, 'main', '--', 'src'],
                           capture_output=True, text=True)
        ty = None
        for ln in r.stdout.splitlines():
            d = re.search(r'\b%s\s*\(\s*((?:struct\s+)?\w+)\s*\*' % re.escape(fn),
                          ln)
            if d and d.group(1) != 'void':
                ty = d.group(1)
                break
        if not ty:
            continue
        txt = re.sub(r'\b(%s\s*\(\s*)void(\s*\*\s*%s\s*\))'
                     % (re.escape(fn), re.escape(arg)),
                     lambda mm: mm.group(1) + ty + mm.group(2), txt)
        params += 1

    with open(src, 'w', encoding='utf-8', newline='') as fh:
        fh.write(txt)
    print('  signatures: %d retyped from void, %d param(s) from void*'
          % (fixed, params))


if __name__ == '__main__':
    main()
