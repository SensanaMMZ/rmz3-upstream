#!/usr/bin/env python3
"""File-specific fixes that are too particular to generalise.

Kept as a script rather than hand-edits so a clean re-run of the chain does not
lose them -- `git checkout -- .` between passes silently reverted these four
more than once, which reads as the fixers regressing when they have not.

Each is idempotent and a no-op on files that do not need it.
"""
import io
import os
import re
import sys


def locomoif(s):
    # struct LocomoIFPlatformObject was a fork-only view whose `unk_00` sat at
    # 0xB4 -- exactly what upstream's LocomoIFPlatform calls `unk_b4`. Upstream
    # never defined the extra struct, so it is an incomplete type here.
    if 'LocomoIFPlatformObject' not in s:
        return s
    s = re.sub(r'\n\s*struct LocomoIFPlatformObject\* obj = '
               r'\(struct LocomoIFPlatformObject\*\)p;', '', s)
    return s.replace('obj->unk_00', 'p->unk_b4')


def zako_disk(s):
    # The fork declares TryDropZakoDisk(struct Enemy*, struct Coord*); upstream
    # has TryDropZakoDisk(struct Entity*, Coords32*) plus a DropEnemyDisk macro
    # that casts. Keeping the local declaration is a `conflicting types` error.
    if 'TryDropZakoDisk' not in s:
        return s
    # `extern` too -- ported files use both spellings, and matching only the
    # bare `void` left the extern ones declaring a conflicting signature.
    s = re.sub(r'^\s*(?:extern\s+)?void TryDropZakoDisk\([^;]*\);\n', '', s,
               flags=re.M)
    return re.sub(r'\bTryDropZakoDisk\(\s*(\w+)\s*,', r'DropEnemyDisk(\1,', s)


def entity_arg(s):
    # FUN_08088ba8 takes a plain struct Entity*; callers now hold the file's own
    # flat type. Every entity type begins with an Entity, so name the cast.
    return re.sub(r'\bFUN_08088ba8\(\s*(\w+)\s*\)',
                  r'FUN_08088ba8((struct Entity*)\1)', s)


def body_handler_signature(s):
    """A collision handler must match BodyFunc, which takes THREE parameters.

        typedef void (*BodyFunc)(struct Body*, Coords32*, Coords32*);

    The fork declares these with just the Body*, so `INIT_BODY(p, ..., handler)`
    reports "assignment from incompatible pointer type" where the macro does
    `body->fn = handler`. Upstream writes the extra two out and marks them
    UNUSED (see Childre_OnCollision). The added parameters arrive in r1/r2 and
    are never read, so the generated code is unchanged.
    """
    handlers = set(re.findall(r'INIT_BODY\([^,]+,[^,]+,[^,]+,\s*(\w+)\s*\)', s))
    handlers.discard('NULL')
    for h in handlers:
        s = re.sub(r'\bvoid\s+%s\(struct Body\* (\w+)\)\s*;' % re.escape(h),
                   r'void %s(struct Body* \1, Coords32* r1 UNUSED, '
                   r'Coords32* r2 UNUSED);' % h, s)
        s = re.sub(r'\bvoid\s+%s\(struct Body\* (\w+)\)\s*\{' % re.escape(h),
                   r'void %s(struct Body* \1, Coords32* r1 UNUSED, '
                   r'Coords32* r2 UNUSED) {' % h, s)
    return s


def hoist_late_proto(s):
    """A prototype that appears AFTER its first use is still implicit."""
    for m in re.finditer(r'^(void\s+(\w+)\(struct \w+\* \w+\);)$', s, re.M):
        proto, name = m.group(1), m.group(2)
        use = s.find(name + '(')
        if use == -1 or s.find(proto) < use:
            continue
        incs = [i.end() for i in re.finditer(r'^#include "[^"]+"\n', s, re.M)]
        if not incs:
            continue
        # AFTER the type definitions, not merely after the includes: the
        # prototype names a file-local struct, and placing it earlier gives
        # "`struct OmegaZX_X' declared inside parameter list" -- a new error in
        # place of the old one.
        at = incs[-1]
        for t in re.finditer(r'^\}\s*\w*\s*;\s*$', s, re.M):
            if t.end() < use:
                at = max(at, t.end() + 1)
        s = s[:at] + '\n' + proto + '\n' + s[at:]
    return s


for path in sys.argv[1:]:
    if not os.path.exists(path):
        continue
    orig = io.open(path, encoding='utf-8', newline='').read()
    s = hoist_late_proto(body_handler_signature(entity_arg(zako_disk(locomoif(orig)))))
    if s != orig:
        io.open(path, 'w', encoding='utf-8', newline='').write(s)
        print('  %s' % path)
