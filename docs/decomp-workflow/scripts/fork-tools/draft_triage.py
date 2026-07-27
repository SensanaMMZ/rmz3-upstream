import os
"""Rank the m2c drafts by attemptability: clean output, few unknowns, moderate
size. Output: build/m2c-drafts/WORKLIST.md (best first)."""
import io, os, re

OUT = 'build/m2c-drafts'
rows = []
for root, d, fs in os.walk(OUT):
    for f in fs:
        if not f.endswith('.c'):
            continue
        p = os.path.join(root, f)
        s = io.open(p, encoding='utf-8', errors='replace').read()
        if 'm2c failed' in s:
            continue
        fn = f[:-2]
        inc = os.path.basename(root)
        instr_guess = s.count(';')
        unknowns = len(re.findall(r'\?\s', s)) + s.count('MIPS2C') + s.count('M2C_ERROR')
        gotos = s.count('goto ')
        temps = len(re.findall(r'\btemp_\w+', set_ := s)) // 2
        raw_offsets = len(re.findall(r'->unk[0-9A-F]{2,}', s))
        # score: prefer mid-size, few unknowns/gotos/raw offsets
        size_pen = abs(instr_guess - 45) / 10.0
        score = unknowns * 3 + gotos * 2 + raw_offsets * 0.5 + size_pen
        rows.append((score, inc, fn, instr_guess, unknowns, gotos, raw_offsets))
rows.sort()
w = io.open(os.path.join(OUT, 'WORKLIST.md'), 'w', encoding='utf-8')
w.write('# m2c draft worklist — best-first (score = unknowns*3 + gotos*2 + rawoffs/2 + sizepen)\n\n')
w.write('| score | inc | fn | ~stmts | ? | gotos | raw-offs |\n|---|---|---|---|---|---|---|\n')
for score, inc, fn, sz, u, g, r in rows[:150]:
    w.write('| %.1f | %s | %s | %d | %d | %d | %d |\n' % (score, inc, fn, sz, u, g, r))
w.close()
print('ranked %d drafts -> %s/WORKLIST.md' % (len(rows), OUT))
print('top 12:')
for score, inc, fn, sz, u, g, r in rows[:12]:
    print('  %.1f %s/%s (%d stmts, %d unk, %d gotos)' % (score, inc, fn, sz, u, g))
