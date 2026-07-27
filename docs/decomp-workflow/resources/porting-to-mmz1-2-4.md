# Porting the rmz3 decompilation to Mega Man Zero 1, 2, and 4

*Hand-off doc for an agent bootstrapping decomps of the sibling GBA games, leveraging the
mature byte-perfect rmz3 (Mega Man Zero 3) project. Written by the rmz3 decomp agent.*

Items marked **VERIFY** are facts I don't have first-hand from the rmz3 repo and the receiving
agent must confirm before relying on them.

---

## 0. TL;DR

- MMZ1/2/3/4 are the **same Inti Creates engine iterated across 2002–2005**. rmz3 (this repo) is a
  mature, byte-perfect decompilation. **~80–90% of the *methodology*, tooling, engine headers,
  macros, and accumulated codegen-idiom knowledge port directly.** Per-game work is (a) a mostly
  mechanical bootstrap (disassembly split, data extraction, symbol maps) and (b) matching
  game-specific functions — **most of which have a near-twin already solved in rmz3.**
- The single biggest force multiplier: **reuse rmz3's `include/`, `tools/`, the dual-form recipe,
  the permuter harness, and the idiom notes.** These took the rmz3 effort many months to
  accumulate; you inherit them for free.
- Do **not** write a line of match code until you have (1) a fully-linking non-matching split and
  (2) proof the compiler reproduces a handful of leaf functions byte-exact. A wrong compiler
  invalidates everything downstream.

---

## 1. What you inherit from rmz3 (the head start)

### Toolchain (near-certainly identical across the series — but VERIFY per game)
- **agbcc** — pret's GCC 2.9 Thumb-1 compiler, which reproduces rmz3's retail codegen
  exactly. All four games are
  the same SDK era, so agbcc is the prime candidate for each.
- **devkitARM** — `arm-none-eabi-as` / `ld` / `objcopy` for assembly, linking, and binary output.
- Build pipeline (per translation unit):
  `cpp -DMODERN=0 -I tools/agbcc ... | agbcc -mthumb-interwork -O2 -fhex-asm ... | arm-none-eabi-as`,
  linked with `ld_script.ld`, then `objcopy -O binary`, then a SHA1 check via `make compare`.

### Reusable source assets (copy + adapt)
- **`include/`** — the entire engine model. This is the crown jewel:
  - `struct Entity` (coord@0x54, d@0x5c, unk_coord@0x64, mode[4]@0xc, work[4]@0x10, flags@0xa,
    onUpdate@0x14, spr@0x34, unk_28@0x28, motion@0x6c), `Object` = Entity+Body, `struct Body`.
  - Routine-table model: `ENTITY_INIT/UPDATE/DIE/DISAPPEAR/EXIT`, per-type FnTables, `EntityHeader`
    (arr/type/size/length/remaining/…), `AllocEntityFirst`, per-type Create fns.
  - `struct Sprite` + `struct EntityOamData` (bitfields), `struct Coord`, motion/collision/blink
    systems, `gJoypad`/`struct KeyState`, `gVideoRegBuffer`/`gWindowRegBuffer` GPU buffers, palette
    manager, text/string tables (`STRING(n)` = `&gStringData[StringOfsTable[n]]`).
- **`include/entity/macros.h`** — `SET_XFLIP`/`SET_YFLIP`/`INIT_BODY`/`EXIT_BODY`/`SET_*_ROUTINE`.
- **`tools/`**:
  - `diff2.sh` — objdiff-style per-function %-match (the core inner-loop tool).
  - `permuter-setup/` — a working decomp-permuter harness (`setup_fn.sh`, candidate carving,
    designated-init fixups, Windows-path handling).
  - The **dual-form recipe**: carve retail asm → `asm/wip/<fn>.inc`; replace the NAKED body with
    `NON_MATCH foo(){ #if MODERN <clean C> #else INCCODE("asm/wip/<fn>.inc"); #endif }`. Lets you
    commit a readable, correct decode for functions that don't byte-match, while keeping the ROM
    byte-perfect.
- **The idiom knowledge** — the accumulated agbcc-codegen lore (see the rmz3 agent's memory files
  and commit messages): bitfield shift-extracts, base+disp vs folded-literal struct access,
  reload-blink CSE, retail-suboptimal flag-OR expansion, the coalescer/register-tie theorem +
  litmus, non-void-return register shift, pointer-temp anti-reassociation, etc. **This is the most
  valuable transfer** — it's the difference between hours and minutes per function.

---

## 2. What's game-specific (the actual per-game work)

- **ROM identity** — each game has its own SHA1 and region. **VERIFY** the exact hash and pick a
  region consistent with any upstream (rmz3 here is JP `ff7a801776dc76e6d8c7ef73a6660ae732934a3f`).
  JP vs US/EU differ in text and sometimes code layout.
- **Compiler version** — **VERIFY per game.** Same SDK era, but MMZ1 (2002) and MMZ4 (2005) may use
  a slightly different agbcc build/flags than MMZ3 (2004). *Litmus:* after splitting, pick 3–5
  trivial leaf functions and confirm agbcc reproduces them byte-exact with the rmz3 flags. If not,
  find the right agbcc build/flags *before doing anything else.*
- **Disassembly split** — each game needs its own splat (or mmzret) config, ROM/RAM symbol map, and
  `.inc` layout. Mechanical but large.
- **Data extraction** — graphics, tilemaps, sound (M4A/MP2k), level/entity/motion/collision tables.
  rmz3's extraction scripts port with path/offset changes; the ROM must rebuild byte-perfect from
  the extracted sources.
- **Struct deltas** — the engine *evolved*: absolute offsets shift between games (e.g. rmz3's
  `GameState.sceneState`@0xDCC and the player pointer@0x64AC are rmz3-specific constants). Expect to
  re-derive offsets per game, but the *shapes* carry over almost unchanged.
- **Content code** — bosses/enemies/stages differ, but the *patterns* recur (VFX callbacks;
  boss alive-check + element-slot dispatch; range-classifiers; minigame handlers; menu focus
  loops), so rmz3's matched functions are ready-made templates.

---

## 3. Bootstrap checklist (per game)

1. Confirm ROM (SHA1, region); place it at the standard path; wire up `make compare`.
2. Stand up agbcc + devkitARM. **Verify the compiler** on a handful of leaf functions (see §2).
   Do not proceed until byte-exact.
3. Disassemble + split (splat / mmzret tooling) into `asm/*.inc`; reach a fully-*linking*,
   non-matching build (everything `INCASM`/`INCBIN`'d) that produces a byte-identical ROM.
4. Port `include/` from rmz3; fix obvious struct/offset deltas as you touch each subsystem.
5. Port `tools/` — `diff2.sh`, `permuter-setup/`, carve scripts, and the dual-form macros
   (`NON_MATCH`, `INCCODE`, `#if MODERN`).
6. Extract data (graphics/sound/tables) until the ROM rebuilds byte-perfect from sources alone.
7. Start matching with the **leaf/util vein** (math, input, gpu-reg helpers, text, area-checkers).
   These are the most shared across games and give fast wins + toolchain confidence.
8. Then content, coarse→fine: VFX → solids → enemies → bosses/menus, always grepping rmz3 for a
   near-twin first.

---

## 4. Force multiplier: cross-reference rmz3 constantly

For almost any MMZ1/2/4 function there is a structurally similar (often near-identical) function
already solved in rmz3. Standard loop:

> identify the function's role → grep the rmz3 tree for the analog → copy its C structure +
> idioms → re-derive game-specific offsets/constants → build + `diff2.sh` → `make compare`.

This is *dramatically* faster than cold decompilation. Keep a checked-out rmz3 tree alongside the
target game purely as a reference corpus.

---

## 5. Walls to expect (pre-warned by rmz3)

- **Trig (`gSineTable`)** — a CSE wall; dual-form, don't grind.
- **Embedded mini-game / peripheral blobs** — rmz3 contains an mmbn4 e-reader port compiled with a
  non-standard *arg-preserving* ABI (`push {r0-r3}` / `pop {r0-r3,pc}`) that **no agbcc flag
  reproduces**. Expect at least one such compiler-environment wall per game; leave as asm / dual-form.
- **Register-allocation & scheduling ties / the coalescer wall** — the "redundant register spread"
  class. rmz3 has the theorem + a litmus test documented; resolve with the permuter (for the
  tractable low-reg/reorder ties) or dual-form (for the proven-dead r8-spread class).
- **Retail-suboptimal codegen** — folded flag-ORs (`flags |= DISPLAY|FLIPABLE` → `|3` vs retail's
  `|1;|2`), per-branch duplicated writes, etc. Clean C over-optimizes; dual-form these.

---

## 6. Existing community work — CHECK THIS FIRST

The Mega Man Zero / ZX decompilation community operates under the **`mmzret`** GitHub org (this rmz3
project derives from it). **Before bootstrapping anything**, check that org (and its Discord/wiki)
for: existing rmz1/2/4 repos or splat configs, shared symbol maps, the agreed toolchain/agbcc
version, and shared `include/`/`tools/`. **VERIFY** current state — efforts may already exist at
various maturities. Contributing into an existing scaffold beats a cold start; if a game already
has a linking split, skip §3.3–3.6 and go straight to matching.

---

## 7. Rough effort

- **Bootstrap (steps 1–6):** days-to-weeks of mostly-mechanical work per game, dominated by data
  extraction + symbol maps — *assuming the compiler is confirmed.*
- **Matching to byte-perfect:** a months-long, function-by-function effort per game, but heavily
  accelerated by rmz3 templates and idioms, and highly parallelizable across contributors/agents by
  subsystem. Treat it as a long-running project, not a sprint.

---

## 8. First-day plan for the receiving agent

1. Pick game + region; get the ROM SHA1; **check mmzret for prior art.**
2. Reach a linking, non-matching split that rebuilds a byte-identical ROM.
3. Verify agbcc on ~5 leaf functions (byte-exact or bust).
4. Match **one** trivial function end-to-end (e.g. an area-check or a simple getter) to prove the
   whole pipeline: build → `diff2.sh` MATCH → `make compare` OK.
5. Report back: compiler-verified (Y/N), split status, and the first byte-perfect function — then
   scale up along the leaf→content veins with rmz3 as the reference corpus.

---

### Appendix: rmz3 facts worth carrying over verbatim
- Always `rm -f` the `.o` and force-rebuild before trusting a diff/SHA (stale objects lie).
- Always `make compare` after a match — the isolated `diff2.sh` can read "MATCH modulo relocations"
  while a real layout/offset problem only shows in the full ROM.
- On Windows/MSYS mixed toolchains, normalize every path with `cygpath -m` before handing it to a
  native Windows binary (agbcc.exe / arm-none-eabi-as.exe).
- The dual-form MODERN branch must also *compile* under `-DMODERN=1` — verify it, don't just trust
  the INCCODE side.
