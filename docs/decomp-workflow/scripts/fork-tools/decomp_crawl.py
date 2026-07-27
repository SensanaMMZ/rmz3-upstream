import os
"""Crawl the GBA decomp corpus and index codegen traits per project.

Generalises tools/pattern_index.py (which only knew pokeruby) to every repo
listed in notes/urls-of-gba-decomps/list-of-decomps.md.

For each project: shallow-clone (or fetch), compile every src/**/*.c with OUR
agbcc, split the output into functions, and record which codegen traits each
function exhibits. Traits are the things that block a match here (high-reg
pinning, byte-truncation form, helper calls), so the reports answer
"which C source shape produces THIS instruction?" against a corpus of
known-good matched C.

Usage:
  python3 tools/decomp_crawl.py clone [proj ...]     # clone/fetch
  python3 tools/decomp_crawl.py index [proj ...]     # compile + index + report
  python3 tools/decomp_crawl.py check                # any upstream updates?
  python3 tools/decomp_crawl.py grep '<regex>' [n]   # query the whole corpus

Outputs (all dated):
  <corpus>/manifest.json                         commit + crawl date per proj
  build/pattern-index/corpus-<proj>.jsonl        one record per function
  notes/decompme/crawl/<proj>_<trait>_report_<date>.md
"""
import io, os, re, sys, json, subprocess, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.environ.get('DECOMP_CORPUS',
                        os.path.join(os.path.dirname(REPO), 'decomp-corpus'))
IDX = os.path.join(REPO, 'build', 'pattern-index')
CRAWL = os.path.join(REPO, 'notes', 'decompme', 'crawl')
LIST = os.path.join(REPO, 'notes', 'urls-of-gba-decomps', 'list-of-decomps.md')
AGBCC = os.path.join(REPO, 'tools', 'agbcc', 'bin', 'agbcc.exe')
AGBINC = os.path.join(REPO, 'tools', 'agbcc', 'include')
CPP = 'arm-none-eabi-cpp'
TODAY = datetime.date.today().isoformat()

# Instruction traits worth cross-referencing before we contort a harness.
TRAITS = {
    'r8':        r'\br8\b|\bsb\b|\bsl\b',
    'and_0xff':  r'\band\b.*#(0xff|255)\b',
    'shift_24':  r'\blsl\b.*#(0x18|24)\b',
    'umod':      r'__umodsi3|__modsi3',
    'udiv':      r'__udivsi3|__divsi3',
    'mul':       r'\bmul\b',
    'rsb':       r'\brsb\b',
    'bic':       r'\bbic\b',
    'tst':       r'\btst\b',
    'mov_ip':    r'\bmov\b\s+ip\b',
}


def projects():
    """[(name, url)] from the decomp list."""
    out = []
    for ln in io.open(LIST, encoding='utf-8'):
        m = re.match(r'\s*(https://github\.com/([\w.-]+)/([\w.-]+))\s*(.*)', ln)
        if m:
            out.append((m.group(3).lower(), m.group(1)))
    return out


def manifest_path():
    return os.path.join(CORPUS, 'manifest.json')


def load_manifest():
    try:
        return json.load(io.open(manifest_path(), encoding='utf-8'))
    except Exception:
        return {}


def save_manifest(m):
    """Merge-on-write.

    A long index run holds its in-memory copy for hours; a concurrent run
    finishing later used to clobber everything the first one recorded (this
    silently reverted pokeemerald/pokefirered/mzm once). Re-read from disk and
    merge per project so parallel crawls compose instead of racing.
    """
    os.makedirs(CORPUS, exist_ok=True)
    cur = load_manifest()
    for k, v in m.items():
        cur.setdefault(k, {}).update(v)
    io.open(manifest_path(), 'w', encoding='utf-8', newline='\n').write(
        json.dumps(cur, indent=2, sort_keys=True))


def run(cmd, cwd=None, timeout=1800):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout)


def clone(names):
    m = load_manifest()
    os.makedirs(CORPUS, exist_ok=True)
    for name, url in projects():
        if names and name not in names:
            continue
        dst = os.path.join(CORPUS, name)
        if os.path.isdir(os.path.join(dst, '.git')):
            run(['git', 'fetch', '--depth', '1', 'origin'], cwd=dst)
            run(['git', 'reset', '--hard', 'FETCH_HEAD'], cwd=dst)
            action = 'fetched'
        else:
            r = run(['git', 'clone', '--depth', '1', url, dst])
            if r.returncode != 0:
                print('%-16s CLONE FAILED' % name)
                continue
            action = 'cloned'
        h = run(['git', 'rev-parse', 'HEAD'], cwd=dst).stdout.decode().strip()
        m.setdefault(name, {})
        m[name].update({'url': url, 'commit': h, 'crawled': TODAY})
        print('%-16s %s @ %s' % (name, action, h[:8]))
    save_manifest(m)


def shim_dir(name):
    return os.path.join(CORPUS, '_shims', name)


# Directories that never hold the game's own translation units.
SKIP_DIRS = {'.git', '.github', 'tools', 'build', 'tests', 'test', 'scripts',
             'plugins', 'graphics', 'sound', 'docs', 'reference', 'preview',
             'banim', 'mgfembp', 'lib'}


def c_files(root):
    """Every game .c under a project, whatever its layout.

    Most decomps use src/, but some (goldensun) split by overlay into
    rom_*/ dirs and some (sma2) have no C at all. Walking the whole repo
    minus the non-source dirs covers all three without per-project config.
    """
    out = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in sorted(files):
            if f.endswith('.c'):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def shim(names):
    """Stub out build-time-generated headers so more of a project preprocesses.

    Decomp repos generate headers (map_groups.h, sprite tables, ...) during
    their own build; we never build them, so cpp dies on the include. An
    EMPTY stub is enough for the corpus: we want representative codegen from
    the files that do compile, not a correct binary.
    """
    for name, url in projects():
        if names and name not in names:
            continue
        root = os.path.join(CORPUS, name)
        srcs = c_files(root)
        if not srcs:
            continue
        sd = shim_dir(name)
        os.makedirs(sd, exist_ok=True)
        made = set()
        for rnd in range(6):
            missing = set()
            args = guess_cpp_args(root)
            for cf in srcs:
                if True:
                    r = run([CPP] + args + [cf], cwd=root, timeout=60)
                    for m in re.finditer(r'fatal error: ([^:\n]+): No such file',
                                         r.stderr.decode('utf-8', 'replace')):
                        missing.add(m.group(1).strip())
            new = missing - made
            if not new:
                break
            for h in sorted(new):
                dst = os.path.join(sd, h)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if not os.path.exists(dst):
                    io.open(dst, 'w', encoding='utf-8', newline='\n').write(
                        '/* corpus shim: generated header, stubbed %s */\n' % TODAY)
                made.add(h)
            print('%-16s round %d: stubbed %d header(s)' % (name, rnd + 1, len(new)))
        print('%-16s shims: %d' % (name, len(made)))


PROJECT_DEFINES = {
    'sa2': ['-D', 'GAME=2', '-D', 'PLATFORM_GBA=1', '-D', 'ENGINE=2'],
    'katam': ['-D', 'GAME=4', '-D', 'PLATFORM_GBA=1'],
}


def guess_cpp_args(root):
    """Include dirs / defines that most agbcc-era GBA decomps want."""
    args = ['-I', AGBINC, '-nostdinc', '-undef', '-std=gnu89']
    name = os.path.basename(root.rstrip(os.sep))
    sd = shim_dir(name)
    if os.path.isdir(sd):
        args += ['-iquote', sd, '-I', sd]
    for d in ('include', 'src', 'tools/agbcc/include'):
        p = os.path.join(root, d)
        if os.path.isdir(p):
            args += ['-iquote', p]
    args += ['-iquote', root]
    for d in ('MODERN=0', 'NONMATCHING=0', 'REVISION=0', 'ENGLISH', 'RUBY',
              'DEBUG=0', 'DEBUG_FIX=0', 'GERMAN=0', 'PORTUGUESE=0'):
        args += ['-D', d]
    # A few projects gate their headers on a project-specific define and
    # #error out without it. Cheaper to carry the handful than to fail whole
    # repos: sa2's config.h refuses to compile unless GAME is set.
    args += PROJECT_DEFINES.get(name, [])
    return args


def fns_from_s(text):
    """Split agbcc .s output into (fn, [instructions]); skip hand-written asm."""
    out, cur, name = [], [], None
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
        if '.syntax unified' in txt:
            continue
        ins = [l.strip() for l in body if re.match(r'\t[a-z]', l)]
        if len(ins) >= 3:
            res.append((fn, ins))
    return res


def index(names):
    os.makedirs(IDX, exist_ok=True)
    os.makedirs(CRAWL, exist_ok=True)
    m = load_manifest()
    for name, url in projects():
        if names and name not in names:
            continue
        root = os.path.join(CORPUS, name)
        if not os.path.isdir(root):
            continue
        srcs = c_files(root)
        if not srcs:
            print('%-16s no C sources — skipped (asm-only decomp?)' % name)
            continue
        cppargs = guess_cpp_args(root)
        recs, ok, fail = [], 0, 0
        if True:
            for c in srcs:
                try:
                    pre = run([CPP] + cppargs + [c], cwd=root, timeout=60)
                    if pre.returncode != 0 or len(pre.stdout) < 200:
                        fail += 1
                        continue
                    cc = subprocess.run(
                        [AGBCC, '-mthumb-interwork', '-O2', '-fshort-enums',
                         '-fhex-asm', '-o', '-'],
                        input=pre.stdout, capture_output=True, timeout=90)
                    txt = cc.stdout.decode('utf-8', errors='replace')
                except Exception:
                    fail += 1
                    continue
                if txt.count('\n') < 40:
                    fail += 1
                    continue
                ok += 1
                rel = os.path.relpath(c, root).replace(os.sep, '/')
                for fn, ins in fns_from_s(txt):
                    recs.append({'proj': name, 'src': rel, 'fn': fn, 'ins': ins})
        out = os.path.join(IDX, 'corpus-%s.jsonl' % name)
        with io.open(out, 'w', encoding='utf-8', newline='\n') as w:
            for r in recs:
                w.write(json.dumps(r) + '\n')
        report(name, recs, ok, fail)
        m.setdefault(name, {})
        m[name].update({'indexed': TODAY, 'files_ok': ok, 'files_failed': fail,
                        'functions': len(recs)})
        save_manifest(m)
        print('%-16s %d fns from %d files (%d unusable)' % (name, len(recs), ok, fail))


def report(name, recs, ok, fail):
    """One dated markdown report per trait, same shape as the pokeruby one."""
    homes = {}
    for r in recs:
        homes.setdefault(r['fn'], set()).add(r['src'])
    for trait, pat in TRAITS.items():
        rx = re.compile(pat)
        byfile = {}
        for r in recs:
            if any(rx.search(i) for i in r['ins']):
                byfile.setdefault(r['src'], []).append(r['fn'])
        if not byfile:
            continue
        p = os.path.join(CRAWL, '%s_%s_report_%s.md' % (name, trait, TODAY))
        with io.open(p, 'w', encoding='utf-8', newline='\n') as w:
            w.write('<!-- %s :: trait=%s :: crawled %s :: %d/%d files compiled -->\n'
                    % (name, trait, TODAY, ok, ok + fail))
            for src in sorted(byfile):
                w.write('- %s: %s :: %s \n' % (trait, src, ' '.join(sorted(set(byfile[src])))))
            for fn in sorted(homes):
                if len(homes[fn]) > 1 and any(fn in v for v in byfile.values()):
                    w.write('- DOUBLE-HOME: %s :: %s\n' % (' '.join(sorted(homes[fn])), fn))


def check():
    """Weekly: which upstreams moved since we crawled?"""
    m = load_manifest()
    stale = []
    for name, url in projects():
        r = run(['git', 'ls-remote', url, 'HEAD'], timeout=120)
        if r.returncode != 0:
            print('%-16s unreachable' % name)
            continue
        head = r.stdout.decode().split()[0] if r.stdout.split() else ''
        have = m.get(name, {}).get('commit', '')
        if not have:
            print('%-16s NOT CRAWLED' % name)
            stale.append(name)
        elif head[:40] != have[:40]:
            print('%-16s UPDATED %s -> %s (crawled %s)'
                  % (name, have[:8], head[:8], m[name].get('crawled', '?')))
            stale.append(name)
        else:
            print('%-16s current @ %s' % (name, have[:8]))
    if stale:
        print('\nre-crawl: python3 tools/decomp_crawl.py clone %s && python3 '
              'tools/decomp_crawl.py index %s' % (' '.join(stale), ' '.join(stale)))
    return stale


def grep(pat, ctx=2):
    rx = re.compile(pat)
    hits = 0
    for f in sorted(os.listdir(IDX)):
        if not f.startswith('corpus'):
            continue
        for ln in io.open(os.path.join(IDX, f), encoding='utf-8'):
            rec = json.loads(ln)
            for i, ins in enumerate(rec['ins']):
                if rx.search(ins):
                    print('== %s %s :: %s' % (rec['proj'], rec['src'], rec['fn']))
                    for j in range(max(0, i - ctx), min(len(rec['ins']), i + ctx + 1)):
                        print('   %s%s' % ('>' if j == i else ' ', rec['ins'][j]))
                    hits += 1
                    break
            if hits > 40:
                print('... (truncated)')
                return
    print('%d functions matched' % hits)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    rest = sys.argv[2:]
    if cmd == 'clone':
        clone(rest)
    elif cmd == 'index':
        index(rest)
    elif cmd == 'shim':
        shim(rest)
    elif cmd == 'check':
        check()
    elif cmd == 'grep':
        grep(rest[0], int(rest[1]) if len(rest) > 1 else 2)
    else:
        print(__doc__)
