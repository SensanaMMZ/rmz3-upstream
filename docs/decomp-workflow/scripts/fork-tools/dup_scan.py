import os
"""Find unmatched functions whose ROM bytes duplicate matched C.

MMZ engine code repeats heavily; a declared holdout OR an undeclared
asm-resident function that is byte-identical (or identical modulo call
targets and pool literals) to an already-matched function inherits that
function's C body nearly verbatim. Scanning for this first is cheaper
than reconstructing from scratch. The undeclared-asm population is the
big one: ~1,864 functions / 52% of code bytes (tools/progress.py).

Three signatures per function, strict to loose:
  exact   raw bytes
  bl      bl offset bits masked (same code, different callee addresses)
  full    bl bits + likely pool words (RAM/IO/ROM addresses) masked

A cluster is reported when it holds at least one unmatched function.
Clusters that also hold a matched-C function are candidate free matches;
unmatched-only clusters mean solving one member solves them all.

Usage: python3 tools/dup_scan.py            # writes notes/dup-scan.md
"""
import hashlib, io, os, re, struct, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM = os.path.join(REPO, 'baseimg.gba')
SYMS = os.path.join(REPO, 'tools', 'ghidra', 'rom_symbols.txt')
HOLDOUT_LISTS = [os.path.join(REPO, 'build', 'holdouts-pure.txt'),
                 os.path.join(REPO, 'build', 'holdouts-withc.txt')]
OUT = os.path.join(REPO, 'notes', 'dup-scan.md')
ROM_SHA1 = 'ff7a801776dc76e6d8c7ef73a6660ae732934a3f'

NAME_IN_DECL = re.compile(r'\b([A-Za-z_][A-Za-z_0-9]*)\s*\(')


def load_symbols():
    out = []
    for l in io.open(SYMS, encoding='utf-8'):
        parts = l.split()
        if len(parts) != 3:
            continue
        name, addr, size = parts[0], int(parts[1], 16), int(parts[2], 16)
        if size:
            out.append((name, addr, size))
    return out


def load_holdouts(sym_names):
    """holdout list lines look like: src/f.c:55 NAKED static void Name(void* p) {

    A static's name can repeat across files while the symbol map keeps only
    one (renamed) entry per address, so matching by bare name would pin the
    holdout label on some unrelated file's function (this produced a false
    "onCollision is a 2-byte free match" on the first run). A name is usable
    only when it is unique in BOTH the holdout lists and the symbol map;
    everything else is reported as ambiguous instead of trusted.
    """
    decls, kind = {}, {}
    for p in HOLDOUT_LISTS:
        k = 'pure' if 'pure' in os.path.basename(p) else 'withc'
        for l in io.open(p, encoding='utf-8'):
            decl = l.split(None, 2)
            if len(decl) < 3:
                continue
            m = NAME_IN_DECL.search(decl[2])
            if m:
                decls[m.group(1)] = decls.get(m.group(1), 0) + 1
                kind[m.group(1)] = k
    from collections import Counter
    sym_count = Counter(sym_names)
    names, ambiguous = set(), []
    for n, c in sorted(decls.items()):
        if c == 1 and sym_count.get(n, 0) == 1:
            names.add(n)
        else:
            ambiguous.append('%s (%d decls, %d map entries)'
                             % (n, c, sym_count.get(n, 0)))
    return names, kind, ambiguous


def asm_resident():
    """function labels defined in asm/ (thumb_func_start NAME) -- the
    undeclared population when not also a declared holdout"""
    txt = subprocess.run(
        ['git', 'grep', '-hE', r'^\s*thumb_func_start\s+\S+', '--', 'asm/'],
        capture_output=True, text=True, cwd=REPO,
        encoding='utf-8', errors='replace').stdout
    return set(l.split()[-1] for l in txt.splitlines())


def mask_bl(b):
    out = bytearray(b)
    i = 0
    while i + 3 < len(out):
        hw1 = out[i] | (out[i + 1] << 8)
        hw2 = out[i + 2] | (out[i + 3] << 8)
        if 0xF000 <= hw1 <= 0xF7FF and 0xF800 <= hw2 <= 0xFFFF:
            out[i:i + 4] = b'\x00\xf0\x00\xf8'
            i += 4
            continue
        i += 2
    return bytes(out)


def mask_pool(b, addr):
    """Mask 4-aligned words that look like GBA addresses (pool literals)."""
    out = bytearray(b)
    # pools are word-aligned in the address space, not relative to the symbol
    start = (4 - addr % 4) % 4
    for i in range(start, len(out) - 3, 4):
        w = struct.unpack_from('<I', out, i)[0]
        hi = w >> 24
        if hi in (0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09):
            struct.pack_into('<I', out, i, 0)
    return bytes(out)


def main():
    rom = open(ROM, 'rb').read()
    if hashlib.sha1(rom).hexdigest() != ROM_SHA1:
        sys.exit('baseimg.gba sha1 mismatch -- refusing to scan the wrong ROM')
    syms = load_symbols()
    holdouts, kind, ambiguous = load_holdouts([n for n, _, _ in syms])
    in_asm = asm_resident()

    matched_names = set(n for n, _, _ in syms)
    missing = sorted(holdouts - matched_names)

    def tag(n):
        """holdout / asm (undeclared, body only in asm/) / C (matched)"""
        if n in holdouts:
            return 'holdout'
        if n in in_asm:
            return 'asm'
        return 'C'

    sigs = {'exact': {}, 'bl': {}, 'full': {}}
    n_bytes = 0
    for name, addr, size in syms:
        off = addr - 0x08000000
        if off < 0 or off + size > len(rom):
            continue
        raw = rom[off:off + size]
        n_bytes += size
        b = mask_bl(raw)
        f = mask_pool(b, addr)
        for level, sig in (('exact', raw), ('bl', b), ('full', f)):
            key = (size, hashlib.md5(sig).hexdigest())
            sigs[level].setdefault(key, []).append(name)

    # verify the verifier: the scan must place every function exactly once
    # per level, and a masked level can only merge clusters, never split.
    for level in sigs:
        total = sum(len(v) for v in sigs[level].values())
        assert total == sum(1 for n, a, s in syms
                            if 0 <= a - 0x08000000 <= len(rom) - s), level

    def clusters(level, tighter_keys):
        """clusters at `level` holding an unmatched fn, new vs tighter level"""
        out = []
        for key, names in sorted(sigs[level].items()):
            if len(names) < 2:
                continue
            un = [n for n in names if tag(n) != 'C']
            if not un:
                continue
            if tighter_keys is not None and key in tighter_keys:
                continue
            out.append((key[0], names, un))
        return out

    tight_exact = set(k for k, v in sigs['exact'].items() if len(v) > 1)
    tight_bl = set(k for k, v in sigs['bl'].items() if len(v) > 1)
    ex = clusters('exact', None)
    bl = clusters('bl', tight_exact)
    fu = clusters('full', tight_bl)

    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as w:
        w.write(u'# Duplicate scan over the ROM (%d functions, %d bytes)\n\n'
                % (len(syms), n_bytes))
        w.write(u'Regenerate with `python3 tools/dup_scan.py`. A holdout in a\n'
                u'cluster with a matched function is a candidate free match:\n'
                u'reuse the matched body, then map callees/globals from the\n'
                u'holdout\'s own relocations (`tools/fnbytes.py` verifies).\n\n')
        for title, rows, note in (
            ('Byte-identical', ex,
             'identical including call offsets and pool words'),
            ('Identical modulo call targets', bl,
             'bl offset bits masked; everything else identical'),
            ('Identical modulo calls and pool literals', fu,
             'bl bits and address-like pool words masked'),
        ):
            big = [r for r in rows if r[0] >= 8]
            small = [r for r in rows if r[0] < 8]
            w.write(u'## %s (%d clusters) — %s\n\n' % (title, len(big), note))
            if small:
                w.write(u'(%d trivial clusters under 8 bytes omitted: '
                        u'%d unmatched nop-class functions)\n\n'
                        % (len(small), sum(len(u_) for _, _, u_ in small)))
            for size, names, un in big:
                cs = [n for n in names if tag(n) == 'C']
                hs = [n for n in un if n in holdouts]
                an = [n for n in un if n not in holdouts]
                label = ('FREE via C twin' if cs
                         else 'solve-one-get-%d' % len(un))
                parts = []
                if hs:
                    parts.append('holdouts ' + ', '.join(
                        '`%s`%s' % (h, '*' if kind.get(h) == 'withc' else '')
                        for h in hs))
                if an:
                    parts.append('asm ' + ', '.join('`%s`' % a for a in an))
                if cs:
                    parts.append('C ' + ', '.join('`%s`' % c for c in cs[:6])
                                 + (' (+%d more)' % (len(cs) - 6) if len(cs) > 6 else ''))
                w.write(u'- **%s** (%d B): %s\n' % (label, size, '; '.join(parts)))
            w.write(u'\n')
        w.write(u'`*` = holdout already has a C body (withc list).\n')
        if ambiguous:
            w.write(u'\n%d holdout names were AMBIGUOUS (static name reused '
                    u'across files or renamed in the map) and were excluded '
                    u'from the scan — check these by address by hand:\n'
                    % len(ambiguous))
            for n in ambiguous:
                w.write(u'- %s\n' % n)
        if missing:
            w.write(u'\n%d holdout names not found in the symbol map '
                    u'(static name collisions or list drift):\n' % len(missing))
            for n in missing:
                w.write(u'- `%s`\n' % n)

    free_h = free_a = 0
    for _, names, un in ex + bl + fu:
        if any(tag(n) == 'C' for n in names):
            free_h += sum(1 for u_ in un if u_ in holdouts)
            free_a += sum(1 for u_ in un if u_ not in holdouts)
    print('scanned %d functions (%d bytes), %d holdout names resolved, %d missing'
          % (len(syms), n_bytes, len(holdouts) - len(missing), len(missing)))
    print('unmatched population: %d declared + %d undeclared-asm'
          % (len(holdouts), len(set(n for n, _, _ in syms)
                                 & in_asm - holdouts)))
    print('clusters with unmatched fns: exact=%d bl-masked=%d fully-masked=%d'
          % (len(ex), len(bl), len(fu)))
    print('free-via-C-twin candidates: %d holdouts, %d undeclared-asm fns'
          % (free_h, free_a))
    print('-> %s' % os.path.relpath(OUT, REPO))


main()
