import os
"""m2c first-draft generator for the INCASM tail (holdout-playbook accelerator).

For every INCASM'd .inc: run each function through m2c (arm-gcc-c), then apply
the idiom-normalizer post-pass (Kappa-style plugin) mapping raw offsets and
constants into project idioms. Drafts land in build/m2c-drafts/<inc>/<fn>.c —
NOT matches, but structurally-correct starting points.

Usage: python3 tools/m2c_drafts.py [limit]
"""
import io, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M2C = os.environ.get('M2C', os.path.join(os.path.expanduser('~'), 'm2c', 'm2c.py'))
OUT = os.path.join(REPO, 'build', 'm2c-drafts')

# ---- idiom normalizer (post-pass "plugins") ----
FIELD_MAP = [
    # (regex on m2c output, replacement) — struct Entity via (p->s).
    (r'\barg0\b', 'p'),
    (r'p->unkC\b', '(p->s).mode[0]'),
    (r'p->unkD\b', '(p->s).mode[1]'),
    (r'p->unkE\b', '(p->s).mode[2]'),
    (r'p->unkF\b', '(p->s).mode[3]'),
    (r'p->unk9\b', '(p->s).id'),
    (r'p->unkA\b', '(p->s).flags'),
    (r'p->unkB\b', '(p->s).flags2'),
    (r'p->unk10\b', '(p->s).work[0]'),
    (r'p->unk11\b', '(p->s).work[1]'),
    (r'p->unk12\b', '(p->s).work[2]'),
    (r'p->unk13\b', '(p->s).work[3]'),
    (r'p->unk14\b', '(p->s).onUpdate'),
    (r'p->unk28\b', '(p->s).unk_28'),
    (r'p->unk2C\b', '(p->s).unk_2c'),
    (r'p->unk54\b', '(p->s).coord.x'),
    (r'p->unk58\b', '(p->s).coord.y'),
    (r'p->unk5C\b', '(p->s).d.x'),
    (r'p->unk60\b', '(p->s).d.y'),
    (r'p->unk64\b', '(p->s).unk_coord.x'),
    (r'p->unk68\b', '(p->s).unk_coord.y'),
    (r'p \+ 0x74', '&p->body'),
    (r'p->unk8C\b', '(p->body).status'),
    (r'p->unkA4\b', '(p->body).hp'),
    (r'p->unkB([4-9A-F])\b', lambda m: 'p->buffer[0x%X]' % (int('B' + m.group(1), 16) - 0xB4)),
    # RNG idiom
    (r'\(?(\w+) \* 0x343FD\)? \+ 0x269EC3', r'LCG(\1)'),
    # motion API
    (r'\bSetMotion\(p,', 'SetSpriteAnimation(p,'),
    (r'\bUpdateMotionGraphic\(p\)', 'UpdateSpriteAnimation(p)'),
    # collision stride 0x30 -> index
    (r'&sCollisions \+ 0x([0-9A-Fa-f]+)',
     lambda m: '&sCollisions[%d]' % (int(m.group(1), 16) // 0x30)),
    (r'\? (\w+)\(', r'void \1('),   # unknown-return externs -> void
]

def normalize(txt):
    for pat, rep in FIELD_MAP:
        txt = re.sub(pat, rep, txt)
    # MOTION(id, idx) for SetSpriteAnimation(p, 0xNNMM)
    def mo(m):
        v = int(m.group(1), 16)
        return 'SetSpriteAnimation(p, MOTION(0x%X, %d))' % (v >> 8, v & 0xFF)
    txt = re.sub(r'SetSpriteAnimation\(p, 0x([0-9A-Fa-f]{3,4})\)', mo, txt)
    return txt

def split_functions(inc_path):
    lines = io.open(inc_path, encoding='utf-8', errors='replace').read().split('\n')
    fns, cur, name = [], [], None
    for ln in lines:
        m = re.match(r'\s*thumb_func_start (\S+)', ln)
        if m:
            if name:
                fns.append((name, cur))
            name, cur = m.group(1), []
        elif name:
            cur.append(ln)
    if name:
        fns.append((name, cur))
    return fns

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10**9
    os.makedirs(OUT, exist_ok=True)
    incs = subprocess.run(['git', 'grep', '-h', 'INCASM(', '--', 'src/'],
                          capture_output=True, text=True, cwd=REPO).stdout
    incs = sorted(set(re.findall(r'INCASM\("([^"]+)"\)', incs)))
    done = 0
    for inc in incs:
        path = os.path.join(REPO, inc)
        if not os.path.exists(path):
            continue
        stem = os.path.basename(inc)[:-4]
        for fn, body in split_functions(path):
            if done >= limit:
                return
            od = os.path.join(OUT, stem)
            os.makedirs(od, exist_ok=True)
            outp = os.path.join(od, fn + '.c')
            if os.path.exists(outp):
                continue
            asm = '.syntax unified\n.thumb\nglabel %s\n%s\n' % (fn, '\n'.join(body))
            tmp = os.path.join(od, fn + '.s')
            io.open(tmp, 'w', encoding='utf-8', newline='\n').write(asm)
            r = subprocess.run(['python3', M2C, '--target', 'arm-gcc-c', tmp],
                               capture_output=True, text=True, encoding='utf-8',
                               errors='replace', timeout=120)
            txt = r.stdout or ''
            if 'Decompilation failure' in txt or not txt.strip():
                txt = '/* m2c failed:\n%s\n%s*/\n' % (txt, (r.stderr or '')[:2000])
            else:
                txt = normalize(txt)
            io.open(outp, 'w', encoding='utf-8', newline='\n').write(txt)
            os.remove(tmp)
            done += 1
            if done % 25 == 0:
                print('drafted %d fns (at %s/%s)' % (done, stem, fn), flush=True)
    print('DONE: %d drafts in %s' % (done, OUT))

main()
