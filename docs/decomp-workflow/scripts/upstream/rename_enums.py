#!/usr/bin/env python3
"""Rename enum members the branch's headers spell differently from upstream's.

Taking upstream's include/ wholesale means any enum member the branch named
itself disappears: `MOD_120` is upstream's `MOD_GYRO_CANNON`. Position inside
the enum is the identity -- these are bit indices, so member N is the same value
in both trees regardless of name.

    rename_enums.py <branch> <file.c> [<file.c> ...]

Comparison is positional and guarded: an enum is only used if both trees list
the same NUMBER of members, and a rename is skipped if upstream still uses the
old name elsewhere (it would then be ambiguous). Read from the two trees at
run time, never from a stored table.
"""
import re
import subprocess
import sys

ENUM = re.compile(r'enum\s+(\w+)?\s*\{(.*?)\}\s*;', re.S)


KEYWORDS = {'void', 'int', 'char', 'struct', 'union', 'enum', 'const',
            'static', 'unsigned', 'signed', 'return', 'u8', 'u16', 'u32',
            's8', 's16', 's32', 'bool8', 'extern', 'typedef'}


def members(body):
    """Member names in order, ignoring comments and explicit values.

    C keywords are rejected outright: the non-greedy `enum ... { ... }` scan
    can overrun into unrelated code, and a mis-parse once produced the
    positional pair `void` -> `_`, which then rewrote `void RenderWipeZ(...)`
    into `_ RenderWipeZ(...)` in script.c. An enum member that spells a
    keyword is a parse error, never a rename candidate."""
    out = []
    for ln in body.splitlines():
        s = re.sub(r'//.*|/\*.*?\*/', '', ln).strip()
        if not s:
            continue
        for part in s.split(','):
            part = part.strip()
            if not part:
                continue
            m = re.match(r'^([A-Za-z_]\w*)\s*(?:=.*)?$', part)
            if m:
                if m.group(1) in KEYWORDS:
                    return []          # overran into real code: reject block
                out.append(m.group(1))
    return out


def sh(*a):
    r = subprocess.run(a, capture_output=True)
    return None if r.returncode else r.stdout.decode('utf-8', errors='replace')


def main():
    branch, files = sys.argv[1], sys.argv[2:]

    headers = (sh('git', 'ls-tree', '-r', '--name-only', 'upstream/dev',
                  'include/') or '').split()
    renames, up_names = {}, set()
    for h in headers:
        if not h.endswith('.h'):
            continue
        up = sh('git', 'show', 'upstream/dev:' + h)
        fk = sh('git', 'show', '%s:%s' % (branch, h))
        if up is None or fk is None:
            continue
        ue = {m.group(1) or i: members(m.group(2))
              for i, m in enumerate(ENUM.finditer(up))}
        fe = {m.group(1) or i: members(m.group(2))
              for i, m in enumerate(ENUM.finditer(fk))}
        for k, ulist in ue.items():
            up_names.update(ulist)
            flist = fe.get(k)
            if not flist or len(flist) != len(ulist):
                continue
            for a, b in zip(flist, ulist):
                if a != b:
                    renames.setdefault(a, b)

    for a in [a for a in renames if a in up_names]:
        del renames[a]          # upstream still uses the old name: ambiguous

    total = 0
    for f in files:
        with open(f, encoding='utf-8', errors='replace') as fh:
            txt = fh.read()
        n = 0
        for a, b in renames.items():
            txt, k = re.subn(r'\b%s\b' % re.escape(a), b, txt)
            n += k
        if n:
            with open(f, 'w', encoding='utf-8', newline='') as fh:
                fh.write(txt)
        total += n
    print('  enum members: %d rewritten (%d rename(s) known)'
          % (total, len(renames)))


if __name__ == '__main__':
    main()
