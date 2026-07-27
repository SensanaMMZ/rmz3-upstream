# Ghidra + pyghidra-mcp — second decompiler for the hard holdouts

Set up 2026-07-20 (harness-roadmap #2). A free alternative to IDA that decodes
exactly what m2c can't: PC-relative literals (m2c emits `M2C_ERROR`) and complex
control flow. Use it as a second opinion on the ~6 structural reconstructions.

## Installed

- **Ghidra 12.1.2** — install anywhere; point `GHIDRA_INSTALL_DIR` at it
- **JDK 21.0.11** (Temurin) — point `JAVA_HOME` at it
  (Ghidra 12.x wants JDK 21; the system JDK 25 is too new.)
- **pyghidra 3.1.0** + **pyghidra-mcp 0.2.3** — `pip install pyghidra-mcp`

## MCP wiring

`.mcp.json` (project root) registers a `pyghidra` MCP server that imports and
analyzes `baseimg.gba` on start, exposing decompile/disasm/xref tools. It sets
`GHIDRA_INSTALL_DIR` and `JAVA_HOME` in its env. **First start is slow** — the
8 MB ROM gets a full analysis pass (a few minutes); pyghidra caches the project
so later starts are fast. Restart the agent CLI to pick up the server.

## Loading a GBA ROM correctly

The raw `.gba` is not an ELF, so:
- language **`ARM:LE:32:v4t`** (ARMv4t little-endian — the GBA CPU),
- **rebase to `0x08000000`** (`setImageBase`), the ROM's mapped address,
- for a Thumb function, set the **`TMode`** context register = 1 at its entry
  before `CreateFunctionCmd`, or Ghidra decodes it as ARM.

`notes/../tmp/gh_test.py` is a standalone decompile-by-address harness that does
all of this; `tools/ghidra_decompile.py` is the reusable version.

## Where it helps (and doesn't)

- **Good for:** structural reconstructions m2c couldn't finish —
  InitMotionLocation (runtime loop counts), IsInHazard (the object-array
  indexing), FlushOAM (the DMA loop). Ghidra's pseudo-C shows the real control
  flow and resolves the pool literals.
- **Not for:** the register-allocation ties (readKeyInput-class, CountRodButton,
  onRod). Ghidra decompiles *semantics*, not agbcc's register choices — the
  instrumented compiler is the tool for those, not Ghidra.
- **Cross-check rule (from fireemblem8j):** trust a reconstruction most when m2c
  and Ghidra agree on the structure; then match it with our mdiff loop.

## Symbols

To make Ghidra's output name things instead of `FUN_08xxxxxx`, apply our symbol
map after import (function addresses are already encoded in most `FUN_0Xxxxxxx`
names). A `sym.txt` generated from the linker map would let it resolve globals.
