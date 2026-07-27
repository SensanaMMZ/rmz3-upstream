#!/usr/bin/env python3
"""Classify the duplicated ("holdout") functions between open PRs.

For each function two PRs both decompiled, extract BOTH bodies straight from the
branches (read-only `git show`, no checkout) and compare them normalised for
whitespace. That splits the 55 into two very different piles:

  IDENTICAL  -- the same decompilation reached twice. Nothing to decide: either
                PR can drop it, and whoever merges second just takes the other's.
  DIFFERENT  -- genuinely divergent C. Only one can match the ROM in context,
                and picking constrains every caller, so this is the maintainer's
                call and the diff is what they need to see.

Prints a per-function verdict so the PRs can be annotated with facts rather
than with "these overlap".
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def body(ref, path, fn):
    r = subprocess.run(['git', 'show', '%s:%s' % (ref, path)],
                       capture_output=True)
    if r.returncode:
        return None
    txt = r.stdout.decode('utf-8', errors='replace')
    for m in re.finditer(r'^[A-Za-z_][\w \*]*\b%s\s*\([^;{)]*\)\s*\{'
                         % re.escape(fn), txt, re.M):
        depth, st = 0, txt.index('{', m.start())
        for j in range(st, len(txt)):
            if txt[j] == '{':
                depth += 1
            elif txt[j] == '}':
                depth -= 1
                if depth == 0:
                    return txt[m.start():j + 1]
    return None


def norm(s):
    return re.sub(r'\s+', ' ', s).strip() if s else None


def main():
    overlaps = json.load(io.open(os.path.join(HERE, 'live_overlaps.json'),
                                 encoding='utf-8'))
    branches = json.load(io.open(os.path.join(HERE, 'pr_branches.json'),
                                 encoding='utf-8'))
    same = diff = missing = 0
    rows = []
    for pr, items in overlaps.items():
        for path, other, fns in items:
            if not fns:
                continue
            a = branches.get(str(pr))
            b = branches.get(str(other))
            if not a or not b:
                missing += len(fns)
                continue
            for fn in fns:
                ba, bb = norm(body(a, path, fn)), norm(body(b, path, fn))
                if ba is None or bb is None:
                    verdict = 'ABSENT'
                    missing += 1
                elif ba == bb:
                    verdict = 'IDENTICAL'
                    same += 1
                else:
                    verdict = 'DIFFERENT'
                    diff += 1
                rows.append((verdict, int(pr), other, path, fn))

    for v, pr, other, path, fn in sorted(rows):
        print('  %-9s #%-3d/#%-3s %-32s %s' % (v, pr, other,
                                               os.path.basename(path), fn))
    print('\n  identical: %d   different: %d   unresolvable: %d'
          % (same, diff, missing))


if __name__ == '__main__':
    main()
