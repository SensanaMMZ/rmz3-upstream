#!/usr/bin/env python3
"""Re-add type definitions a branch contributes that upstream's headers lack.

Taking upstream's `include/` wholesale is right for the fork's *spellings*
(`Weapon*` vs `struct Weapon*`, the removed `OBJECT_HDR`), but it is too blunt
on its own: some branches also add genuinely new declarations. `struct Omega1`
exists in the branch's `include/boss/omega1.h` and nowhere in upstream's, so
reverting the header deletes real work and every user of it fails with
"dereferencing pointer to incomplete type".

So: after the revert, copy back any struct/union/enum the branch defined and
upstream does not. Definitions are matched by NAME, and only whole brace-matched
blocks are moved, so nothing is reflowed or half-copied.

    preserve_header_additions.py <branch>
"""
import io
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OPEN = re.compile(r'(?:typedef\s+)?(?:struct|union|enum)(?:\s+(\w+))?\s*\{')


def blocks(txt):
    """name -> full text of each definition, brace-matched."""
    out = {}
    for m in OPEN.finditer(txt):
        depth, st = 0, txt.index('{', m.start())
        for j in range(st, len(txt)):
            if txt[j] == '{':
                depth += 1
            elif txt[j] == '}':
                depth -= 1
                if depth == 0:
                    end = txt.find(';', j)
                    whole = txt[m.start():end + 1 if end > 0 else j + 1]
                    tail = re.match(r'\s*(\w+)\s*;', txt[j + 1:])
                    name = m.group(1) or (tail.group(1) if tail else None)
                    if name:
                        out[name] = whole
                    break
    return out


def sh(*a):
    r = subprocess.run(a, capture_output=True)
    return None if r.returncode else r.stdout.decode('utf-8', errors='replace')


import rename_fork_types as RF  # noqa: E402


def main():
    branch = sys.argv[1]
    headers = (sh('git', 'ls-tree', '-r', '--name-only', branch, 'include/')
               or '').split()

    # A type is "missing" only if NO upstream header declares it, under either
    # its tag or its typedef name. Checking just the same file re-added `Object`
    # into entity.h alongside upstream's own `typedef struct CollisionObject
    # {...} Object;`, giving "conflicting types for `Object'" -- a break caused
    # by the repair, not by the branch.
    upstream_names = set()
    for h in headers:
        if not h.endswith('.h') or not os.path.exists(h):
            continue
        with io.open(h, encoding='utf-8', errors='replace') as fh:
            t = fh.read()
        upstream_names |= set(blocks(t))
        upstream_names |= set(re.findall(r'\}\s*(\w+)\s*;', t))

    added = 0
    for h in headers:
        if not h.endswith('.h') or not os.path.exists(h):
            continue
        fk = sh('git', 'show', '%s:%s' % (branch, h))
        if fk is None:
            continue
        with io.open(h, encoding='utf-8', errors='replace') as fh:
            up = fh.read()
        have, want = blocks(up), blocks(fk)
        missing = [n for n in want
                   if n not in have and n not in upstream_names
                   and n not in RF.RENAMES
                   and not re.search(r'\}\s*%s\s*;' % re.escape(n), up)]
        if not missing:
            continue
        # Append before the include guard's #endif so ordering stays sane.
        extra = '\n' + '\n\n'.join(want[n] for n in missing) + '\n'
        idx = up.rfind('#endif')
        up = (up[:idx] + extra + up[idx:]) if idx > 0 else up + extra
        with io.open(h, 'w', encoding='utf-8', newline='') as fh:
            fh.write(up)
        added += len(missing)
        sys.stderr.write('    %s: re-added %s\n' % (h, ', '.join(missing)))
    print('  header additions preserved: %d' % added)


if __name__ == '__main__':
    main()
