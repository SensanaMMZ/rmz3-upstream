#!/usr/bin/env python3
import os
# List functions that are genuine C upstream (mmzret/rmz3) but still asm here,
# i.e. portable candidates. Auto-excludes ones already ported (they become local C)
# and NAKED/asm-bodied upstream functions (asm there too). Regenerate the worklist
# anytime with:  py tools/list_portable.py [path-to-upstream-clone]
import re, glob, os, sys

UP = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('RMZ3_WT', '../rmz3-up')
LO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

defre = re.compile(r'^(?:NAKED\s+|static\s+|inline\s+)*[A-Za-z_][\w\s\*]*?\b([A-Za-z_]\w+)\s*\([^;{]*\)\s*\{?\s*$')

def c_defs(root, real_only=False):
    out = {}
    for f in glob.glob(os.path.join(root, "src", "**", "*.c"), recursive=True):
        lines = open(f, encoding="utf-8", errors="ignore").read().split("\n")
        for i, ln in enumerate(lines):
            if ln.endswith(';') or ln.strip().startswith(('//', '*', '/*')):
                continue
            m = defre.match(ln)
            if not m:
                continue
            naked = 'NAKED' in ln
            bodyi = i if ln.rstrip().endswith('{') else None
            if bodyi is None:
                for j in range(i + 1, min(i + 3, len(lines))):
                    s = lines[j].strip()
                    if s == '':
                        continue
                    if s.startswith('{'):
                        bodyi = j
                    break
            if bodyi is None:
                continue
            if real_only and (naked or re.search(r'\basm\s*\(', "\n".join(lines[bodyi:bodyi + 4]))):
                continue
            out[m.group(1)] = os.path.relpath(f, root).replace(os.sep, '/')
    return out

def asm_funcs(root):
    n = set()
    for f in glob.glob(os.path.join(root, "asm", "**", "*.inc"), recursive=True):
        for m in re.finditer(r'thumb_func_start\s+(\S+)', open(f, encoding="utf-8", errors="ignore").read()):
            n.add(m.group(1))
    return n

up = c_defs(UP, real_only=True)
lo = set(c_defs(LO))
lo_asm = asm_funcs(LO)
rem = sorted((set(up) & lo_asm) - lo, key=lambda n: (up[n], n))
print(f"# {len(rem)} portable functions still asm here (C upstream):")
cur = None
for n in rem:
    if up[n] != cur:
        cur = up[n]
        print(f"\n## {cur}")
    print(f"  {n}")
