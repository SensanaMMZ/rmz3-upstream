#!/usr/bin/env python3
"""Rewrite lifted fork C into upstream conventions, scoped to the lifted functions.

Scoping matters: a blanket regex over the whole file once rewrote `p->work[]` to
`p->buffer[]` inside pre-existing upstream code, where `p` was an `Entity*` that
has no `buffer` member. Only ever touch the brace-range of the functions we
inserted.

Rules (from the upstream dev's structure policy):
  * flattened types (Boss/Projectile/Weapon/CyberElf/FlopperObject/VFX50) use
    `p->x`; nested ones (Enemy/VFX/Solid) keep `(p->s).x`
  * `taskCol` is `renderPrio`
  * the entity's own props area is `buffer[]`
  * INIT_<KIND>_ROUTINE already emits renderPrio + routine + tileNum/palID
    (+ WHITE_PAINTABLE/invincibleID for ENEMY) -- writing those out again
    duplicates the stores
  * on a flattened type, the entity-local `p->work[]` (0xB4) must become
    `buffer[]` BEFORE flattening, or it collides with the entity work[] at 0x10

usage: adapt_up.py <src.c> flat|nested <old-type> <new-type> <fn> [<fn> ...]
"""
import io
import re
import sys


def convert(body, flat, old_ty, new_ty):
    if flat:
        # entity-local work[]/props[] first, while (p->s) still disambiguates
        body = re.sub(r'(?<!s\))\bp->work\[', 'p->buffer[', body)
        body = re.sub(r'(?<!s\))\bp->props\[', 'p->buffer[', body)
    else:
        body = re.sub(r'\bp->props\[', 'p->buffer[', body)
    if old_ty and new_ty:
        body = body.replace(old_ty, new_ty)
    if flat:
        body = body.replace('&p->s', '(struct Entity*)p').replace('(p->s).', 'p->')
    body = body.replace('.taskCol', '.renderPrio').replace('->taskCol', '->renderPrio')
    # collapse the hand-written preamble that INIT_*_ROUTINE already covers
    body = re.sub(r' *[\w>().s-]+[.>]+renderPrio = \d+;\n(?= *INIT_\w+_ROUTINE)', '', body)
    body = re.sub(
        r'( *INIT_\w+_ROUTINE\([^;]*\);\n)'
        r'(?: *[\w>().s-]+[.>]+tileNum = 0(?:, *[\w>().s-]+[.>]+palID = 0)?;\n)?'
        r'(?: *[\w>().s-]+[.>]+palID = 0;\n)?'
        r'(?: *[\w>().s-]+[.>]+flags2 \|= WHITE_PAINTABLE;\n)?'
        r'(?: *[\w>().s-]+[.>]+invincibleID = [\w>().s-]+[.>]+uniqueID;\n)?',
        lambda m: m.group(1), body)
    return body


def main():
    src, mode = sys.argv[1], sys.argv[2]
    old_ty, new_ty = sys.argv[3], sys.argv[4]
    fns = sys.argv[5:]
    flat = mode == 'flat'
    if old_ty == '-':
        old_ty = new_ty = None

    s = io.open(src, encoding='utf-8', errors='replace', newline='').read()
    for fn in fns:
        m = re.search(r'^[A-Za-z_][\w \*]*\b%s\([^)]*\)\s*\{' % re.escape(fn), s, re.M)
        if not m:
            print('   !! %s not found in %s' % (fn, src))
            continue
        d = 0
        end = None
        for j in range(m.end() - 1, len(s)):
            if s[j] == '{':
                d += 1
            elif s[j] == '}':
                d -= 1
                if d == 0:
                    end = j + 1
                    break
        s = s[:m.start()] + convert(s[m.start():end], flat, old_ty, new_ty) + s[end:]
    io.open(src, 'w', encoding='utf-8', newline='').write(s)
    print('   adapted %-38s %s (%d fn)' % (src, mode, len(fns)))


main()
