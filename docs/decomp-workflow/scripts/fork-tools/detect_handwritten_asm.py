import os
"""Flag holdouts that were hand-written assembly, not compiler output.

A compiler always emits the prologue first. If a function does real work
*before* its `push`, it was written by hand and there is no C source to
recover -- no amount of permuting will reach it. FUN_080ee328 in
src/game/main.c is the clear case:

    lsrs r1, r1, #1        <-- work
    push {r4, r5, r6, r7}  <-- prologue, second

Reporting these up front stops people burning days on functions that cannot
match. Run it before picking reconstruction targets.

Also reports the `push {r7, lr}` frame-pointer form, which in this ROM appears
only in src/mmbn4.c -- the separately-built link-cable and e-Reader library,
compiled by something other than agbcc.

Usage: python3 tools/detect_handwritten_asm.py
Writes notes/handwritten-asm.md
"""
import io, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, 'notes', 'handwritten-asm.md')

# an instruction line in a .inc or in an inline asm() block
INSN = re.compile(r'^\s*(?:\\n\\?)?\s*([a-z][a-z0-9.]*)\b')
SKIP = re.compile(r'^\s*(?:@|/\*|\.|_[0-9A-Za-z_]*:|[A-Za-z_][A-Za-z_0-9]*:)')
PROLOGUE = ('push',)
# things that legitimately precede a push in compiler output: nothing.
# things that are not instructions at all:
NOT_INSN = ('syntax', 'align', 'byte', 'short', 'word', 'incbin', 'text',
            'thumb_func_start', 'thumb_func_end', 'global', 'section', 'end')


def instructions(text):
    out = []
    for raw in text.split('\n'):
        l = raw.strip().rstrip('\\')
        l = l.replace('\\n', '').strip()
        if not l or SKIP.match(l):
            continue
        m = INSN.match(l)
        if not m:
            continue
        op = m.group(1)
        if op in NOT_INSN:
            continue
        out.append((op, l))
    return out


def classify(insns):
    """-> (verdict, detail) or None when it looks like ordinary output."""
    if not insns:
        return None
    ops = [o for o, _ in insns]
    if 'push' in ops:
        i = ops.index('push')
        if i > 0:
            return ('work before the prologue',
                    '%d instruction(s) precede `%s`: %s'
                    % (i, insns[i][1], '; '.join(l for _, l in insns[:i])))
        if re.match(r'^push\s*\{r7,\s*lr\}', insns[i][1]):
            return ('r7 frame-pointer prologue', insns[i][1])
    return None


def main():
    os.chdir(REPO)
    hits = []
    # Coverage counters. A detector that silently parses nothing reports a
    # clean bill of health, so make its reach visible on every run.
    stats = {'segments': 0, 'push': 0, 'leaf': 0, 'empty': 0}

    def note(insns):
        stats['segments'] += 1
        if not insns:
            stats['empty'] += 1
        elif any(o == 'push' for o, _ in insns):
            stats['push'] += 1
        else:
            stats['leaf'] += 1
        return insns

    # 1. asm fragments. Most .inc files are monolithic, so split them at
    #    thumb_func_start boundaries and classify each function separately --
    #    skipping them (an earlier version did) misses nearly the whole backlog.
    START = re.compile(r'^\s*thumb_func_start\s+(\S+)', re.M)
    for root, _, files in os.walk('asm'):
        for f in files:
            if not f.endswith(('.inc', '.s')):
                continue
            p = os.path.join(root, f).replace('\\', '/')
            t = io.open(p, encoding='utf-8', errors='replace').read()
            marks = list(START.finditer(t))
            if not marks:
                c = classify(note(instructions(t)))
                if c:
                    hits.append((p, os.path.splitext(f)[0], c[0], c[1]))
                continue
            for i, m in enumerate(marks):
                end = marks[i + 1].start() if i + 1 < len(marks) else len(t)
                body = t[m.end():end]
                c = classify(note(instructions(body)))
                if c:
                    hits.append((p, m.group(1), c[0], c[1]))

    # 2. inline asm() bodies of NAKED functions in the C sources
    FN = re.compile(r'^(?:NON_MATCH|NAKED)\b[^\n{]*?([A-Za-z_][A-Za-z_0-9]*)\s*\('
                    r'[^\n]*\{\s*\n\s*asm\(', re.M)
    for root, _, files in os.walk('src'):
        for f in files:
            if not f.endswith('.c'):
                continue
            p = os.path.join(root, f).replace('\\', '/')
            t = io.open(p, encoding='utf-8', errors='replace').read()
            for m in FN.finditer(t):
                body = t[m.end():t.find('.syntax divided', m.end())]
                c = classify(note(instructions(body)))
                if c:
                    hits.append((p, m.group(1), c[0], c[1]))

    bykind = {}
    for h in hits:
        bykind.setdefault(h[2], []).append(h)

    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as w:
        w.write(u'# Holdouts that are hand-written assembly (%d)\n\n' % len(hits))
        w.write(u'A compiler always emits the prologue first. A function that does\n'
                u'real work *before* its `push` was written by hand, so there is no C\n'
                u'source to recover and no amount of permuting will reach it.\n\n'
                u'Regenerate with `python3 tools/detect_handwritten_asm.py`.\n\n')
        for kind in sorted(bykind):
            rows = bykind[kind]
            w.write(u'## %s (%d)\n\n' % (kind, len(rows)))
            for p, fn, _, detail in sorted(rows):
                w.write(u'- **%s** — `%s`\n  - %s\n' % (fn, p, detail))
            w.write(u'\n')

    print('scanned %d function segments: %d with a prologue, %d leaf, %d parsed empty'
          % (stats['segments'], stats['push'], stats['leaf'], stats['empty']))
    if stats['empty'] > stats['segments'] // 4:
        print('WARNING: many segments parsed empty -- the instruction regex may be wrong')
    for kind in sorted(bykind):
        print('%-32s %d' % (kind, len(bykind[kind])))
    print('%d total -> %s' % (len(hits), os.path.relpath(OUT, REPO)))


main()
