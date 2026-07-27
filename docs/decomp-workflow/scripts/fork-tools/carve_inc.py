#!/usr/bin/env python3
"""Carve one function out of an .inc, leaving the before/after halves.

usage: carve_inc.py <inc> <fn>

Writes <base>_a.inc (functions before FN) and <base>_b.inc (functions after FN),
deletes the original, and prints the paths that survived. A half with no content
is not written, and an existing filename is never clobbered (an earlier split may
already have claimed <base>_b.inc).

ORPHAN RESCUE: the region being deleted can end with content that belongs to the
ROM but carries no thumb_func_start -- alignment padding, or a stray `bx lr`
(`.byte 0x70, 0x47`). Dropping it shifts every later object and moves the whole
ROM. Any trailing labelled `.byte` run is therefore reattached to the surviving
half. Literal pools are `.4byte` and correctly stay with the removed function.
"""
import os
import re
import sys

HDR = '\t.include "asm/macros.inc"\n\n\t.syntax unified\n\t\n\t.text\n\n'
ORPHAN = re.compile(r'(^_[0-9A-Fa-f]{8}:\n(?:[ \t]*\.byte [^\n]*\n?)+)', re.M)


def free_path(base, suffix):
    path = base + suffix + '.inc'
    n = 0
    while os.path.exists(path):
        n += 1
        path = '%s%s%s.inc' % (base, suffix, chr(ord('b') + n))
    return path


def main():
    inc, fn = sys.argv[1], sys.argv[2]
    txt = open(inc, encoding='utf-8').read()
    body = (txt[txt.index('.text') + len('.text'):].lstrip('\n')
            if txt.startswith('\t.include') else txt)

    marks = [(m.start(), m.group(1))
             for m in re.finditer(r'^\tthumb_func_start (\S+)$', body, re.M)]
    names = [n for _, n in marks]
    if fn not in names:
        sys.exit('no thumb_func_start %s in %s' % (fn, inc))

    i = names.index(fn)
    before = body[:marks[i][0]]
    cut_end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
    after = body[cut_end:]

    orphan = ORPHAN.search(body[marks[i][0]:cut_end])
    if orphan:
        print('ORPHAN RESCUED (dropping this would have shifted the ROM):\n%s'
              % orphan.group(1).rstrip())
        after = orphan.group(1) + '\n' + after

    out = []
    base = os.path.splitext(inc)[0]
    for suffix, part in (('_a', before), ('_b', after)):
        if part.strip():
            path = free_path(base, suffix)
            open(path, 'w', encoding='utf-8', newline='\n').write(
                HDR + part.rstrip('\n') + '\n')
            out.append(path)
    os.remove(inc)
    print('\n'.join(out))


main()
