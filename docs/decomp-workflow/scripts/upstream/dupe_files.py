#!/usr/bin/env python3
"""Per (PR, file): are the duplicated functions the WHOLE file's contribution?

If a file's every added function is already claimed by an older PR, the file can
simply be reverted to upstream/dev -- a clean, reviewable removal. Partial
overlap needs surgery instead, so it is worth knowing the split before starting.

Rule: the LOWEST-numbered PR keeps a contested function (it was submitted first
and is likely already under review).
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
per = {}          # pr -> {file -> set(fns)}
for p in prs:
    ref = 'prfork/' + p['head']['ref']
    if subprocess.run(['git','rev-parse','--verify','-q',ref],
                      capture_output=True).returncode:
        continue
    d = subprocess.run(['git','diff','upstream/dev...'+ref,'--','src'],
                       capture_output=True, text=True, errors='replace').stdout
    cur, m = None, {}
    for l in d.split('\n'):
        f = re.match(r'^\+\+\+ b/(\S+)', l)
        if f:
            cur = f.group(1); continue
        d2 = DEF.match(l)
        if d2 and cur:
            m.setdefault(cur, set()).add(d2.group(1))
    per[p['number']] = m

first = {}
for n in sorted(per):
    for f, fns in per[n].items():
        for fn in fns:
            first.setdefault(fn, n)

print('%-5s %-42s %5s %5s  %s' % ('PR','file','dup','uniq','action'))
plan = collections.defaultdict(list)
for n in sorted(per):
    for f, fns in sorted(per[n].items()):
        dup = {x for x in fns if first[x] != n}
        if not dup:
            continue
        uniq = len(fns) - len(dup)
        act = 'REVERT FILE' if uniq == 0 else 'partial (%d keep)' % uniq
        print('#%-4d %-42s %5d %5d  %s' % (n, f[:42], len(dup), uniq, act))
        plan[n].append((f, len(dup), uniq))
print()
for n in sorted(plan):
    whole = sum(1 for _, _, u in plan[n] if u == 0)
    print('  #%-4d %d file(s) affected, %d fully revertable' % (n, len(plan[n]), whole))
