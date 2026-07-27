#!/usr/bin/env python3
"""Decompile trivial stubs that neither tree has done: `bx lr` and
`movs r0, #N; bx lr`.

These are not ports -- the fork has no C for them either -- so the body is
GENERATED from the assembly, which is unambiguous for these two shapes. The
signature is not invented: upstream already declares every one of them, because
they are referenced from routine tables, so the declaration in the .c is used
verbatim.

One correction is needed and it matters. A `movs r0, #1; bx lr` function returns
a value, but upstream's placeholder declaration usually says `void` -- nothing
checked it while the body was assembly. Emitting `void f(...) { return TRUE; }`
does not compile, and emitting `void f(...) {}` compiles to a bare `bx lr`,
silently dropping the `movs` and failing the ROM compare. So the declaration is
retyped to `bool8` alongside the definition.

    port_stubs.py <inc> <src.c> <fn>:<kind> [...]
"""
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_to_upstream as PU  # noqa: E402

DECL = r'^([A-Za-z_][\w \*]*?)\b%s\s*\(([^;{)]*)\)\s*;'


def main():
    inc, src = sys.argv[1], sys.argv[2]
    specs = [a.split(':', 1) for a in sys.argv[3:]]

    with open(src, encoding='utf-8', errors='replace') as fh:
        txt = fh.read()

    # Fallback parameter type for stubs the C never mentions. These exist only
    # because other .inc files branch to them, so no declaration and no routine
    # table entry names them -- but for `bx lr` and `movs r0,#1; bx lr` the
    # signature cannot change the emitted bytes, and the file's own convention
    # is the honest choice. Taken as the most common parameter type among the
    # declarations already in this file, so it is read, not invented.
    seen = re.findall(r'^[A-Za-z_][\w \*]*?\b\w+\s*\(\s*((?:struct\s+)?\w+\s*\*)',
                      txt, re.M)
    common = collections.Counter(s.strip() for s in seen).most_common(1)
    fallback = common[0][0] if common else None

    bodies, retype, declare = {}, [], []
    for fn, kind in specs:
        m = re.search(DECL % re.escape(fn), txt, re.M)
        if m:
            ret, params = m.group(1).strip(), m.group(2).strip()
        elif fallback:
            ret, params = 'void', '%s p' % fallback
            declare.append(fn)
        else:
            sys.exit('no declaration for %s in %s and no convention to follow '
                     '-- refusing to invent a signature' % (fn, src))
        if kind == 'empty':
            bodies[fn] = '%s %s(%s) {\n}\n' % (ret, fn, params)
        else:
            val = kind.rsplit('-', 1)[1]
            if ret == 'void':
                ret = 'bool8'
                retype.append(fn)
            lit = 'TRUE' if val == '1' else val
            bodies[fn] = '%s %s(%s) {\n  return %s;\n}\n' % (ret, fn, params,
                                                             lit)

    if declare:
        decls = ''.join('void %s(%s p);\n' % (fn, fallback) for fn in declare)
        # Anchor AFTER the definition of the fallback parameter type when the
        # file defines it. pantheon_fist.c declares `PantheonFist` as an
        # anonymous typedef below the includes, so inserting the declarations
        # at the include block produced `void nop_...(PantheonFist* p);`
        # before the name existed -- "syntax error before `*'".
        tyname = re.sub(r'^struct\s+|\s*\*$', '', fallback).strip()
        tydef = re.search(r'\}\s*%s\s*;' % re.escape(tyname), txt)
        if tydef:
            at = txt.index('\n', tydef.end()) + 1
        else:
            incs = list(re.finditer(r'^#include "[^"]+"\n', txt, re.M))
            at = incs[-1].end() if incs else 0
        txt = txt[:at] + '\n' + decls + txt[at:]

    # Retype the declarations before the carve rewrites the file.
    if retype or declare:
        for fn in retype:
            txt = re.sub(r'^void(\s+%s\s*\()' % re.escape(fn), r'bool8\1',
                         txt, flags=re.M)
        # Retyping breaks the routine tables that hold these functions: the
        # array is `const BossFunc[]` and a bool8-returning function no longer
        # matches, giving "initialization from incompatible pointer type".
        # Upstream already casts some entries the same way -- follow that.
        for m in re.finditer(r'const\s+(\w+)\s+\w+\[[^\]]*\]\s*=\s*\{',
                             txt):
            ety = m.group(1)
            depth, st = 0, txt.index('{', m.start())
            en = st
            for j in range(st, len(txt)):
                if txt[j] == '{':
                    depth += 1
                elif txt[j] == '}':
                    depth -= 1
                    if depth == 0:
                        en = j
                        break
            blk = txt[st:en]
            new = blk
            for fn in retype:
                new = re.sub(r'(^\s*)%s(\s*,)' % re.escape(fn),
                             r'\1(%s)%s\2' % (ety, fn), new, flags=re.M)
            if new != blk:
                txt = txt[:st] + new + txt[en:]
        with open(src, 'w', encoding='utf-8', newline='') as fh:
            fh.write(txt)

    # Reuse the carving path wholesale; only the body source differs.
    PU.c_body = lambda hint, fn: bodies[fn]
    sys.argv = ['port_to_upstream.py', inc, src, src] + [s[0] for s in specs]
    PU.main()


main()
