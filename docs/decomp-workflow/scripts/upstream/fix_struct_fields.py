#!/usr/bin/env python3
"""Rename struct FIELDS that the two trees spell differently.

Linker maps cannot help here: a map lists symbols, not struct members, so the
address-join that resolves function names is blind to this entirely. What does
work is that both trees describe the same ROM struct in the same order -- so
when a header declares the same struct in both, field N in the fork IS field N
upstream, and any name difference is a rename.

`struct StageLayer` is the clear case: 31 fields on both sides, differing only
at 0x34/0x3C, where the fork reads the value as the screen CENTRE and upstream
as the screen TOP-LEFT. Same bytes, opposite interpretation, and six ports
across four landscape.c files failed on it.

Guards, because a bad rename here compiles and simply reads another field:
  * skip the struct entirely unless the two field counts match -- a differing
    count means one side split or merged something and position no longer
    implies identity;
  * skip any rename whose OLD name is still a live field name somewhere in
    upstream's headers, since then the access might legitimately be that other
    struct's;
  * only rewrite member accesses (`.x` / `->x`), never bare identifiers.
"""
import re
import sys
import glob
import subprocess

STRUCT = re.compile(r'\bstruct\s+(\w+)\s*\{(.*?)\n\};', re.S)
FIELD = re.compile(r'\s*(?:struct\s+)?(\w+)\s*\**\s*(\w+)\s*(?:\[[^\]]*\])?\s*;')


def fields(body):
    """Field names in declaration order, STOPPING at the first anonymous
    union/struct.

    Only the sequential prefix carries positional meaning. Union arms are
    alternative views of the same bytes, so their order is arbitrary -- and the
    two trees do order them differently: in StageLayer the fork lists the
    eruptionX arm fifth and upstream lists it third, and one arm has three
    members where the other has two. Walking into them shifts every later
    position and would map fields onto unrelated ones."""
    out = []
    for ln in body.splitlines():
        s = ln.strip()
        if not s or s.startswith('//') or s.startswith('/*'):
            continue
        if re.match(r'(union|struct)\s*\{', s):
            break
        if s.startswith('}'):
            continue
        m = FIELD.match(ln)
        if m and m.group(1) not in ('return', 'typedef'):
            out.append(m.group(2))
    return out


import fix_buffer_offsets as BO  # noqa: E402  (brace-matching struct scanner)

# Structs the two trees spell differently. Positional comparison is keyed by
# name, so without this the pair is never even considered. Fork name -> the
# upstream type that occupies the same bytes.
ALIASES = {'Motion': 'AnimState'}


DEFINE = re.compile(r'^[ \t]*#define[ \t]+(\w+)[ \t]*\\\n((?:.*\\\n)*.*)$', re.M)


def expand_macros(txt):
    """Inline the `..._HDR` field macros into the structs that use them.

    Upstream keeps the fields every entity shares in `#define ENTITY_HDR` and
    friends, so a struct body is often just `COLLISION_OBJECT_HDR;` plus a few
    extras. The fork spells those fields out inside `struct Entity` instead.
    Without expanding, the two field lists are not remotely comparable and every
    shared field is invisible -- which is why `hazardAttr` (fork, 0x26) was
    never matched to `physicsAttr` (upstream, same offset)."""
    macros = {m.group(1): m.group(2) for m in DEFINE.finditer(txt)
              if m.group(1).endswith('_HDR') or m.group(1) == 'ENTITY_SPRITE'}
    if not macros:
        return txt
    body = {k: v.replace('\\\n', '\n') for k, v in macros.items()}
    for _ in range(4):                    # nested: COLLISION_OBJECT_HDR -> ...
        new = txt
        for k, v in body.items():
            new = re.sub(r'^([ \t]*)%s\s*;' % k,
                         lambda m, v=v: v, new, flags=re.M)
        if new == txt:
            break
        txt = new
    return txt


def structs(txt):
    """name -> field list, for named structs AND `typedef struct {...} Name;`.

    The plain regex form only saw `struct X {`, which misses every anonymous
    typedef -- including AnimState, the type behind every `p->motion`."""
    return {nm: fields(body) for nm, body in BO._bodies(expand_macros(txt))}


def field_types(txt):
    """(struct, member) -> declared type, for resolving `x->mem.fld`.

    Keying the member's type by NAME alone is not enough: `s` is an `Entity` in
    every entity struct but a `Story` elsewhere, so the name-keyed map had two
    candidates and refused to resolve -- which is why `(p->s).hazardAttr` was
    left alone. Going through the variable's own type removes the ambiguity."""
    out = {}
    for nm, body in BO._bodies(expand_macros(txt)):
        for ln in body.splitlines():
            s = ln.strip()
            if not s or s.startswith('//') or s.startswith('}'):
                continue
            if re.match(r'(union|struct)\s*\{', s):
                break
            d = re.match(r'\s*(?:struct\s+)?(\w+)\s+(\w+)\s*(?:\[[^\]]*\])?\s*;',
                         ln)
            if d:
                out[(nm, d.group(2))] = d.group(1)
    return out


def main():
    src = sys.argv[1]
    lifted = set(sys.argv[2:])
    # glob hands back backslashes on Windows, and `git show main:include\x.h`
    # is not a valid pathspec -- it fails, the header gets skipped, and the tool
    # cheerfully reports zero renames for the whole tree.
    headers = sorted(p.replace('\\', '/')
                     for p in glob.glob('include/**/*.h', recursive=True))

    renames = {}
    upstream_names = set()
    fork_uses = {}
    pairs = []
    qualified = {}          # (upstream struct, fork field) -> upstream field
    member_type = {}        # member name -> {upstream types declaring it}
    inv_alias = {v: k for k, v in ALIASES.items()}
    up_texts, all_us, all_fs, ftypes = [], {}, {}, {}

    # Collect BOTH trees' structs across every header before pairing anything.
    # Pairing per-file cannot see a struct the two trees moved: AnimState lives
    # in upstream's animation.h while its fork counterpart Motion is in
    # motion.h, so the file-local view never had both in hand and the pair was
    # silently skipped.
    for h in headers:
        with open(h, encoding='utf-8', errors='replace') as fh:
            up = fh.read()
        up_texts.append(up)
        all_us.update(structs(up))
        ftypes.update(field_types(up))
    for h in subprocess.run(['git', 'ls-tree', '-r', '--name-only', 'main',
                             'include/'], capture_output=True, text=True
                            ).stdout.split():
        if h.endswith('.h'):
            all_fs.update(structs(subprocess.run(
                ['git', 'show', 'main:' + h], capture_output=True).stdout
                .decode('utf-8', errors='replace')))

    for h in headers:
        with open(h, encoding='utf-8', errors='replace') as fh:
            up = fh.read()
        r = subprocess.run(['git', 'show', 'main:' + h], capture_output=True)
        if r.returncode:
            continue                      # header is upstream-only
        fk = r.stdout.decode('utf-8', errors='replace')
        # Every field-looking declaration in the header counts towards the
        # ambiguity check, not just the ones inside a `struct X { }`. The entity
        # types get their common fields from the ENTITY_HDR / ENTITY_SPRITE /
        # COLLISION_OBJECT_HDR macros, which are #defines -- so `step`, declared
        # there, was invisible, and `MetaspriteHeader.step -> texture` got
        # applied to every entity's `p->step` in the file.
        upstream_names.update(m.group(2) for m in
                              (FIELD.match(ln) for ln in up.splitlines())
                              if m and m.group(1) not in ('return', 'typedef'))

        # How many DIFFERENT fork structs declare each name. A rename is only
        # safe to apply by text if the old name belongs to exactly one struct in
        # the fork as well: `step` is MetaspriteHeader's field at 0x1F (upstream
        # `texture`) but it is also a field of Motion, and rewriting the lot
        # turned `p->motion.step` into `p->motion.texture`.
        for st, fl in structs(fk).items():
            for f in fl:
                fork_uses.setdefault(f, set()).add(st)

        us, fs = structs(up), structs(fk)
        for name, ufl in us.items():
            ffl = fs.get(name)
            if ffl is None or len(ffl) != len(ufl):
                continue                  # counts differ: position proves nothing
            for a, b in zip(ffl, ufl):
                if a != b:
                    pairs.append((name, a, b))

    # Qualified table, built from the global view so a struct the trees keep in
    # different files (or under different names, see ALIASES) still pairs up.
    for name, ufl in all_us.items():
        ffl = all_fs.get(name) or all_fs.get(inv_alias.get(name))
        if ffl is not None and len(ffl) == len(ufl):
            for a, b in zip(ffl, ufl):
                if a != b:
                    qualified[(name, a)] = b

    # Member name -> its upstream type, for the qualified pass. This has to run
    # across ALL headers at once: `AnimState motion;` is declared in entity.h
    # while AnimState itself is defined in animation.h, so checking each header
    # against only its own structs resolved nothing.
    for up in up_texts:
        for ln in up.splitlines():
            d = re.match(r'\s*(?:struct\s+)?(\w+)\s+(\w+)\s*;', ln)
            if d and d.group(1) in all_us:
                member_type.setdefault(d.group(2), set()).add(d.group(1))

    conflicting = {a for a, _ in
                   ((x[1], x[2]) for x in pairs)
                   if sum(1 for y in pairs if y[1] == a) > 1
                   and len({y[2] for y in pairs if y[1] == a}) > 1}
    # An old name that upstream still uses somewhere is ambiguous -- the access
    # in hand might belong to that other struct. Same for one old name that maps
    # to two different new names depending on the struct: applying either by
    # text alone would corrupt the other.
    unsafe = {a for _, a, _ in pairs
              if a in upstream_names or a in conflicting
              or len(fork_uses.get(a, ())) > 1}
    # If a struct has ANY unsafe rename, drop that struct's renames entirely.
    # EntityHeader is relabelled wholesale -- last/next/prev become cur/tail/head
    # -- and two of the three are ambiguous. Applying only `prev`->`head` would
    # leave the other two pointing at the wrong links, which compiles fine and
    # walks the list backwards. A partial relabelling is worse than none.
    poisoned = {s for s, a, _ in pairs if a in unsafe}
    dropped = sorted({a for s, a, _ in pairs if a in unsafe or s in poisoned})
    for s, a, b in pairs:
        if a not in dropped:
            renames.setdefault(a, b)

    with open(src, encoding='utf-8', errors='replace') as fh:
        txt = fh.read()
    n = 0
    for a, b in renames.items():
        txt, k = re.subn(r'(?<=[.>])%s\b' % re.escape(a), b, txt)
        n += k

    # Qualified pass: `x->motion.step` / `(x->motion).step`. The unqualified
    # table cannot carry these -- `step` is MetaspriteHeader's field (upstream
    # `texture`) AND Motion/AnimState's (upstream `id`), so by text alone either
    # substitution corrupts the other site. Resolving the member's type first
    # makes both safe.
    single = {k: next(iter(v)) for k, v in member_type.items() if len(v) == 1}

    scope = {}

    def owner(var, mem):
        """Type of `var->mem`: through var's own declared type when it can be
        resolved, falling back to the member name only when it is unambiguous
        tree-wide."""
        vt = (scope.get(var) or (BO.var_type(txt, var) if var else None))
        if vt and (vt, mem) in ftypes:
            return ftypes[(vt, mem)]
        return single.get(mem)

    def qsub(m):
        nonlocal n
        d = m.groupdict()
        fld = d['fld']
        want = qualified.get((owner(d.get('var'), d['mem']), fld))
        if not want:
            return m.group(0)
        n += 1
        return m.group(0)[:-len(fld)] + want

    def vsub(m):
        """Single-level `var->fld`, resolved through var's declared type. This
        is what the guarded text pass cannot do: `hazardAttr` is unambiguous but
        `next`/`prev` are SWAPPED between the trees, and only a type-resolved
        rewrite can apply a swap without corrupting the other half."""
        nonlocal n
        var, fld = m.group('var'), m.group('fld')
        vt = scope.get(var) or BO.var_type(txt, var)
        want = qualified.get((vt, fld)) if vt else None
        if not want:
            return m.group(0)
        n += 1
        return m.group(0)[:-len(fld)] + want

    for pat in (r'(?P<var>\w+)\s*->\s*(?P<mem>\w+)\s*\.\s*(?P<fld>\w+)\b',
                r'\(\s*(?P<var>\w+)\s*->\s*(?P<mem>\w+)\s*\)\s*\.\s*(?P<fld>\w+)\b',
                r'(?:[.]|->)(?P<mem>\w+)\s*\.\s*(?P<fld>\w+)\b'):
        txt = re.sub(pat, qsub, txt)
    txt = re.sub(r'(?P<var>\w+)\s*->\s*(?P<fld>\w+)\b', vsub, txt)
    with open(src, 'w', encoding='utf-8', newline='') as fh:
        fh.write(txt)
    print('  struct fields: %d rewritten (%d rename(s) known, %d ambiguous)'
          % (n, len(renames), len(dropped)))


if __name__ == '__main__':
    main()
