#!/usr/bin/env python3
"""Verify every BL target by ADDRESS, not by name.

WHY THIS EXISTS
---------------
verify_up.py masks BL targets as relocations, because the linker fills them in.
That makes a call to the WRONG upstream function byte-identical to a correct
one. If the wrong name also exists upstream, the file compiles, links, and
byte-verifies green -- and the only symptom is a wrong branch offset in the
linked ROM.

That is not hypothetical. The fork and upstream have two names SWAPPED:

    0x08006f5c   fork AllocEntityLast   == upstream AllocEntityFirst
    0x08006f90   fork AllocEntityFirst  == upstream AllocEntityLast

Porting shellcrawler kept the fork spelling, so it called the wrong allocator.
24/24 functions said MATCH and the ROM differed by exactly one byte.

This script closes the hole: for each BL relocation it looks up where the named
symbol actually lives upstream and compares that against where the retail ROM's
BL at the same spot points. A mismatch names both functions.

usage: verify_calls.py <src.c> <fn>:<addr>[:<size>] ...
"""
import os
import re
import subprocess
import sys

ROM = os.path.join(os.environ['RMZ3_FORK'], 'baseimg.gba')
AGBCC = os.path.join(os.environ['RMZ3_FORK'], 'tools/agbcc')
CPPFLAGS = ['-I', AGBCC, '-I', AGBCC + '/include', '-iquote', 'include',
            '-nostdinc', '-undef', '-std=gnu89', '-DMODERN=0']
CFLAGS = ['-mthumb-interwork', '-Wimplicit', '-Wparentheses', '-Werror',
          '-O2', '-fshort-enums', '-fhex-asm']


MAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upstream.map')


def map_addresses(path=MAP):
    """symbol -> ROM address, from a linker map of a GREEN upstream build.

    This is the authoritative source and supersedes scraping source comments:
    most upstream C functions carry no `// 0x...` annotation at all, so a
    text-derived map silently omits them and reports false unknowns.

    Regenerate by downloading build/rmz3/rmz3.map from any green CI run.
    """
    addr = {}
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            m = re.match(r'^\s+0x0([0-9a-f]{7})\s+([A-Za-z_]\w*)\s*$', line)
            if m:
                a = int(m.group(1), 16)
                if 0x8000000 <= a < 0x9000000:
                    addr[m.group(2)] = a
    return addr


def upstream_addresses(ref='upstream/dev'):
    """symbol -> ROM address, read from PRISTINE upstream/dev, not the worktree.

    It has to be the pristine tree: a function this branch has already lifted
    out of asm into C no longer carries its address anywhere in the worktree,
    so a worktree-only scan silently loses exactly the symbols under test.

    asm:  `FUN_08050090: @ 0x08050090`
    C:    `// 0x08006f90` on its own line, then (past any further comment
          lines) the definition whose name we want.
    """
    addr = {}
    files = subprocess.run(['git', 'ls-tree', '-r', '--name-only', ref],
                           capture_output=True, text=True).stdout.split('\n')
    want = [f for f in files if f.endswith(('.inc', '.s', '.c'))]
    # Must stay BYTES end to end: the header length is a byte count, and this
    # repo's comments are full of multi-byte Japanese, so slicing a decoded
    # str desynchronises the walk and silently yields an empty map.
    blob = subprocess.run(['git', 'cat-file', '--batch'],
                          input='\n'.join('%s:%s' % (ref, f) for f in want).encode(),
                          capture_output=True).stdout
    # `git cat-file --batch` emits "<sha> blob <len>\n<content>\n" per request,
    # in request order -- walk it rather than shelling out once per file.
    pos, idx = 0, 0
    while pos < len(blob) and idx < len(want):
        nl = blob.find(b'\n', pos)
        if nl < 0:
            break
        hdr = blob[pos:nl].split()
        if len(hdr) < 3:
            pos = nl + 1
            idx += 1
            continue
        n = int(hdr[2])
        text = blob[nl + 1:nl + 1 + n].decode('utf-8', 'replace')
        name = want[idx]
        pos, idx = nl + 1 + n + 1, idx + 1
        if name.endswith('.c'):
            lines = text.split('\n')
            for i, line in enumerate(lines):
                m = re.match(r'^\s*//\s*0x([0-9A-Fa-f]{8})\s*$', line)
                if not m:
                    continue
                for j in range(i + 1, min(i + 8, len(lines))):
                    nxt = lines[j].strip()
                    if not nxt or nxt.startswith('//'):
                        continue
                    d = re.match(r'^[A-Za-z_][\w \*]*?\b(\w+)\s*\(', nxt)
                    if d:
                        addr[d.group(1)] = int(m.group(1), 16)
                    break
        else:
            for m in re.finditer(r'^(\w+):\s*@\s*0x([0-9A-Fa-f]{8})\s*$', text, re.M):
                addr[m.group(1)] = int(m.group(2), 16)
    return addr


FORK_MAP = os.path.join(os.environ['RMZ3_FORK'], 'build/rmz3/rmz3.map')


def fork_addresses():
    """Fallback for locating the function UNDER TEST, not for call targets.

    A linker map lists only global symbols, so a `static` function upstream has
    no entry and cannot be placed. The fork builds the same ROM, so if it has
    the same name non-static the address is the same.

    Only ever used for the definition being checked. Using it for call targets
    would defeat the whole point: the fork and upstream disagree about names,
    and for AllocEntityFirst/AllocEntityLast they disagree by swapping them.
    """
    try:
        return map_addresses(FORK_MAP)
    except OSError:
        return {}


def resolve(name, upstream):
    """ROM address of a function under test.

    Prefer the pristine-tree address; fall back to the address embedded in a
    `FUN_08096348`-style name, which is how most not-yet-named functions are
    spelled."""
    if name in upstream:
        return upstream[name]
    m = re.match(r'^(?:\w+?_)?((?:08|8)[0-9a-fA-F]{5,6})$', name)
    if m:
        return int(m.group(1), 16) | 0x08000000
    return None


def compile_obj(src):
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'upobj')
    os.makedirs(tmp, exist_ok=True)
    base = os.path.basename(src)[:-2]
    i, s, o = (os.path.join(tmp, base + e) for e in ('.i', '.s', '.o'))
    # NOT a CRLF hazard despite text mode: subprocess writes raw bytes
    # straight to the file descriptor, bypassing Python's newline
    # translation. Verified. Leave as-is.
    with open(i, 'w') as f:
        r = subprocess.run(['arm-none-eabi-cpp'] + CPPFLAGS + [src],
                           stdout=f, stderr=subprocess.PIPE)
    if r.returncode:
        sys.exit('CPP FAIL: ' + r.stderr.decode()[:300])
    with open(i) as f:
        r = subprocess.run([AGBCC + '/bin/agbcc.exe'] + CFLAGS + ['-o', s],
                           stdin=f, capture_output=True)
    if r.returncode:
        sys.exit('AGBCC FAIL: ' + r.stderr.decode()[:400])
    r = subprocess.run(['arm-none-eabi-as', '-mcpu=arm7tdmi', '-mthumb-interwork',
                        '-I', '.', s, '-o', o], capture_output=True)
    if r.returncode:
        sys.exit('AS FAIL: ' + r.stderr.decode()[:400])
    return o


def text_syms(obj):
    """name -> (offset, size) for .text function symbols."""
    out = subprocess.run(['arm-none-eabi-objdump', '-t', obj],
                         capture_output=True, text=True).stdout
    syms = {}
    for m in re.finditer(r'^([0-9a-f]{8})\s.*\sF\s+\.text\s+([0-9a-f]{8})\s+(\S+)$',
                         out, re.M):
        syms[m.group(3)] = (int(m.group(1), 16), int(m.group(2), 16))
    return syms


def bl_relocs(obj):
    """[(offset, symbol)] for every Thumb BL relocation in .text."""
    out = subprocess.run(['arm-none-eabi-objdump', '-r', obj],
                         capture_output=True, text=True).stdout
    hits, section = [], None
    for line in out.split('\n'):
        m = re.match(r"^RELOCATION RECORDS FOR \[([^\]]+)\]", line)
        if m:
            section = m.group(1)
            continue
        m = re.match(r'^([0-9a-f]{8})\s+(R_ARM_\S+)\s+(\S+)', line)
        if m and section == '.text' and 'THM_' in m.group(2) and \
                ('PC22' in m.group(2) or 'CALL' in m.group(2) or 'XPC22' in m.group(2)):
            hits.append((int(m.group(1), 16), m.group(3)))
    return hits


def decode_bl(rom, addr):
    """Thumb BL/BLX pair at ROM `addr` -> absolute target address."""
    off = addr & 0xFFFFFF
    hw1 = rom[off] | (rom[off + 1] << 8)
    hw2 = rom[off + 2] | (rom[off + 3] << 8)
    if (hw1 & 0xF800) != 0xF000 or (hw2 & 0xF800) not in (0xF800, 0xE800):
        return None
    imm = ((hw1 & 0x7FF) << 12) | ((hw2 & 0x7FF) << 1)
    if imm & 0x400000:
        imm -= 0x800000
    return (addr + 4 + imm) & 0xFFFFFFFF


def main():
    src = sys.argv[1]
    # The map alone, by default. upstream_addresses() re-reads ~1500 blobs from
    # git on every invocation, which is fine once and ruinous in a per-file loop
    # over a 101-file branch. Pass --deep only when a symbol is genuinely absent
    # from the map (a function this branch is introducing under a new name).
    upstream = map_addresses()
    # The functions this branch is LIFTING are not in the map under these
    # names -- upstream still has them as asm labels. Read just this file's own
    # inc group from upstream/dev; that is one cheap git call, versus the whole
    # tree, and it is where their addresses live.
    stem = re.sub(r'^src/', 'asm/', src)[:-2]
    incs = subprocess.run(['git', 'ls-tree', '-r', '--name-only', 'upstream/dev',
                           os.path.dirname(stem) + '/'],
                          capture_output=True, text=True).stdout.split('\n')
    base = os.path.basename(stem)
    for inc in incs:
        if not re.match(r'.*/%s(_[a-z0-9]+)*\.inc$' % re.escape(base), inc or ''):
            continue
        txt = subprocess.run(['git', 'show', 'upstream/dev:' + inc],
                             capture_output=True, text=True, errors='replace').stdout
        for m in re.finditer(r'^(\w+):\s*@\s*0x([0-9A-Fa-f]{8})\s*$', txt, re.M):
            upstream.setdefault(m.group(1), int(m.group(2), 16))
    if '--deep' in sys.argv:
        upstream.update({k: v for k, v in upstream_addresses().items()
                         if k not in upstream})
    obj = compile_obj(src)
    syms = text_syms(obj)
    relocs = bl_relocs(obj)
    rom = open(ROM, 'rb').read()

    # Every function the object defines, not a hand-passed list: the whole
    # point is to catch a call nobody thought to check.
    fork = fork_addresses()
    specs, skipped = [], []
    for fn in sorted(syms):
        a = resolve(fn, upstream) or fork.get(fn)
        (specs.append((fn, a)) if a else skipped.append(fn))
    if skipped:
        print('no address, not checked: ' + ' '.join(skipped))

    bad = checked = 0
    for fn, fn_addr in specs:
        sym_off, sym_size = syms[fn]
        for off, target in relocs:
            if not (sym_off <= off < sym_off + sym_size):
                continue
            rom_addr = (fn_addr & 0xFFFFFF) + (off - sym_off) + 0x08000000
            want = decode_bl(rom, rom_addr)
            if want is None:
                continue
            checked += 1
            have = upstream.get(target)
            if have is None:
                print('%-26s %-28s target address UNKNOWN upstream '
                      '(rom calls 0x%08X)' % (fn, target, want))
                bad += 1
            elif (have & ~1) != (want & ~1):
                who = [n for n, a in upstream.items() if (a & ~1) == (want & ~1)]
                print('%-26s %-28s WRONG: is 0x%08X, rom calls 0x%08X%s'
                      % (fn, target, have, want,
                         '  == ' + who[0] if who else ''))
                bad += 1
    print('%d BL target(s) checked, %d wrong' % (checked, bad))
    return 1 if bad else 0


sys.exit(main())
