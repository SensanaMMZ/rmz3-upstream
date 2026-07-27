#!/usr/bin/env python3
"""Recompute which functions two open PRs BOTH decompile, from current branches.

The stored overlap map is stale: it predates 16 hand-offs and 5 union merges, so
functions it lists as contested (`createFlameRain1` in #45) are no longer in that
branch at all. Quoting 55 from it is the same mistake as the 467 portable-list
figure -- a snapshot reused after the thing it described had moved.

For every open PR branch this reads the files it changes relative to
`upstream/dev`, collects the functions it defines in C, and reports names defined
by more than one branch. NAKED / INCCODE / NON_MATCH definitions are skipped:
they look like C but the body is still assembly, so they are not a claim on the
function.
"""
import collections
import io
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
DEF = re.compile(r'^(?!.*\b(?:NAKED|WIP|INCCODE|NON_MATCH)\b)'
                 r'[A-Za-z_][\w \*]*?\b(\w+)\s*\([^;{)]*\)\s*\{', re.M)


def sh(*args):
    r = subprocess.run(args, capture_output=True)
    return None if r.returncode else r.stdout.decode('utf-8', errors='replace')


def main():
    branches = json.load(io.open(os.path.join(HERE, 'pr_branches.json'),
                                 encoding='utf-8'))
    owns = collections.defaultdict(set)      # (file, fn) -> {PR}
    missing = []
    for pr, ref in sorted(branches.items(), key=lambda kv: int(kv[0])):
        if sh('git', 'rev-parse', '--verify', '-q', ref) is None:
            missing.append((pr, ref))
            continue
        files = sh('git', 'diff', '--name-only', 'upstream/dev', ref) or ''
        for f in files.split():
            if not f.endswith('.c'):
                continue
            txt = sh('git', 'show', '%s:%s' % (ref, f))
            if txt is None:
                continue
            # Only what this branch ADDS. Taking every function defined in a
            # touched file counted everything upstream had already decompiled,
            # so 1470 functions looked contested between nearly every pair --
            # a number that says the measure is wrong, not that the PRs collide.
            base = sh('git', 'show', 'upstream/dev:%s' % f) or ''
            already = {m.group(1) for m in DEF.finditer(base)}
            for m in DEF.finditer(txt):
                if m.group(1) not in already:
                    owns[(f, m.group(1))].add(int(pr))

    contested = {k: v for k, v in owns.items() if len(v) > 1}
    print('PR branches examined: %d (%d not fetched locally)'
          % (len(branches) - len(missing), len(missing)))
    print('functions claimed by more than one open PR: %d' % len(contested))
    if missing:
        print('  not fetched: ' + ', '.join('#%s' % p for p, _ in missing[:8]))

    by_pair = collections.Counter()
    for (f, fn), prs in contested.items():
        for a in prs:
            for b in prs:
                if a < b:
                    by_pair[(a, b)] += 1
    print('\ntop contested PR pairs:')
    for (a, b), n in by_pair.most_common(12):
        print('  #%-3d vs #%-3d  %d function(s)' % (a, b, n))

    io.open(os.path.join(HERE, 'contested_now.txt'), 'w',
            encoding='utf-8', newline='').write(
        ''.join('%s\t%s\t%s\n' % (f, fn, ','.join(str(p) for p in sorted(prs)))
                for (f, fn), prs in sorted(contested.items())))
    print('\nwritten: contested_now.txt')


if __name__ == '__main__':
    main()
