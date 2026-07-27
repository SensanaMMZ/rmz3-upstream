#!/usr/bin/env python3
"""Build the de-duplication hand-off plan for the open PRs.

Writes two files to the scratchpad:

  handoffs.txt    one row per contested (PR, file): CLEAN or LOSSY, plus the
                  functions the loser has that the owner does not
  clean_plan.txt  '<branch>\\t<file> <file> ...' for the CLEAN rows only,
                  ready for `while IFS=$'\\t' read -r br files`

Owner of a contested file = the PR contributing the most functions to it; ties
go to the lower PR number (submitted first, likely already under review).

EVERY write uses newline='' on purpose. Python text mode turns \\n into \\r\\n on
Windows, and a bash `read` loop then puts a trailing CR on the last field --
git reports `pathspec 'src/enemy/puffy.c?' did not match`, where the `?` IS the
carriage return. That silently skipped most of a batch once.

usage: make_handoff_plan.py
"""
import collections
import io
import json
import os
import re
import subprocess
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TOK = os.environ['GITHUB_TOKEN']

DEF = re.compile(r'^\+\s*(?:static\s+)?(?:NAKED\s+|NON_MATCH\s+)?'
                 r'[A-Za-z_][\w \*]*?\b(\w+)\s*\([^;)]*\)\s*\{')


def api(path):
    req = urllib.request.Request(
        'https://api.github.com' + path,
        headers={'Authorization': 'Bearer ' + TOK,
                 'Accept': 'application/vnd.github+json', 'User-Agent': 'x'})
    return json.load(urllib.request.urlopen(req))


prs = sorted(api('/repos/mmzret/rmz3/pulls?state=open&per_page=100'),
             key=lambda p: p['number'])
branch = {p['number']: p['head']['ref'] for p in prs}

per = {}
for p in prs:
    ref = 'prfork/' + p['head']['ref']
    if subprocess.run(['git', 'rev-parse', '--verify', '-q', ref],
                      capture_output=True).returncode:
        continue
    diff = subprocess.run(['git', 'diff', 'upstream/dev...' + ref, '--', 'src'],
                          capture_output=True, text=True,
                          errors='replace').stdout
    cur, files = None, {}
    for line in diff.split('\n'):
        m = re.match(r'^\+\+\+ b/(\S+)', line)
        if m:
            cur = m.group(1)
            continue
        d = DEF.match(line)
        if d and cur:
            files.setdefault(cur, set()).add(d.group(1))
    per[p['number']] = files

byfile = collections.defaultdict(dict)
for n, files in per.items():
    for f, fns in files.items():
        byfile[f][n] = fns

rows, clean = [], collections.defaultdict(list)
for f, claims in sorted(byfile.items()):
    if len(claims) < 2:
        continue
    owner = max(claims.items(), key=lambda kv: (len(kv[1]), -kv[0]))[0]
    for n, fns in claims.items():
        if n == owner:
            continue
        extra = sorted(fns - claims[owner])
        rows.append('%s\t%d\t%s\t%d\t%s'
                    % ('CLEAN' if not extra else 'LOSSY', n, f, owner,
                       ' '.join(extra)))
        if not extra and n in branch:
            clean[branch[n]].append(f)

io.open(os.path.join(HERE, 'handoffs.txt'), 'w',
        encoding='utf-8', newline='').write('\n'.join(rows) + '\n')
io.open(os.path.join(HERE, 'clean_plan.txt'), 'w',
        encoding='utf-8', newline='').write(
    '\n'.join('%s\t%s' % (b, ' '.join(fs)) for b, fs in sorted(clean.items()))
    + '\n')

print('%d contested file(s); %d clean hand-off(s), %d lossy'
      % (len({r.split('\t')[2] for r in rows}),
         sum(1 for r in rows if r.startswith('CLEAN')),
         sum(1 for r in rows if r.startswith('LOSSY'))))
print('wrote handoffs.txt and clean_plan.txt (LF endings)')
