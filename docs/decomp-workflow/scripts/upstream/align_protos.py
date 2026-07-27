#!/usr/bin/env python3
"""Make a ported definition agree with the prototype already in the file.

Upstream declares its handlers with the file's own flat typedef:

    void Weapon5_Die(SaverWave* p);          <- upstream's prototype
    void Weapon5_Die(struct Weapon* w) {     <- our ported definition
      (w->s).flags &= ~DISPLAY;

That is a hard `conflicting types` error, and the body still uses the nested
`(w->s)` spelling besides. Both halves have to move together: retype the
parameter to the prototype's type, then flatten every access through it.

Doing only the retype would leave `(w->s)` against a flat type ("structure has
no member named `s`"); doing only the flatten would leave the signatures
disagreeing. So this handles both, per function.

usage: align_protos.py <file.c> ...
"""
import io
import os
import re
import sys

PROTO = re.compile(r'^\s*(?:static\s+)?[A-Za-z_][\w \*]*?\b(?P<name>\w+)\s*'
                   r'\(\s*(?P<type>[\w ]+?)\s*\*\s*\w+\s*\)\s*;', re.M)
DEF = re.compile(r'^(?P<head>(?:static\s+)?[A-Za-z_][\w \*]*?\b(?P<name>\w+)\s*'
                 r'\(\s*(?P<type>[\w ]+?)\s*\*\s*(?P<var>\w+)\s*\))\s*\{')


# Return type + name, whatever the parameter list looks like. The PROTO/DEF
# pair above only handles a single pointer parameter, which misses
# `CyberElf* CreateBirdElf(struct Zero*, u8, u8, u8)` entirely.
RET_PROTO = re.compile(r'^\s*(?:extern\s+)?(?P<ret>[A-Za-z_][\w ]*?\s*\**)\s*'
                       r'(?P<name>\w+)\s*\([^;{)]*\)\s*;', re.M)
RET_DEF = re.compile(r'^(?P<ret>[A-Za-z_][\w ]*?\s*\**)\s*(?P<name>\w+)\s*'
                     r'\((?P<args>[^;{)]*)\)\s*\{', re.M)


def align_return_types(s, headers):
    """Make a definition's RETURN type match its declared prototype.

    A lifted body carries the fork's spelling -- `struct Elf* CreateBirdElf(...)`
    where upstream's header says `CyberElf*`. Both name the same object, but C
    calls it `conflicting types` and the error points at the header, not at the
    line that is actually wrong.
    """
    protos = {}
    for text in [s] + headers:
        for m in RET_PROTO.finditer(text):
            protos.setdefault(m.group('name'), m.group('ret').strip())
    n = 0
    out = s
    for m in RET_DEF.finditer(s):
        want = protos.get(m.group('name'))
        have = m.group('ret').strip()
        if not want or want == have or 'return' in have:
            continue
        # NEVER touch a NAKED / INCCODE / NON_MATCH definition. Those look like
        # C but the body is still assembly, and the keyword is part of the
        # declaration -- rewriting the return type drops it, so the compiler
        # starts emitting a prologue and epilogue around raw asm. That is what
        # made `hellbat.c` grow 8 bytes in functions this port never touched,
        # and the overflow got blamed on the ported function.
        if re.search(r'\b(NAKED|WIP|INCCODE|NON_MATCH)\b', have):
            continue
        old = m.group(0)
        new = old.replace(have, want, 1)
        out = out.replace(old, new, 1)
        n += 1
    return out, n


def fix_return_casts(s):
    """`return p;` where p's type is not the function's return type.

    After a struct import the body works on the per-entity typedef
    (`CyberElfBird*`) while the function is declared to return the generic
    (`CyberElf*`). Same object, same address -- upstream casts. Only applied
    where BOTH are pointers and the returned name is a local declared in that
    function, so a genuine type error is not papered over.
    """
    lines, n = s.split('\n'), 0
    i = 0
    while i < len(lines):
        m = RET_DEF.match(lines[i])
        if not m:
            i += 1
            continue
        ret = m.group('ret').strip()
        # Drop storage-class and inline keywords before this type is ever used
        # to build a cast. `static PillerCannon* f(...)` otherwise yields
        # `return (static PillerCannon*)p;`, which fails as `syntax error before
        # 'static'` -- and the error points at the cast, not at the function
        # whose signature actually supplied the word.
        ret = re.sub(r'^(?:static|extern|inline|register)\s+', '', ret).strip()
        depth, j = 0, i
        end = i
        while j < len(lines):
            depth += lines[j].count('{') - lines[j].count('}')
            if depth <= 0 and j > i:
                end = j
                break
            j += 1
        if not ret.endswith('*'):
            i = end + 1
            continue
        block = lines[i:end + 1]
        local = {}
        for l in block:
            d = re.match(r'\s*((?:struct\s+)?\w+)\s*\*\s*(\w+)\s*[=;]', l)
            if d:
                local[d.group(2)] = d.group(1).strip()
        for k, l in enumerate(block):
            r = re.match(r'(\s*)return\s+(\w+)\s*;', l)
            if r and r.group(2) in local and local[r.group(2)] != ret.rstrip('*').strip():
                block[k] = '%sreturn (%s)%s;' % (r.group(1), ret, r.group(2))
                n += 1
                continue
            # An EXISTING cast naming a type that does not exist upstream --
            # `return (struct Elf*)p;` where the fork's `struct Elf` is this
            # repo's `CyberElf`. Retype it to what the function returns.
            c = re.match(r'(\s*)return\s+\(\s*((?:struct\s+)?[\w ]+?)\s*\*\s*\)\s*(\w+)\s*;', l)
            if c and c.group(2).strip() != ret.rstrip('*').strip():
                block[k] = '%sreturn (%s)%s;' % (c.group(1), ret, c.group(3))
                n += 1
        lines[i:end + 1] = block
        i = end + 1
    return '\n'.join(lines), n


def unify_local_type(s):
    """Use the file's own typedef everywhere, not a mix of it and the struct tag.

    A ported file ends up with both spellings for the same object:

        typedef struct { COLLISION_OBJECT_HDR; ... } Anubis;
        static_assert(sizeof(Anubis) == sizeof(struct Boss));
        bool8 FUN_080500f4(struct Boss* p);      <- declared with the tag
        void Anubis_Update(Anubis* p) { FUN_080500f4(p); }   <- incompatible

    The `static_assert` is the file telling us the two ARE the same object, so
    it is also the safe trigger: only unify when the file asserts the sizes
    match, which is what makes the substitution meaning-preserving.
    """
    # The typedef often lives in the file's OWN header (include/boss/anubis.h),
    # not the .c, so search the included project headers too. Without this,
    # anubis.c looks like it has no local type at all and the mixed spellings
    # survive.
    text = s
    for h in re.findall(r'^#include\s+"([^"]+)"', s, re.M):
        try:
            with open(os.path.join('include', h), encoding='utf-8',
                      errors='replace') as f:
                text += '\n' + f.read()
        except OSError:
            pass

    # Only when the file has exactly ONE flat typedef. A file can carry a second,
    # auxiliary view of the same object (an imported per-entity struct with named
    # fields alongside the generic one with `buffer[]`). Unifying then retypes
    # every `struct Enemy*` to the auxiliary type, and functions using
    # `p->buffer[n]` break with "structure has no member named `buffer'" --
    # the import itself causes the regression.
    flats = re.findall(r'typedef\s+struct\s*\{[^}]*COLLISION_OBJECT_HDR[^}]*\}\s*(\w+)\s*;',
                       text, re.S)
    if len(set(flats)) != 1:
        return s, 0

    m = re.search(r'static_assert\(\s*sizeof\(\s*(\w+)\s*\)\s*==\s*'
                  r'sizeof\(\s*(?:struct\s+)?(\w+)\s*\)\s*\)', text)
    if not m:
        return s, 0
    local, tag = m.group(1), m.group(2)
    if local == tag or not re.search(
            r'typedef\s+struct\s*\{[^}]*COLLISION_OBJECT_HDR[^}]*\}\s*%s\s*;'
            % re.escape(local), text, re.S):
        return s, 0
    # Only the .c is rewritten -- never the shared header.
    #
    # And only DECLARATIONS, never cast expressions. A cast is usually there
    # precisely because the code wants the tag's view: `((struct Enemy*)par)->buffer[4]`
    # works because struct Enemy has `buffer`, while the per-entity typedef
    # names those bytes individually (unk_b4, unk_b8, ...) and has no `buffer`
    # at all. Rewriting the cast turns working code into
    # "structure has no member named `buffer'". The negative lookahead skips
    # `(struct Enemy*)` by refusing a `*` that is immediately closed.
    s2 = re.sub(r'\bstruct\s+%s\s*\*(?!\s*\))' % re.escape(tag), local + '*', s)
    if s2 == s:
        return s, 0
    # The tag was nested (`struct Enemy { Entity s; ... }`) and the typedef is
    # flat, so retyping alone turns every `(p->s).x` in those bodies into
    # "structure has no member named `s`". Flatten them in the same pass --
    # skipping this made the broken-file count go UP.
    for var in set(re.findall(r'\b%s\s*\*\s*(\w+)' % re.escape(local), s2)):
        v = re.escape(var)
        s2 = re.sub(r'\(\s*%s->s\s*\)\.' % v, '%s->' % var, s2)
        s2 = re.sub(r'\b%s->s\.' % v, '%s->' % var, s2)
        s2 = re.sub(r'&%s->s\b' % v, '(struct Entity*)%s' % var, s2)
    return s2, 1


def fix_decl_casts(s):
    """`T* x = (U*)e;` -- make the cast name the type being assigned to.

    Retyping a declaration to the file's typedef leaves the initialiser's cast
    naming the old struct tag: `Anubis* atk = (struct Boss*)body->parent;`.
    Both describe the same object, so the cast simply follows the declaration.
    Casts NOT in an initialiser are left alone -- see the note in
    unify_local_type about `((struct Enemy*)par)->buffer`.
    """
    def sub(m):
        typ, var, cast, rest = (m.group(1).strip(), m.group(2),
                                m.group(3).strip(), m.group(4))
        if cast == typ:
            return m.group(0)
        return '%s* %s = (%s*)%s' % (typ, var, typ, rest)

    # The declared type must be captured WHOLE, `struct` included. Capturing
    # only the trailing word rewrote `struct Enemy* p = (struct Enemy*)...`
    # into `Enemy* p = (Enemy*)...`, and `Enemy` is not a typedef -- that one
    # slip took the broken-file count from 16 to 28.
    #
    # Single-star only: a `T** x = (U**)e;` slot conversion is deliberate
    # (see fix_element_effect) and must not be touched.
    new = re.sub(r'^(\s*(?:struct\s+)?\w+)\s*\*\s+(\w+)\s*=\s*'
                 r'\(\s*((?:struct\s+)?\w+)\s*\*\s*\)\s*([^;]+;)',
                 lambda m: (m.group(0) if m.group(1).strip() == m.group(3).strip()
                            else '%s* %s = (%s*)%s'
                            % (m.group(1), m.group(2),
                               m.group(1).strip(), m.group(4))),
                 s, flags=re.M)
    return new, int(new != s)


def fix_call_casts(s, protos):
    """A cast at a call site must name the callee's declared parameter type.

    Flattening rewrites arguments (`&p->s` becomes a cast), and the type it
    picks is not necessarily the one the callee was declared with:

        static void Projectile28_Die(Projectile28* p);
        Projectile28_Die((Object*)p);        <- incompatible pointer type

    Both point at the same object, so the fix is simply to name the declared
    type. Only call sites whose callee has a prototype IN THIS FILE are
    touched, so nothing external is guessed at.
    """
    n = 0
    for name, want in protos.items():
        # an existing cast naming the wrong type
        pat = re.compile(r'\b%s\(\s*\(\s*(?!%s\b)[\w ]+\s*\*\s*\)\s*(\w+)\s*\)'
                         % (re.escape(name), re.escape(want)))
        s2 = pat.sub(lambda m: '%s((%s*)%s)' % (name, want, m.group(1)), s)
        n += s2 != s
        s = s2
        # A bare argument whose own declared type differs from the callee's.
        # These are all views of the SAME entity at offset 0 -- the generic
        # `struct Enemy*` and a per-entity typedef naming the same bytes -- so
        # the cast is a spelling change, not a reinterpretation. Restricted to
        # names that are declared as pointers somewhere in this file, so an
        # unrelated identifier is never cast.
        ptr_locals = dict(re.findall(
            r'\b((?:struct\s+)?\w+)\s*\*\s*(\w+)\s*[=;,)]', s))
        ptr_locals = {v: t for t, v in
                      re.findall(r'\b((?:struct\s+)?\w+)\s*\*\s*(\w+)\s*[=;,)]', s)}

        def sub_bare(m):
            arg = m.group(1)
            have = ptr_locals.get(arg)
            if have is None or have == want:
                return m.group(0)
            return '%s((%s*)%s)' % (name, want, arg)

        s2 = re.sub(r'\b%s\(\s*(\w+)\s*\)' % re.escape(name), sub_bare, s)
        n += s2 != s
        s = s2

    # Dispatch through a handler table: the element type is `void (*)(struct X*)`
    # while the caller now holds the file's own typedef. `void*` converts
    # implicitly to any object pointer in C, so it satisfies the table's
    # parameter type whatever it is, without asserting a specific one.
    # The index is usually itself a subscript (`sUpdates1[p->mode[1]]`), so the
    # inner brackets have to be allowed for -- a plain [^\]]+ stops at the first
    # `]` and the pattern never matches the calls that actually need fixing.
    s2 = re.sub(r'\((\w+)\[((?:[^\[\]]|\[[^\[\]]*\])+)\]\)\(\s*(\w+)\s*\)',
                r'(\1[\2])((void*)\3)', s)
    n += s2 != s
    return s2, n


def main():
    total = 0
    for path in sys.argv[1:]:
        s = io.open(path, encoding='utf-8', newline='').read()
        protos = {m.group('name'): m.group('type').strip()
                  for m in PROTO.finditer(s)}
        # DEFINITIONS too, not only prototypes. A callee defined in this file
        # with no separate declaration is absent from a prototype-only map, so
        # its call sites never get the cast they need.
        for m in DEF.finditer(s):
            protos.setdefault(m.group('name'), m.group('type').strip())
        # Prototypes from the INCLUDED HEADERS as well. A freshly lifted body
        # carries the fork's spelling (`struct Elf* CreateBirdElf(...)`) while
        # the header upstream says `CyberElf*` -- a hard `conflicting types`
        # error that nothing in the .c itself reveals. The header is
        # authoritative here, so definitions follow it.
        for h in re.findall(r'^#include\s+"([^"]+)"', s, re.M):
            try:
                with io.open(os.path.join('include', h), encoding='utf-8',
                             errors='replace') as f:
                    for m in PROTO.finditer(f.read()):
                        protos.setdefault(m.group('name'),
                                          m.group('type').strip())
            except OSError:
                pass
        hdrs = []
        for h in re.findall(r'^#include\s+"([^"]+)"', s, re.M):
            try:
                with io.open(os.path.join('include', h), encoding='utf-8',
                             errors='replace') as f:
                    hdrs.append(f.read())
            except OSError:
                pass
        s, nr = align_return_types(s, hdrs)
        if nr:
            print('  %-40s %d return type(s) aligned'
                  % (path.split('/')[-1], nr))
        s, nu = unify_local_type(s)
        if nu:
            protos = {m.group('name'): m.group('type').strip()
                      for m in PROTO.finditer(s)}
            print('  %-40s unified to the file typedef' % path.split('/')[-1])
        s, nrc = fix_return_casts(s)
        s, nd = fix_decl_casts(s)
        nd += nrc
        s, nc = fix_call_casts(s, protos)
        nc += nu + nd + nr
        if nc:
            io.open(path, 'w', encoding='utf-8', newline='').write(s)
            print('  %-40s %d call-site cast(s) retyped'
                  % (path.split('/')[-1], nc))
        lines = s.split('\n')
        changed = 0
        for i, line in enumerate(lines):
            m = DEF.match(line)
            if not m:
                continue
            name, have, var = m.group('name'), m.group('type').strip(), m.group('var')
            want = protos.get(name)
            if not want or want == have:
                continue
            # retype the parameter
            lines[i] = line.replace('%s* %s' % (have, var), '%s* %s' % (want, var), 1)
            if lines[i] == line:
                lines[i] = re.sub(r'\b%s\s*\*\s*%s\b' % (re.escape(have), re.escape(var)),
                                  '%s* %s' % (want, var), line, count=1)
            # ... and flatten the body, since the new type has no `.s`
            depth, j = 0, i
            while j < len(lines):
                depth += lines[j].count('{') - lines[j].count('}')
                lines[j] = re.sub(r'\(\s*%s->s\s*\)\.' % re.escape(var),
                                  '%s->' % var, lines[j])
                lines[j] = re.sub(r'\b%s->s\.' % re.escape(var), '%s->' % var, lines[j])
                lines[j] = re.sub(r'&%s->s\b' % re.escape(var),
                                  '(struct Entity*)%s' % var, lines[j])
                if depth <= 0 and j > i:
                    break
                j += 1
            changed += 1
            print('  %-40s %s: %s* -> %s*' % (path.split('/')[-1], name, have, want))
        if changed:
            io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(lines))
            total += changed
    print('aligned %d definition(s)' % total)
    return 0


sys.exit(main())
