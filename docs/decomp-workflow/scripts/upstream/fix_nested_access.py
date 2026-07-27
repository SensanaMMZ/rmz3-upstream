#!/usr/bin/env python3
"""Route entity-header field accesses through `->s` for NESTED entity types.

Upstream has two shapes for an entity struct. The FLAT ones splice the shared
fields in with `COLLISION_OBJECT_HDR;`, so `p->work[2]` is valid. The NESTED
ones (`struct VFX { Entity s; u8 buffer[16]; }`) keep them one level down, so
the same access has to read `(p->s).work[2]`.

The fork types these handlers `struct Entity*` and upstream types them
`struct VFX*`, so a lifted body written against the fork's signature reaches for
`p->work` on a struct that has no such member. This is the mirror image of
to_flat, which handles the flat direction.

Only fields the shared entity header actually declares are moved -- a field the
nested struct declares itself must stay where it is.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_buffer_offsets as BO  # noqa: E402
import fix_struct_fields as FSF  # noqa: E402


def main():
    src = sys.argv[1]
    with open(src, encoding='utf-8', errors='replace') as fh:
        txt = fh.read()

    # Fields the shared entity header declares.
    entity_fields = set()
    nested = {}
    own = {}
    for h in sorted(p.replace('\\', '/') for p in
                    glob.glob('include/**/*.h', recursive=True)) + [src]:
        if not os.path.exists(h):
            continue
        with open(h, encoding='utf-8', errors='replace') as fh:
            raw = fh.read()
        for nm, body in BO._bodies(FSF.expand_macros(raw)):
            fl = FSF.fields(body)
            own.setdefault(nm, set()).update(fl)
            if nm == 'Entity':
                entity_fields.update(fl)
        for nm, body in BO._bodies(raw):
            first = next((l.strip() for l in body.splitlines()
                          if l.strip() and not l.strip().startswith('//')), '')
            if re.match(r'(?:struct\s+)?Entity\s+s\s*;', first):
                nested[nm] = True

    n = 0
    have = {}

    def sub(m):
        nonlocal n
        var, fld = m.group('var'), m.group('fld')
        if fld not in entity_fields:
            return m.group(0)
        ty = have.get(var)
        if not ty or not nested.get(ty):
            return m.group(0)
        if fld in own.get(ty, ()):
            return m.group(0)      # the nested struct declares it itself
        n += 1
        return '(%s->s).%s' % (var, fld)

    # Per-function, never file-wide: this file's first `X* p` is
    # `struct Entity* p` inside CreateVFX56, so a file-wide lookup typed every
    # `p` as an Entity -- which is not nested -- and the pass rewrote nothing
    # while the error stayed put. Same trap as fix_arg_casts had.
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
        have = {}
        for mm in re.finditer(r'\b((?:struct\s+)?\w+)\s*\*\s*(\w+)\s*[,;=){]',
                              block):
            have.setdefault(mm.group(2),
                            re.sub(r'^struct\s+', '', mm.group(1).strip()))
        out.append(txt[pos:m.start()])
        out.append(re.sub(r'(?P<var>\w+)\s*->\s*(?P<fld>\w+)\b', sub, block))
        pos = end
    out.append(txt[pos:])
    with open(src, 'w', encoding='utf-8', newline='') as fh:
        fh.write(''.join(out))
    print('  nested access: %d rewritten' % n)


if __name__ == '__main__':
    main()
