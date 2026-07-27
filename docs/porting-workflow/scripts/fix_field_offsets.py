#!/usr/bin/env python3
"""Map the fork's per-entity field NAMES onto upstream's, by offset.

Both trees describe the same bytes after the collision header (0xB4..), but the
fork names them once per entity KIND -- `struct Projectile { ...; u8 work[4];
struct Coord prevCoord; u32 unk_c0; }` -- while upstream lets each source file
declare its own struct over those bytes with its own names. So a lifted body
says `p->prevCoord` and the file's struct has never heard of it.

fix_buffer_offsets already handles the blob form (`(p->props).raw[0x20]`). This
handles the named form: look up the field's offset in the fork's struct for this
entity kind, then emit whatever upstream's struct calls the field covering that
offset.

The entity kind comes from the source path (`src/projectile/...` ->
`struct Projectile`). Both trees lay their own fields out starting at 0xB4, so
neither side needs sizeof(Body) -- the leading `struct Entity s; struct Body
body;` / `COLLISION_OBJECT_HDR;` is skipped and the walk starts at 180.

Nothing is rewritten unless the fork offset resolves EXACTLY onto one upstream
field: a near miss here compiles and reads the wrong bytes, and only the ROM
compare would catch it.
"""
import glob
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_buffer_offsets as BO  # noqa: E402

BASE = 180  # 0xB4, where every entity's own fields begin

KIND = {'projectile': 'Projectile', 'boss': 'Boss', 'enemy': 'Enemy',
        'weapon': 'Weapon', 'vfx': 'VFX', 'solid': 'Solid',
        'cyberelf': 'Elf', 'pickup': 'Pickup'}


def _typedef_sizes():
    """Scalar typedefs resolved to their underlying size.

    The game types its fields with names like `motion_t`, `motion_sub_id_t` and
    `metatile_attr_t`. Without these the field walk hits an unknown type, gives
    up on the whole struct, and the caller silently falls back to the generic
    entity struct -- so `struct MobObject`'s `m_c0`/`m_c2` were never mapped."""
    out = dict(BO.SIZES)
    for h in glob.glob('include/**/*.h', recursive=True):
        with open(h, encoding='utf-8', errors='replace') as fh:
            for ln in fh:
                m = re.match(r'\s*typedef\s+(\w+)\s+(\w+)\s*;', ln)
                if m and m.group(1) in out:
                    out.setdefault(m.group(2), out[m.group(1)])
    # Two passes: a typedef of a typedef only resolves once the first is known.
    for _ in range(2):
        for h in glob.glob('include/**/*.h', recursive=True):
            with open(h, encoding='utf-8', errors='replace') as fh:
                for ln in fh:
                    m = re.match(r'\s*typedef\s+(\w+)\s+(\w+)\s*;', ln)
                    if m and m.group(1) in out:
                        out.setdefault(m.group(2), out[m.group(1)])
    return out


SIZES = {}


def own_fields(body):
    """(offset, name, elemsize, count) for the struct's OWN fields, i.e. the
    ones after the shared header, walked from 0xB4."""
    out, off = [], BASE
    for ln in body.splitlines():
        s = ln.strip()
        if not s or s.startswith('//') or s.startswith('/*') or s.startswith('}'):
            continue
        if re.match(r'(union|struct)\s*\{', s):
            return None                      # anonymous aggregate: give up
        # Any bare `SOMETHING_HDR;` is a shared-header macro, not a field. The
        # fork still uses `OBJECT_HDR`, which upstream removed, and listing the
        # macros by name missed it -- so parsing bailed out and every enemy file
        # reported "no fork struct Enemy" as if the header were missing.
        if re.match(r'(?:struct\s+)?(?:Entity|Body)\s+\w+\s*;', s) or \
           re.match(r'\w*_HDR\s*;', s):
            continue                         # shared header, already accounted
        m = BO.FIELD.match(ln)
        if not m:
            return None
        ty, ptr, nm, dim, _ = m.groups()
        esz = 4 if ptr else SIZES.get(ty)
        if esz is None:
            if ty in ('Coord', 'Coords32', 'PixelCoords'):
                esz = 8                      # two s32s, treated as one unit
            else:
                return None
        try:
            cnt = int(dim, 0) if dim else 1
        except ValueError:
            return None
        off += (-off) % min(esz, 4)
        out.append((off, nm, esz, cnt, ty))
        off += esz * cnt
    return out


def bodies_of(txt, names):
    """(start, end) of each named function's definition.

    Every rewrite below must stay inside the bodies actually being LIFTED.
    Applied file-wide they also edit code upstream has already decompiled:
    `CreateShotcounterBullet` was correct upstream with `p->work[0]` -- the
    Entity header's work[4] at 0x10 -- and the mapper reinterpreted it as the
    fork Projectile's own work[4] at 0xB4 and wrote `p->buffer[0]`. Silently
    rewriting a neighbour's working code is worse than failing to port.
    """
    spans = []
    for m in re.finditer(r'^[A-Za-z_][\w \*]*\b(\w+)\s*\([^;{)]*\)\s*\{',
                         txt, re.M):
        if m.group(1) not in names:
            continue
        depth, st = 0, txt.index('{', m.start())
        for j in range(st, len(txt)):
            if txt[j] == '{':
                depth += 1
            elif txt[j] == '}':
                depth -= 1
                if depth == 0:
                    spans.append((m.start(), j + 1))
                    break
    return spans


def scoped_sub(pat, fn, txt, spans, restrict):
    """re.sub, but only inside `spans`.

    FAILS CLOSED. The first version treated an empty span list as "no
    restriction" and rewrote the whole file -- so whenever the lifted functions
    were not located, the pass quietly went back to editing upstream's existing
    code. That is how `CreateShotcounterBullet`'s correct `p->work[0]` kept
    becoming `p->buffer[0]` even after the scoping was added. No spans now means
    no rewrites."""
    if restrict:
        if not spans:
            sys.stderr.write('    no lifted bodies located; skipping\n')
            return txt
    elif not spans:
        return re.sub(pat, fn, txt)
    out, pos = [], 0
    for a, b in sorted(spans):
        out.append(txt[pos:a])
        out.append(re.sub(pat, fn, txt[a:b]))
        pos = b
    out.append(txt[pos:])
    return ''.join(out)


def main():
    global SIZES
    SIZES = _typedef_sizes()
    src = sys.argv[1]
    lifted = set(sys.argv[2:])
    kind = None
    for part in src.replace('\\', '/').split('/'):
        if part in KIND:
            kind = KIND[part]
            break
    if not kind:
        print('  field offsets: no entity kind for %s' % src)
        return

    with open(src, encoding='utf-8', errors='replace') as fh:
        txt = fh.read()

    r = subprocess.run(['git', 'show',
                        'main:include/entity/%s.h' % kind.lower()],
                       capture_output=True)
    fork_body = (None if r.returncode
                 else r.stdout.decode('utf-8', errors='replace'))
    fork = None
    if fork_body:
        for nm, b in BO._bodies(fork_body):
            if nm == kind:
                fork = own_fields(b)
                break
    # The entity-KIND struct is only the FALLBACK. Returning here when it fails
    # to parse skipped the whole file before fork_for() -- which resolves the
    # file's OWN struct and is the more precise answer -- ever got a chance.
    # `struct Solid` does not parse, and that alone blocked every solid/ file.
    fork_at = {nm: (off, esz, ty) for off, nm, esz, _, ty in (fork or [])}

    # Names that belong to the SHARED header, not to any entity's own fields.
    # Both trees keep these identical, so they must never be remapped: the fork
    # writes `(p->s).work[0]`, which flattens to `p->work[0]` -- the Entity
    # header's work[4] at 0x10. Treating it as the Projectile's own work[4] at
    # 0xB4 rewrote it to `p->unk_b4[0]`, leaving `p->unk_b4[0][0]`, i.e.
    # "subscripted value is neither array nor pointer" pointing at a line the
    # mapper had silently corrupted.
    # Only the MACRO bodies and struct Body count as shared. Sweeping all of
    # entity.h also pulled in `struct Enemy { ...; u8 buffer[16]; }` -- a
    # per-entity field, not a shared one -- so the 0xB4 blob was excluded from
    # the map and `p->buffer[0]` stayed unresolved in every enemy file.
    shared = set()
    for h in ('include/entity/entity.h', 'include/entity/sprite.h',
              'include/collision.h'):
        if not os.path.exists(h):
            continue
        with open(h, encoding='utf-8', errors='replace') as fh:
            txt_h = fh.read()
        blocks = [m.group(0) for m in re.finditer(
            r'#define\s+(?:ENTITY_HDR|ENTITY_SPRITE|COLLISION_OBJECT_HDR)'
            r'(?:.*\\\n)*.*', txt_h)]
        b = re.search(r'struct\s+Body\s*\{(.*?)\n\};', txt_h, re.S)
        if b:
            blocks.append(b.group(1))
        for blk in blocks:
            for ln in blk.replace('\\', '').splitlines():
                d = BO.FIELD.match(ln)
                if d and d.group(1) not in ('return', 'typedef', 'define'):
                    shared.add(d.group(3))
    fork_at = {k: v for k, v in fork_at.items() if k not in shared}
    # `props` has already been renamed to `buffer` by the time this runs, so the
    # text says `buffer` while the fork header still says `props`. Register both
    # spellings against the same offset.
    if 'props' in fork_at:
        fork_at.setdefault('buffer', fork_at['props'])

    cache = {}
    fork_cache = {}
    scope = {}
    changed = skipped = 0

    def fork_for(ty):
        """The fork's own version of upstream type `ty`, when it has one.

        Preferred over the entity-KIND struct: `struct MobObject` is declared in
        mob_npc.c in both trees, and the fork gives 0xC0..0xC3 two named fields
        (`m_c0`, `m_c2`) where upstream has one `u8 unk_0c[4]`. Falling back to
        `struct Solid` cannot express that at all -- the mapping only exists
        between the two spellings of MobObject itself."""
        if ty in fork_cache:
            return fork_cache[ty]
        got = None
        r = subprocess.run(['git', 'grep', '-l', '-F', 'struct %s {' % ty,
                            'main', '--', 'src', 'include'],
                           capture_output=True, text=True)
        for line in r.stdout.splitlines():
            path = line.split(':', 1)[1] if ':' in line else line
            t = subprocess.run(['git', 'show', 'main:' + path],
                               capture_output=True)
            if t.returncode:
                continue
            for nm, b in BO._bodies(t.stdout.decode('utf-8', errors='replace')):
                if nm == ty:
                    f = own_fields(b)
                    if f:
                        got = {n: (o, e, t) for o, n, e, _, t in f}
                    break
            if got:
                break
        fork_cache[ty] = got
        return got

    def sub(m):
        nonlocal changed, skipped
        var, fld = m.group('var'), m.group('fld')
        # A subscript right after the field belongs to subidx, which folds the
        # index into the offset. Rewriting here instead leaves the old
        # subscript stranded on the new name -- `p->props[9]` became
        # `p->unk_b4[0][9]`, which fails as "subscripted value is neither array
        # nor pointer" and reads as a mapper bug rather than a leftover.
        if m.string[m.end():m.end() + 1] == '[':
            return m.group(0)
        ty = scope.get(var) or BO.var_type(txt, var)
        if not ty:
            return m.group(0)
        ent = fork_for(ty) or {}
        at = ent if fld in ent else fork_at
        if fld not in at:
            if os.environ.get('FFO_DEBUG'):
                sys.stderr.write('    miss %s->%s ty=%s at=%d\n'
                                 % (var, fld, ty, len(at)))
            return m.group(0)
        if ty not in cache:
            b = BO.find_struct(ty, src)
            cache[ty] = own_fields(b) if b else None
        up = cache[ty]
        if not up:
            return m.group(0)
        if any(nm == fld for _, nm, _, _, _ in up):
            return m.group(0)                # upstream uses the same name
        off = at[fld][0]
        for uoff, unm, uesz, ucnt, _uty in up:
            if uoff <= off < uoff + uesz * ucnt:
                d = off - uoff
                if d % uesz:
                    break
                i = d // uesz
                changed += 1
                tail = unm if (ucnt == 1 and i == 0) else '%s[%d]' % (unm, i)
                if uesz != at[fld][1]:
                    # The fork's field is wider than the upstream element it
                    # lands in (a motion_t over one byte of `u8 unk_0c[4]`).
                    # Writing through the narrow name compiles and silently
                    # TRUNCATES, so go through a pointer of the original type.
                    return '*(%s*)&%s->%s' % (at[fld][2], var, tail)
                return m.group(0)[:-len(fld)] + tail
        n_ty = at[fld][2]
        changed += 1
        return '*(%s*)((u8*)%s + 0x%X)' % (n_ty, var, off)

    def subxy(m):
        """`(p->prevCoord).x` -- the fork keeps one `struct Coord` where
        upstream declares two separate u32s over the same 8 bytes, so the
        member access has to be resolved too, not just the field name."""
        nonlocal changed
        var, fld, xy = m.group('var'), m.group('fld'), m.group('sub')
        ty = scope.get(var) or BO.var_type(txt, var)
        if not ty:
            return m.group(0)
        ent = fork_for(ty) or {}
        at = ent if fld in ent else fork_at
        if fld not in at or at[fld][1] != 8:
            return m.group(0)
        if ty not in cache:
            b = BO.find_struct(ty, src)
            cache[ty] = own_fields(b) if b else None
        up = cache[ty]
        if not up or any(nm == fld for _, nm, _, _, _ in up):
            return m.group(0)
        off = at[fld][0] + (0 if xy == 'x' else 4)
        for uoff, unm, uesz, ucnt, _uty in up:
            if uoff <= off < uoff + uesz * ucnt and (off - uoff) % uesz == 0:
                i = (off - uoff) // uesz
                changed += 1
                return '%s->%s' % (var, unm if (ucnt == 1 and i == 0)
                                   else '%s[%d]' % (unm, i))
        changed += 1
        return '*(%s*)((u8*)%s + 0x%X)' % (at[fld][2], var, off)

    # Keep the ORIGINAL to compare against. `txt` is reassigned by the first
    # pass, so testing `new != txt` after it would miss a file that only the
    # .x/.y pass touched and silently write nothing.
    def subidx(m):
        """`p->buffer[8]` -- a byte-array field indexed directly. The index is
        part of the offset, so it has to be folded in before the lookup and
        dropped from the output; rewriting the name alone leaves a stray
        subscript on a field that is not an array."""
        nonlocal changed
        var, fld, k = m.group('var'), m.group('fld'), int(m.group('idx'), 0)
        ty = scope.get(var) or BO.var_type(txt, var)
        if not ty:
            return m.group(0)
        ent = fork_for(ty) or {}
        at = ent if fld in ent else fork_at
        if fld not in at or at[fld][1] != 1:
            return m.group(0)
        cast = ''
        if ty == 'Entity':
            ty, cast = kind, '(struct %s*)' % kind
        if ty not in cache:
            b = BO.find_struct(ty, src)
            cache[ty] = own_fields(b) if b else None
        up = cache[ty]
        if not up:
            return m.group(0)
        if any(nm == fld for _, nm, _, _, _ in up):
            return (m.group(0) if not cast
                    else '(%s%s)->%s[%d]' % (cast, var, fld, k))
        off = at[fld][0] + k
        for uoff, unm, uesz, ucnt, _uty in up:
            if uoff <= off < uoff + uesz * ucnt and (off - uoff) % uesz == 0:
                i = (off - uoff) // uesz
                changed += 1
                tgt = unm if (ucnt == 1 and i == 0) else '%s[%d]' % (unm, i)
                return ('(%s%s)->%s' % (cast, var, tgt) if cast
                        else '%s->%s' % (var, tgt))
        # Same unnamed-offset fallback as the other two passes. `p->props[9]`
        # is 0xBD, which upstream's PantheonHunter leaves as padding between
        # `isRight` (0xBC) and `unk_c0` (0xC0) -- no field covers it, so address
        # it directly rather than declaring the cluster unportable.
        changed += 1
        return '*(%s*)((u8*)%s + 0x%X)' % (at[fld][2], var, off)

    def per_function(pat, fn):
        """Apply `fn` inside each function body, with that function's own
        variable types in scope. Honours the lifted-bodies restriction."""
        nonlocal scope
        out, pos = [], 0
        for fm in re.finditer(r'^[A-Za-z_][\w \*]*\b(\w+)\s*\([^;{)]*\)\s*\{',
                              txt_ref[0], re.M):
            body = txt_ref[0]
            depth, st = 0, body.index('{', fm.start())
            en = st
            for j in range(st, len(body)):
                if body[j] == '{':
                    depth += 1
                elif body[j] == '}':
                    depth -= 1
                    if depth == 0:
                        en = j + 1
                        break
            blk = body[fm.start():en]
            out.append(body[pos:fm.start()])
            pos = en
            if lifted and fm.group(1) not in lifted:
                out.append(blk)
                continue
            scope = {}
            for mm in re.finditer(
                    r'\b((?:struct\s+)?\w+)\s*\*\s*(\w+)\s*[,;=){]', blk):
                scope.setdefault(mm.group(2),
                                 re.sub(r'^struct\s+', '', mm.group(1).strip()))
            out.append(re.sub(pat, fn, blk))
        out.append(txt_ref[0][pos:])
        txt_ref[0] = ''.join(out)

    txt_ref = [txt]
    orig = txt
    r = bool(lifted)
    # Drive every pass through per_function so `scope` is populated. Calling
    # scoped_sub here left scope empty, so the type lookup silently fell back
    # to the file-wide answer -- the exact bug this was meant to fix.
    per_function(r'(?P<var>\w+)\s*->\s*(?P<fld>\w+)\s*\[\s*'
                 r'(?P<idx>0[xX][0-9A-Fa-f]+|\d+)\s*\]', subidx)
    per_function(r'\(?\s*(?P<var>\w+)\s*->\s*(?P<fld>\w+)\s*\)?\s*\.\s*'
                 r'(?P<sub>[xy])\b', subxy)
    per_function(r'(?P<var>\w+)\s*->\s*(?P<fld>\w+)\b', sub)
    new = txt_ref[0]
    if new != orig:
        with open(src, 'w', encoding='utf-8', newline='') as fh:
            fh.write(new)
    print('  field offsets: %d rewritten, %d unresolved' % (changed, skipped))


if __name__ == '__main__':
    main()
