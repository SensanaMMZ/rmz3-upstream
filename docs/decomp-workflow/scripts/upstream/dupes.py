#!/usr/bin/env python3
"""Which functions do my open PRs define, and which are claimed twice?

Reads each PR's branch from the fork and lists the function DEFINITIONS it adds
relative to upstream/dev. Two PRs defining the same symbol is a duplicate: only
one can merge, and the other becomes a conflict for the maintainer.
"""
import json, os, re, subprocess, urllib.request
tok = os.environ['GITHUB_TOKEN']
def api(p):
    return json.load(urllib.request.urlopen(urllib.request.Request(
        'https://api.github.com'+p, headers={'Authorization':'Bearer '+tok,
        'Accept':'application/vnd.github+json','User-Agent':'x'})))

DEF = re.compile(r'^\+\s*(?:static\s+)?(?:NAKED\s+|NON_MATCH\s+)?'
                 r'[A-Za-z_][\w \*]*?\b(\w+)\s*\([^;)]*\)\s*\{')

prs = [p for p in api('/repos/mmzret/rmz3/pulls?state=open&per_page=100')]
owner = {}
for p in sorted(prs, key=lambda x: x['number']):
    ref = 'prfork/' + p['head']['ref']
    if subprocess.run(['git','rev-parse','--verify','-q',ref],
                      capture_output=True).returncode:
        continue
    d = subprocess.run(['git','diff','upstream/dev...'+ref,'--','src'],
                       capture_output=True, text=True, errors='replace').stdout
    fns = {m.group(1) for m in (DEF.match(l) for l in d.split('\n')) if m}
    for f in fns:
        owner.setdefault(f, []).append(p['number'])

dupes = {f: ns for f, ns in owner.items() if len(ns) > 1}
print('%d function definitions across my open PRs, %d claimed by more than one'
      % (len(owner), len(dupes)))
pair = {}
for f, ns in dupes.items():
    pair.setdefault(tuple(sorted(ns)), []).append(f)
for k, v in sorted(pair.items(), key=lambda x: -len(x[1])):
    print('  PRs %-18s %3d shared: %s' % (','.join('#%d'%n for n in k), len(v),
                                          ' '.join(sorted(v)[:5])))
