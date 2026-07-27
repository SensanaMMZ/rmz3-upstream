#!/usr/bin/env python3
"""Count undeclared asm on upstream/dev, and how much open PRs already claim.

Three numbers, each computed from the tree at run time:
  * functions still `thumb_func_start` in dev's asm/*.inc
  * of those, defined as REAL C (not NAKED/INCCODE/NON_MATCH) on at least one
    open PR branch -> lands when PRs merge
  * the remainder = genuinely unclaimed work

    undecl_recount.py <branch1> [<branch2> ...]
"""
import re
import subprocess
import sys

START = re.compile(r'^\tthumb_func_start (\S+)', re.M)
DEF = re.compile(r'^(?!.*\b(?:NAKED|WIP|INCCODE|NON_MATCH)\b)'
                 r'[A-Za-z_][\w \*]*?\b(\w+)\s*\([^;{)]*\)\s*\{', re.M)


def sh(*a):
    r = subprocess.run(a, capture_output=True)
    return None if r.returncode else r.stdout.decode('utf-8', errors='replace')


def main():
    branches = [b.strip() for b in sys.argv[1:] if b.strip()]

    asm = set()
    for f in (sh('git', 'ls-tree', '-r', '--name-only', 'upstream/dev', 'asm/')
              or '').split():
        if f.endswith('.inc'):
            asm |= set(START.findall(sh('git', 'show', 'upstream/dev:' + f)
                                     or ''))

    claimed = set()
    for b in branches:
        files = (sh('git', 'diff', '--name-only', 'upstream/dev', b,
                    '--', 'src') or '').split()
        for f in files:
            if not f.endswith('.c'):
                continue
            txt = sh('git', 'show', '%s:%s' % (b, f))
            if txt is None:
                continue
            base = sh('git', 'show', 'upstream/dev:%s' % f) or ''
            have = set(DEF.findall(base))
            claimed |= set(DEF.findall(txt)) - have

    both = asm & claimed
    print('functions still asm on upstream/dev: %d' % len(asm))
    print('claimed as real C by open PRs:       %d' % len(both))
    print('UNCLAIMED (nobody has them):         %d' % len(asm - claimed))


if __name__ == '__main__':
    main()
