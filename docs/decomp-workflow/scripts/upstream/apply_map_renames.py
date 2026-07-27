#!/usr/bin/env python3
"""Translate fork symbol names to upstream names, driven by the two linker maps.

The fork and upstream are independent decompilations of the SAME retail ROM, so
a ROM address is a reliable join key between their linker maps. Everything this
script does is derived from that join -- there is no hand-maintained list to
drift out of date. Regenerate `upstream.map` from any green CI run (the Build
workflow uploads build/rmz3/rmz3.map alongside the ROM).

Two classes of difference, and the second is why this exists:

  RENAME     one address, two spellings (`CalcFromCamera` -> `Camera_GetDistance`).
             Porting verbatim fails to link, so it is at least loud.
  SWAP       a name that exists on BOTH sides but means a DIFFERENT function:
             fork `AllocEntityLast` is upstream `AllocEntityFirst` and vice
             versa. This links fine, byte-verifies green, and silently calls the
             wrong function. Only a full build catches it.

All substitutions happen in ONE regex pass, so a swap can never be applied twice
and collapse back to the original.

Edits are confined to lines the branch ADDS versus upstream/dev. Pre-existing
upstream C already uses upstream spelling; rewriting it would corrupt correct
code (a blanket rewrite has done exactly that here before).

usage: apply_map_renames.py <fork.map> <upstream.map> <file.c> ...
       apply_map_renames.py --table <fork.map> <upstream.map>
"""
import io
import re
import subprocess
import sys


def load(path):
    """address -> set(names).

    ROM (0x08..) plus EWRAM (0x02..) and IWRAM (0x03..). Restricting this to
    ROM meant every global variable was invisible to the join: `gMission` and
    `gScore` are the same object at 0x0202fe20, and without the EWRAM range the
    lifted code kept the fork's spelling and failed as `gMission undeclared` /
    `invalid use of undefined type 'struct Mission'`. Both trees link the same
    image, so a RAM address is exactly as reliable a key as a ROM one."""
    by_addr = {}
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            m = re.match(r'^\s+0x0([0-9a-f]{7})\s+([A-Za-z_]\w*)\s*$', line)
            if not m:
                continue
            a = int(m.group(1), 16)
            if (0x8000000 <= a < 0x9000000
                    or 0x2000000 <= a < 0x2040000
                    or 0x3000000 <= a < 0x3008000):
                by_addr.setdefault(a, set()).add(m.group(2))
    return by_addr


def rename_table(fork_map, up_map):
    """fork name -> upstream name."""
    fork, up = load(fork_map), load(up_map)
    table = {}
    for a, fns in fork.items():
        uns = up.get(a)
        if not uns:
            continue
        only_f, only_u = sorted(fns - uns), sorted(uns - fns)
        if only_f and only_u:
            table[only_f[0]] = only_u[0]
    return table


def added_lines(path):
    d = subprocess.run(['git', 'diff', 'upstream/dev', '--', path],
                       capture_output=True, text=True, errors='replace').stdout
    return {l[1:].rstrip('\r\n') for l in d.split('\n')
            if l.startswith('+') and not l.startswith('+++')}


def main():
    if sys.argv[1] == '--table':
        t = rename_table(sys.argv[2], sys.argv[3])
        for k in sorted(t):
            print('%-34s -> %s' % (k, t[k]))
        print('%d rename(s)' % len(t))
        return 0

    table = rename_table(sys.argv[1], sys.argv[2])
    # Longest-first so a name that is a prefix of another cannot win.
    pat = re.compile(r'\b(%s)\b' % '|'.join(
        re.escape(k) for k in sorted(table, key=len, reverse=True)))

    grand = 0
    for path in sys.argv[3:]:
        added = added_lines(path)
        text = io.open(path, encoding='utf-8', newline='').read()
        lines = text.split('\n')
        hits, n = {}, 0
        for i, line in enumerate(lines):
            if line.rstrip('\r') not in added:
                continue

            def sub(m):
                hits[m.group(1)] = hits.get(m.group(1), 0) + 1
                return table[m.group(1)]

            new = pat.sub(sub, line)
            if new != line:
                lines[i] = new
                n += 1
        if n:
            io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
            detail = ', '.join('%s->%s x%d' % (k, table[k], v)
                               for k, v in sorted(hits.items()))
            print('  %s' % path)
            print('      %s' % detail)
            grand += sum(hits.values())
    print('applied %d rename(s)' % grand)
    return 0


sys.exit(main())
