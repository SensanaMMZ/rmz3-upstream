#!/usr/bin/env python3
"""Rewrite the fork's `props`/`buffer` scratch-area accesses onto whatever
upstream calls that region.

The fork treats the bytes after the collision header as one blob and reaches
into it by byte offset: `(p->props).raw[0x20]`. Upstream instead gives each
entity its OWN named fields over the same bytes (see the note in entity.h:
"buffer のレイアウトが Entity によって違うため"), so `Blazin` has
`u8 unk_b4[16]; BlazinTail* tail; u16 anim_c8; u8 unk_ca[26];` and no `buffer`
at all. A plain props->buffer rename therefore produces
`structure has no member named 'buffer'` -- 11 of the 18 member errors in the
backlog were this.

Two sub-cases:
  * the type DOES declare `u8 buffer[N]` (Weapon, Projectile, ...) -- then only
    the union's `.raw` is wrong, so `(p->buffer).raw[K]` -> `p->buffer[K]`.
  * the type does not -- resolve the absolute offset (base + K) against the
    declared fields and emit the field that actually covers it.

Offsets are COMPUTED from the declared types, not read from the `// 0xNN`
comments. The comments lie: `Blazin` carries `u16 anim_c8; // 0xC8` followed by
`u8 unk_ca[26]; // 0xC8` -- the second is a copy-paste of the first, and the
field really starts at 0xCA. Trusting it put the rewritten access 2 bytes off,
which compiles perfectly and simply reads the wrong memory. The comments are
still checked against the computed layout and any disagreement is reported.

Base is the size of the header the struct opens with (COLLISION_OBJECT_HDR =
180, a nested `Entity s;` = 116, both static_asserted upstream). Anything that
cannot be resolved exactly is left alone for a human -- guessing here writes to
the wrong bytes, and only the ROM compare would ever notice.
"""
import re
import sys
import glob
import os

SIZES = {'u8': 1, 's8': 1, 'bool8': 1, 'char': 1,
         'u16': 2, 's16': 2, 'vu16': 2,
         'u32': 4, 's32': 4, 'vu32': 4, 'int': 4, 'void*': 4}

FIELD = re.compile(
    r'^\s*(?:struct\s+)?(\w+)\s*(\*+)?\s*(\w+)\s*(?:\[\s*(\w+)\s*\])?\s*;'
    r'\s*(?://\s*(0x[0-9A-Fa-f]+))?')


OPEN = re.compile(r'(?:typedef\s+)?struct(?:\s+\w+)?\s*\{')


def _bodies(txt):
    """(name, body) for every struct in `txt`, found by matching braces.

    A non-greedy `\\{(.*?)\\}\\s*NAME\\s*;` cannot do this: it starts at the
    FIRST `typedef struct` in the file and stretches to the first `} NAME;` it
    can reach, so asking entity.h for `Boss` returned a body beginning at
    `Entity` and containing three other structs plus their static_asserts. The
    field walk then hit `static_assert(...)`, failed to parse it, and bailed out
    -- reported as "unresolved", which reads like the access was odd rather than
    like the struct lookup was wrong."""
    out = []
    for m in OPEN.finditer(txt):
        depth, i = 0, m.end() - 1
        for j in range(i, len(txt)):
            if txt[j] == '{':
                depth += 1
            elif txt[j] == '}':
                depth -= 1
                if depth == 0:
                    tail = re.match(r'\s*(\w+)?\s*;', txt[j + 1:])
                    inner = re.search(r'struct\s+(\w+)\s*\{', m.group(0))
                    nm = (tail.group(1) if tail and tail.group(1)
                          else (inner.group(1) if inner else None))
                    if nm:
                        out.append((nm, txt[i + 1:j]))
                    break
    return out


def find_struct(name, csrc):
    """Body of `name`, searched in the .c first (many of these types are
    file-local) then the headers."""
    files = [csrc] + sorted(p.replace('\\', '/') for p in
                            glob.glob('include/**/*.h', recursive=True))
    for f in files:
        if not os.path.exists(f):
            continue
        with open(f, encoding='utf-8', errors='replace') as fh:
            for nm, body in _bodies(fh.read()):
                if nm == name:
                    return body
    return None


HDR_SIZE = {'COLLISION_OBJECT_HDR': 180, 'ENTITY_HDR': 40}


def base_of(body):
    """Size of the header the struct opens with, i.e. the offset its own fields
    start at. Both values are static_asserted upstream."""
    for ln in body.splitlines():
        s = ln.strip()
        if not s or s.startswith('//'):
            continue
        for k, v in HDR_SIZE.items():
            if s.startswith(k):
                return v
        if re.match(r'^(?:struct\s+)?Entity\s+s\s*;', s):
            return 116
        return None
    return None


def fields(body):
    """(offset, name, elemsize, count) for every field, with offsets COMPUTED
    by walking the declarations under C alignment rules. Returns None if any
    field has a type whose size is unknown -- a wrong running offset after that
    point would silently mis-target every later field."""
    base = base_of(body)
    if base is None:
        return None
    out, off, saw_hdr = [], base, False
    for ln in body.splitlines():
        s = ln.strip()
        if not s or s.startswith('//') or s.startswith('/*'):
            continue
        if not saw_hdr:                       # skip the header line itself
            saw_hdr = True
            if (any(s.startswith(k) for k in HDR_SIZE)
                    or re.match(r'^(?:struct\s+)?Entity\s+s\s*;', s)):
                continue
        m = FIELD.match(ln)
        if not m:
            return None
        ty, ptr, nm, dim, cmt = m.groups()
        if ptr:
            esz = 4
        elif ty in SIZES:
            esz = SIZES[ty]
        else:
            return None
        try:
            cnt = int(dim, 0) if dim else 1
        except ValueError:
            return None
        off += (-off) % esz                   # align to the element size
        if cmt and int(cmt, 16) != off:
            sys.stderr.write('    note: %s comment says %s, layout says 0x%X\n'
                             % (nm, cmt, off))
        out.append((off, nm, esz, cnt))
        off += esz * cnt
    return out


def resolve(flds, base, k):
    """Field covering absolute offset base+k, or None if nothing lines up."""
    a = base + k
    for off, nm, esz, cnt in flds:
        if off <= a < off + esz * cnt:
            d = a - off
            if d % esz:
                return None   # straddles an element -- not expressible
            i = d // esz
            if cnt == 1:
                return nm if i == 0 else None
            return '%s[%d]' % (nm, i)
    return None


def var_type(txt, var):
    """Declared type of `var` -- parameter or local. First match wins; these
    handlers take a single typed entity pointer."""
    m = re.search(r'\b(?:struct\s+)?(\w+)\s*\*\s*%s\b' % re.escape(var), txt)
    return m.group(1) if m else None


ACCESS = re.compile(r'\(?\s*(\w+)\s*->\s*buffer\s*\)?\s*\.\s*raw\s*\['
                    r'\s*(0[xX][0-9A-Fa-f]+|\d+)\s*\]')


def main():
    src = sys.argv[1]
    with open(src, encoding='utf-8', errors='replace') as fh:
        txt = fh.read()

    cache = {}
    local_type = {}          # per-function name -> type, filled in below
    changed = unresolved = 0

    def sub(m):
        nonlocal changed, unresolved
        var, idx = m.group(1), int(m.group(2), 0)
        ty = local_type.get(var) or var_type(txt, var)
        if not ty:
            unresolved += 1
            return m.group(0)
        if ty not in cache:
            body = find_struct(ty, src)
            cache[ty] = fields(body) if body else None
        flds = cache[ty]
        if not flds:
            unresolved += 1
            return m.group(0)
        # `u8 buffer[N]` present: only the union's .raw is wrong.
        if any(nm == 'buffer' for _, nm, _, _ in flds):
            changed += 1
            return '%s->buffer[%d]' % (var, idx)
        got = resolve(flds, flds[0][0], idx)
        if not got:
            unresolved += 1
            return m.group(0)
        changed += 1
        return '%s->%s' % (var, got)

    # Per-function, not file-wide. blazin.c types most of its handlers
    # `Blazin* p` but `blazin_0803fed8` takes a `struct Boss* p`; a file-wide
    # lookup returned Blazin for BOTH, so the Boss function's 0xB4 blob was
    # mapped through Blazin's field names and produced `p->unk_b4[12]` on a
    # struct that has `buffer[48]`. Same trap as fix_arg_casts and
    # fix_nested_access -- see the name-scope memory.
    parts, pos = [], 0
    for fm in re.finditer(r'^[A-Za-z_][\w \*]*\b\w+\s*\([^;{)]*\)\s*\{', txt,
                          re.M):
        depth, st = 0, txt.index('{', fm.start())
        en = st
        for j in range(st, len(txt)):
            if txt[j] == '{':
                depth += 1
            elif txt[j] == '}':
                depth -= 1
                if depth == 0:
                    en = j + 1
                    break
        blk = txt[fm.start():en]
        scope = {}
        for mm in re.finditer(r'\b((?:struct\s+)?\w+)\s*\*\s*(\w+)\s*[,;=){]',
                              blk):
            scope.setdefault(mm.group(2),
                             re.sub(r'^struct\s+', '', mm.group(1).strip()))
        local_type.clear()
        local_type.update(scope)
        parts.append(txt[pos:fm.start()])
        parts.append(ACCESS.sub(sub, blk))
        pos = en
    parts.append(txt[pos:])
    new = ''.join(parts)
    if new != txt:
        with open(src, 'w', encoding='utf-8', newline='') as fh:
            fh.write(new)
    print('  buffer offsets: %d rewritten, %d unresolved' % (changed, unresolved))


if __name__ == '__main__':
    main()
