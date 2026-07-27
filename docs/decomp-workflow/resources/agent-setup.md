# Our the agent + decomp setup (rmz3 / agbcc)

Written for other agent users doing GBA-era matching decomp. Model matters
far less than harness: the whole trick is giving the agent a **verification loop
it can run itself**, and **memory that compounds across sessions**.

## The core loop (this is 80% of it)

One script: compile ONE .c with the exact retail toolchain, objdump-diff ONE
function against the proven-matching object, print instr counts + diff.

    tools/mdiff.sh <src.c> <function> [MODERN]

Rules baked in from painful lessons:
- Guard empty compiles (a failed compile diffs two empty dumps = fake match).
- Print `[cur=N exp=M instrs]` — size parity first, then encodings.
- Filter cosmetic label diffs; normalize resolved-vs-reloc `bl`s.
- The FINAL arbiter is raw bytes: `objdump -s -j .text` both objects and
  eyeball that every differing word is a reloc/pool word. Disassembly framing
  can produce false "real diffs" (we rolled back a correct match once
  because of this).

the agent runs this loop dozens of times per function. Without it you get
"looks plausible" C; with it you get byte-proofs.

## Memory (why week 2 goes faster than week 1)

Persistent memory dir (survives across sessions) holding:
- **An idioms catalog** — every construct that cracked a match gets recorded:
  `register T x asm("rN")` pins for register ties, chained `a=b=c=x`
  assignments, bitfield shift-extract forms, switch dispatch shapes,
  struct-field naming maps. Next function that smells the same: look it up.
- **A resume-state note** — what's running, what's proven, what's falsified.
  Sessions pick up mid-thought instead of rediscovering.
- **Negative results** — "these 20 holdouts resist X and Y for reason Z" is
  as valuable as a match; it stops repeat work forever.

## Pipeline for fresh functions (the throughput path)

1. **m2c first drafts** — m2c supports GBA (`--target arm-gcc-c`). We batch
   it over every remaining asm file: 1,861 drafts from 616 asm includes at a
   98% success rate (driver: tools/m2c_drafts.py).
2. **Idiom normalizer** — a post-pass rewriting m2c output into project
   idioms: `arg0`→`p`, raw offsets→named fields, `*0x343FD+0x269EC3`→`LCG()`,
   `SetMotion(p,0xNNMM)`→`SetSpriteAnimation(p, MOTION(...))`. This is what
   makes the result NOT look like shit — the draft arrives already speaking
   the project's language.
3. **Triage** — score drafts (unknown types, gotos, raw offsets, size) and
   work best-first (tools/draft_triage.py → WORKLIST.md).
4. **Close with mdiff loop** + idioms catalog.

Matched output quality comes from steps 2-4, not from massaging random C
until the differ goes green. Understand-then-match beats permute-then-pray.

## The permuter: last resort, seeded only

decomp-permuter from plain C is nearly useless on register-allocation ties
(3,000 iterations, zero improvement on a 1-copy diff). It only earns its
CPU when seeded with an **engineered basin** — a source form that already
materializes the target's weird structure (copy-pins, derived-value copies).
Also: its sandbox strips `__attribute__((packed))`, so packed-struct readers
FALSE-match — always re-verify any permuter "improvement" in the real build.

## Corpus mining (the underrated superpower)

When codegen resists, don't guess — search proven examples:
- Index every matched function's asm in YOUR repo + a same-compiler sibling
  project (for agbcc: pokeruby). Query by instruction regex, look up the C
  that produced the pattern (tools/pattern_index.py).
- This found in one afternoon what 48h of permuter search didn't: the exact
  C construct that makes agbcc emit an r8 reload base, and the
  derived-variable shape that survives CSE as a register copy.

## Verification discipline (non-negotiable)

- Never ship on % match. Byte-verify: size, per-function encodings, symbol
  spans, and reloc names joined on offset (same-name relocs can still be
  WRONG — we caught a swapped-allocator bug that way).
- Force-rebuild before trusting any .o; stale objects lie.
- Compiler diagnostics ≠ warnings only: agbcc EMITS partial code past some
  errors — hard-fail the loop on any non-warning diagnostic.

## What a session looks like

the agent CLI (this repo uses Fable 5, but the harness is the leverage), with:
memory dir + mdiff loop + worklist. Background: permuters on engineered
seeds, batch jobs (m2c runs, corpus scans) as long-running tasks that notify.
Every finding — positive or negative — lands in memory before the session
ends. Two weeks in, the catalog answers half the new questions before they
are asked.
