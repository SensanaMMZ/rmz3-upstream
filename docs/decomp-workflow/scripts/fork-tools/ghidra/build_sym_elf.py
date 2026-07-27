import os
"""Build a fully symbolized ARM ELF of the ROM for Ghidra.

Why not objcopy: `objcopy --add-symbol` cannot set `st_size`. A Ghidra function
symbol with size 0 has no end boundary, so the decompiler runs flow off the end
of the function and fails with "Flow exceeded maximum allowable instructions".
Sizes are the whole point, so we emit the symbol table ourselves.

What this produces:
  * ET_EXEC, EM_ARM, `.rom` PROGBITS at 0x08000000 holding the raw ROM image
  * the GBA memory regions as NOBITS blocks (ewram/iwram/io/palram/vram/oam) so
    RAM globals land in named, mapped memory instead of nowhere
  * every function from rom_symbols.txt as STT_FUNC with its exact size and the
    Thumb bit set in st_value (how Ghidra's ArmElfExtension picks Thumb over ARM)
  * a `$t` local mapping symbol at each function start, reinforcing the same
  * every global from rom_data_symbols.txt as STT_OBJECT with its size

Usage: python3 tools/ghidra/build_sym_elf.py [out.elf]
Regenerate the inputs first with tools/ghidra/map_symbols.py.
"""
import io, os, struct, sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROM = os.path.join(REPO, 'baseimg.gba')
CODE = os.path.join(REPO, 'tools', 'ghidra', 'rom_symbols.txt')
DATA = os.path.join(REPO, 'tools', 'ghidra', 'rom_data_symbols.txt')
OUT = sys.argv[1] if len(sys.argv) > 1 else \
    os.environ.get('RMZ3_SYM_ELF', os.path.join(REPO, 'build', 'rmz3_sym.elf'))

SHT_PROGBITS, SHT_SYMTAB, SHT_STRTAB, SHT_NOBITS = 1, 2, 3, 8
SHF_WRITE, SHF_ALLOC, SHF_EXECINSTR = 1, 2, 4
STB_LOCAL, STB_GLOBAL = 0, 1
STT_NOTYPE, STT_OBJECT, STT_FUNC = 0, 1, 2

# name, addr, size, is_rom_backed, flags
REGIONS = [
    ('.ewram',  0x02000000, 0x40000, False, SHF_ALLOC | SHF_WRITE),
    ('.iwram',  0x03000000, 0x08000, False, SHF_ALLOC | SHF_WRITE),
    ('.io',     0x04000000, 0x00400, False, SHF_ALLOC | SHF_WRITE),
    ('.palram', 0x05000000, 0x00400, False, SHF_ALLOC | SHF_WRITE),
    ('.vram',   0x06000000, 0x18000, False, SHF_ALLOC | SHF_WRITE),
    ('.oam',    0x07000000, 0x00400, False, SHF_ALLOC | SHF_WRITE),
    ('.rom',    0x08000000, 0x800000, True, SHF_ALLOC | SHF_EXECINSTR),
]


def read_syms(path):
    out = []
    for ln in io.open(path):
        p = ln.split()
        if len(p) == 3:
            out.append((p[0], int(p[1], 16), int(p[2], 16)))
        elif len(p) == 2:                      # tolerate the old 2-column form
            out.append((p[0], int(p[1], 16), 0))
    return out


class Strtab(object):
    def __init__(self):
        self.buf = bytearray(b'\0')
        self.off = {'': 0}

    def add(self, s):
        if s not in self.off:
            self.off[s] = len(self.buf)
            self.buf += s.encode('utf-8') + b'\0'
        return self.off[s]


def section_of(addr):
    for i, (nm, a, sz, _, _) in enumerate(REGIONS):
        if a <= addr < a + sz:
            return i + 1                        # +1 for the NULL section header
    return None


def main():
    rom = open(ROM, 'rb').read()
    code, data = read_syms(CODE), read_syms(DATA)

    strtab = Strtab()
    locals_, globals_ = [], []
    dropped = 0

    for name, addr, size in code:
        shndx = section_of(addr)
        if shndx is None:
            dropped += 1
            continue
        # local $t mapping symbol: tells the ARM loader "Thumb starts here"
        locals_.append((strtab.add('$t'), addr, 0,
                        (STB_LOCAL << 4) | STT_NOTYPE, 0, shndx))
        globals_.append((strtab.add(name), addr | 1, size,
                         (STB_GLOBAL << 4) | STT_FUNC, 0, shndx))
    for name, addr, size in data:
        shndx = section_of(addr)
        if shndx is None:
            dropped += 1
            continue
        globals_.append((strtab.add(name), addr, size,
                         (STB_GLOBAL << 4) | STT_OBJECT, 0, shndx))

    syms = [(0, 0, 0, 0, 0, 0)] + locals_ + globals_
    first_global = 1 + len(locals_)
    symtab = b''.join(struct.pack('<IIIBBH', *s) for s in syms)

    shstr = Strtab()
    shnames = [shstr.add('')] + [shstr.add(r[0]) for r in REGIONS] + \
              [shstr.add('.symtab'), shstr.add('.strtab'), shstr.add('.shstrtab')]

    # ---- lay the file out: ehdr, phdr, region contents, symtab, strtab, shstrtab, shdrs
    ehsize, phentsize, shentsize = 52, 32, 40
    off = ehsize + phentsize                    # one PT_LOAD, for .rom
    rom_off = off
    off += len(rom)
    off = (off + 3) & ~3
    symtab_off = off; off += len(symtab)
    strtab_off = off; off += len(strtab.buf)
    shstr_off = off;  off += len(shstr.buf)
    off = (off + 3) & ~3
    shoff = off

    nsec = 1 + len(REGIONS) + 3
    ehdr = struct.pack('<16sHHIIIIIHHHHHH',
                       b'\x7fELF\x01\x01\x01' + b'\0' * 9, 2, 40, 1,
                       0x08000000, ehsize, shoff, 0x05000000,
                       ehsize, phentsize, 1, shentsize, nsec, nsec - 1)
    phdr = struct.pack('<IIIIIIII', 1, rom_off, 0x08000000, 0x08000000,
                       len(rom), len(rom), 5, 4)

    shdrs = [struct.pack('<10I', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)]
    for i, (nm, addr, size, backed, flags) in enumerate(REGIONS):
        shdrs.append(struct.pack('<10I', shnames[i + 1],
                                 SHT_PROGBITS if backed else SHT_NOBITS,
                                 flags, addr, rom_off if backed else shoff,
                                 size, 0, 0, 4, 0))
    n = len(REGIONS)
    strtab_idx = n + 2
    shdrs.append(struct.pack('<10I', shnames[n + 1], SHT_SYMTAB, 0, 0,
                             symtab_off, len(symtab), strtab_idx,
                             first_global, 4, 16))
    shdrs.append(struct.pack('<10I', shnames[n + 2], SHT_STRTAB, 0, 0,
                             strtab_off, len(strtab.buf), 0, 0, 1, 0))
    shdrs.append(struct.pack('<10I', shnames[n + 3], SHT_STRTAB, 0, 0,
                             shstr_off, len(shstr.buf), 0, 0, 1, 0))

    with open(OUT, 'wb') as w:
        w.write(ehdr); w.write(phdr)
        assert w.tell() == rom_off
        w.write(rom)
        w.write(b'\0' * (symtab_off - w.tell()))
        w.write(symtab); w.write(strtab.buf); w.write(shstr.buf)
        w.write(b'\0' * (shoff - w.tell()))
        for s in shdrs:
            w.write(s)

    print('%s' % OUT)
    print('  %d functions (STT_FUNC, Thumb bit, sized)' % len(code))
    print('  %d data globals (STT_OBJECT)' % len(data))
    print('  %d $t mapping symbols' % len(locals_))
    if dropped:
        print('  %d symbols dropped (address outside every mapped region)' % dropped)


main()
