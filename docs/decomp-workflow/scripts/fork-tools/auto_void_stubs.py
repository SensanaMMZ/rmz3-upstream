#!/usr/bin/env python3
"""Automate extracting empty void stubs from a .inc file.

Usage:
  auto_void_stubs.py <c_path> <inc_path> <fn1> [<fn2> ...]

Splits the .inc at each function and inserts `void fnN(<param>) {}`
between the new INCASM parts. Param type detected from existing
forward decl, defaults to `struct Enemy*`.
"""
import re
import sys
import subprocess
from pathlib import Path

c_path = Path(sys.argv[1])
inc_path = Path(sys.argv[2])
fns = sys.argv[3:]
if not fns:
    sys.exit("need at least one fn")

c_text = c_path.read_text(encoding="utf-8")
inc_rel = str(inc_path).replace("\\", "/")
incasm_re = re.compile(r'INCASM\("(' + re.escape(inc_rel) + r')"\);')
matches = incasm_re.findall(c_text)
if len(matches) != 1:
    sys.exit(f"expected exactly one INCASM({inc_rel!r}) in {c_path}, found {len(matches)}")

# Detect param decl
param_decl = "struct Enemy* p"
for fn in fns:
    m = re.search(r"(?:void|bool8)\s+" + fn + r"\s*\(([^)]+)\)\s*;", c_text)
    if m:
        param_decl = m.group(1).strip()
        break

script = Path(__file__).parent / "split_inc_multi.py"
proc = subprocess.run(
    [sys.executable, str(script), str(inc_path), *fns],
    capture_output=True, text=True, check=True
)
parts = [Path(p.strip()) for p in proc.stdout.strip().split("\n") if p.strip()]

base = inc_path.with_suffix("")
relbase = str(base).replace("\\", "/")
lines = [f'INCASM("{relbase}_p1.inc");']
for i, fn in enumerate(fns, 1):
    lines.append("")
    lines.append(f"void {fn}({param_decl}) {{}}")
    lines.append("")
    lines.append(f'INCASM("{relbase}_p{i+1}.inc");')
block = "\n".join(lines)
new_c = incasm_re.sub(lambda m_: block, c_text, count=1)
c_path.write_text(new_c, encoding="utf-8")
print(f"patched {c_path}")
print(f"  inc parts: {len(parts)}")
