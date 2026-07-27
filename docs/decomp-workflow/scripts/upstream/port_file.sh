#!/bin/bash
# Port one fork source file's matched functions onto upstream, end to end.
#
#   port_file.sh <fork-src.c> <flat|nested> [<old-type> <new-type>]
#
# Steps: locate the upstream .inc/.c, lift every portable function, adapt to
# upstream conventions, resolve missing declarations from the fork, byte-verify
# each function against the ROM, and print the verified list. Nothing is
# committed -- inspect the output, then re-run the port restricted to the
# verified names before opening a PR.
set -u
cd "${RMZ3_WT:?set RMZ3_WT to the upstream worktree}"
export PATH="/c/devkitPro/devkitARM/bin:$PATH"
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
A=${RMZ3_FORK}/tools/agbcc

FORK_SRC=$1; MODE=$2; OLD=${3:--}; NEW=${4:--}
FNS=$(grep " ${FORK_SRC}\$" ~/portable.txt | awk '{print $1}' | tr '\n' ' ')
[ -z "$FNS" ] && { echo "no portable functions for $FORK_SRC"; exit 1; }

# the upstream .inc holding them, and the .c that INCASMs it
INC=""
for f in $FNS; do
  INC=$(grep -rl "thumb_func_start $f\$" asm 2>/dev/null | head -1)
  [ -n "$INC" ] && break
done
[ -z "$INC" ] && { echo "all already matched upstream"; exit 0; }
UPSRC=$(grep -rl "INCASM(\"$INC\")" src 2>/dev/null | head -1)
[ -z "$UPSRC" ] && { echo "no upstream .c INCASMs $INC"; exit 1; }

# only the ones still asm upstream
KEEP=""
for f in $FNS; do
  grep -q "thumb_func_start $f\$" "$INC" && KEEP="$KEEP $f"
done
echo "== $FORK_SRC -> $UPSRC via $INC"
echo "   $(echo $KEEP | wc -w) portable and still asm upstream"

python3 $S/port_to_upstream.py "$INC" "$UPSRC" "$FORK_SRC" $KEEP >/dev/null || exit 1
python3 $S/adapt_up.py "$UPSRC" "$MODE" "$OLD" "$NEW" $KEEP >/dev/null

# props union -> plain buffer, and adopt this file's existing prototypes
python3 - "$UPSRC" "$FORK_SRC" <<'PY'
import io,os,re,subprocess,sys
f,fork=sys.argv[1],sys.argv[2]
s=io.open(f,encoding='utf-8',errors='replace',newline='').read()

# Copy across every prototype the fork declares that this file lacks. Without
# one, C89 defaults the callee to implicit int -- and an int return needs no
# truncation, so agbcc drops the `lsls r0,r0,#24` the ROM performs on a bool8
# return, and every caller comes out short. This alone took phantom 53 -> 68.
ftxt=subprocess.run(['git','show','main:'+fork],capture_output=True).stdout.decode('utf-8','replace')

# Carry over any file-local struct the lifted code needs. port_to_upstream only
# moves function bodies, so a `struct PantheonFistObject*` parameter arrives with
# no definition and every field access is "dereferencing pointer to incomplete
# type".
for sname in sorted(set(re.findall(r'struct\s+(\w+)\s*\*', s))):
    if re.search(r'^\s*(?:typedef\s+)?struct\s+%s\s*\{' % re.escape(sname), s, re.M):
        continue
    if re.search(r'struct\s+%s\s*;' % re.escape(sname), s):
        continue
    m = re.search(r'^struct\s+%s\s*\{.*?^\};\n' % re.escape(sname), ftxt, re.M | re.S)
    if m:
        at = list(re.finditer(r'^#include "[^"]+"\n', s, re.M))
        at = at[-1].end() if at else 0
        # OBJECT_HDR is fork-only. Expand it to the NESTED form rather than
        # COLLISION_OBJECT_HDR: these file-local structs must mirror
        # `struct Enemy`, which upstream has not flattened, and the file usually
        # mixes them with plain `struct Enemy*` handlers.
        body = m.group(0).replace('OBJECT_HDR;',
                                  'struct Entity s;\n  struct Body body;')
        s = s[:at] + '\n' + body + s[at:]
        print('   +struct %s from the fork' % sname)

# Some needs show up as "dereferencing pointer to incomplete type" rather than
# an undeclared identifier, so fixdecls.sh never sees them. Add the header when
# the ported code touches the type at all.
for token, hdr in (('scriptEntity', 'script.h'), ('SIN(', 'trig.h'),
                   ('COS(', 'trig.h'), ('Sin(', 'trig.h'), ('Cos(', 'trig.h')):
    if token in s and '#include "%s"' % hdr not in s and os.path.exists('include/' + hdr):
        incs = list(re.finditer(r'^#include "[^"]+"\n', s, re.M))
        at = incs[-1].end() if incs else 0
        s = s[:at] + '#include "%s"\n' % hdr + s[at:]
        print('   +%s (for %s)' % (hdr, token))

added=[]
for m in re.finditer(r'^((?:bool8|bool32|u8|s8|u16|s16|u32|s32|void|struct\s+\w+\s*\*)'
                     r'\s*\**\s*\w+\([^;{)]*\));\s*$', ftxt, re.M):
    decl=m.group(1).strip()
    name=re.search(r'\b(\w+)\s*\(',decl).group(1)
    if re.search(r'^[A-Za-z_][\w \*]*\b%s\s*\([^;{)]*\);'%re.escape(name), s, re.M):
        continue          # already declared here
    if not re.search(r'\b%s\s*\('%re.escape(name), s):
        continue          # not referenced
    added.append(decl+';')
if added:
    incs=list(re.finditer(r'^#include "[^"]+"\n', s, re.M))
    at=incs[-1].end() if incs else 0
    s=s[:at]+'\n'+'\n'.join(added)+'\n'+s[at:]
    print('   +%d prototype(s) from the fork'%len(added))
# Fork -> upstream FUNCTION renames. Critical: the byte probe masks BL targets
# as relocations, so a call to a function that does not exist upstream verifies
# green and only fails at link time. -Werror + these renames are what actually
# catch it.
s=re.sub(r'\bUpdateMotionGraphic\b', 'UpdateEntityAnim', s)

# Fork -> upstream global renames. These are the same storage under a
# different name, so a missing rename shows up as an undeclared identifier
# that no header can resolve.
s=re.sub(r'\bgMission\.', 'gScore.', s)
s=re.sub(r'\bgSystemSavedataManager\.mods\[(\d+)\]',
         lambda m: 'gSystemSavedata.flags[%d]' % (7+int(m.group(1))), s)
s=re.sub(r'\(p->props\)\.raw\[','p->buffer[',s)
s=re.sub(r'->props\[','->buffer[',s)
s=re.sub(r'\)\.props\[',').buffer[',s)
s=re.sub(r'\(p->props\)\[','p->buffer[',s)
protos={}
for m in re.finditer(r'^([A-Za-z_][\w \*]*?)\b(\w+)\(([^;{)]*)\);\s*$', s, re.M):
    protos[m.group(2)]=(m.group(1).strip(),[a.strip() for a in m.group(3).split(',')])
def fix(m):
    ret,name,args=m.group(1).strip(),m.group(2),[a.strip() for a in m.group(3).split(',')]
    if name not in protos: return m.group(0)
    pret,pargs=protos[name]
    if len(pargs)!=len(args): return m.group(0)
    new=[]
    for pa,da in zip(pargs,args):
        # Leave an argument alone if it carries an attribute macro: the name is
        # not the last token there, and taking it turned
        # `struct Body* body UNUSED` into `struct Body* UNUSED`.
        if re.search(r'\b(UNUSED|ALIGNED)\b', da):
            new.append(da); continue
        nm=re.search(r'(\w+)\s*$',da); ty=re.sub(r'\w+\s*$','',pa).strip()
        new.append('%s %s'%(ty,nm.group(1)) if nm else pa)
    # Keep the DEFINITION's return type: it is the byte-verified one. Adopting
    # the prototype's return type turned a bool8 function into void and left
    # `return TRUE;` in a void body.
    return '%s %s(%s) {'%(ret,name,', '.join(new))
s=re.sub(r'^([A-Za-z_][\w \*]*?)\b(\w+)\(([^;{)]*)\)\s*\{',fix,s,flags=re.M)

# Flattening is per-FUNCTION, not per-file: one file can mix a flat typedef
# (Boss, Projectile, PantheonFist -- no `struct` keyword) with nested
# `struct Enemy` handlers. Flatten only the bodies whose resolved first
# parameter is a flat typedef.
def flatten_flat_params(text):
    out=[]; pos=0
    for m in re.finditer(r'^([A-Za-z_][\w \*]*?)\b(\w+)\(([^;{)]*)\)\s*\{', text, re.M):
        first=m.group(3).split(',')[0].strip()
        # Do NOT skip functions whose first parameter is a nested type: a
        # collision handler takes `struct Body*` first and derives the flat
        # entity into a local, and skipping the function left that local alone.
        d=0; end=None
        for j in range(m.end()-1, len(text)):
            if text[j]=='{': d+=1
            elif text[j]=='}':
                d-=1
                if d==0: end=j+1; break
        if end is None: continue
        var=re.search(r'(\w+)\s*$', first)
        vs=set()
        if var and not first.startswith('struct ') and '*' in first:
            vs.add(var.group(1))
        body=text[m.start():end]
        # Flatten every variable of a flat typedef, not just the parameter --
        # collision handlers take `struct Body*` and derive the real entity into
        # a local (`Projectile32* self = ...`), which the parameter-only rule
        # left untouched.
        # Flat types are flat whether or not the `struct` keyword is written:
        # `struct Projectile* self = body->parent;` is just as flat as
        # `Projectile* p`. Match both spellings against the known flat set.
        FLAT=r'(?:Boss|Projectile|Weapon|CyberElf|Entity)'
        vs |= set(re.findall(r'\b(?:struct\s+)?%s\s*\*\s*(\w+)\s*=' % FLAT, body))
        vs |= set(re.findall(r'\b(?<!struct )[A-Z]\w*\s*\*\s*(\w+)\s*=', body))
        for v in vs:
            body=(body.replace('&%s->s'%v, '(struct Entity*)%s'%v)
                      .replace('(%s->s).'%v, '%s->'%v))
        out.append((m.start(), end, body))
    for st,en,body in reversed(out):
        text = text[:st] + body + text[en:]
    return text
s = flatten_flat_params(s)

# correct any prototype whose return type disagrees with its definition
for m in list(re.finditer(r'^([A-Za-z_][\w \*]*?)\b(\w+)\(([^;{)]*)\)\s*\{',s,re.M)):
    nm, dret = m.group(2), m.group(1).strip()
    if nm in protos and protos[nm][0] != dret:
        s=re.sub(r'^%s\s+%s\(' % (re.escape(protos[nm][0]), re.escape(nm)),
                 '%s %s(' % (dret, nm), s, count=1, flags=re.M)
io.open(f,'w',encoding='utf-8',newline='').write(s)
PY
bash $S/fixdecls.sh "$UPSRC" "$FORK_SRC" >/dev/null 2>&1

# addresses/sizes for the functions this inc used to hold
python3 - "$INC" > /tmp/spec.txt <<'PY'
import re,subprocess,sys
inc=sys.argv[1]
txt=subprocess.run(['git','show','upstream/dev:'+inc],capture_output=True).stdout.decode('utf-8','replace')
parts=re.split(r'\n\s*thumb_func_start\s+(\S+)\n', txt)
seq=[]
for i in range(1,len(parts),2):
    m=re.search(r'@ (0x[0-9A-Fa-f]{8})', parts[i+1])
    if m:
        seq.append((parts[i],int(m.group(1),16)))
        continue
    # No address comment: recover it from the name. Skipping these silently
    # makes the PREVIOUS function's size span several functions, which reads
    # as a huge bogus size mismatch.
    m2=re.search(r'_([0-9a-fA-F]{8})$', parts[i])
    if m2: seq.append((parts[i],int(m2.group(1),16)))
seq.sort(key=lambda t:t[1])
for k,(n,a) in enumerate(seq):
    if k+1<len(seq): print('%s:%08X:%X'%(n,a,seq[k+1][1]-a))
PY
SPECS=$(for f in $KEEP; do grep "^$f:" /tmp/spec.txt; done | tr '\n' ' ')
python3 $S/verify_up.py "$UPSRC" $SPECS 2>&1 | tee /tmp/vres.txt | grep -v MATCH | head -6
echo "   VERIFIED $(grep -c MATCH /tmp/vres.txt) of $(echo $SPECS | wc -w)"
grep MATCH /tmp/vres.txt | awk '{print $1}' > /tmp/ok.txt
