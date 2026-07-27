#!/usr/bin/env python3
"""Fix the two porting defects that recur in every batch.

Both are invisible to the byte probe and only surface under the real CFLAGS.

1. ApplyElementEffect. Upstream it is
       struct Entity* ApplyElementEffect(u8, struct CollisionObject*, const struct Coord*)
   The fork narrowed the return to `struct VFX*` and passed `&p->s`. So the
   slot the result is stored in has the wrong pointer type, and arg 2 is a
   `struct Entity*` where a `struct CollisionObject*` is wanted. For a nested
   Enemy the collision object starts at offset 0, so `(Object*)p` is the cast.

2. EnemyFunc tables. `typedef void (*EnemyFunc)(struct Enemy*)`, but plenty of
   the byte-verified handlers really do return bool8 -- that is what the retail
   code does, and the definition is the verified artefact, so the table entry
   gets the cast rather than the function getting a bogus return type. This
   repo already does exactly that for DeleteEntity.

   Every entry in an affected table is cast, not just the ones the compiler
   names: it reports only the first few, so fixing those leaves the rest to
   fail on the next run.

usage: fix_common.py <file.c> ...
"""
import io
import re
import sys


# Struct FIELD renames. These cannot come from the linker-map join that
# apply_map_renames.py uses -- a map lists symbols, not members -- so they have
# to be listed. Each is verified against include/entity/entity.h upstream.
FIELD_RENAMES = {
    'taskCol': 'renderPrio',      # 0x25
    'props': 'buffer',            # the 0xB4 scratch area
}

# A rename is only safe if the file does not itself define that member. A
# per-entity struct names the 0xB4 bytes individually and has neither `props`
# nor `buffer`, so renaming there just swaps one "no member named" error for
# another.
def _renameable(s, old, new):
    if re.search(r'^\s*(?:const\s+)?[\w \*]*\b%s\s*(?:\[[^\]]*\])?\s*;' % re.escape(old),
                 s, re.M):
        return False
    # Also the `} props;` form -- a member declared by CLOSING a nested struct:
    #     struct { struct VFX* elfx; s32 init_y; } props;
    # The pattern above starts at a type name and never matches a line opening
    # with `}`, so these files had their accesses renamed to `buffer` while the
    # declaration stayed `props`, turning a working file into
    # "structure has no member named `buffer'".
    if re.search(r'^\s*\}\s*%s\s*(?:\[[^\]]*\])?\s*;' % re.escape(old), s, re.M):
        return False
    return True


def fix_field_renames(s):
    """Rename struct members the fork and upstream spell differently.

    `p->taskCol = 16` compiles for years in the fork and then reports
    "structure has no member named `taskCol'" upstream, because the field is
    called `renderPrio` there. Nothing in the symbol map can tell you that.
    """
    n = 0
    for old, new in FIELD_RENAMES.items():
        # Skip when this file defines the member itself: a per-entity struct
        # names the 0xB4 bytes individually and has neither `props` nor
        # `buffer`, so renaming there swaps one "no member named" error for
        # another.
        if not _renameable(s, old, new):
            continue
        s2 = re.sub(r'(->|\.)%s\b' % re.escape(old), r'\1' + new, s)
        n += s2 != s
        s = s2
    return s, n


def fix_element_effect(s):
    if 'ApplyElementEffect' not in s:
        return s, 0
    n = 0
    # Everything holding this call's result is a struct Entity* upstream. The
    # slot is spelled several ways -- `(struct VFX**)&p->buffer[8]`,
    # `(struct VFX**)((u8*)p + 0xBC)` -- so retype the pointer itself rather
    # than trying to enumerate the address expressions. Scoped to files that
    # actually call ApplyElementEffect, so an unrelated VFX* is left alone.
    for a, b in (('(struct VFX**)', '(struct Entity**)'),
                 ('struct VFX** ', 'struct Entity** '),
                 ('(struct VFX*)ApplyElementEffect', 'ApplyElementEffect')):
        s2 = s.replace(a, b)
        n += s2 != s
        s = s2
    # locals reading out of such a slot, or taking the result directly
    s2 = re.sub(r'struct VFX\* (\w+) = (\*\w+|ApplyElementEffect)',
                r'struct Entity* \1 = \2', s)
    n += s2 != s
    s = s2
    # arg 2 wants a CollisionObject*. Three spellings reach here: the fork's
    # `&p->s`, whatever the flattener left behind (`(struct Entity*)p`), and a
    # bare pointer.
    s2 = re.sub(r'ApplyElementEffect\(([^,]+),\s*&(\w+)->s\s*,',
                r'ApplyElementEffect(\1, (Object*)\2,', s)
    n += s2 != s
    s = s2
    s2 = re.sub(r'ApplyElementEffect\(([^,]+),\s*\(struct Entity\*\)\s*(\w+)\s*,',
                r'ApplyElementEffect(\1, (Object*)\2,', s)
    n += s2 != s
    s = s2
    # `(struct Entity*)ApplyElementEffect(...)` -- it already returns one
    s2 = s.replace('(struct Entity*)ApplyElementEffect', 'ApplyElementEffect')
    n += s2 != s
    s = s2
    # a bare `struct VFX* e;` declared up front and assigned further down
    for var in set(re.findall(r'\b(\w+)\s*=\s*ApplyElementEffect', s)):
        s2 = re.sub(r'\bstruct VFX\*\s+%s\s*;' % re.escape(var),
                    'struct Entity* %s;' % var, s)
        n += s2 != s
        s = s2
    return s, n


def fix_enemyfunc_tables(s):
    """Cast every entry of a handler table holding a non-void-returning fn.

    Covers EnemyFunc / BossFunc / ProjectileFunc / ... -- all typedef'd as
    `void (*)(struct X*)`, while plenty of the byte-verified handlers really do
    return bool8 or bool32. The definition is the verified artefact, so the
    table entry takes the cast, exactly as this repo already does for
    DeleteEntity.
    """
    bool_fns = set(re.findall(r'^bool(?:8|32)\s+(\w+)\s*\(', s, re.M))
    # Also: any handler whose parameter type is not the one the Func typedef
    # expects. `EnemyFunc` is `void (*)(struct Enemy*)`, so once a handler is
    # retyped to the file's own `PantheonHunter*` the bare entry no longer
    # matches -- same symptom as the bool8 case, same remedy.
    # PROTOTYPES as well as definitions. Most table entries are still assembly,
    # so the .c only declares them -- a definitions-only scan finds nothing and
    # every such table silently goes unfixed.
    defs = {m.group('n'): m.group('t').strip() for m in
            re.finditer(r'^(?:static\s+)?[A-Za-z_][\w \*]*?\b(?P<n>\w+)\s*'
                        r'\(\s*(?P<t>[\w ]+?)\s*\*\s*\w+\s*\)\s*[{;]', s, re.M)}
    out, n = s, 0
    for m in list(re.finditer(
            r'((?:static\s+)?const\s+(?P<ft>\w+)Func\s+\w+\[\d*\]\s*=\s*\{)([^}]*)(\})', s)):
        body = m.group(3)
        entries = [e.strip() for e in body.split(',')]
        want = m.group('ft')          # EnemyFunc -> Enemy
        mismatch = any(e in defs and defs[e] not in ('struct ' + want, want)
                       for e in entries if e)
        if not (mismatch or any(e in bool_fns for e in entries if e)):
            continue
        new_entries = []
        for e in entries:
            if not e:
                continue
            ftype = want + 'Func'
            new_entries.append(e if e.startswith('(') else '(%s)%s' % (ftype, e))
        indent = '\n    '
        newbody = indent + (',' + indent).join(new_entries) + ',\n'
        out = out.replace(m.group(0), m.group(1) + newbody + m.group(4))
        n += 1
    return out, n


def fix_routine_tables(s):
    """Cast the entries of a `const XRoutine gFoo = {...}` designated table.

    `EnemyRoutine` is `EnemyFunc[5]`, i.e. `void (*)(struct Enemy*)`. Once the
    handlers are retyped to the file's own typedef (`PantheonHunter*`), bare
    entries no longer match and every slot reports "initialization from
    incompatible pointer type". Upstream casts these with `(void*)` -- the same
    spelling it already uses for `DeleteEnemy` in the very same tables.

    Only designated `[ENTITY_x] =` entries are touched, so a plain data
    initialiser is never rewritten.
    """
    n = 0
    for m in list(re.finditer(r'(const\s+\w+Routine\s+\w+\s*=\s*\{)([^}]*)(\};)', s)):
        body = m.group(2)
        new = re.sub(r'(\[\s*ENTITY_\w+\s*\]\s*=\s*)(?!\()(\w+)\s*,',
                     r'\1(void*)\2,', body)
        if new != body:
            s = s.replace(m.group(0), m.group(1) + new + m.group(3))
            n += 1
    return s, n


def flatten_local_structs(s):
    """Flatten accesses through any file-local struct built on COLLISION_OBJECT_HDR.

    `fix_object_hdr` only catches structs still spelled with the old
    `OBJECT_HDR`. A file may already declare
    `struct OmegaZX_X { COLLISION_OBJECT_HDR; ... }` -- flat -- while its bodies
    still reach through `(p->s).mode[2]`. Nothing else notices, because the
    struct itself is perfectly valid; only the accesses are wrong.

    Covers both spellings: `struct X { ... }` and `typedef struct { ... } X;`.
    """
    tags = re.findall(r'struct\s+(\w+)\s*\{\s*\n\s*COLLISION_OBJECT_HDR', s)
    tds = re.findall(r'typedef\s+struct\s*\{[^}]*COLLISION_OBJECT_HDR[^}]*\}\s*(\w+)\s*;',
                     s, re.S)
    if not tags and not tds:
        return s, 0
    # Variable names are FUNCTION-scoped. Rewriting every `p->s` in the file
    # because some function has a flat `p` corrupts the next function whose `p`
    # is a genuinely nested `struct Enemy*` -- it turns one error into a
    # different one ("no member `s`" becomes "no member `mode`"). Walk function
    # by function and only rewrite inside the one that declares it.
    decls = ([r'struct\s+%s\s*\*\s*(\w+)\b' % re.escape(t) for t in tags] +
             [r'\b%s\s*\*\s*(\w+)\b' % re.escape(t) for t in tds])
    lines = s.split('\n')
    n, i = 0, 0
    while i < len(lines):
        if not re.match(r'^[A-Za-z_][\w \*]*?\b\w+\s*\(.*\)\s*\{\s*$', lines[i]):
            i += 1
            continue
        depth, j = 0, i
        while j < len(lines):
            depth += lines[j].count('{') - lines[j].count('}')
            if depth <= 0 and j > i:
                break
            j += 1
        block = '\n'.join(lines[i:j + 1])
        names = set()
        for pat in decls:
            names |= set(re.findall(pat, block))
        for var in names:
            v = re.escape(var)
            before = block
            block = re.sub(r'\(\s*%s->s\s*\)\.' % v, '%s->' % var, block)
            block = re.sub(r'\b%s->s\.' % v, '%s->' % var, block)
            block = re.sub(r'&%s->s\b' % v, '(struct Entity*)%s' % var, block)
            n += block != before
        lines[i:j + 1] = block.split('\n')
        i = j + 1
    return '\n'.join(lines), n


def fix_duplicate_work(s):
    """A 0xB4 member named `work` collides once the struct is flattened.

    `ENTITY_HDR` already declares `u8 work[4]` at 0x10. A per-entity struct that
    also names its 0xB4 scratch array `work` was fine while the header was
    nested (they lived in different structs) and is a `duplicate member` error
    the moment COLLISION_OBJECT_HDR inlines the entity fields.

    Rename the 0xB4 one to `buffer` -- the name upstream uses for exactly these
    bytes -- and follow every access through that struct. Doing it the other way
    round would silently alias the entity's own work[] at 0x10.
    """
    n = 0
    for m in re.finditer(r'struct\s+(\w+)\s*\{\s*\n\s*COLLISION_OBJECT_HDR\s*;'
                         r'(?P<body>(?:[^{}]|\{[^{}]*\})*?)\n\};', s):
        if not re.search(r'^\s*u8\s+work\[', m.group('body'), re.M):
            continue
        st = m.group(1)
        newbody = re.sub(r'(^\s*u8\s+)work(\[)', r'\1buffer\2', m.group('body'),
                         flags=re.M)
        s = s.replace(m.group(0), m.group(0).replace(m.group('body'), newbody))
        # Per-function. Collecting the variable NAMES file-wide and then
        # rewriting every `name->work[` is precisely the aliasing this function
        # warns about above: shotcounter_bullet.c declares a `struct Projectile*
        # p` in one function, and that made `p->work[0]` in
        # CreateShotcounterBullet -- where `p` is an `Entity*` and `work` is the
        # entity's own at 0x10 -- get rewritten to `p->buffer[0]`, corrupting
        # code upstream had already decompiled correctly.
        out, pos = [], 0
        for fm in re.finditer(r'^[A-Za-z_][\w \*]*\b\w+\s*\([^;{)]*\)\s*\{',
                              s, re.M):
            depth, bst = 0, s.index('{', fm.start())
            ben = bst
            for j in range(bst, len(s)):
                if s[j] == '{':
                    depth += 1
                elif s[j] == '}':
                    depth -= 1
                    if depth == 0:
                        ben = j + 1
                        break
            blk = s[fm.start():ben]
            out.append(s[pos:fm.start()])
            pos = ben
            for var in set(re.findall(
                    r'struct\s+%s\s*\*\s*(\w+)' % re.escape(st), blk)):
                blk = re.sub(r'\b%s->work\[' % re.escape(var),
                             '%s->buffer[' % var, blk)
            out.append(blk)
        out.append(s[pos:])
        s = ''.join(out)
        # CAST EXPRESSIONS too: `((struct Projectile33x*)p)->work[2]`.
        # These are the common spelling in ported code and they have no declared
        # variable, so a name-based pass misses them entirely. Missing them is
        # not a compile error -- the flattened struct inherits ENTITY_HDR's own
        # `work[4]` at 0x10, so the access silently retargets from 0xB6 to 0x12
        # and every affected function comes out 4 bytes short. Six functions in
        # cubit.c shifted the whole ROM that way while compiling perfectly.
        s = re.sub(r'(\(\s*\(\s*struct\s+%s\s*\*\s*\)[^;]*?\)\s*)->work\['
                   % re.escape(st), r'\1->buffer[', s)
        n += 1
    return s, n


def fix_table_forward_decls(s):
    """Make a table's forward declaration match how it is actually defined.

    Ported files declare `static const BossFunc sDeads[3];` up top but define
    `static void (*const sDeads[3])(Blizzack*) = {...}` once the handlers use the
    file's own typedef. That is `conflicting types`. The definition is the one
    that has to compile against the handlers, so the declaration follows it.
    """
    n = 0
    for m in re.finditer(r'^static\s+(\w+)\s*\(\*const\s+(\w+)\[(\d*)\]\)\s*'
                         r'\((\w+)\s*\*\)', s, re.M):
        ret, name, size, arg = m.groups()
        want = 'static %s (*const %s[%s])(%s*);' % (ret, name, size, arg)
        pat = re.compile(r'^static\s+const\s+\w+Func\s+%s\[\d*\]\s*;'
                         % re.escape(name), re.M)
        if pat.search(s):
            s = pat.sub(want, s)
            n += 1
    return s, n


def fix_collidable_entity(s):
    """`struct CollidableEntity` no longer exists upstream; it is `Object` now.

    The old name was the nested 180-byte collision entity. Upstream replaced it
    with `typedef struct CollisionObject { COLLISION_OBJECT_HDR; } Object;`,
    which is FLAT -- so both the type and every `(p->s).x` through it have to
    change, and `body->parent` (a `struct Entity*`) needs an explicit cast.

    Careful: `DrawCollidableEntity` is a real upstream function whose name
    merely contains the string, so match the struct keyword, not the substring.
    """
    if not re.search(r'\bstruct\s+CollidableEntity\b', s):
        return s, 0
    vars_ = set(re.findall(r'struct\s+CollidableEntity\s*\*\s*(\w+)', s))
    s = re.sub(r'struct\s+CollidableEntity\s*\*\s*(\w+)\s*=\s*(\w+)->parent\s*;',
               r'Object* \1 = (Object*)\2->parent;', s)
    s = re.sub(r'struct\s+CollidableEntity\s*\*', 'Object*', s)
    for v in vars_:
        s = re.sub(r'\(\s*%s->s\s*\)\.' % re.escape(v), '%s->' % v, s)
        s = re.sub(r'\b%s->s\.' % re.escape(v), '%s->' % v, s)
    return s, 1


def fix_object_hdr(s):
    """`OBJECT_HDR` is gone upstream; the replacement is `COLLISION_OBJECT_HDR`.

    They describe the same 180 bytes but differently:

        #define OBJECT_HDR  struct Entity s; struct Body body;      (nested, old)
        #define COLLISION_OBJECT_HDR  ENTITY_HDR; ENTITY_SPRITE; struct Body body;

    So swapping the macro also flattens the struct, and every `(p->s).x` through
    a pointer to it has to follow. A file-local struct still spelled with
    OBJECT_HDR does not even parse against current headers
    ("syntax error before `OBJECT_HDR'").
    """
    names = re.findall(r'struct\s+(\w+)\s*\{\s*\n\s*OBJECT_HDR\s*;', s)
    if not names:
        return s, 0
    s = re.sub(r'(\{\s*\n\s*)OBJECT_HDR(\s*;)', r'\1COLLISION_OBJECT_HDR\2', s)
    for st in names:
        for var in set(re.findall(r'struct\s+%s\s*\*\s*(\w+)' % re.escape(st), s)):
            s = re.sub(r'\(\s*%s->s\s*\)\.' % re.escape(var), '%s->' % var, s)
            s = re.sub(r'\b%s->s\.' % re.escape(var), '%s->' % var, s)
            s = re.sub(r'&%s->s\b' % re.escape(var),
                       '(struct Entity*)%s' % var, s)
    return s, 1


def fix_entity_arg_casts(s):
    """`DeleteBoss(p)` where p is a now-flat Boss* needs the cast upstream uses.

    These helpers take `struct Entity*`. That used to be satisfied implicitly
    because Boss nested an Entity at offset 0; now that Boss is flat it is a
    type error. Upstream writes `DeleteBoss((void*)p)` -- match that spelling.
    """
    n = 0
    for fn in ('DeleteBoss', 'DeleteEnemy', 'DeleteEntity'):
        s2 = re.sub(r'\b%s\(\s*(\w+)\s*\)' % fn, r'%s((void*)\1)' % fn, s)
        n += s2 != s
        s = s2
    return s, n


def main():
    import os
    for path in sys.argv[1:]:
        s = io.open(path, encoding='utf-8', newline='').read()
        # In CONVERSION runs the source is already upstream-idiom; the fork
        # spellings this pass renames (props->buffer, taskCol->renderPrio) can
        # legitimately EXIST there -- WeaponCommon's member is named `props` in
        # BOTH trees, and renaming it broke five weapon files with
        # "structure has no member named `buffer'". Branch-vs-dev renames are
        # rename_branch_fields' job; this pass is for lifted FORK bodies only.
        if os.environ.get('CONV_NO_FIELD_RENAMES'):
            k = 0
        else:
            s, k = fix_field_renames(s)
        s, a = fix_element_effect(s)
        a += k
        s, b = fix_enemyfunc_tables(s)
        s, c = fix_entity_arg_casts(s)
        s, d = fix_collidable_entity(s)
        s, e = fix_object_hdr(s)
        s, g = fix_routine_tables(s)
        s, j = flatten_local_structs(s)
        s, h = fix_duplicate_work(s)
        s, i = fix_table_forward_decls(s)
        a += c + d + e + h + i + j
        b += g
        if a or b:
            io.open(path, 'w', encoding='utf-8', newline='').write(s)
            print('  %-46s element:%d tables:%d' % (path, a, b))
    return 0


sys.exit(main())
