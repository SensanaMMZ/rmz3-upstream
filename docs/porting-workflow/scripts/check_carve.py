#!/usr/bin/env python3
"""Every function upstream had must still exist: in asm, or lifted into C.

Porting splits a whole-file `asm/x.inc` into pieces and interleaves C bodies.
If the split loses a range, the functions in it vanish from the build entirely.
Nothing catches that until the link: `lemmingles.inc` had 18 functions and a
branch shipped 13 asm + 3 C, silently dropping Lemmingles_Init and
Lemmingles_Update, whose names were still referenced by the routine table.

So compare the SETS, not just counts -- a count can coincidentally match while
a different function goes missing.

usage: check_carve.py <ref>
"""
import re
import subprocess
import sys

ref = sys.argv[1]


def git(*a):
    r = subprocess.run(['git'] + list(a), capture_output=True, text=True,
                       errors='replace')
    return r.stdout if r.returncode == 0 else ''


def labels(text):
    return set(re.findall(r'^\s*thumb_func_start\s+(\S+)', text, re.M))


changed = [f for f in git('diff', '--name-only', 'upstream/dev...' + ref,
                          '--', 'asm', 'src').split('\n') if f]
# Group by the upstream inc each carved piece came from: asm/enemy/lemmingles.inc
# -> lemmingles_a.inc, lemmingles_mid.inc, lemmingles_b.inc
bases = {}
for f in changed:
    if not f.endswith('.inc'):
        continue
    m = re.match(r'^(asm/.*?/[a-z0-9_]+?)(?:_[a-z0-9]+)*\.inc$', f)
    if m:
        bases.setdefault(m.group(1) + '.inc', set()).add(f)

# Every function this branch defines in C, from ANY changed source file. The
# lifted body does not always land in the path that mirrors the inc --
# asm/minigame/harpuia.inc is lifted into src/enemy/minigame/harpuia.c -- and
# assuming the mirrored path reports perfectly good ports as "lost".
all_c = set()
for f in changed:
    if f.endswith('.c'):
        all_c |= set(re.findall(r'^[A-Za-z_][\w \*]*?\b(\w+)\s*\([^;)]*\)\s*\{',
                                git('show', '%s:%s' % (ref, f)), re.M))

bad = 0
for orig, pieces in sorted(bases.items()):
    up = git('show', 'upstream/dev:' + orig)
    if not up:
        continue
    want = labels(up)
    have = set()
    for p in pieces:
        have |= labels(git('show', '%s:%s' % (ref, p)))
    # anything still present unsplit
    have |= labels(git('show', '%s:%s' % (ref, orig)))
    csrc = orig.replace('asm/', 'src/').replace('.inc', '.c')
    ctext = git('show', '%s:%s' % (ref, csrc))
    in_c = set(re.findall(r'^[A-Za-z_][\w \*]*?\b(\w+)\s*\([^;)]*\)\s*\{',
                          ctext, re.M))
    missing = want - have - in_c - all_c
    if missing:
        print('  %-42s LOST %d: %s' % (orig, len(missing),
                                       ' '.join(sorted(missing))))
        bad += 1
if not bad:
    print('  carve OK (%d inc group(s))' % len(bases))
sys.exit(1 if bad else 0)
