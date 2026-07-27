#!/bin/bash
# Resolve undeclared identifiers in a ported upstream .c.
#
#   fixdecls.sh <upstream-src.c> <fork-src.c>
#
# Two sources, in order: a known header for well-known globals, then the fork's
# own declaration of the symbol. Loops until the compiler stops complaining.
cd "${RMZ3_WT:?set RMZ3_WT to the upstream worktree}"
export PATH="/c/devkitPro/devkitARM/bin:$PATH"
A=${RMZ3_FORK}/tools/agbcc
SRC=$1; FORK=$2

for round in $(seq 1 12); do
  UND=$(arm-none-eabi-cpp -I $A -I $A/include -iquote include -nostdinc -undef \
        -std=gnu89 -DMODERN=0 $SRC 2>/dev/null \
    | $A/bin/agbcc.exe -mthumb-interwork -Wimplicit -Wparentheses -O2 \
        -fshort-enums -fhex-asm -o /tmp/x.s 2>&1 \
    | grep -oE "\`[A-Za-z_][A-Za-z0-9_]*' (undeclared|implicitly declared)|implicit declaration of function \`[A-Za-z_][A-Za-z0-9_]*'" \
    | sed "s/.*\`//;s/'.*//" | sort -u)
  [ -z "$UND" ] && { echo "   declarations resolved (round $round)"; break; }
  python3 - "$SRC" "$FORK" $UND <<'PY'
import io, re, subprocess, sys, os
src, fork = sys.argv[1], sys.argv[2]
names = sys.argv[3:]

# Well-known globals live in a specific header; adding it is cleaner (and more
# in keeping with the file) than pasting an extern declaration.
HDR = {
    'pZero2': 'zero.h', 'pZero': 'zero.h',
    'gCurStory': 'story.h',
    'gStageRun': 'stagerun.h',
    'gSineTable': 'trig.h',
    'gScore': 'score.h',
    'gSystemSavedata': 'syssav.h',
    'gJoypad': 'input.h',
    'gCamera': 'camera.h',
    'RNG_0202f388': 'global.h',
    'gOverworld': 'overworld.h',
    'gVideoRegBuffer': 'gpu_regs.h',
    'gWeaponTileNum': 'weapon.h',
    'gWeaponPalIDs': 'weapon.h',
    # macros, not globals -- they report as undeclared identifiers just the same
    'IS_METTAUR': 'story.h',
    'IS_MISSION': 'story.h',
    'ENEMY_KILLCOUNT': 'story.h',
}
s = io.open(src, encoding='utf-8', errors='replace', newline='').read()
ftxt = subprocess.run(['git', 'show', 'main:' + fork],
                      capture_output=True).stdout.decode('utf-8', 'replace')


def fork_prototype(name):
    """Find `name`'s prototype anywhere in the fork -- its own file first, then
    the fork's headers. Cross-file callees (FUN_080c68cc etc.) are declared in
    a header, not in the file being ported, and without the declaration agbcc
    falls back to implicit int, which -Werror rejects."""
    pat = (r'^((?:extern\s+)?(?:bool8|bool32|u8|s8|u16|s16|u32|s32|void|'
           r'struct\s+\w+\s*\*|\w+\s*\*)\s*\**\s*%s\([^;{)]*\));' % re.escape(name))
    m = re.search(pat, ftxt, re.M)
    if m:
        return m.group(1).strip() + ';'
    out = subprocess.run(['git', 'grep', '-h', '-E', pat.replace('^', ''), 'main', '--',
                          'include', 'src'], capture_output=True).stdout.decode('utf-8', 'replace')
    for line in out.split('\n'):
        m = re.search(pat.replace('^', r'^\s*'), line.strip(), re.M)
        if m:
            return m.group(1).strip() + ';'
    return None
incs_added, decls = [], []
for n in names:
    h = HDR.get(n)
    if h and os.path.exists(os.path.join('include', h)) \
            and '#include "%s"' % h not in s:
        incs_added.append(h)
        continue
    proto = fork_prototype(n)
    if proto and proto not in s:
        decls.append(proto)
        continue
    m = (re.search(r'^((?:static |extern |const )*[\w \*]+\b%s\s*(?:\[[^\]]*\])*)\s*;'
                   % re.escape(n), ftxt, re.M)
         or re.search(r'^((?:static |extern |const )*[\w \*]+\b%s\s*(?:\[[^\]]*\])*)\s*='
                      % re.escape(n), ftxt, re.M))
    if m:
        d = m.group(1).strip() + ';'
        # If this file defines the symbol later, a forward declaration copied
        # from the fork can disagree on linkage (extern vs static) or size and
        # produce "conflicting types". Match the local definition's storage
        # class instead of pasting the fork's.
        # Capture the whole declarator up to the '=' so function-pointer arrays
        # like `static void (*const sUpdates1[9])(PantheonFist*)` are handled;
        # a simpler pattern misses them and the pasted `extern const EnemyFunc
        # sUpdates1[]` then conflicts with the real definition.
        local = re.search(r'^((?:static\s+|const\s+|extern\s+)*[^=;\n]*?\b%s\b[^=;\n]*?)\s*='
                          % re.escape(n), s, re.M)
        if local:
            d = local.group(1).strip() + ';'
        if d not in s:
            decls.append(d)
if incs_added or decls:
    inc_at = list(re.finditer(r'^#include "[^"]+"\n', s, re.M))
    inc_at = inc_at[-1].end() if inc_at else 0
    # Declarations go AFTER the type definitions, not straight after the
    # includes: they often name a file-local typedef (PantheonFist, VFX50) that
    # is declared further down, and hoisting them above it is a syntax error.
    decl_at = inc_at
    for m in re.finditer(r'^\}\s*\w*\s*;\n', s, re.M):
        decl_at = max(decl_at, m.end())
    first_fn = re.search(r'^[A-Za-z_][\w \*]*\b\w+\([^;{)]*\)\s*\{', s, re.M)
    if first_fn:
        decl_at = min(decl_at, first_fn.start()) if decl_at > first_fn.start() else decl_at
    parts = [s[:inc_at], ''.join('#include "%s"\n' % h for h in incs_added)]
    rest = s[inc_at:]
    off = decl_at - inc_at
    rest = rest[:off] + ('\n' + '\n'.join(decls) + '\n' if decls else '') + rest[off:]
    s = ''.join(parts) + rest
    io.open(src, 'w', encoding='utf-8', newline='').write(s)
    print('   +%d header(s), +%d declaration(s)' % (len(incs_added), len(decls)))
else:
    print('   unresolved:', ' '.join(names[:6]))
PY
done
