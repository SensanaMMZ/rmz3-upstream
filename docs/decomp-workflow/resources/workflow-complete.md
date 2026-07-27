# The complete rmz3 workflow, beginning to end

Written 2026-07-23 at the user's request: everything about how this project
runs, in one place. Companions: `notes/matching-workflow.md` (the per-match
procedure + byte-diff evidence table), `notes/backlog-truth.md`
(per-function findings), `notes/urls-of-gba-decomps/extracted-practices.md`
(cross-project knowledge base), `notes/urls-of-gba-decomps/fe8j-playbook.md`
(the 100%-JP-decomp lever catalog and doctrine).

## 0. Ground truth and environment

- **The only truth is the ROM**: `baseimg.gba`, sha1
  `ff7a801776dc76e6d8c7ef73a6660ae732934a3f`. A function is matched when
  the full ROM rebuilds to that hash with the function as real C.
  `expected/build/rmz3/**` holds the sha1-proven objects and generated .s.
- **Toolchain**: agbcc (GCC 2.9 Thumb, pret family — accepts `-fhex-asm`,
  `-fprologue-bugfix`, `-foptimize-comparisons`, `-ffix-debug-line`) +
  old_agbcc + devkitARM binutils. Base flags `-mthumb-interwork -Wimplicit
  -Wparentheses -O2 -fshort-enums -fhex-asm`; **always read the per-file
  overrides at the bottom of `makefile` first** (mmbn4.o = `-O
  -mno-thumb-interwork`, agb_sram.o = `-O -mthumb-interwork`, m4a.o =
  old_agbcc) — probing a holdout with the wrong flags produced a whole
  wrong conclusion once.
- **Build recipe (Windows)**: `make -j4 DEVKITARM=/c/devkitPro/devkitARM`
  (profile's DEVKITARM is a Linux path). After any branch switch: touch
  `tools/{gbagfx,mid2agb,preproc,scaninc,...}/*.exe` (host tools rebuild
  into -Werror failures on modern g++ — devkitPro's MSYS gcc has no
  system headers at all) and delete stale `build/**/*.d`. Never leave
  `_*.py`/`_*.png` scraps in the repo root (a makefile `find` shell-expands
  them). Never edit files while make runs. Windows Store Python shows up
  as `python3.11` in process lists; MSYS `/tmp` paths are invisible to
  Windows Python — keep scratch under `build/scratch/`.
- **Symbol maps**: `tools/ghidra/rom_symbols.txt` (5,835 functions,
  NAME ADDR SIZE) + `rom_data_symbols.txt`, built by
  `tools/ghidra/map_symbols.py` from the linker map ∪ per-object symtabs
  (recovers statics) ∪ asm labels. `tools/ghidra/build_sym_elf.py` writes
  the hand-made symbolized ELF Ghidra needs (st_size set, Thumb via odd
  st_value, RAM regions as NOBITS).

## 1. Knowing what's left (run these, don't trust stale lists)

- `python3 tools/progress.py` — four buckets by count and bytes:
  declared-pure (INCCODE stubs, no C), declared-withc (NON_MATCH with a
  MODERN C draft), **undeclared-asm (functions living in asm/ with no C
  stub at all — 1,864 fns / 52% of code bytes, the real bulk)**, matched C.
- `python3 tools/classify_holdouts.py` — regenerates the declared holdout
  lists (`notes/holdouts-{pure,withc}.md`).
- `python3 tools/dup_scan.py` — **run this first when picking targets**:
  clusters every ROM function by exact / bl-masked / pool-masked bytes.
  A holdout or asm-resident function in a cluster with matched C is a
  near-free match (reuse the body, remap callees). Found the ghost-init
  family (4 matches) and the FUN_080e58bc/FUN_080e964c leads. It excludes
  ambiguous static names and says so — check those by address by hand.

## 2. Picking a target

Priority order: (1) dup-scan free candidates; (2) smallest pure stubs
(cheapest matches — 24–232 bytes so far); (3) family members of a solved
codegen puzzle (the pool-anchor recipe → the gOverworld+0x1DC hazard
cluster); (4) withc near-misses whose root-cause tag matches a new lever.
Before attacking a small stub as standalone code, sanity-check it isn't a
false function boundary (out-of-range branches make agbcc emit `bl`,
splitting one function into two symbols).

## 3. Reconstructing the C

- `python3 tools/ghidra/batch_decompile.py` → `build/ghidra-drafts/*.c`,
  then `python3 tools/ghidra/resolve_pool_refs.py` (names the DAT_08xxxxxx
  pool literals). Cross-check the shape against m2c; a disagreement means
  one of them mis-decoded control flow.
- `bash tools/genctx.sh` builds `build/ctx.c` (preprocessed context) for
  decomp.me/cexplore/m2c.
- **Probe-TU method** (how FlushOAM fell): before contorting the real
  function, write a tiny standalone TU reproducing the questionable
  codegen (pool form, fold, extension) and compile just it —
  `arm-none-eabi-cpp -nostdinc -undef -std=gnu89 probe.c | agbcc <flags>`.
  GCC 2.9 rejects `//` comments; always cpp first. This answers "what
  source shape produces this instruction form" in seconds.

## 4. The compile-and-compare loop

- Compile the file with **its own** flags (step 0!). For dual-form files
  the C body compiles at `-DMODERN=1`; a finished match replaces the
  NON_MATCH/INCCODE entirely (remember: NON_MATCH implies naked at
  MODERN=0 — removing a dual-form MUST remove the marker).
- **Byte-diff, never disassembly-diff**: `python3 tools/fnbytes.py ours.o
  expected/.../file.o FUNC --diff`. INCCODE'd functions are raw data in
  expected objects (no symbol size) — fall back to comparing against ROM
  bytes at the symbol's address with relocation masking (mask words where
  ours is 0/addend and target is an 02–09 address; remember ARM REL
  relocations keep the addend in place, so `symbol+0x400` shows as
  `0x00000400` + R_ARM_ABS32).
- Read the diff as evidence (table in matching-workflow.md): epilogue pop
  register = return-value liveness; lsls/lsrs #24 = u8 truncation; asr vs
  lsr = signedness (see fe8j checklist); bl byte diffs = check relocations
  before calling them real; single pool reloc with addend = anchor-pointer
  source shape.
- objdiff (root `objdiff.json`) for visual diffing; decomp-permuter (root
  `permuter_settings.toml`) for search — but the fe8j/Mizuchi evidence
  says permuter plateaus are vocabulary limits, not proof of
  impossibility; byte-diff reasoning outperforms it on agbcc.

## 5. The escalation ladder for a stubborn function

1. **Flag sweep with stock binaries**: {-O0, -O1/-O, -O2, -Os} ×
   {agbcc, old_agbcc} × {-fprologue-bugfix, -foptimize-comparisons,
   -fno-gcse, -fno-strength-reduce}, plus -mno-thumb-interwork where the
   makefile says so. Per-file flags are precedented in every mature
   decomp (fe8j ships six kinds).
2. **Pure-C nudge catalog** (extracted-practices §3): self-assign,
   param→local copy, `int zero = 0`, explicit narrow casts, literal shift
   pairs, `do{}while(0)` separators, duplicated case labels, kept
   identities, temp-pointer increments, loop-shape swaps.
3. **fe8j P-levers** (fe8j-playbook §2–3): signedness casts at shift
   sites, int-local widening, shifted-domain counters, BB separators,
   readback shapes, declaration-order plays.
4. **GNU-extension escapes** (extracted-practices §4) — only with a
   comment, only when the honest form is proven unreachable; our repo
   convention prefers keeping honest asm (INCCODE) over shipping
   fakematches upstream.
5. **Post to decomp.me** (tools/scratch_up.py; www.decomp.me + browser UA;
   divided syntax; claim scratches promptly — anonymous ones expire) and
   annotate the source/notes with the scratch URL + root-cause tag
   (`regalloc-tie`, `pool-anchor`, `jump-thread`, `combine-shift`,
   `sign-extension`). Community forks crack these (readKeyInput fell to
   TsilaAllaoui's fork). Verify any community score-0 against the real
   ABI + linked ROM before accepting.
6. **Park it honestly**: record the attempts and the blocker in
   backlog-truth.md (negative results are as valuable as matches — fe8j
   keeps a decisions log for exactly this).

## 6. Verification discipline

- ROM sha1 after every match, before every commit claiming one.
- **A check that can pass without doing its work is not a check**:
  calibrate comparisons both directions (known-identical AND
  known-different); make detectors print their own coverage; empty
  output + exit 0 is the classic false PASS (bit us three times: empty
  objcopy pipes, name-collision holdout labels, `src/**/*.c` pathspec
  silently skipping top-level files).
- Static name collisions: symbol map renames duplicates — never match a
  holdout to a map entry by bare name without checking uniqueness.

## 7. Shipping

- **Local commits**: project author identity, plain factual messages. Run the
  shared-branch content check before every push. Credentials are pasted
  per-session and revoked after.
- **Upstream PR on every match** (standing directive): work in the
  worktree `../rmz3-pr-ghost28` (or a fresh one) — never branch-switch the
  main checkout. `git checkout -b contrib/<name> upstream/dev`; apply the
  match using **their** names/macros/style (check their file first — they
  renamed e.g. InitNonAffineMotion→EnableSpriteAnimation_Normal, use
  RANDOM(), Coords32, OAM_SIZE); compile their file with their exact
  pipeline (arm-none-eabi-cpp CPPFLAGS | agbcc CFLAGS incl. -Werror, plus
  the `.align 2,0` append) and fnbytes-verify against our sha1-proven
  object; commit (same authorship rules, casual human message); push the
  branch to SensanaMMZ/rmz3-upstream; open the PR via API with base:dev,
  body written from a JSON file (inline JSON breaks on shell quoting).
- **Batching**: related functions (a family) can share one branch/PR;
  unrelated matches get separate PRs.

## 8. Knowledge upkeep (after every session)

- New codegen fact → matching-workflow.md's evidence table or
  extracted-practices.md; retractions and negative A/Bs recorded, never
  deleted.
- Session state → the project memory's `project_resume_state.md` (newest
  entry marked as the pickup point; include unpushed work, open PRs,
  claimed scratches, the next queue, and any credential still alive).
- decomp.me scratches tracked in notes/decompme/ with claim links.
- Watch open upstream PRs (#49–#52+) for review feedback; watch claimed
  scratches for community forks.

## 9. Tool inventory (one line each)

- `tools/dup_scan.py` — ROM-wide duplicate clusters; free-match finder.
- `tools/progress.py` — the four-bucket truth (--csv for tracking).
- `tools/classify_holdouts.py` — declared holdout lists.
- `tools/fnbytes.py` — byte-exact function compare (--diff gates scripts).
- `tools/ghidra/{map_symbols,build_sym_elf,batch_decompile,resolve_pool_refs}.py`
  — the Ghidra harness.
- `tools/genctx.sh` — one-command scratch context.
- `tools/detect_handwritten_asm.py` — flags never-was-C functions (4 known).
- `tools/verify_rank.sh` / `tools/objdiff_rank.sh` — MODERN=1 ranking
  (trust match% only for declared NON_MATCH/NAKED).
- `tools/check_shared_branch.sh` — provenance/identity guard.
- `tools/refresh_memory_snapshot.sh` — scrubbed memory snapshot publisher.
- `tools/scratch_up.py` — decomp.me scratch poster.
- root `objdiff.json`, `permuter_settings.toml` — reproducible tool configs.
- Fork compilers for experiments (rebuild recipe in project memory):
  Dream-Atelier legacy-works old_agbcc (`-ftst` verified) — build under
  `/c/msys64/usr/bin/bash -lc` with PATH=/mingw64/bin; `-j4` races on
  genrtl.h for the new compiler (use -j1).
