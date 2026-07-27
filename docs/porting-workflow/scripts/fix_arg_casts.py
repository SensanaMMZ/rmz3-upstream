#!/usr/bin/env python3
"""Cast the first argument of a call when the callee wants a different entity
pointer than the caller holds.

Upstream gives each source file its own flat type over the shared entity layout
(`BabyElf`), while the helpers it calls are still declared in terms of the
generic one (`bool8 FUN_08045d54(struct Boss* p);`). The fork had one type for
both, so its bodies pass `p` straight through and agbcc rejects it with
`passing arg 1 of 'FUN_08045d54' from incompatible pointer type`.

Both types describe the same bytes, so the cast is the whole fix. It is applied
only when BOTH sides are known pointer types and they actually differ -- an
unconstrained cast here would paper over a genuinely wrong argument, which is
the one mistake in this area the compiler would otherwise have caught for us.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fix_buffer_offsets import _bodies  # noqa: E402

# `TYPE fn(TYPE* name, ...)` -- prototypes and definitions both match.
PROTO = re.compile(
    r'^[A-Za-z_][\w \*]*?\b(?P<fn>\w+)\s*\(\s*(?P<ty>(?:struct\s+)?\w+)\s*\*',
    re.M)


def main():
    src = sys.argv[1]
    with open(src, encoding='utf-8', errors='replace') as fh:
        txt = fh.read()

    want = {}
    for m in PROTO.finditer(txt):
        want.setdefault(m.group('fn'), m.group('ty').strip())
    # Headers too. `UpdateEntityAnim(struct Entity*)` is declared in motion.h,
    # not in the file, so a file-only scan had no expectation for it and the
    # mismatch went unfixed -- while the identical situation for a
    # file-declared callee was handled.
    for h in sorted(p.replace('\\', '/') for p in
                    glob.glob('include/**/*.h', recursive=True)):
        with open(h, encoding='utf-8', errors='replace') as fh:
            for m in PROTO.finditer(fh.read()):
                want.setdefault(m.group('fn'), m.group('ty').strip())

    n = 0
    have = {}

    def types_in(block):
        """Declared pointer types inside one function body + its parameters.

        This MUST be per-function. A file-wide pass takes the first `X* p` it
        sees, and that is invariably a PROTOTYPE at the top of the file --
        `bool8 FUN_08045d54(struct Boss* p);` -- so every `p` in the file looked
        like a `struct Boss*` and no call ever needed a cast. Nothing was
        rewritten and the error stayed exactly as it was."""
        d = {}
        for mm in re.finditer(r'\b((?:struct\s+)?\w+)\s*\*\s*(\w+)\s*[,;=){]',
                              block):
            d.setdefault(mm.group(2), mm.group(1).strip())
        return d

    def sub(m):
        nonlocal n
        fn, var, tail = m.group('fn'), m.group('var'), m.group('tail')
        w, h = want.get(fn), have.get(var)
        if not w or not h or w == h:
            return m.group(0)
        # `void*` accepts anything; casting to it is never the missing piece.
        if w == 'void':
            return m.group(0)
        n += 1
        return '%s((%s*)%s%s' % (fn, w, var, tail)

    # Assignment casts: `b->parent = (Object*)p;` where upstream declares
    # `struct Entity* parent`. The fork had one type for both, so its cast names
    # the wrong one and agbcc reports "assignment from incompatible pointer
    # type" -- on the assignment, not on the cast that caused it.
    pass
    ftypes = {}
    for h in sorted(p.replace('\\', '/') for p in
                    glob.glob('include/**/*.h', recursive=True)):
        with open(h, encoding='utf-8', errors='replace') as fh:
            for nm, body in _bodies(fh.read()):
                for ln in body.splitlines():
                    d = re.match(r'\s*((?:struct\s+)?\w+)\s*\*\s*(\w+)\s*;', ln)
                    if d:
                        ftypes[(nm, d.group(2))] = d.group(1).strip()

    def acast(m):
        nonlocal n
        var, fld, cast = m.group('var'), m.group('fld'), m.group('cast')
        vt = have_global.get(var)
        # `_bodies` names the struct `Body`, while a declaration reads
        # `struct Body* b;`. Without stripping the keyword the lookup key is
        # `('struct Body', 'parent')` and never matches anything.
        if vt:
            vt = re.sub(r'^struct\s+', '', vt)
        want_t = ftypes.get((vt, fld)) if vt else None
        if not want_t or want_t == cast.strip():
            return m.group(0)
        n += 1
        return '%s->%s = (%s*)' % (var, fld, want_t)

    have_global = {}
    for m in re.finditer(r'\b((?:struct\s+)?\w+)\s*\*\s*(\w+)\s*[;=]', txt):
        have_global.setdefault(m.group(2), m.group(1).strip())
    txt = re.sub(r'(?P<var>\w+)\s*->\s*(?P<fld>\w+)\s*=\s*'
                 r'\(\s*(?P<cast>(?:struct\s+)?\w+)\s*\*\s*\)', acast, txt)

    # Return types, for `q = CreateLemon(...)` where upstream declares
    # `Entity* CreateLemon(...)` and the local is a `struct Projectile*`. Same
    # object either way, so the assignment just needs the cast the fork never
    # had to write.
    rets = {}
    for h in sorted(p.replace('\\', '/') for p in
                    glob.glob('include/**/*.h', recursive=True)) + [src]:
        with open(h, encoding='utf-8', errors='replace') as fh:
            for ln in fh:
                d = re.match(r'^((?:struct\s+)?\w+)\s*\*\s*(\w+)\s*\(', ln)
                if d:
                    rets.setdefault(d.group(2), d.group(1).strip())

    def rsub(m):
        nonlocal n
        var, fn = m.group('var'), m.group('fn')
        r, h = rets.get(fn), have.get(var)
        if not r or not h or r == h or fn in ('if', 'while', 'for', 'switch'):
            return m.group(0)
        n += 1
        return '%s = (%s*)%s(' % (var, h, fn)

    # Walk the file function by function, rewriting each body with only that
    # function's own declarations in scope.
    out, pos = [], 0
    for m in re.finditer(r'^[A-Za-z_][\w \*]*\b\w+\s*\([^;{)]*\)\s*\{', txt,
                         re.M):
        depth, start = 0, txt.index('{', m.start())
        end = start
        for j in range(start, len(txt)):
            if txt[j] == '{':
                depth += 1
            elif txt[j] == '}':
                depth -= 1
                if depth == 0:
                    end = j + 1
                    break
        block = txt[m.start():end]
        have = types_in(block)
        out.append(txt[pos:m.start()])
        block = re.sub(r'\b(?P<fn>\w+)\s*\(\s*(?P<var>\w+)\s*(?P<tail>[,)])',
                       sub, block)
        out.append(re.sub(r'(?P<var>\w+)\s*=\s*(?P<fn>\w+)\s*\(', rsub, block))
        pos = end
    out.append(txt[pos:])
    with open(src, 'w', encoding='utf-8', newline='') as fh:
        fh.write(''.join(out))
    print('  arg casts: %d added' % n)


if __name__ == '__main__':
    main()
