#!/usr/bin/env python3
"""Every INCASM(...) target must exist, and every carved .inc must be included.

Two failure modes, both invisible to a changed-files sweep:

* the .c matches upstream (so it is not in `git diff --name-only`) while the
  branch deleted the .inc it includes -> "can't open asm/x.inc for reading"
* the branch created x_a.inc / x_b.inc that nothing includes -> dead weight, and
  usually a sign the .c was reverted without its asm

Scans the WHOLE tree, not the diff, because that is exactly where the gap is.
"""
import os
import re
import subprocess
import sys

SEP = chr(92)    # backslash, spelled out -- a shell heredoc eats a literal one

want, have = {}, set()
for root, _, files in os.walk('src'):
    for fn in files:
        if not fn.endswith('.c'):
            continue
        p = os.path.join(root, fn).replace(SEP, '/')
        with open(p, encoding='utf-8', errors='replace') as f:
            for inc in re.findall(r'INCASM\("([^"]+)"\)', f.read()):
                want.setdefault(inc, []).append(p)
for root, _, files in os.walk('asm'):
    for fn in files:
        if fn.endswith('.inc'):
            have.add(os.path.join(root, fn).replace(SEP, '/'))

missing = sorted(i for i in want if i not in have)
for i in missing:
    print('  MISSING %-44s included by %s' % (i, want[i][0]))

# Both sides from the WORKTREE. Reading `want` from disk but `added` from a
# committed ref reports files as orphaned after they have already been deleted,
# and the reverse once new ones are written -- the report never matches what a
# build would actually see. An orphan is: a .inc that exists on disk now, that
# nothing includes now, and that upstream does not have.
upstream_incs = set(subprocess.run(
    ['git', 'ls-tree', '-r', '--name-only', 'upstream/dev', '--', 'asm'],
    capture_output=True, text=True).stdout.split())
orphans = sorted(a for a in have if a not in want and a not in upstream_incs)
for a in orphans:
    print('  ORPHAN  %s (added but nothing includes it)' % a)

print('  %d missing, %d orphaned' % (len(missing), len(orphans)))
sys.exit(1 if missing or orphans else 0)
