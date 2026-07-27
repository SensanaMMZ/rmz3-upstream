import os
"""Resolve Ghidra's DAT_08xxxxxx placeholders in the batch drafts.

Ghidra names an unrecognised literal-pool slot `DAT_08xxxxxx` and dereferences
it, so a global access shows up as `*DAT_080ea274` -- correct, but unreadable,
and it is the single most common noise in the drafts (5,648 occurrences across
357 files when this was written).

The slot is just four bytes of ROM. Read them, resolve the value against the
symbol map, and rename the token, so `*DAT_080ea274` becomes
`*p_gVideoRegBuffer`. Pointer semantics are preserved -- the token is renamed,
not the expression rewritten -- so the draft stays honest.

Handles three cases:
  * a slot inside .text        -> read the word, resolve what it points at
  * an address in .rodata/RAM  -> resolve it directly
  * a GBA I/O register         -> REG_* name from include/gba/io_reg.h

Usage: python3 tools/ghidra/resolve_pool_refs.py [draft_dir]
Rewrites the drafts in place and appends a legend to each.
"""
import bisect, io, os, re, struct, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROM = os.path.join(REPO, 'baseimg.gba')
DRAFTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, 'build', 'ghidra-drafts')
CODE = os.path.join(REPO, 'tools', 'ghidra', 'rom_symbols.txt')
DATA = os.path.join(REPO, 'tools', 'ghidra', 'rom_data_symbols.txt')
IOREG = os.path.join(REPO, 'include', 'gba', 'io_reg.h')

ROM_BASE = 0x08000000
TEXT_END = 0x080FEA74          # .rodata base; below this a ROM word is code/pool
TOKEN = re.compile(r'\b(_?DAT|PTR_DAT|PTR)_(0[0-9a-fA-F]{7})\b')
REG_OFF = re.compile(r'^#define\s+REG_OFFSET_([A-Z0-9_]+)\s+0x([0-9A-Fa-f]+)')


def load_syms():
    addrs, names, sizes = [], [], []
    rows = []
    for path in (CODE, DATA):
        if not os.path.exists(path):
            continue
        for ln in io.open(path):
            p = ln.split()
            if len(p) >= 2:
                rows.append((int(p[1], 16), int(p[2], 16) if len(p) > 2 else 0, p[0]))
    rows.sort()
    for a, s, n in rows:
        addrs.append(a); sizes.append(s); names.append(n)
    return addrs, sizes, names


def load_regs():
    d = {}
    if os.path.exists(IOREG):
        for ln in io.open(IOREG, errors='replace'):
            m = REG_OFF.match(ln)
            if m:
                d.setdefault(0x04000000 + int(m.group(2), 16), 'REG_' + m.group(1))
    return d


def main():
    if not os.path.isdir(DRAFTS):
        sys.exit('no draft dir: %s' % DRAFTS)
    rom = open(ROM, 'rb').read()
    addrs, sizes, names = load_syms()
    regs = load_regs()
    print('%d symbols, %d I/O registers' % (len(addrs), len(regs)))

    def resolve(a):
        """address -> symbol name (with +offset when interior), or None."""
        if a in regs:
            return regs[a]
        if 0x04000000 <= a < 0x04000400:
            return 'IO_%08X' % a
        i = bisect.bisect_right(addrs, a) - 1
        if i < 0:
            return None
        base, size, nm = addrs[i], sizes[i], names[i]
        if a == base:
            return nm
        if size and a < base + size:
            return '%s_plus_%X' % (nm, a - base)
        return None

    def word_at(a):
        off = a - ROM_BASE
        if 0 <= off <= len(rom) - 4:
            return struct.unpack('<I', rom[off:off + 4])[0]
        return None

    total, hit = 0, 0
    for fname in sorted(os.listdir(DRAFTS)):
        if not fname.endswith('.c'):
            continue
        p = os.path.join(DRAFTS, fname)
        t = io.open(p, encoding='utf-8', errors='replace').read()
        legend = {}

        def sub(m):
            tok, hx = m.group(0), int(m.group(2), 16)
            if hx < TEXT_END:                      # literal-pool slot: deref it
                v = word_at(hx)
                if v is None:
                    return tok
                r = resolve(v)
                if r is None:
                    # not an address -- the slot holds a plain constant, which is
                    # what you need to write the C. Only safe where the token is
                    # read as a value: never behind * or &, which would mean
                    # Ghidra is treating it as an object.
                    lead = t[max(0, m.start() - 1):m.start()]
                    if lead in ('*', '&'):
                        return tok
                    legend['0x%X' % v] = '[%08X] literal' % hx
                    return '0x%X' % v
                new = 'p_' + r
                legend[new] = '[%08X] -> %08X %s' % (hx, v, r)
            else:                                  # a real data address
                r = resolve(hx)
                if r is None:
                    return tok
                new = r
                legend[new] = '%08X' % hx
            return new

        n_before = len(TOKEN.findall(t))
        t2 = TOKEN.sub(sub, t)
        total += n_before
        hit += n_before - len(TOKEN.findall(t2))
        if legend:
            t2 = t2.rstrip('\n') + '\n\n/* resolved from the literal pool:\n'
            for k in sorted(legend):
                t2 += '     %-34s %s\n' % (k, legend[k])
            t2 += ' */\n'
        io.open(p, 'w', encoding='utf-8', newline='\n').write(t2)

    print('resolved %d of %d DAT_ tokens (%.1f%%)'
          % (hit, total, 100.0 * hit / total if total else 0))


main()
