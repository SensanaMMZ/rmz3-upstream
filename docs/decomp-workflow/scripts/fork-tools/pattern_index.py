import os
"""Codegen pattern index (holdout-playbook 1a).

Build once: extract every matched C function's asm body from expected/*.s
(rmz3) and the pokeruby clone's compiled .s files into one indexed file.
Query: regex over instruction text; prints function, project, file, and
the matched window, so the C source can be looked up.

Usage:
  python3 tools/pattern_index.py build
  python3 tools/pattern_index.py grep '<regex>' [context_lines]
Index: build/pattern-index/corpus.jsonl (one record per function)
"""
import io, os, re, sys, json, subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX = os.path.join(REPO, 'build', 'pattern-index')
PK = os.environ.get('POKERUBY', os.path.join(os.path.expanduser('~'), 'pokeruby'))

def fns_from_s(path, text):
    """Split a GCC .s file into (fn, body) pairs; skip NAKED (.syntax unified)."""
    out = []
    cur, name = [], None
    for ln in text.split('\n'):
        m = re.match(r'^([A-Za-z_][A-Za-z_0-9]*):\s*$', ln)
        if m:
            if name:
                out.append((name, cur))
            name, cur = m.group(1), []
        elif name is not None:
            if ln.startswith('\t.size') or ln.startswith('.Lfe'):
                out.append((name, cur))
                name, cur = None, []
            else:
                cur.append(ln)
    if name:
        out.append((name, cur))
    res = []
    for fn, body in out:
        txt = '\n'.join(body)
        if '.syntax unified' in txt:   # NAKED / hand asm
            continue
        ins = [l.strip() for l in body if re.match(r'\t[a-z]', l)]
        if len(ins) >= 3:
            res.append((fn, ins))
    return res

def build():
    os.makedirs(IDX, exist_ok=True)
    w = io.open(os.path.join(IDX, 'corpus.jsonl'), 'w', encoding='utf-8')
    n = 0
    # rmz3: expected .s files are the PROVEN matched compiler output
    for root, d, fs in os.walk(os.path.join(REPO, 'expected', 'build', 'rmz3', 'src')):
        for f in fs:
            if not f.endswith('.s'):
                continue
            p = os.path.join(root, f)
            txt = io.open(p, encoding='utf-8', errors='replace').read()
            rel = os.path.relpath(p, REPO).replace(os.sep, '/')
            src = rel.replace('expected/build/rmz3/', '').replace('.s', '.c')
            for fn, ins in fns_from_s(p, txt):
                w.write(json.dumps({'proj': 'rmz3', 'src': src, 'fn': fn, 'ins': ins}) + '\n')
                n += 1
    # pokeruby: compile every src/*.c with our agbcc (reuse crawl recipe)
    if os.path.isdir(PK):
        agbcc = os.path.join(REPO, 'tools', 'agbcc', 'bin', 'agbcc.exe')
        incdir = os.path.join(REPO, 'tools', 'agbcc', 'include')
        for root, d, fs in os.walk(os.path.join(PK, 'src')):
            for f in fs:
                if not f.endswith('.c'):
                    continue
                c = os.path.join(root, f)
                try:
                    cp = subprocess.run(
                        ['cpp', '-I', incdir, '-iquote', os.path.join(PK, 'include'),
                         '-iquote', PK, '-nostdinc', '-undef', '-D', 'RUBY',
                         '-D', 'REVISION=0', '-D', 'ENGLISH', '-D', 'DEBUG_FIX=0',
                         '-D', 'DEBUG=0', '-D', 'MODERN=0', c],
                        capture_output=True, cwd=PK, timeout=60)
                    cc = subprocess.run(
                        [agbcc, '-mthumb-interwork', '-Wimplicit', '-Wparentheses',
                         '-O2', '-fhex-asm', '-o', '-'],
                        input=cp.stdout, capture_output=True, timeout=60)
                    txt = cc.stdout.decode('utf-8', errors='replace')
                except Exception:
                    continue
                if txt.count('\n') < 60:
                    continue
                rel = 'src/' + os.path.relpath(c, os.path.join(PK, 'src')).replace(os.sep, '/')
                for fn, ins in fns_from_s(c, txt):
                    w.write(json.dumps({'proj': 'pokeruby', 'src': rel, 'fn': fn, 'ins': ins}) + '\n')
                    n += 1
    w.close()
    print('indexed %d functions -> %s/corpus.jsonl' % (n, IDX))

def grep(pat, ctx=2):
    rx = re.compile(pat)
    hits = 0
    for ln in io.open(os.path.join(IDX, 'corpus.jsonl'), encoding='utf-8'):
        rec = json.loads(ln)
        for i, ins in enumerate(rec['ins']):
            if rx.search(ins):
                lo, hi = max(0, i - ctx), min(len(rec['ins']), i + ctx + 1)
                print('%s %s :: %s' % (rec['proj'], rec['src'], rec['fn']))
                for j in range(lo, hi):
                    mark = '>' if j == i else ' '
                    print('  %s %s' % (mark, rec['ins'][j]))
                hits += 1
                break
        if hits >= 40:
            print('... (capped at 40)')
            return
    print('%d hits' % hits)

if sys.argv[1] == 'build':
    build()
else:
    grep(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2)
