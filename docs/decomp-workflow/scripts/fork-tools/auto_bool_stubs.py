#!/usr/bin/env python3
"""Automate extracting bool8-returning-TRUE stubs from a .inc file.

Usage:
  auto_bool_stubs.py <c_path> <inc_path> <fn1> [<fn2> ...]

- Runs split_inc_multi on the .inc with the listed functions
- Patches the .c to replace its INCASM("inc_path") with:
    INCASM("base_p1.inc");
    bool8 fn1(struct ...) { return TRUE; }
    INCASM("base_p2.inc");
    ...
- Auto-detects the param type from the existing forward decl
- Auto-rewrites `void fnN(...)` forward decls to bool8 and adds
  (FuncType)fnN casts inside any sUpdates/PTR_ARRAY tables
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

# Verify the .c has exactly one INCASM matching the .inc
c_text = c_path.read_text(encoding="utf-8")
inc_rel = str(inc_path).replace("\\", "/")
incasm_re = re.compile(r'INCASM\("(' + re.escape(inc_rel) + r')"\);')
matches = incasm_re.findall(c_text)
if len(matches) != 1:
    sys.exit(f"expected exactly one INCASM({inc_rel!r}) in {c_path}, found {len(matches)}")

# Detect param type from one of the existing forward decls (or default to struct Enemy*)
param_decl = "struct Enemy* p"
for fn in fns:
    m = re.search(r"(?:void|bool8)\s+" + fn + r"\s*\(([^)]+)\)\s*;", c_text)
    if m:
        param_decl = m.group(1).strip()
        break

# Split the inc
script = Path(__file__).parent / "split_inc_multi.py"
proc = subprocess.run(
    [sys.executable, str(script), str(inc_path), *fns],
    capture_output=True, text=True, check=True
)
parts = [Path(p.strip()) for p in proc.stdout.strip().split("\n") if p.strip()]

# Build replacement block
base = inc_path.with_suffix("")
relbase = str(base).replace("\\", "/")
lines = [f'INCASM("{relbase}_p1.inc");']
for i, fn in enumerate(fns, 1):
    lines.append("")
    lines.append(f"bool8 {fn}({param_decl}) {{ return TRUE; }}")
    lines.append("")
    lines.append(f'INCASM("{relbase}_p{i+1}.inc");')
block = "\n".join(lines)

# Replace the INCASM in .c
new_c = incasm_re.sub(lambda m_: block, c_text, count=1)

# Auto-rewrite forward decls: void fnN(...)  -> bool8 fnN(...)
for fn in fns:
    new_c = re.sub(
        r"\bvoid\s+" + fn + r"\b(\s*\([^)]*\)\s*;)",
        r"bool8 " + fn + r"\1",
        new_c,
    )

# Auto-add (TypeName)fn casts in tables: find usages within {...} arrays
# Strategy: in any line that's `    fnN,` inside a `const SomeType array[] = {...}`,
# add a cast based on the declared array type. We look for the type by scanning back.
def add_cast_in_tables(text, fn, c_path_name):
    # Find array declarations using each fn as a bare identifier
    # General pattern: "<TYPE> name[<N>] = {"  followed by entries until "};"
    out = text
    arr_re = re.compile(
        r"(const\s+(\w+)\s+\w+\s*\[[^\]]*\]\s*=\s*\{)([^}]*?)(\};)",
        re.DOTALL,
    )
    def repl(m):
        head, type_name, body, tail = m.groups()
        # if fn appears bare (not already inside a cast), inject the cast
        new_body = re.sub(
            r"(?<![A-Za-z0-9_\)])" + re.escape(fn) + r"\b(?!\s*\()",
            f"({type_name}){fn}",
            body,
        )
        return head + new_body + tail
    return arr_re.sub(repl, out)

for fn in fns:
    new_c = add_cast_in_tables(new_c, fn, c_path.name)

c_path.write_text(new_c, encoding="utf-8")
print(f"patched {c_path}")
print(f"  inc parts: {len(parts)}")
