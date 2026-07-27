#!/usr/bin/env python3
"""Port verified matches from the fork's main onto upstream's inc layout.

The fork splits incs (`copy_x_p2_p3_p1_p1.inc`); upstream keeps one whole-file
inc per source file. So a cherry-pick always conflicts and each function has to
be re-carved against upstream's file.

For one upstream .inc plus the functions to lift out of it, this:
  * splits the inc at thumb_func_start boundaries,
  * writes the surviving runs back as <base>_a.inc, <base>_b.inc, ...,
  * replaces the single INCASM in the .c with the interleaved
    INCASM / C / INCASM / C / INCASM sequence,
  * takes each function's C body verbatim from `git show main:<file>`.

usage: port_to_upstream.py <inc> <src.c> <main-src.c> <fn> [<fn> ...]
"""
import os
import re
import subprocess
import sys

HDR = '\t.include "asm/macros.inc"\n\n\t.syntax unified\n\t\n\t.text\n\n'


def fork_text(path):
    """Read a file out of the fork. These files carry Japanese comments, so
    decode explicitly rather than letting subprocess pick the console codepage
    (cp1252 here, which throws)."""
    r = subprocess.run(['git', 'show', 'main:' + path], capture_output=True)
    if r.returncode:
        return None
    return r.stdout.decode('utf-8', errors='replace')


def extract(txt, fn):
    """Return `fn`'s full definition from `txt`, or None if it is only
    declared there. Must land on the DEFINITION, not a forward declaration --
    these files list every handler as `void fn(struct Boss* p);` long before
    defining it, and matching that swallows the whole declaration block."""
    start = i = None
    for m in re.finditer(r'^[A-Za-z_][\w \*]*\b%s\(' % re.escape(fn), txt, re.M):
        close = txt.index(')', m.end() - 1)
        tail = txt[close + 1:close + 40].lstrip()
        if tail.startswith('{'):
            start, i = m.start(), txt.index('{', close)
            break
    if start is None:
        return None
    depth = 0
    for j in range(i, len(txt)):
        if txt[j] == '{':
            depth += 1
        elif txt[j] == '}':
            depth -= 1
            if depth == 0:
                return txt[start:j + 1] + '\n'
    sys.exit('unbalanced braces for %s' % fn)


USED_SRC = []          # fork files the bodies were actually taken from
SRC_NOTE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'fork_src.txt')


def c_body(hint, fn):
    """Pull `fn`'s definition out of the fork. `hint` is the mirrored path, but
    the fork does NOT always keep a function in the file whose name matches the
    upstream .inc -- FUN_0809fa44 lives in src/projectile/unk_13.c while the inc
    is baby_elf.inc. Assuming the mirror silently failed 6 clusters, so fall back
    to asking git where the definition actually is."""
    txt = fork_text(hint)
    if txt is not None:
        got = extract(txt, fn)
        if got:
            USED_SRC.append(hint)
            return got
    # `git grep -l` alone matches declarations and call sites too, so it only
    # narrows the candidates -- extract() is what decides.
    r = subprocess.run(['git', 'grep', '-l', '-F', fn, 'main', '--', 'src'],
                       capture_output=True, text=True)
    for line in r.stdout.splitlines():
        path = line.split(':', 1)[1] if ':' in line else line
        if path == hint or not path.endswith('.c'):
            continue
        txt = fork_text(path)
        if txt is None:
            continue
        got = extract(txt, fn)
        if got:
            sys.stderr.write('    %s: taking body from %s (not %s)\n'
                             % (fn, path, hint))
            USED_SRC.append(path)
            return got
    sys.exit('no definition of %s anywhere in the fork (hint was main:%s) -- '
             'it is declared but never defined, so it is not portable' % (fn, hint))


def main():
    inc, src, main_src = sys.argv[1], sys.argv[2], sys.argv[3]
    fns = sys.argv[4:]

    # Extract every C body FIRST. The original version split the .inc before
    # doing this, so a failure here left the tree half-ported: incs carved up
    # but the .c never updated, i.e. functions silently dropped from the link.
    bodies = {fn: c_body(main_src, fn) for fn in fns}
    # Record where the bodies came from. Later fixers need it: a file-local
    # table name like `sUpdates` exists in dozens of fork files, and resolving
    # it tree-wide picks the wrong type.
    with open(SRC_NOTE, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(dict.fromkeys(USED_SRC)))

    txt = open(inc, encoding='utf-8', errors='replace').read()
    body = (txt[txt.index('.text') + len('.text'):].lstrip('\n')
            if txt.startswith('\t.include') else txt)
    marks = [(m.start(), m.group(1))
             for m in re.finditer(r'^\tthumb_func_start (\S+)$', body, re.M)]
    if not marks:
        sys.exit('no functions in ' + inc)
    names = [n for _, n in marks]
    for fn in fns:
        if fn not in names:
            sys.exit('%s not in %s' % (fn, inc))

    bounds = [m[0] for m in marks] + [len(body)]
    # Walk the functions in file order, accumulating runs of asm between lifts.
    pieces, run, order = [], [], []
    for idx, name in enumerate(names):
        chunk = body[bounds[idx]:bounds[idx + 1]]
        if name in fns:
            if run:
                pieces.append(''.join(run))
                order.append(('asm', len(pieces) - 1))
                run = []
            order.append(('c', name))
        else:
            run.append(chunk)
    if run:
        pieces.append(''.join(run))
        order.append(('asm', len(pieces) - 1))

    # CHECK EVERY PRECONDITION BEFORE MUTATING ANYTHING. The old order wrote
    # piece files one by one and hit `refusing to clobber` (or the marker check
    # below) only after some were already on disk -- bee_server was left with
    # bee_server_a/_b.inc written, the original inc still present, and the .c
    # untouched, and that half-applied state got committed. Now: all piece
    # paths are validated, and the .c marker is validated, before the first
    # byte is written.
    base = os.path.splitext(inc)[0]
    paths = ['%s_%s.inc' % (base, chr(ord('a') + n))
             for n in range(len(pieces))]
    for p in paths:
        if os.path.exists(p):
            sys.exit('refusing to clobber ' + p)
    s = open(src, encoding='utf-8', errors='replace', newline='').read()
    marker = 'INCASM("%s");\n' % inc
    if marker not in s:
        sys.exit('marker not found in %s: %s' % (src, marker.strip()))

    for p, part in zip(paths, pieces):
        open(p, 'w', encoding='utf-8', newline='\n').write(
            HDR + part.rstrip('\n') + '\n')
    os.remove(inc)

    out = []
    for kind, val in order:
        if kind == 'asm':
            out.append('INCASM("%s");\n' % paths[val])
        else:
            out.append(bodies[val])
    replacement = '\n'.join(out)

    open(src, 'w', encoding='utf-8', newline='').write(
        s.replace(marker, replacement, 1))

    print('%s -> %d asm part(s), %d function(s) lifted into %s'
          % (inc, len(paths), len(fns), src))


# Guarded so this module can be imported for its carving logic. Unguarded,
# `import port_to_upstream` ran the whole port immediately using the IMPORTER's
# argv -- which read a `fn:kind` spec as the source path.
if __name__ == '__main__':
    main()
