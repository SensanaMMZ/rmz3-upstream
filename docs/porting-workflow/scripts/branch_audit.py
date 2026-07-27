#!/usr/bin/env python3
"""Audit every local branch against its pushed counterpart on prfork.

For each local head: does prfork have the same name; are they identical; if
not, who is ahead/behind and what are the differing commits. Pure ref
inspection -- no checkouts, so it cannot disturb the worktree.

Classification:
  IDENTICAL      nothing to do
  LOCAL-ONLY     never pushed (scratch/stub branches are expected here)
  LOCAL-AHEAD    local strictly ahead -- unpushed work; list it
  REMOTE-AHEAD   remote strictly ahead -- local is stale; safe to fast-forward
  DIVERGED       both sides have unique commits; needs a decision
"""
import subprocess
import sys


def sh(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def main():
    heads = sh('git', 'for-each-ref', '--format=%(refname:short)',
               'refs/heads/').split('\n')
    groups = {}
    for b in heads:
        if b.startswith('ci/'):
            continue                      # scratch harness branches
        remote = 'prfork/' + b
        rsha = sh('git', 'rev-parse', '--verify', '-q', remote)
        lsha = sh('git', 'rev-parse', b)
        if rsha is None:
            groups.setdefault('LOCAL-ONLY', []).append((b, lsha[:8], ''))
            continue
        if rsha == lsha:
            groups.setdefault('IDENTICAL', []).append((b, lsha[:8], rsha[:8]))
            continue
        ahead = sh('git', 'rev-list', '--count', '%s..%s' % (remote, b))
        behind = sh('git', 'rev-list', '--count', '%s..%s' % (b, remote))
        if behind == '0':
            key = 'LOCAL-AHEAD'
        elif ahead == '0':
            key = 'REMOTE-AHEAD'
        else:
            key = 'DIVERGED'
        subs = sh('git', 'log', '--format=%h %s', '%s..%s' % (remote, b)) or ''
        rsubs = sh('git', 'log', '--format=%h %s', '%s..%s' % (b, remote)) or ''
        groups.setdefault(key, []).append(
            (b, '+%s/-%s' % (ahead, behind),
             ('L:' + subs.replace('\n', ' | '))[:120]
             + ((' R:' + rsubs.replace('\n', ' | '))[:100] if rsubs else '')))

    for key in ('DIVERGED', 'LOCAL-AHEAD', 'REMOTE-AHEAD', 'LOCAL-ONLY',
                'IDENTICAL'):
        rows = groups.get(key, [])
        print('%s: %d' % (key, len(rows)))
        if key == 'IDENTICAL' or key == 'LOCAL-ONLY':
            continue
        for b, counts, detail in rows:
            print('  %-40s %-8s %s' % (b, counts, detail))


if __name__ == '__main__':
    main()
