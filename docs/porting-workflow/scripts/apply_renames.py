#!/usr/bin/env python3
"""Apply the confirmed fork->upstream symbol renames to a ported file.

Each was established by matching ROM addresses, not by guessing. A missed rename
is invisible to the byte probe (BL targets are masked as relocations) and only
shows up as an undefined reference at link time.

usage: apply_renames.py <src.c> [<src.c> ...]
"""
import io
import re
import sys

FN = {
    'UpdateMotionGraphic': 'UpdateEntityAnim',   # 0x0801765C
    'CalcFromCamera': 'Camera_GetDistance',      # 0x0801A810
    'FUN_080b145c': 'CreateProjectile43',        # 0x080B145C
}

for src in sys.argv[1:]:
    s = io.open(src, encoding='utf-8', errors='replace', newline='').read()
    hits = []
    for old, new in FN.items():
        n = len(re.findall(r'\b%s\b' % re.escape(old), s))
        if n:
            s = re.sub(r'\b%s\b' % re.escape(old), new, s)
            hits.append('%s->%s x%d' % (old, new, n))
    # upstream signatures differ for these two
    s = re.sub(r'ApplyElementEffect\(([^,]+),\s*&(\w+)->s,',
               r'ApplyElementEffect(\1, (struct CollisionObject*)\2,', s)
    s = re.sub(r'\(\*\(struct VFX\*\*\)', '(*(struct Entity**)', s)
    s = re.sub(r'TryDropZakoDisk\((\w+),', r'TryDropZakoDisk(&\1->s,', s)
    io.open(src, 'w', encoding='utf-8', newline='').write(s)
    if hits:
        print('   %-40s %s' % (src, ', '.join(hits)))
