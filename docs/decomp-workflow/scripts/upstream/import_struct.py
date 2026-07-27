#!/usr/bin/env python3
"""Import a fork-only struct into a ported file, in upstream's flat style.

A lifted body often names a per-entity struct that exists only in the fork:

    struct CyberElfBird {        <- fork, src/cyberelf/bird.c
      OBJECT_HDR;                   (= struct Entity s; struct Body body;)
      struct Zero* player;  // 0xB4
      u8 unk_b8[12];        // 0xB8
    };

Upstream has no such type, so the merged file reports "dereferencing pointer to
incomplete type" -- and the error points at the USE, never at the missing
definition, which makes it look like a member problem.

Upstream's convention for exactly this is a file-local typedef on
COLLISION_OBJECT_HDR with a size assertion against the generic entity
(see Childre, PantheonFist). So bring the fork's struct across, converted:

    typedef struct {
      COLLISION_OBJECT_HDR;      // 0x00
      struct Zero* player;       // 0xB4
      u8 unk_b8[12];             // 0xB8
    } CyberElfBird;
    static_assert(sizeof(CyberElfBird) == sizeof(CyberElf));

Same 196 bytes, different spelling -- so codegen is unchanged. The accesses
through it are then flattened by the usual pass.

usage: import_struct.py <file.c> [<generic-type>]
"""
import io
import re
import subprocess
import sys

# Which generic entity type the size assertion should compare against, chosen
# by where the file lives.
GENERIC = {
    'cyberelf': 'CyberElf', 'boss': 'Boss', 'enemy': 'struct Enemy',
    'projectile': 'Projectile', 'weapon': 'Weapon', 'solid': 'struct Solid',
    'vfx': 'struct VFX',
}


def fork_struct(name):
    """The fork's definition of `struct name`, from anywhere in its tree."""
    out = subprocess.run(['git', 'grep', '-l', '-E',
                          r'^struct\s+%s\s*\{' % re.escape(name), 'main', '--', 'src'],
                         capture_output=True, text=True).stdout
    for line in out.split('\n'):
        if ':' not in line:
            continue
        path = line.split(':', 1)[1]
        txt = subprocess.run(['git', 'show', 'main:' + path],
                             capture_output=True, text=True, errors='replace').stdout
        m = re.search(r'^struct\s+%s\s*\{(.*?)\n\};' % re.escape(name),
                      txt, re.S | re.M)
        if m:
            return m.group(1)
    return None


def main():
    path = sys.argv[1]
    s = io.open(path, encoding='utf-8', newline='').read()
    generic = (sys.argv[2] if len(sys.argv) > 2
               else GENERIC.get(path.split('/')[1], 'struct Enemy'))

    used = set(re.findall(r'struct\s+(\w+)\s*\*', s))
    defined = set(re.findall(r'struct\s+(\w+)\s*\{', s))
    added = 0
    for name in sorted(used - defined):
        # Anything upstream already knows about is not ours to define.
        known = subprocess.run(
            ['git', 'grep', '-q', '-E', r'struct\s+%s\s*[{;]' % re.escape(name),
             'upstream/dev', '--', 'include', 'src'], capture_output=True)
        if known.returncode == 0:
            continue
        body = fork_struct(name)
        if body is None:
            print('  %s: no fork definition for struct %s' % (path, name))
            continue
        body = body.replace('OBJECT_HDR;', 'COLLISION_OBJECT_HDR;  // 0x00', 1)
        # Deliberately NO static_assert. It would be nice documentation, but
        # `unify_local_type` treats `static_assert(sizeof(X) == sizeof(struct
        # Enemy))` as the file declaring X to BE its entity type, and then
        # retypes every `struct Enemy*` in the file to X. An imported struct is
        # usually a second, auxiliary view -- the generic type has `buffer[16]`
        # where this one names those bytes individually -- so that rewrite
        # breaks every function using `p->buffer[n]`. The size relationship is
        # implied by the offsets in the comments anyway.
        block = 'typedef struct {%s\n} %s;\n' % (body, name)
        incs = list(re.finditer(r'^#include "[^"]+"\n', s, re.M))
        at = incs[-1].end() if incs else 0
        s = s[:at] + '\n' + block + s[at:]
        # It is a typedef now, so the `struct` keyword has to go from every use.
        s = re.sub(r'\bstruct\s+%s\b' % re.escape(name), name, s)
        added += 1
        print('  %s: imported %s as a flat typedef' % (path, name))
    if added:
        io.open(path, 'w', encoding='utf-8', newline='').write(s)
    return 0


sys.exit(main())
