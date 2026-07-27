#!/usr/bin/env python3
import os
"""The next porting queue: functions the FORK has as real C, still asm on
upstream/dev, and claimed by NO open PR.

    portable_next.py <prfork/branch>...   (the open-PR branch list)

Prints the count and a cluster plan (grouped by upstream .inc), sorted by
cluster size so the easy wins are visible.
"""
import collections
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

    # asm on dev, per inc
    fn_inc = {}
    for f in (sh('git', 'ls-tree', '-r', '--name-only', 'upstream/dev',
                 'asm/') or '').split():
        if f.endswith('.inc'):
            for fn in START.findall(sh('git', 'show', 'upstream/dev:' + f)
                                    or ''):
                fn_inc[fn] = f

    # real C in the fork
    fork_c = set()
    for f in (sh('git', 'ls-tree', '-r', '--name-only', 'main', 'src/')
              or '').split():
        if f.endswith('.c'):
            fork_c |= set(DEF.findall(sh('git', 'show', 'main:' + f) or ''))

    # HOMONYM GUARD: if the fork ALSO still has an asm thumb_func with the
    # same name, its C definition is a different function that happens to
    # share the name (static copy in another TU -- e.g. BlizzardArrow_Update:
    # 144-byte static in buster.c vs the 872-byte global still asm in BOTH
    # repos). Matching by name alone queued an unportable cluster.
    fork_asm = set()
    for f in (sh('git', 'ls-tree', '-r', '--name-only', 'main', 'asm/')
              or '').split():
        if f.endswith('.inc') or f.endswith('.s'):
            fork_asm |= set(START.findall(sh('git', 'show', 'main:' + f)
                                          or ''))
    fork_c -= fork_asm

    # claimed by open PRs
    claimed = set()
    for b in branches:
        for f in (sh('git', 'diff', '--name-only', 'upstream/dev', b,
                     '--', 'src') or '').split():
            if not f.endswith('.c'):
                continue
            txt = sh('git', 'show', '%s:%s' % (b, f)) or ''
            base = sh('git', 'show', 'upstream/dev:%s' % f) or ''
            claimed |= set(DEF.findall(txt)) - set(DEF.findall(base))

    todo = (set(fn_inc) & fork_c) - claimed
    plan = collections.defaultdict(list)
    for fn in todo:
        plan[fn_inc[fn]].append(fn)

    print('asm on dev: %d | fork has as C: %d of those | claimed by PRs: %d'
          % (len(fn_inc), len(set(fn_inc) & fork_c),
             len(set(fn_inc) & fork_c & claimed)))
    print('PORTABLE NOW (unclaimed, fork-matched): %d in %d clusters'
          % (len(todo), len(plan)))
    for inc, fns in sorted(plan.items(), key=lambda kv: -len(kv[1]))[:15]:
        print('  %-44s %2d: %s' % (inc, len(fns),
                                   ' '.join(sorted(fns)[:4])
                                   + (' ...' if len(fns) > 4 else '')))
    import io
    io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'portable_next.txt'), 'w', encoding='utf-8', newline='').write(
        ''.join('%s\t%s\n' % (inc, ' '.join(sorted(fns)))
                for inc, fns in sorted(plan.items())))


if __name__ == '__main__':
    main()
