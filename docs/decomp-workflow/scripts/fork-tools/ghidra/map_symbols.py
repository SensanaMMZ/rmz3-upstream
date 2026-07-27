import os
"""Generate the Ghidra symbol map from the expected build's linker map + objects.

Three sources, unioned, in increasing order of coverage:

1. `expected/build/rmz3/rmz3.map` -- every GLOBAL symbol with its final VMA,
   emitted by the linker that produced the matching ROM. Ground truth, but the
   GNU map lists only globals, so every `static` function is missing.
2. Per-object symbol tables. The map's section-contribution lines give each
   object's `.text` base; `objdump -t` on that object lists its LOCAL functions
   too, so `VMA(fn) = objbase + offset(fn)` recovers every static exactly.
   This is what supersedes resolve_holdout_addrs.py's anchor arithmetic --
   same formula, but with the base read from the linker instead of inferred.
3. The `Name: @ 0x08XXXXXX` comments in `asm/**/*.inc` -- catches labels in
   hand-written asm that never became object-file symbols.

Cross-checks that passed when this was written: the linker map, the anchor
arithmetic, and the asm harvest all put Beetank_Update at 0x0807b9f0, and the
asm harvest agreed with the linker map on all 1,868 names they share, with zero
disagreements.

Symbols at or above the .rodata base are emitted as DATA, not code -- e.g. the
`Camera_0834d268` cutscene-script labels in asm/scripts/*.s are script bytes;
marking them FUNC would make Ghidra disassemble data as Thumb.

Sizes matter as much as addresses: a Ghidra function symbol with size 0 has no
end boundary, so the decompiler follows flow off the end of the function and
dies with "Flow exceeded maximum allowable instructions". Object symbol tables
carry exact sizes; anything else falls back to the distance to the next symbol.

Writes (three columns, NAME ADDR SIZE, hex, size 0 = unknown):
  tools/ghidra/rom_symbols.txt       -- code
  tools/ghidra/rom_data_symbols.txt  -- data (rodata / ewram / iwram)

Usage: python3 tools/ghidra/map_symbols.py
"""
import io, os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAP = os.path.join(REPO, 'expected', 'build', 'rmz3', 'rmz3.map')
EXPBUILD = os.path.join(REPO, 'expected', 'build', 'rmz3')
CODE_OUT = os.path.join(REPO, 'tools', 'ghidra', 'rom_symbols.txt')
DATA_OUT = os.path.join(REPO, 'tools', 'ghidra', 'rom_data_symbols.txt')
OBJDUMP = 'arm-none-eabi-objdump'

CODE_SECTIONS = ('.text', 'lib_text')

SECT_HDR = re.compile(r'^(\S+)\s+0x([0-9a-f]+)\s+0x([0-9a-f]+)\s*$')
# " .text          0x08032d80     0x1154 src/player/zero/input/util.o"
CONTRIB = re.compile(r'^\s+(\.\S+)\s+0x([0-9a-f]+)\s+0x([0-9a-f]+)\s+(\S+\.o)\s*$')
SYMBOL = re.compile(r'^\s+0x([0-9a-f]{8,16})\s+([A-Za-z_][A-Za-z_0-9]*)\s*$')
# objdump -t: "00000abc l     F .text\t000000d4 someStaticFn"
OBJSYM = re.compile(r'^([0-9a-f]{8})\s.*\bF\s+(\.text\S*)\t([0-9a-f]{8})\s+(\S+)\s*$')
ASMLABEL = re.compile(r'^([A-Za-z_][A-Za-z_0-9]*):\s*@\s*0x(08[0-9A-Fa-f]{6})\s*$')
FILEHDR = re.compile(r'^(.*):\s+file format elf32-littlearm\s*$')


def parse_map():
    """-> (globals {name: addr}, contribs {objpath: text_base}, rodata_base)"""
    syms, contribs, sect, rodata_base = {}, {}, None, None
    started = False
    for ln in io.open(MAP, errors='replace'):
        if not started:
            started = ln.startswith('Linker script and memory map')
            continue
        if ln.startswith('LOAD ') or ln.startswith('OUTPUT('):
            continue
        m = SECT_HDR.match(ln)
        if m and not ln.startswith((' ', '\t')):
            sect = m.group(1)
            if sect == '.rodata':
                rodata_base = int(m.group(2), 16)
            continue
        m = CONTRIB.match(ln)
        if m:
            if m.group(1).startswith('.text') and sect in CODE_SECTIONS:
                contribs.setdefault(m.group(4), int(m.group(2), 16))
            continue
        m = SYMBOL.match(ln)
        if m:
            syms.setdefault(m.group(2), (int(m.group(1), 16), sect))
    return syms, contribs, rodata_base


def statics_from_objects(contribs):
    """Every function symbol in each object, placed via the linker's .text base.

    objdump is batched -- one process per ~80 objects rather than per object,
    because process spawn dominates on Windows (600 objects = 4 min serially).
    """
    bases, paths = {}, []
    for objrel, base in sorted(contribs.items()):
        for cand in (os.path.join(REPO, objrel), os.path.join(EXPBUILD, objrel)):
            if os.path.exists(cand):
                bases[os.path.normcase(os.path.abspath(cand))] = base
                paths.append(cand)
                break
    out, CHUNK = {}, 80
    for k in range(0, len(paths), CHUNK):
        try:
            t = subprocess.run([OBJDUMP, '-t'] + paths[k:k + CHUNK],
                               capture_output=True, text=True).stdout
        except OSError:
            sys.exit('%s not on PATH (add devkitARM/bin)' % OBJDUMP)
        base = None
        for l in t.split('\n'):
            mf = FILEHDR.match(l)
            if mf:  # rsplit-safe: Windows paths contain a drive-letter colon
                base = bases.get(os.path.normcase(os.path.abspath(mf.group(1))))
                continue
            if base is None:
                continue
            m = OBJSYM.match(l)
            if m and m.group(2) == '.text':
                out.setdefault(m.group(4),
                               (base + int(m.group(1), 16), int(m.group(3), 16)))
    return out


def asm_labels():
    out = {}
    for root, _, files in os.walk(os.path.join(REPO, 'asm')):
        for f in files:
            if not f.endswith(('.inc', '.s')):
                continue
            for ln in io.open(os.path.join(root, f), errors='replace'):
                m = ASMLABEL.match(ln.rstrip())
                if m:
                    out.setdefault(m.group(1), int(m.group(2), 16))
    return out


def infer_sizes(d, cap=0x4000):
    """Fill size-0 symbols with the gap to the next distinct address.

    Capped: an over-long size would swallow following functions, which is worse
    for Ghidra than leaving the boundary to its own flow analysis.
    """
    ordered = sorted(d.items(), key=lambda kv: kv[1][0])
    for i, (n, (a, sz, c)) in enumerate(ordered):
        if sz:
            continue
        nxt = next((v[0] for _, v in ordered[i + 1:] if v[0] > a), None)
        if nxt is not None and 0 < nxt - a <= cap:
            d[n] = (a, nxt - a, c)


def main():
    if not os.path.exists(MAP):
        sys.exit('missing %s -- link the expected build first' % MAP)
    gl, contribs, rodata_base = parse_map()
    print('linker map:   %d globals, %d .text contributions, .rodata @ %08X'
          % (len(gl), len(contribs), rodata_base))
    st = statics_from_objects(contribs)
    print('object files: %d function symbols (globals + statics)' % len(st))
    al = asm_labels()
    print('asm comments: %d labels' % len(al))

    merged, conflicts = {}, []

    def add(name, addr, size, is_code):
        cur = merged.get(name)
        if cur is not None:
            if cur[0] != addr:
                conflicts.append((name, cur[0], addr))
            elif size and not cur[1]:      # keep the address, gain a real size
                merged[name] = (addr, size, cur[2])
            return
        merged[name] = (addr, size, is_code)

    # object symbol tables first: they are the only source with exact sizes
    for n, (a, sz) in st.items():
        add(n, a, sz, True)
    for n, (a, sect) in gl.items():
        add(n, a, 0, sect in CODE_SECTIONS)
    for n, a in al.items():
        add(n, a, 0, a < rodata_base)

    if conflicts:
        print('WARNING: %d address conflicts between sources:' % len(conflicts))
        for n, a, b in conflicts[:10]:
            print('   %-30s %08X vs %08X' % (n, a, b))

    code = {n: v for n, v in merged.items() if v[2]}
    data = {n: v for n, v in merged.items() if not v[2]}
    for path, d, what in ((CODE_OUT, code, 'code'), (DATA_OUT, data, 'data')):
        infer_sizes(d)
        with io.open(path, 'w', newline='\n') as w:
            for n in sorted(d, key=lambda k: (d[k][0], k)):
                w.write(u'%s %08X %X\n' % (n, d[n][0], d[n][1]))
        nosize = len([1 for v in d.values() if not v[1]])
        print('%-6s %5d symbols (%d still size-0) -> %s'
              % (what, len(d), nosize, os.path.relpath(path, REPO)))


main()
