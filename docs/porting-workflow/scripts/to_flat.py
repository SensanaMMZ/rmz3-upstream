#!/usr/bin/env python3
"""Convert ported functions to the upstream flat-struct style.

Upstream's house style (stated by the maintainer, and used by every recent
file) is a flat typedef built on COLLISION_OBJECT_HDR:

    typedef struct {
      COLLISION_OBJECT_HDR;   // 0x00
      struct Entity* elfx;    // 0xB4
    } Childre;
    static_assert(sizeof(Childre) == sizeof(Boss));

so members are reached directly -- `p->mode[1]`, `p->body`, `p->coord.x` --
never through a nested `(p->s).mode[1]`. Entity helpers are reached through the
wrapper macros in the headers, which do the cast themselves:
`SetSpriteAnimation(p, id)` rather than `SetMotion(&p->s, id)`.

Ported code arrives in the fork's nested style, and mixing the two in one file
is not just untidy: the file's own `static void (*const sUpdates1[9])(Fist*)`
tables then get handed a `struct Enemy*`, which is a hard -Werror failure.

Flattening is codegen-neutral -- same offsets, same instructions -- so a
byte-verified function stays byte-verified.

Only functions this branch ADDED are touched. Pre-existing upstream C is
already in the right style, and rewriting it has corrupted correct code before.

usage: to_flat.py <file.c> [<flat-typedef-name>]
"""
import io
import re
import subprocess
import sys

# `&p->s` handed to an entity helper becomes the wrapper macro that casts.
WRAPPERS = {
    'UpdateEntityAnim': ('UpdateSpriteAnimation', 1),
    'SetMotion': ('SetSpriteAnimation', 2),
    'GotoMotion': ('GotoSpriteAnimation', 4),
    'ResetDynamicMotion': ('SetSpriteTableDynamic', 1),
    'InitNonAffineMotion': ('EnableSpriteAnimation_Normal', 1),
    'InitRotatableMotion': ('EnableSpriteAnimation_Rotatable', 1),
    'InitScalerotMotion1': ('EnableSpriteAnimation_Affine', 1),
    'isKilled': ('IsDead', 1),
    'TryDropZakoDisk': ('DropEnemyDisk', 2),
}
# Helpers already taking void*/Object* -- the bare pointer is enough.
VOIDISH = {'IsFrozen'}

# Types that are FLAT on upstream/dev a4dff327 -- a parameter declared as one of
# these with `(p->s).x` inside is a genuine compile error after a rebase, not a
# style nit. Enemy/VFX/Solid/Widget are still nested and must NOT be converted.
NESTED_TYPES = r'struct\s+(?:Boss|Projectile|Weapon|CyberElf|Pickup)\s*\*'


def added_line_set(path):
    d = subprocess.run(['git', 'diff', 'upstream/dev', '--', path],
                       capture_output=True, text=True, errors='replace').stdout
    return {l[1:].rstrip('\r\n') for l in d.split('\n')
            if l.startswith('+') and not l.startswith('+++')}


def find_flat_type(text):
    m = re.search(r'typedef\s+struct\s*\{[^}]*COLLISION_OBJECT_HDR[^}]*\}\s*(\w+)\s*;',
                  text, re.S)
    return m.group(1) if m else None


def func_ranges(lines, added):
    """(start, end, [vars]) per added function.

    `vars` is every identifier in that function holding a now-flat type --
    parameters AND locals. Locals matter: `CopyX_OnDamage(struct Body* body)`
    takes a Body, then does `struct Boss* self = (struct Boss*)body->parent;`
    and reaches through `(self->s).coord`. A parameter-only scan leaves those
    behind and the file still will not compile.
    """
    out = []
    for i, line in enumerate(lines):
        if line.rstrip('\r') not in added:
            continue
        m = re.match(r'^[A-Za-z_][\w \*]*?\b\w+\s*\((.*)\)\s*\{\s*$', line)
        if not m:
            continue
        depth, j = 0, i
        while j < len(lines):
            depth += lines[j].count('{') - lines[j].count('}')
            if depth <= 0 and j > i:
                break
            j += 1
        names = [v for v in re.findall(NESTED_TYPES + r'\s*(\w+)', m.group(1))]
        for k in range(i + 1, min(j + 1, len(lines))):
            names += re.findall(NESTED_TYPES + r'\s*(\w+)\s*[=;]', lines[k])
        if names:
            out.append((i, j, list(dict.fromkeys(names))))
    return out


def main():
    path = sys.argv[1]
    text = io.open(path, encoding='utf-8', newline='').read()
    # No file-local typedef is fine: `struct Boss*` is itself flat on current
    # upstream/dev, so the parameter type stays and only the accesses change.
    # Retyping to a file-local typedef is an extra nicety, not the fix.
    flat = sys.argv[2] if len(sys.argv) > 2 else find_flat_type(text)

    added = added_line_set(path)
    lines = text.split('\n')
    ranges = func_ranges(lines, added)
    if not ranges:
        print('  %s: no nested-style added functions' % path)
        return 0

    changed = 0
    for start, end, vars_ in ranges:
      for var in vars_:
        v = re.escape(var)
        for i in range(start, min(end + 1, len(lines))):
            orig = lines[i]
            s = orig
            if i == start and flat:
                # the signature itself: struct Boss* p  ->  Phantom* p
                s = re.sub(NESTED_TYPES + r'(\s*' + v + r'\b)',
                           flat + r'*\1', s)
            # helper(&p->s, ...) -> wrapper(p, ...) / helper(p, ...)
            for fn, (wrap, _) in WRAPPERS.items():
                s = re.sub(r'\b%s\s*\(\s*&%s->s\s*(,|\))' % (re.escape(fn), v),
                           lambda m, w=wrap: '%s(%s%s' % (w, var, m.group(1)), s)
            for fn in VOIDISH:
                s = re.sub(r'\b%s\s*\(\s*&%s->s\s*\)' % (re.escape(fn), v),
                           '%s(%s)' % (fn, var), s)
            # (p->s).member -> p->member ; p->s.member -> p->member
            s = re.sub(r'\(\s*%s->s\s*\)\.' % v, '%s->' % var, s)
            s = re.sub(r'\b%s->s\.' % v, '%s->' % var, s)
            # any remaining &p->s handed to something expecting an Entity*
            s = re.sub(r'&%s->s\b' % v, '(struct Entity*)%s' % var, s)
            if s != orig:
                lines[i] = s
                changed += 1
    if changed:
        io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
    print('  %-44s %d line(s), %d function(s)%s'
          % (path, changed, len(ranges), ' -> ' + flat if flat else ''))
    return 0


sys.exit(main())
