#!/usr/bin/env python3
"""Add the headers a ported file needs, by asking the compiler.

Ported code calls helpers the upstream file never included. Under the project's
real CFLAGS an implicit declaration is a hard error, so each one has to be
resolved -- and it matters beyond the error: C89 defaults an undeclared callee
to `int`, which silently changes codegen (a bool8 return loses the caller's
`lsls r0,r0,#24`, and a u32 comparison becomes signed, `ble` instead of `bls`).

So this is not cosmetic: without the right prototype the function compiles and
byte-MISmatches.

Loops until the compiler stops complaining or nothing new can be resolved.

usage: fix_includes.py <file.c> ...
"""
import io
import os
import re
import subprocess
import sys

AGBCC = os.path.join(os.environ['RMZ3_FORK'], 'tools/agbcc')


def compile_errors(path):
    cpp = subprocess.run(
        ['arm-none-eabi-cpp', '-I', AGBCC, '-I', AGBCC + '/include',
         '-iquote', 'include', '-nostdinc', '-undef', '-std=gnu89',
         '-DMODERN=0', path], capture_output=True)
    cc = subprocess.run(
        [AGBCC + '/bin/agbcc.exe', '-mthumb-interwork', '-Wimplicit',
         '-Wparentheses', '-Werror', '-O2', '-fshort-enums', '-fhex-asm',
         '-o', os.devnull], input=cpp.stdout, capture_output=True)
    return cc.stderr.decode('utf-8', 'replace')


def fork_prototype(name):
    """The fork's declaration of `name`, from anywhere in its tree.

    Cross-file callees (FUN_080c68cc and friends) have no upstream header, so
    the only place a correct signature exists is the fork. Prefer a real
    prototype; fall back to the definition's own signature, which is the
    byte-verified one.
    """
    # Grep LOOSELY for the bare name (-F), then match precisely in Python.
    #
    # Two bugs made the previous version find nothing at all, silently:
    #   * `git grep -E` does not accept `\s`. It exits 128, and nothing checked
    #     the return code, so every single lookup came back empty.
    #   * `pat.replace('^', r'^\s*')` also rewrote the `^` INSIDE the character
    #     class `[^;{)]`, turning it into `[^\s*;{)]`.
    # Keeping the real regex on the Python side sidesteps both.
    out = subprocess.run(['git', 'grep', '-h', '-F', name, 'main', '--', 'src', 'include'],
                         capture_output=True, text=True, errors='replace')
    pat = (r'^\s*((?:extern\s+|static\s+)?(?:bool8|bool32|u8|s8|u16|s16|u32|s32|void|'
           r'struct\s+\w+\s*\**|\w+\s*\**)\s*\**\s*%s\s*\([^;{)]*\))\s*[;{]'
           % re.escape(name))
    for line in out.stdout.split('\n'):
        m = re.match(pat, line.rstrip())
        if m:
            return (m.group(1).strip()
                    .replace('extern ', '').replace('static ', '') + ';')
    return None


def _fork_src():
    """The fork file the bodies were lifted from, as recorded by
    port_to_upstream. Empty when it was not run (standalone use)."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     'fork_src.txt')
    try:
        with open(p, encoding='utf-8') as fh:
            return fh.read().split('\n')[0].strip()
    except OSError:
        return ''


FORK_SRC = _fork_src()


def fork_object_decl(name):
    """The fork's `extern` declaration for a DATA symbol.

    Shared read-only data (`extern const struct Rect Rect_08370c60;`) lives in
    the ROM under the same name in both trees -- the linker maps agree on the
    address -- but upstream has no header for it, and it is not a function, so
    the prototype fallback never sees it.
    """
    # Loose grep, precise Python match -- same reasoning as fork_prototype.
    # Also accepts a `static const X foo[N];` forward declaration, which is how
    # file-local tables are spelled; the storage class is dropped since the
    # object lives in another translation unit here.
    pat = (r'^\s*(?:extern\s+|static\s+)?((?:const\s+)?(?:struct\s+)?[\w ]+?\**\s*'
           r'%s\s*(?:\[[^\]]*\])*)\s*;' % re.escape(name))

    def scan(args):
        out = subprocess.run(['git', 'grep', '-h', '-F', name, 'main', '--']
                             + args, capture_output=True, text=True,
                             errors='replace')
        for line in out.stdout.split('\n'):
            m = re.match(pat, line.rstrip())
            if m:
                return 'extern %s;' % m.group(1).strip()
        return None

    # Prefer the file the body came from. Names like `sUpdates` are file-local
    # tables reused all over the tree, and a whole-tree grep returns whichever
    # sorts first -- for `unk_34.c` that was a cyberelf file, giving
    # `extern const ElfFunc sUpdates[2];` where the truth is
    # `static const ProjectileFunc sUpdates[4];`. ElfFunc is not even declared
    # in that translation unit, so it failed as `syntax error before 'sUpdates'`
    # -- pointing at the name, never at the wrong type it had been given.
    if FORK_SRC:
        got = scan([FORK_SRC])
        if got:
            return got
    return scan(['src', 'include'])


def declaring_header(name):
    """Which include/*.h actually DECLARES `name`.

    Order matters: look for a real declaration before any mention. `gStageRun`
    is declared in stagerun.h but merely named inside a comment in script.h --
    and script.h wins a "shortest filename" tie-break, so the wrong header gets
    added and the identifier stays undeclared.
    """
    n = re.escape(name)
    for pattern in (
            r'\b%s\s*\(' % n,                       # function declaration
            r'^\s*extern\b[^;]*\b%s\b\s*(\[|;)' % n,  # extern object
            r'^\s*#define\s+%s\b' % n,              # macro
            r'\b%s\b' % n):                         # last resort: any mention
        out = subprocess.run(
            ['git', 'grep', '-l', '-E', pattern, 'HEAD', '--', 'include'],
            capture_output=True, text=True).stdout
        hits = [l.split(':', 1)[1] for l in out.split('\n') if ':' in l]
        if hits:
            # Prefer the shallowest path, then the shortest.
            hits.sort(key=lambda h: (h.count('/'), len(h)))
            return hits[0][len('include/'):]
    return None


def main():
    for path in sys.argv[1:]:
        for _ in range(12):
            err = compile_errors(path)
            names = set(re.findall(
                r"implicit declaration of function `(\w+)'", err))
            names |= set(re.findall(r"`(\w+)' undeclared", err))
            if not names:
                break
            added, fwd, fwd_late = [], [], []
            s = io.open(path, encoding='utf-8', newline='').read()
            for n in sorted(names):
                # Defined further down this same file? Then it needs a forward
                # declaration, not an include -- copy the definition's own
                # signature so the return type cannot disagree with it.
                d = re.search(
                    r'^((?:static\s+)?[A-Za-z_][\w \*]*?\b%s\s*\([^;{)]*\))\s*\{'
                    % re.escape(n), s, re.M)
                if d:
                    proto = d.group(1).strip() + ';'
                    if proto not in s:
                        fwd.append(proto)
                    continue
                # A static table defined further down: `static const EnemyFunc
                # sUpdates[9] = {...}` used above its definition. Hoist the
                # declaration, matching the definition's storage class so the
                # two cannot disagree.
                # Arrays AND plain objects. `static const Coords32
                # sElementCoord = {...}` has no brackets, so a bracket-required
                # pattern leaves it undeclared while handling sUpdates[9] fine.
                d2 = re.search(
                    r'^((?:static\s+)?(?:const\s+)?[\w \*]+\b%s\s*(?:\[[^\]]*\])*)\s*='
                    % re.escape(n), s, re.M)
                if d2:
                    decl = d2.group(1).strip() + ';'
                    if decl not in s:
                        fwd.append(decl)
                    continue
                h = declaring_header(n)
                if h and '#include "%s"' % h not in s:
                    added.append(h)
                    continue
                # Cross-file callee with no header: take the fork's own
                # declaration. Without a prototype C89 assumes `int`, which
                # silently changes codegen -- a bool8 return loses the caller's
                # truncation and a u32 comparison becomes signed. So this is
                # not merely about silencing the warning.
                proto = fork_prototype(n) or fork_object_decl(n)
                # Never import a declaration for something this file already
                # DEFINES. Upstream keeps its own
                # `static void (*const sUpdates[4])(Projectile34*) = {...}`
                # further down, so `extern const ProjectileFunc sUpdates[4];`
                # is not a missing-prototype fix, it is a second incompatible
                # declaration -- "conflicting types for 'sUpdates'".
                #
                # The name is still undeclared at the point of USE, though, so
                # hoist a forward declaration cut from that very definition:
                # everything up to the `=`, plus a semicolon. Taking it from the
                # definition rather than from the fork is the whole point -- the
                # fork's spelling is what conflicted.
                # Must be a TOP-LEVEL definition: starts at column 0, and the
                # `=` is an initialiser, not the tail of a comparison. Without
                # both guards this matched
                # `    if (gMission.weaponCount[WEAPON_SABER] <= 0xFFFE) {`
                # on the `<=`, and hoisted `if (gMission.weaponCount[...] <;`
                # to the top of the file as a declaration.
                own = re.search(r'^(\S[^\n=]*?\b%s\b[^\n=]*?)'
                                r'(?<![<>!=+\-*/%%&|^])\s*=\s*[{\w]'
                                % re.escape(n), s, re.M)
                # A declaration needs a TYPE. `SEA = PIXEL(10240);` -- an
                # assignment to a macro upstream does not define -- matched as
                # well, and hoisting `SEA;` produced "data definition has no
                # type or storage class" instead of the real problem.
                if own and not re.search(r'[\w\]\)]\s*[\* ]\s*\w', own.group(1)):
                    own = None
                if own:
                    decl = own.group(1).strip() + ';'
                    if decl not in s:
                        fwd_late.append((n, decl))
                    continue
                if proto and proto not in s:
                    fwd.append(proto)
            if not added and not fwd and not fwd_late:
                print('  %s: unresolved %s' % (path, ' '.join(sorted(names))))
                break
            incs = list(re.finditer(r'^#include "[^"]+"\n', s, re.M))
            at = incs[-1].end() if incs else 0
            s = (s[:at] + ''.join('#include "%s"\n' % h for h in added)
                 + ('\n' + '\n'.join(fwd) + '\n' if fwd else '') + s[at:])
            # Declarations cut from this file's own definitions name types that
            # the file itself declares (`Projectile34`), so they cannot go up
            # with the includes -- that gave "syntax error before '*'" on a
            # perfectly good declaration. Put them after the last type
            # definition instead.
            # Anchor each one to ITS OWN first use: after the last type
            # definition that still precedes that use. Taking the last `};` in
            # the whole file put the declaration BELOW the function that needed
            # it, so the name was still undeclared -- with the error moving to
            # the use site, which looks like the declaration never happened.
            spots = []
            for n, decl in fwd_late:
                use = re.search(r'\b%s\b' % re.escape(n), s)
                if not use:
                    continue
                ends = [m for m in re.finditer(r'^\}[^\n]*;\n', s, re.M)
                        if m.end() <= use.start()]
                spots.append((ends[-1].end() if ends else at, decl))
            for pos, decl in sorted(spots, reverse=True):
                s = s[:pos] + '\n' + decl + '\n' + s[pos:]
            io.open(path, 'w', encoding='utf-8', newline='').write(s)
            # Progress line only -- must never be able to fail. The old form
            # assumed every forward declaration contains `name(`, so an OBJECT
            # declaration (`extern const ProjectileFunc sUpdates[4];`) crashed
            # the whole pass here, AFTER the file had been written.
            def _nm(f):
                m = re.search(r'\b(\w+)\s*[(\[;]', f)
                return m.group(1) if m else f[:20]
            print('  %s: %s%s' % (path, ' '.join('+' + h for h in added),
                                  (' fwd:' + ','.join(_nm(f) for f in fwd))
                                  if fwd else ''))
    return 0


sys.exit(main())
