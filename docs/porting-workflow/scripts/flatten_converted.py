#!/usr/bin/env python3
"""Flatten `->s.` accesses for structs just converted to COLLISION_OBJECT_HDR.

`OBJECT_HDR` nests the entity (`struct Entity s; struct Body body;`) so code
reads `p->s.coord`. `COLLISION_OBJECT_HDR` splices the same fields in flat, so
the identical access is `p->coord` and `s` no longer exists.

to_flat.py cannot do this job: it keys off a fixed list of entity type names
(Boss, Projectile, Weapon, ...), while these files declare their own local
structs -- `struct WeaponRod`, `struct CubitFoot` -- and those are exactly the
ones being converted.

So the set of types to flatten is computed from the file itself: every struct
whose body now contains COLLISION_OBJECT_HDR. Variables are resolved per
FUNCTION, never file-wide, because a name like `p` is a converted local type in
one function and a plain `struct Entity*` in the next.
"""
import glob
import io
import re
import sys


def converted_types(txt):
    """Structs in this file that carry COLLISION_OBJECT_HDR."""
    names = set()
    for m in re.finditer(r'(?:typedef\s+)?struct(?:\s+(\w+))?\s*\{', txt):
        depth, st = 0, txt.index('{', m.start())
        for j in range(st, len(txt)):
            if txt[j] == '{':
                depth += 1
            elif txt[j] == '}':
                depth -= 1
                if depth == 0:
                    body = txt[st:j]
                    tail = re.match(r'\s*(\w+)?\s*;', txt[j + 1:])
                    # FLAT means the entity fields are spliced in directly --
                    # via COLLISION_OBJECT_HDR *or* a bare ENTITY_HDR splice.
                    # Only checking the former missed every ENTITY_HDR struct
                    # (AfterImage and most of vfx/), which dev declares flat
                    # while the branch nests `struct Entity s;` -- the exact
                    # class behind the 34 broken files.
                    if re.search(r'\b(?:COLLISION_OBJECT_HDR|ENTITY_HDR)\s*;',
                                 body):
                        if m.group(1):
                            names.add(m.group(1))
                        if tail and tail.group(1):
                            names.add(tail.group(1))
                    break
    return names


def header_flat_types():
    """Entity types upstream declares FLAT, read from the headers.

    Not from memory: which types are flat and which still nest `Entity s;` is
    exactly the kind of fact that drifts, and getting it backwards flattens an
    access that should stay nested. Computed by scanning include/ for structs
    whose body carries COLLISION_OBJECT_HDR."""
    names = set()
    for h in glob.glob('include/**/*.h', recursive=True):
        with io.open(h, encoding='utf-8', errors='replace') as fh:
            names |= converted_types(fh.read())
    return names


def main():
    src = sys.argv[1]
    txt = io.open(src, encoding='utf-8', errors='replace').read()
    types = converted_types(txt) | header_flat_types()
    if not types:
        print('  flatten: no converted structs')
        return

    n = 0
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
        # Locals and parameters of a converted type, in THIS function only.
        # Pointer vars flatten `->s.`; ARRAY/base vars flatten `[i].s.` --
        # cyberelf.c walks the header pool as `p[i].s.uniqueID`, which the
        # pointer-only patterns never touched.
        vs, va = set(), set()
        for mm in re.finditer(r'\b(?:struct\s+)?(\w+)\s*\*\s*(\w+)\s*[,;=){]',
                              blk):
            if mm.group(1) in types:
                vs.add(mm.group(2))
                va.add(mm.group(2))
        for mm in re.finditer(r'\b(?:struct\s+)?(\w+)\s+(\w+)\s*\[', blk):
            if mm.group(1) in types:
                va.add(mm.group(2))
        for v in vs:
            # `(p->s).x` and `p->s.x` both become `p->x`; a bare `&p->s`
            # becomes `p`, which is the same address.
            blk, k1 = re.subn(r'\(\s*%s\s*->\s*s\s*\)\s*\.' % re.escape(v),
                              '%s->' % v, blk)
            blk, k2 = re.subn(r'\b%s\s*->\s*s\s*\.' % re.escape(v),
                              '%s->' % v, blk)
            blk, k3 = re.subn(r'&\s*%s\s*->\s*s\b' % re.escape(v), v, blk)
            n += k1 + k2 + k3
        for v in va:
            blk, k4 = re.subn(
                r'\b%s\s*\[([^\]]+)\]\s*\.\s*s\s*\.' % re.escape(v),
                lambda m: '%s[%s].' % (v, m.group(1)), blk)
            blk, k5 = re.subn(
                r'&\s*%s\s*\[([^\]]+)\]\s*\.\s*s\b' % re.escape(v),
                lambda m: '&%s[%s]' % (v, m.group(1)), blk)
            n += k4 + k5
        out.append(txt[pos:fm.start()])
        out.append(blk)
        pos = en
    out.append(txt[pos:])
    io.open(src, 'w', encoding='utf-8', newline='').write(''.join(out))
    print('  flatten: %d access(es) in %d type(s)' % (n, len(types)))


if __name__ == '__main__':
    main()
