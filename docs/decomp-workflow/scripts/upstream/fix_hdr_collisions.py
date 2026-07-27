#!/usr/bin/env python3
import os
"""Rename file-local struct fields that flattening put in collision with an
entity-header field of the same name.

Flattening splices ENTITY_HDR's fields (`id`, `mode`, `work`, `motion`, ...)
directly into a converted struct, so a file-local member that reuses one of
those names becomes a duplicate member: follower.c's `cyberelf_t id;` at 0xB8
collides with the header's `u8 id;` at 0x09.

The colliding LOCAL field is renamed `<name>_<hexoffset>` following upstream's
own convention (mob_npc.c names its 0xBE field `motion_be`). Only accesses on
variables of the affected struct type are rewritten, resolved per FUNCTION.
The header field keeps its name; codegen is unaffected (same offsets).
"""
import io
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_buffer_offsets as BO  # noqa: E402
import fix_struct_fields as FSF  # noqa: E402

# Field names ENTITY_HDR / ENTITY_SPRITE / COLLISION_OBJECT_HDR contribute.
def header_fields():
    """Fields the shared entity header splices into a flat struct.

    Read by EXPANDING the macros and parsing the resulting Entity /
    CollisionObject bodies -- the previous hand-rolled `#define ...`
    continuation-line regex silently matched nothing, so this pass ran as a
    no-op and the id/motion duplicate-member collisions survived it."""
    import fix_struct_fields as FSF
    out = set()
    for h in ('include/entity/entity.h', 'include/entity/sprite.h'):
        try:
            txt = io.open(h, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        for nm, body in BO._bodies(FSF.expand_macros(txt)):
            if nm in ('Entity', 'CollisionObject'):
                out.update(FSF.fields(body))
    return out


HDR_FIELDS = None


def process(path):
    global HDR_FIELDS
    if HDR_FIELDS is None:
        HDR_FIELDS = header_fields()
    txt = io.open(path, encoding='utf-8', errors='replace').read()

    # Structs in this file that are now flat, and their colliding fields.
    renames = {}          # (type, old) -> new
    def replace_struct(m):
        body = m.group('body')
        nm = m.group('tag') or m.group('td')
        if not nm or not re.search(
                r'\b(?:COLLISION_OBJECT_HDR|ENTITY_HDR)\s*;', body):
            return m.group(0)
        newbody = body
        for fm in re.finditer(
                r'^(\s*[\w \*]+?\s)(\w+)(\s*(?:\[[^\]]*\])?\s*;\s*(?://\s*(0x[0-9A-Fa-f]+))?)',
                body, re.M):
            fname, off = fm.group(2), fm.group(4)
            if fname in HDR_FIELDS:
                suffix = off.lower().replace('0x', '') if off else 'l'
                new = '%s_%s' % (fname, suffix)
                renames[(nm, fname)] = new
                newbody = newbody.replace(fm.group(0),
                                          fm.group(1) + new + fm.group(3), 1)
        return m.group(0).replace(body, newbody)

    txt = re.sub(r'(?:typedef\s+)?struct(?:\s+(?P<tag>\w+))?\s*\{(?P<body>[^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\s*(?P<td>\w+)?\s*;',
                 replace_struct, txt)

    if not renames:
        print('  hdr collisions: none in %s' % path)
        io.open(path, 'w', encoding='utf-8', newline='').write(txt)
        return

    # Rewrite accesses, per function, only on variables of the affected types.
    types = {t for t, _ in renames}
    out, pos, n = [], 0, 0
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
        scope = {}
        for mm in re.finditer(r'\b(?:struct\s+)?(\w+)\s*\*\s*(\w+)\s*[,;=){]',
                              blk):
            if mm.group(1) in types:
                scope[mm.group(2)] = mm.group(1)
        for var, ty in scope.items():
            for (t, old), new in renames.items():
                if t != ty:
                    continue
                blk, k = re.subn(r'\b%s\s*->\s*%s\b' % (re.escape(var),
                                                        re.escape(old)),
                                 '%s->%s' % (var, new), blk)
                n += k
        out.append(txt[pos:fm.start()])
        out.append(blk)
        pos = en
    out.append(txt[pos:])
    io.open(path, 'w', encoding='utf-8', newline='').write(''.join(out))
    print('  hdr collisions in %s: %s; %d access(es)'
          % (path, ', '.join('%s.%s->%s' % (t, o, nw)
                             for (t, o), nw in renames.items()), n))


for p in sys.argv[1:]:
    try:
        process(p)
    except OSError:
        pass
