---
name: rmz-decomp
description: The complete matching-decompilation workflow for RMZ-series (and other agbcc/GBA) games — environment setup, target selection, C reconstruction with Ghidra/m2c, the byte-diff verification loop, the escalation ladder for stubborn functions, decomp.me delegation, upstreaming, cross-game bootstrap (rmz1/2/4), and knowledge upkeep. Use for any GBA matching-decomp task; the upstream-porting subset also lives in the rmz-decomp-port skill.
---

# RMZ matching-decomp — the complete workflow

Everything built for the rmz3 (Mega Man Zero 3) byte-perfect decomp,
packaged for reuse on the sibling games (rmz1/2/4 checkouts exist next to
the fork) and any agbcc-era project. The deep material lives in
`resources/` — this file is the map. Read the specific resource when you
reach that phase; don't front-load all of it.

## The one rule

**The only truth is the ROM.** A function is matched when the full ROM
rebuilds to the expected sha1 with the function as real C. Compiling
proves nothing about bytes; assembling nothing about size; linking
nothing about the ROM. Every claim names the stage that proved it.
A check that can pass without doing its work is not a check — calibrate
detectors both directions; empty output + exit 0 is the classic false PASS.

## Environment (once per machine/game)

- agbcc (GCC 2.9 Thumb, pret family) + old_agbcc + devkitARM binutils.
  Base flags `-mthumb-interwork -Wimplicit -Wparentheses -O2 -fshort-enums
  -fhex-asm` — but ALWAYS read the per-file overrides at the bottom of the
  makefile first (wrong flags once produced a whole wrong conclusion).
- agbcc does NOT preprocess: `//` comments are syntax errors, `#define`
  silently no-ops. Always `arm-none-eabi-cpp -nostdinc -undef -std=gnu89 |
  agbcc`. This bites in scratch kits, probe TUs, everywhere.
- Windows specifics, symbol maps, build recipe: resources/workflow-complete.md §0.
- Second decompiler: Ghidra via the pyghidra MCP server —
  resources/ghidra-mcp-setup.md (ARM:LE:32:v4t, rebase 0x08000000, TMode=1
  for Thumb). m2c and Ghidra disagreeing on shape = one of them mis-decoded
  control flow; that disagreement is signal, not noise.
- Agent harness philosophy (verification loop the agent can run itself +
  compounding memory): resources/agent-setup.md. The core loop is ONE
  script: `mdiff.sh <src.c> <function> [MODERN]` — compile one file with
  retail flags, diff one function, print instruction counts.

## The lifecycle (per function / per session)

1. **Know what's left** — run the counters, never trust stale lists
   (progress.py four buckets; dup_scan.py FIRST — duplicate clusters are
   near-free matches; classify_holdouts.py). workflow-complete.md §1.
   Stale-notes lesson: a candidate list from notes once contained an
   already-matched function; re-derive from the tree every time.
2. **Pick a target** — priority: dup-scan freebies → smallest pure stubs →
   family members of solved codegen puzzles → near-misses matching a new
   lever. Check for false function boundaries first. §2.
3. **Reconstruct** — Ghidra batch_decompile + resolve_pool_refs,
   cross-check m2c; genctx.sh for context; the probe-TU method for
   "what source shape produces this instruction form". §3.
4. **Compile-and-compare** — byte-diff, never disassembly-diff
   (fnbytes.py --diff; relocation masking rules). Read diffs as evidence:
   the table in resources/matching-workflow.md maps byte-diff patterns to
   source-level causes (epilogue pop = return liveness; lsls/lsrs #24 =
   u8 truncation; asr vs lsr = signedness; pool reloc + addend =
   anchor-pointer shape). §4.
5. **Escalate a stubborn function** in order: flag sweep → pure-C nudge
   catalog (resources/extracted-practices.md §3) → fe8j P-levers
   (resources/fe8j-playbook.md) → GNU-extension escapes (only commented,
   only when the honest form is proven unreachable) → post to decomp.me →
   park it honestly with a root-cause tag. §5 + resources/holdout-playbook.md.
   Root-cause tags: regalloc-tie, pool-anchor, jump-thread, combine-shift,
   sign-extension. Permuter plateaus are vocabulary limits, not proof of
   impossibility — byte-diff reasoning outperforms it on agbcc.
6. **decomp.me kits** — target asm + best C + context that compiles
   server-side. Gate locally with cpp → agbcc → assembler (all three), post
   with scratch_up.py, then INDEPENDENTLY verify success=True via
   `POST /api/scratch/<slug>/compile`. Claim promptly — anonymous scratches
   expire. Source fn name must equal the diff label. A reusable
   agbcc+assembler-clean context lives in the fork at
   notes/decompme/ctx-agbcc-clean.c (genctx output minus unnamed-varargs
   prototypes, leaked const defs, and __asm__/.incbin rodata).
7. **Upstream every match** — the full porting pipeline (carve, fixer
   chain, gates, CI byte-verify, PR hygiene, dedup, holdout/unclaimed
   accounting) is resources/upstream-porting.md with its scripts in
   scripts/upstream/. Follow the maintainer's structure policy
   (COLLISION_OBJECT_HDR flat splices, wrapper macros, typedefs).
8. **Knowledge upkeep** — new codegen facts into the evidence table;
   negative results recorded, never deleted; session state into project
   memory with the pickup point marked. §8.

## Starting a sibling game (rmz1/2/4)

resources/porting-to-mmz1-2-4.md is the hand-off doc: same Inti Creates
engine iterated 2002–2005; ~80–90% of methodology, tooling, headers, and
idiom knowledge ports directly. Bootstrap order: linking non-matching
split first, then prove the compiler on a handful of leaf functions
byte-exact BEFORE writing any match code. Most functions have a near-twin
already solved in rmz3 — the cross-reference corpus and dup-scan mindset
carry over whole.

## Knowledge sources

- resources/matching-workflow.md — per-match procedure + the byte-diff
  evidence table (the project's crown jewel).
- resources/extracted-practices.md — cross-project levers mined from
  mature GBA decomps; resources/fe8j-playbook.md — the 100%-JP-decomp
  lever catalog; resources/list-of-decomps.md — the repo list.
- The agbcc corpus (17 sibling decomps, checked out under
  ../decomp-corpus): before contorting a harness around an odd
  instruction, grep the corpus for it — someone usually solved it.
  Refresh weekly (decomp_crawl.py).
- resources/rank-verified.md + objdiff-ranking.md — why MODERN=1 rank% is
  only meaningful for declared NON_MATCH/NAKED functions.
- resources/handwritten-asm.md — functions that never were C (4 known);
  resources/dup-scan.md — the duplicate-cluster method.
- resources/harness-roadmap.md — what the harness still lacks, in order.

## Triage and debugging doctrine (the expensive lessons)

- Resolve a variable's type PER FUNCTION, never file-wide (prototypes at
  the top of a file shadow definitions and make "the fix did nothing").
- Restrictions fail CLOSED: an empty span list rewrites nothing.
- Never patch scripts through a bash heredoc (`\b` becomes backspace and
  regexes silently match nothing); sweep with repair_escapes.py after any
  scripted edit.
- One worktree = one writer; background jobs outlive TaskStop on Windows —
  ps + kill + verify zero; take an mkdir lock. Read result files only when
  written atomically (tmp + mv).
- Layout comments lie; compute offsets from declared types.
- Same name ≠ same function: a static copy in another TU can share the
  name of a still-asm global (homonyms). The ROM span between labels is
  the arbiter of which function you have.
- NAKED is not the only asm-body attribute (upstream also has WIP == naked);
  every guard alternation must include all of them.
- An "impossible" negative (every subset overflows) usually means per-FILE
  damage from your own tooling, not per-function impossibility — find the
  mechanism before declaring defeat.
- Check the branch before AND after acting; scripts and failed rebases
  move HEAD silently. Commit as soon as gates pass.
- State only what the check proves. Verify from the code, not notes.

## Scripts

- scripts/fork-tools/ — the decomp side: progress, dup_scan,
  classify_holdouts, fnbytes/fnsize, mdiff/diff/diff2, genctx, scratch_up,
  ghidra/ (map_symbols, build_sym_elf, batch_decompile, resolve_pool_refs),
  objdiff_rank + verify_rank, m2c_drafts, pattern_index, decomp_crawl,
  detect_handwritten_asm, lift_fn, probe_fn, flag/modern sweeps, carve and
  split helpers, auto stub generators, check_shared_branch,
  refresh_memory_snapshot.
- scripts/upstream/ — the 89 porting-pipeline scripts (see
  resources/upstream-porting.md for the chain order and gates). These are
  the path-generalized versions: set RMZ3_FORK and RMZ3_WT env vars.
