#!/usr/bin/env python3
"""Cast ANY mismatched pointer argument, and pointer initialisers.

fix_arg_casts only ever looked at argument 1, because that is where the entity
pointer sits in the routine-table convention. Real calls miss on later ones too
--  `ApplyElementEffect(0, &p->s, &Coord_...)` wants a `struct CollidableEntity*`
in position 2 -- and declarations miss as well:
`struct CollidableEntity* p = body->parent;` where `parent` is a `struct
Entity*`.

Both are the same fact as everywhere else in this tree: the entity views
describe the same bytes, so the cast is the whole fix. Applied only when both
sides are known pointer types and they differ, so a genuinely wrong argument
still fails to compile.

Types are read from prototypes in the file and in include/**.h, and variable
types are resolved per FUNCTION -- file-wide lookup picks a prototype's
parameter and silently answers for every same-named local.
"""
import glob
import os
import re
import sys

PROTO = re.compile(r'^[A-Za-z_][\w \*]*?\b(?P<fn>\w+)\s*\((?P<args>[^;{)]*)\)\s*;',
                   re.M)


def split_args(s):
    out, depth, cur = [], 0, ''
    for ch in s:
        if ch == ',' and depth == 0:
            out.append(cur)
            cur = ''
            continue
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        cur += ch
    if cur.strip():
        out.append(cur)
    return out


def ptype(decl):
    m = re.match(r'\s*((?:const\s+)?(?:struct\s+)?\w+)\s*\*', decl)
    return m.group(1).replace('const ', '').strip() if m else None


def main():
    src = sys.argv[1]
    with open(src, encoding='utf-8', errors='replace') as fh:
        txt = fh.read()

    want = {}
    sources = [txt]
    for h in sorted(p.replace('\\', '/') for p in
                    glob.glob('include/**/*.h', recursive=True)):
        with open(h, encoding='utf-8', errors='replace') as fh:
            sources.append(fh.read())
    for s in sources:
        for m in PROTO.finditer(s):
            want.setdefault(m.group('fn'),
                            [ptype(a) for a in split_args(m.group('args'))])

    n = 0
    have = {}

    def call(m):
        nonlocal n
        fn = m.group('fn')
        sig = want.get(fn)
        if not sig:
            return m.group(0)
        args = split_args(m.group('args'))
        if len(args) != len(sig):
            return m.group(0)
        out = []
        changed = False
        for a, wt in zip(args, sig):
            bare = a.strip()
            v = re.match(r'^&?(\w+)(?:->(\w+))?$', bare)
            if wt and v and not bare.startswith('('):
                ht = have.get(v.group(1))
                if v.group(2):
                    ht = None            # member: type unknown here, skip
                if ht and ht != wt and wt != 'void':
                    a = ' (%s*)%s' % (wt, bare)
                    changed = True
            out.append(a)
        if not changed:
            return m.group(0)
        n += 1
        return '%s(%s)' % (fn, ','.join(out))

    out, pos = [], 0
    for fm in re.finditer(r'^[A-Za-z_][\w \*]*\b\w+\s*\([^;{)]*\)\s*\{', txt,
                          re.M):
        depth, st = 0, txt.index('{', fm.start())
        en = st
        for j in range(st, len(txt)):
            if txt[j] == '{':
                depth += 1
            elif txt[j] == '}':
                depth -= 1
                if depth == 0:
                    en = j + 1
                    break
        blk = txt[fm.start():en]
        have = {}
        for mm in re.finditer(r'\b((?:struct\s+)?\w+)\s*\*\s*(\w+)\s*[,;=){]',
                              blk):
            have.setdefault(mm.group(2),
                            re.sub(r'^struct\s+', '', mm.group(1).strip()))
        out.append(txt[pos:fm.start()])
        out.append(re.sub(r'\b(?P<fn>\w+)\s*\((?P<args>[^();]*)\)', call, blk))
        pos = en
    out.append(txt[pos:])
    txt = ''.join(out)

    with open(src, 'w', encoding='utf-8', newline='') as fh:
        fh.write(txt)
    print('  arg casts (any position): %d call(s)' % n)


if __name__ == '__main__':
    main()
