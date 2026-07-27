#!/usr/bin/env python3
"""Drop explicit stores that upstream's INIT_*_ROUTINE macros already perform.

Upstream: INIT_PROJECTILE_ROUTINE(p, n) -> INIT_RENDER_ENTITY(8, ...) which
writes renderPrio = 8, runs INIT_ENTITY_ROUTINE, then tileNum = 0, palID = 0.
The fork's macro of the same name only runs INIT_ENTITY_ROUTINE, so fork bodies
spell the other three out. Lifted verbatim, the body then stores tileNum twice
-- 4 extra bytes that read as "this function does not fit" and got whole
functions dropped from PRs #83/#84/#91/#92/#96.

The ROM's own instruction order (renderPrio, id, onUpdate, tileNum, palID) IS
the upstream macro's expansion, so deleting the explicit stores is not a
guess; it reproduces the original codegen.

Per macro, the render prio is read from upstream's headers at run time. The
explicit renderPrio store is only removed when its value equals the macro's
hardcoded one; tileNum/palID only when assigned literal 0 near the macro call.
"""
import glob
import io
import re
import sys


def macro_prios():
    """INIT_<KIND>_ROUTINE -> (render prio, is_object) from upstream headers.

    Two wrapper families: INIT_RENDER_ENTITY writes renderPrio/tileNum/palID;
    INIT_OBJECT_ENTITY additionally does `flags2 |= WHITE_PAINTABLE` and
    `invincibleID = uniqueID` (confirmed in include/entity/macros.h). The fork
    spells all of those out, so each family has its own duplicate set."""
    out = {}
    for h in glob.glob('include/**/*.h', recursive=True):
        txt = io.open(h, encoding='utf-8', errors='replace').read()
        for m in re.finditer(
                r'#define\s+(INIT_\w+_ROUTINE)\(([^)]*)\)\s+'
                r'INIT_(RENDER_ENTITY|OBJECT_ENTITY)\((\d+)\s*,', txt):
            out[m.group(1)] = (int(m.group(4)),
                               m.group(3) == 'OBJECT_ENTITY')
    return out


def main():
    src = sys.argv[1]
    prios = macro_prios()
    if not prios:
        print('  init macros: none found')
        return
    txt = io.open(src, encoding='utf-8', errors='replace').read()
    n = 0
    for macro, (prio, is_object) in prios.items():
        for call in list(re.finditer(r'^[ \t]*%s\s*\([^;]*\)\s*;[ \t]*\n'
                                     % re.escape(macro), txt, re.M)):
            # Window: a few lines either side of the call.
            lo = txt.rfind('\n', 0, max(0, call.start() - 250))
            hi = txt.find('\n', min(len(txt), call.end() + 250))
            window = txt[lo:hi]
            neww = window
            # LHS accepts both spellings: flat `p->fld` and nested
            # `(e->s).fld` -- Enemy/VFX/Solid are nested upstream, so their
            # bodies keep the ->s form and the flat-only pattern matched
            # nothing there.
            L = r'^[ \t]*\(?\s*\w+\s*->\s*(?:s\s*\)?\s*\.\s*)?'
            pats = [
                L + r'renderPrio\s*\)?\s*=\s*%d\s*;[ \t]*\n' % prio,
                # The macro's own spelling is a comma pair on one line
                # (`p->tileNum = 0, p->palID = 0;`) and fork bodies use both
                # that and two separate statements -- match the pair first so
                # one removal covers it.
                L + r'tileNum\s*\)?\s*=\s*0\s*,\s*\(?\s*\w+\s*->\s*(?:s\s*\)?\s*\.\s*)?palID\s*\)?\s*=\s*0\s*;[ \t]*\n',
                L + r'tileNum\s*\)?\s*=\s*0\s*;[ \t]*\n',
                L + r'palID\s*\)?\s*=\s*0\s*;[ \t]*\n',
            ]
            if is_object:
                pats += [
                    L + r'flags2\s*\)?\s*\|=\s*(?:WHITE_PAINTABLE|0x10|16)\s*;[ \t]*\n',
                    L + r'invincibleID\s*\)?\s*=\s*\(?\s*\w+\s*->\s*(?:s\s*\)?\s*\.\s*)?uniqueID\s*\)?\s*;[ \t]*\n',
                ]
            for pat in pats:
                neww, k = re.subn(pat, '', neww, count=1, flags=re.M)
                n += k
            if neww != window:
                txt = txt[:lo] + neww + txt[hi:]
    if n:
        io.open(src, 'w', encoding='utf-8', newline='').write(txt)
    print('  init macros: %d duplicate store(s) removed' % n)


if __name__ == '__main__':
    main()
