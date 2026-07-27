#!/usr/bin/env python3
"""Rename struct tags the fork spells differently from upstream.

Both entries were confirmed by reading upstream's headers, not from notes:
  * `struct Elf` -- upstream declares `typedef struct CyberElf { ... } CyberElf;`
    in include/entity/entity.h; `Elf` exists nowhere there.
  * `struct CollidableEntity` -- upstream's include/element.h declares
    `ApplyElementEffect(u8, struct CollisionObject*, const struct Coord*)`.

Left as `struct X` rather than switched to the typedef: the tag form is valid,
minimises the diff, and the typedef question is the maintainer's to decide.
"""
import io
import re
import sys

RENAMES = {
    'Elf': 'CyberElf',
    'CollidableEntity': 'CollisionObject',
}


def main():
    src = sys.argv[1]
    s = io.open(src, encoding='utf-8', errors='replace').read()
    n = 0
    for old, new in RENAMES.items():
        s, k = re.subn(r'\bstruct\s+%s\b' % re.escape(old), 'struct ' + new, s)
        n += k
    io.open(src, 'w', encoding='utf-8', newline='').write(s)
    print('  fork type names: %d rewritten' % n)


if __name__ == '__main__':
    main()
