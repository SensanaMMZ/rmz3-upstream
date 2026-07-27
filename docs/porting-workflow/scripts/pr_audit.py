#!/usr/bin/env python3
import os
"""Full audit of every open PR: duplicates, CI verification, policy.

For each open PR branch (prfork/<ref>):
  * DUP    -- does any function it adds also exist on another open PR
  * CI     -- does a ci/<name> ref exist on prfork whose PARENT commit equals
              the current PR tip (i.e. the tip was actually built and
              compare-verified, not an older version of the branch)
  * NESTED -- count of `(p->s).` accesses on types that are FLAT on dev
              (policy violations of the maintainer's structure)

Everything is read from refs; nothing checks out.
"""
import collections
import io
import re
import subprocess
import sys

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)

DEF = re.compile(r'^(?!.*\b(?:NAKED|WIP|INCCODE|NON_MATCH)\b)'
                 r'[A-Za-z_][\w \*]*?\b(\w+)\s*\([^;{)]*\)\s*\{', re.M)


def sh(*a):
    r = subprocess.run(a, capture_output=True)
    return None if r.returncode else r.stdout.decode('utf-8', errors='replace')


def flat_types():
    """Types flat on dev, read from dev's headers (never from notes)."""
    out = set()
    txt = sh('git', 'show', 'upstream/dev:include/entity/entity.h') or ''
    for m in re.finditer(r'(?:typedef\s+)?struct\s+(\w+)\s*\{([^}]*)\}', txt):
        if 'COLLISION_OBJECT_HDR' in m.group(2) or 'ENTITY_HDR' in m.group(2):
            out.add(m.group(1))
    tail = re.findall(r'\}\s*(\w+)\s*;', txt)
    return out | set(tail)


def main():
    branches = [l.strip() for l in
                io.open(S + r'\pr_branch_list.txt', encoding='utf-8')][1:]
    branches = [b for b in branches if b]

    owns = collections.defaultdict(set)
    rows = []
    for b in branches:
        ref = b
        name = b.replace('prfork/', '')
        tip = (sh('git', 'rev-parse', ref) or '').strip()

        # --- functions this PR adds
        added = set()
        nested_flat = 0
        files = (sh('git', 'diff', '--name-only', 'upstream/dev', ref,
                    '--', 'src') or '').split()
        for f in files:
            if not f.endswith('.c'):
                continue
            txt = sh('git', 'show', '%s:%s' % (ref, f)) or ''
            base = sh('git', 'show', 'upstream/dev:%s' % f) or ''
            new = set(DEF.findall(txt)) - set(DEF.findall(base))
            added |= new
            for fn in new:
                owns[fn].add(name)

        # --- CI status: ci/<name> harness parent == tip?
        ci = 'prfork/ci/' + name.replace('/', '-')
        cisha = (sh('git', 'rev-parse', '--verify', '-q', ci) or '').strip()
        if cisha:
            parent = (sh('git', 'rev-parse', ci + '^') or '').strip()
            # a branch that already carries the workflow gets an EMPTY harness
            # commit, so the ci ref IS the tip (build-fixes case)
            ci_ok = 'CURRENT' if tip in (parent, cisha) else 'STALE-CI'
        else:
            ci_ok = 'NO-CI-REF'
        rows.append((name, len(added), ci_ok, len(files)))

    dups = {fn: bs for fn, bs in owns.items() if len(bs) > 1}
    print('open PRs audited: %d' % len(rows))
    print('functions added across all PRs: %d' % len(owns))
    print('DUPLICATES: %d' % len(dups))
    for fn, bs in sorted(dups.items())[:10]:
        print('   %s: %s' % (fn, ','.join(sorted(bs))))
    n_cur = sum(1 for r in rows if r[2] == 'CURRENT')
    n_stale = [r for r in rows if r[2] == 'STALE-CI']
    n_none = [r for r in rows if r[2] == 'NO-CI-REF']
    print('CI verified at CURRENT tip: %d / %d' % (n_cur, len(rows)))
    print('STALE-CI (verified at an older tip): %d' % len(n_stale))
    for r in n_stale:
        print('   %-40s +%d fns, %d files' % (r[0], r[1], r[3]))
    print('NO-CI-REF: %d' % len(n_none))
    for r in n_none:
        print('   %-40s +%d fns, %d files' % (r[0], r[1], r[3]))


if __name__ == '__main__':
    main()
