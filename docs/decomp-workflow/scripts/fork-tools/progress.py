import os
"""Progress metrics: how much of the ROM's code is real, matching C.

Three buckets, reported by function count and by bytes (sizes from the
symbol map, tools/ghidra/rom_symbols.txt):

  declared-withc   NON_MATCH with a #if MODERN C body (near-miss territory)
  declared-pure    NON_MATCH/NAKED with no C at all (reconstruction backlog)
  undeclared-asm   functions living in asm/ .inc files with no C stub at all

Everything else is matched C. The tmc project tracks "matching" and
"nonmatching" as two separate curves; this is our equivalent, and it also
surfaces the undeclared-asm population that the holdout lists miss (found
via dup_scan: e.g. FUN_0803a5c8 lives only in asm/weapon/shield_fly.inc).

Usage: python3 tools/progress.py            # prints a summary
       python3 tools/progress.py --csv      # date,bucket,count,bytes rows
"""
import io, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYMS = os.path.join(REPO, 'tools', 'ghidra', 'rom_symbols.txt')
NAME_IN_DECL = re.compile(r'\b([A-Za-z_][A-Za-z_0-9]*)\s*\(')


def declared_holdouts():
    """-> {name: 'pure'|'withc'} straight from the source tree (not the
    cached build/ lists, so this never goes stale)."""
    out = {}
    # pathspec is plain 'src', NOT 'src/**/*.c' -- the latter silently skips
    # top-level files (src/mmbn4.c, src/player.c: 130+ declarations missed)
    txt = subprocess.run(
        ['git', 'grep', '-nE', r'^(NON_MATCH|NAKED)\b', '--', 'src'],
        capture_output=True, text=True, cwd=REPO,
        encoding='utf-8', errors='replace').stdout
    for l in txt.splitlines():
        parts = l.split(':', 2)
        if len(parts) < 3 or not parts[0].endswith('.c'):
            continue
        m = NAME_IN_DECL.search(parts[2])
        if not m:
            continue
        # withc == the function body carries a #if MODERN C alternative;
        # cheap test: read forward a few lines for '#if MODERN'
        try:
            src = io.open(os.path.join(REPO, parts[0]), encoding='utf-8',
                          errors='replace').read().split('\n')
            ln = int(parts[1]) - 1
            body = '\n'.join(src[ln:ln + 4])
            kind = 'withc' if '#if MODERN' in body else 'pure'
        except (IOError, ValueError):
            kind = 'pure'
        out[m.group(1)] = kind
    return out


def asm_functions():
    """function labels defined in asm/ (thumb_func_start NAME)"""
    txt = subprocess.run(
        ['git', 'grep', '-hE', r'^\s*thumb_func_start\s+\S+', '--', 'asm/'],
        capture_output=True, text=True, cwd=REPO,
        encoding='utf-8', errors='replace').stdout
    return set(l.split()[-1] for l in txt.splitlines())


def main():
    declared = declared_holdouts()
    in_asm = asm_functions()

    sizes, dup = {}, set()
    for l in io.open(SYMS, encoding='utf-8'):
        parts = l.split()
        if len(parts) != 3:
            continue
        n, size = parts[0], int(parts[2], 16)
        if n in sizes:
            dup.add(n)
        sizes[n] = sizes.get(n, 0) + size

    total_fns = sum(1 for _ in io.open(SYMS, encoding='utf-8'))
    total_bytes = sum(sizes.values())

    buckets = {'declared-withc': [0, 0], 'declared-pure': [0, 0],
               'undeclared-asm': [0, 0]}
    for n, kind in declared.items():
        b = buckets['declared-' + kind]
        b[0] += 1
        b[1] += sizes.get(n, 0)
    for n in in_asm:
        if n not in declared and n in sizes:
            buckets['undeclared-asm'][0] += 1
            buckets['undeclared-asm'][1] += sizes[n]

    un_c, un_b = (total_fns - sum(v[0] for v in buckets.values()),
                  total_bytes - sum(v[1] for v in buckets.values()))

    if '--csv' in sys.argv:
        import datetime
        d = datetime.date.today().isoformat()
        for k, (c, b) in sorted(buckets.items()):
            print('%s,%s,%d,%d' % (d, k, c, b))
        print('%s,matched,%d,%d' % (d, un_c, un_b))
        return

    print('total functions: %d   total code bytes: %d' % (total_fns, total_bytes))
    for k, (c, b) in sorted(buckets.items()):
        print('  %-16s %4d fns  %7d B  (%.2f%% of code bytes)'
              % (k, c, b, 100.0 * b / total_bytes))
    print('  %-16s %4d fns  %7d B  (%.2f%% of code bytes)'
          % ('matched C', un_c, un_b, 100.0 * un_b / total_bytes))
    if dup:
        print('note: %d duplicated static names in the map -- their byte '
              'attribution is approximate: %s'
              % (len(dup), ', '.join(sorted(dup)[:8])))


main()
