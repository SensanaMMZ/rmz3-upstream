#!/usr/bin/env python3
"""Assign each contested source file to ONE PR.

Function-level overlap is the symptom; FILE-level overlap is what actually
conflicts. Two PRs touching the same .c cannot both merge cleanly even if their
function sets are disjoint, because each rewrites the file's INCASM boundaries.

Rule: the PR contributing MORE functions to a file owns it; ties go to the older
(lower-numbered) PR, which is likely already under review. Every other PR reverts
that file to upstream/dev.
"""
import json, os, re, subprocess, urllib.request, collections
tok = os.environ['GITHUB_TOKEN']
def api(p):
    return json.load(urllib.request.urlopen(urllib.request.Request(
        'https://api.github.com'+p, headers={'Authorization':'Bearer '+tok,
        'Accept':'application/vnd.github+json','User-Agent':'x'})))
DEF = re.compile(r'^\+\s*(?:static\s+)?(?:NAKED\s+|NON_MATCH\s+)?'
                 r'[A-Za-z_][\w \*]*?\b(\w+)\s*\([^;)]*\)\s*\{')

prs = sorted(api('/repos/mmzret/rmz3/pulls?state=open&per_page=100'),
             key=lambda x: x['number'])
per = {}
for p in prs:
    ref = 'prfork/' + p['head']['ref']
    if subprocess.run(['git','rev-parse','--verify','-q',ref],
                      capture_output=True).returncode: continue
    d = subprocess.run(['git','diff','upstream/dev...'+ref,'--','src'],
                       capture_output=True, text=True, errors='replace').stdout
    cur, m = None, {}
    for l in d.split('\n'):
        f = re.match(r'^\+\+\+ b/(\S+)', l)
        if f: cur = f.group(1); continue
        d2 = DEF.match(l)
        if d2 and cur: m.setdefault(cur, set()).add(d2.group(1))
    per[p['number']] = m

byfile = collections.defaultdict(dict)
for n, m in per.items():
    for f, fns in m.items():
        byfile[f][n] = len(fns)

drops = collections.defaultdict(list)
print('%-44s %s' % ('contested file', 'owner <- losers'))
for f, claims in sorted(byfile.items()):
    if len(claims) < 2: continue
    owner = max(claims.items(), key=lambda kv: (kv[1], -kv[0]))[0]
    losers = [n for n in claims if n != owner]
    for n in losers: drops[n].append(f)
    print('%-44s #%d(%d) <- %s' % (f[:44], owner, claims[owner],
          ' '.join('#%d(%d)' % (n, claims[n]) for n in sorted(losers))))
print()
for n in sorted(drops):
    total = len(per[n]); d = len(drops[n])
    print('  #%-4d revert %d of %d file(s)%s' % (n, d, total,
          '   -> PR becomes EMPTY, close it' if d == total else ''))
# newline='' -- text mode would write CRLF on Windows and any shell loop
# reading this back gets a trailing CR on the last field.
with open(os.environ['DROPS'], 'w', newline='') as _f:
    json.dump({str(k): v for k, v in drops.items()}, _f, indent=1)
