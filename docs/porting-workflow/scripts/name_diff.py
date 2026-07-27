#!/usr/bin/env python3
"""Compare the fork's linker map with upstream's to find naming differences.

Both maps describe the SAME retail ROM, so an address is a reliable join key.
Three outcomes matter:

  DANGEROUS  a name exists in both maps at DIFFERENT addresses -- porting it
             verbatim compiles, links, byte-verifies green and calls the wrong
             function (AllocEntityFirst/Last is exactly this)
  RENAME     one address, two different names -- must be translated when porting
  fork-only  no upstream symbol at that address yet

usage: name_diff.py <fork.map> <upstream.map>
"""
import re
import sys


def load(path):
    """address -> set(names). The map lists a symbol per line as
    `                0x08006f5c                AllocEntityFirst`."""
    by_addr = {}
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            m = re.match(r'^\s+0x0([0-9a-f]{7})\s+([A-Za-z_]\w*)\s*$', line)
            if not m:
                continue
            a = int(m.group(1), 16)
            if not (0x8000000 <= a < 0x9000000):     # ROM only, skip RAM/IO
                continue
            by_addr.setdefault(a, set()).add(m.group(2))
    return by_addr


fork, up = load(sys.argv[1]), load(sys.argv[2])
fork_names = {n: a for a, ns in fork.items() for n in ns}
up_names = {n: a for a, ns in up.items() for n in ns}

dangerous, renames = [], []
for n, fa in sorted(fork_names.items()):
    ua = up_names.get(n)
    if ua is not None and ua != fa:
        other = sorted(up.get(fa, set()))
        dangerous.append((n, fa, ua, other[0] if other else '?'))
for a, fns in sorted(fork.items()):
    uns = up.get(a)
    if not uns:
        continue
    only_f, only_u = fns - uns, uns - fns
    if only_f and only_u:
        renames.append((a, sorted(only_f)[0], sorted(only_u)[0]))

print('=== DANGEROUS: same name, different function (%d)' % len(dangerous))
for n, fa, ua, other in dangerous:
    print('  %-30s fork 0x%08X  upstream 0x%08X   (0x%08X is `%s` upstream)'
          % (n, fa, ua, fa, other))
print()
print('=== RENAMES: same address, different name (%d)' % len(renames))
for a, f, u in renames:
    print('  0x%08X  %-32s -> %s' % (a, f, u))
