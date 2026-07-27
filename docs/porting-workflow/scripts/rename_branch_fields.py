#!/usr/bin/env python3
"""Rename struct fields positionally between a BRANCH's headers and the current
(dev) headers.

The conversion takes dev's include/ wholesale, but the branch's .c files were
written against the branch's own header spellings: after_image.h names the
0x74 coord `c` on the branch and `c_74` on dev. Same struct, same offsets,
different names -- so every access breaks with "structure has no member".

This is fix_struct_fields' positional comparison with the pair being
<branch header> vs <working-tree header> instead of <fork> vs <upstream>.
Same guards: identical member counts, stop at the first anonymous aggregate,
skip renames whose old name dev still uses anywhere (ambiguous), skip C
keywords, and resolve variables per FUNCTION.

    rename_branch_fields.py <branch> <file.c> [...]
"""
import io
import re
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_buffer_offsets as BO  # noqa: E402
import fix_struct_fields as FSF  # noqa: E402

KEYWORDS = {'void', 'int', 'char', 'struct', 'union', 'enum', 'const',
            'static', 'return', 'if', 'else', 'while', 'for', 'u8', 'u16',
            'u32', 's8', 's16', 's32', 'bool8'}


HDR_NAMES = None


def _hdr_names():
    """Fields the entity header contributes, read from the working headers."""
    global HDR_NAMES
    if HDR_NAMES is None:
        HDR_NAMES = set()
        for h in ('include/entity/entity.h', 'include/entity/sprite.h'):
            try:
                txt = io.open(h, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            for nm, body in BO._bodies(FSF.expand_macros(txt)):
                if nm in ('Entity', 'CollisionObject'):
                    HDR_NAMES.update(FSF.fields(body))
        HDR_NAMES |= {'s', 'body'}
    return HDR_NAMES


def structs_of(txt):
    """name -> OWN-field list, entity-header fields stripped.

    The branch declares many of these structs NESTED (`struct Entity s;`)
    while dev splices the header flat, so whole-struct positional comparison
    can never align them (1 leading field vs ~27). Stripping the header
    contribution from BOTH sides leaves each struct's own fields, which do
    align positionally -- AfterImage's `c` vs dev's `c_74`."""
    hdr = _hdr_names()
    out = {}
    for nm, body in BO._bodies(FSF.expand_macros(txt)):
        fl = [f for f in FSF.fields(body) if f not in hdr]
        # Validity filter: macro expansion can shed parse garbage (dev's
        # after_image.h yielded phantom fields `R` and `E`). A real field is
        # DECLARED somewhere in the raw, unexpanded text.
        fl = [f for f in fl
              if re.search(r'\b%s\s*(?:\[[^\]]*\])?\s*;' % re.escape(f), txt)]
        out[nm] = fl
    return out


def sh(*a):
    r = subprocess.run(a, capture_output=True)
    return None if r.returncode else r.stdout.decode('utf-8', errors='replace')


def main():
    branch, files = sys.argv[1], sys.argv[2:]
    headers = (sh('git', 'ls-tree', '-r', '--name-only', branch, 'include/')
               or '').split()
    # (type, oldfield) -> newfield, plus dev-side name census for the guard.
    qualified, dev_names = {}, set()
    for h in headers:
        if not h.endswith('.h') or not os.path.exists(h):
            continue
        bt = sh('git', 'show', '%s:%s' % (branch, h))
        with io.open(h, encoding='utf-8', errors='replace') as fh:
            dt = fh.read()
        if bt is None:
            continue
        bs, ds = structs_of(bt), structs_of(dt)
        for nm, dfl in ds.items():
            dev_names.update(dfl)
            bfl = bs.get(nm)
            if not bfl or len(bfl) != len(dfl):
                continue
            for a, b in zip(bfl, dfl):
                if a != b and a not in KEYWORDS and b not in KEYWORDS:
                    qualified[(nm, a)] = b

    # No name-ambiguity guard here: unlike fix_struct_fields' text pass, every
    # rewrite below is scoped to variables of the EXACT struct type, so a
    # common old name (`c`) cannot leak onto another type's access. The guard
    # was inherited anyway and killed the very rename this pass exists for
    # (after_image's `c` -> `c_74`).
    if not qualified:
        print('  branch fields: no renames')
        return

    total = 0
    for f in files:
        try:
            txt = io.open(f, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        n = 0
        out, pos = [], 0
        for fm in re.finditer(r'^[A-Za-z_][\w \*]*\b\w+\s*\([^;{)]*\)\s*\{',
                              txt, re.M):
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
            for mm in re.finditer(
                    r'\b(?:struct\s+)?(\w+)\s*\*\s*(\w+)\s*[,;=){]', blk):
                scope.setdefault(mm.group(2),
                                 re.sub(r'^struct\s+', '',
                                        mm.group(1).strip()))
            for var, ty in scope.items():
                for (t, old), new in qualified.items():
                    if t != ty:
                        continue
                    blk, k = re.subn(
                        r'\b%s\s*->\s*%s\b' % (re.escape(var),
                                               re.escape(old)),
                        '%s->%s' % (var, new), blk)
                    n += k
            out.append(txt[pos:fm.start()])
            out.append(blk)
            pos = en
        out.append(txt[pos:])
        new_txt = ''.join(out)
        if n:
            io.open(f, 'w', encoding='utf-8', newline='').write(new_txt)
        total += n
    print('  branch fields: %d access(es) renamed (%d pair(s))'
          % (total, len(qualified)))


if __name__ == '__main__':
    main()
