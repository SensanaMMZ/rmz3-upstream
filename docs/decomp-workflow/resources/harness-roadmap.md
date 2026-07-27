# Harness roadmap — lessons from fireemblem8j and other GBA decomp repos

Assessed the laqieer/fireemblem8j workflow docs (reverse-engineering.md,
tooling-investigation.md) plus the repos they cite (frog-adv-temple, kappa,
coddog, mizuchi) against our current setup. Below: what we already match, the
genuinely additive builds, and what we have that they don't.

## Where we already match or lead them

| Their tool | Purpose | Ours | Verdict |
|---|---|---|---|
| m2c `-t gba` seed-C | first drafts | `tools/m2c_drafts.py` — **batch** over all 616 incs (1,861 drafts) **+ idiom normalizer** | we lead (they run it per-function) |
| decomp-permuter (upstream) | matching | `tools/decomp-permuter` (upstream, not the stale fork) | match |
| asm-differ / objdiff | diffing | `tools/mdiff.sh` + `objdiff-cli.exe` present + raw-byte oracle | match |
| decompme new_scratch.sh | post scratches | `tools/scratch_up.py` (POST + claim link) | match |
| kappa AST-grep offset/STRUCT_PAD fixes | normalize decompiler output | our m2c idiom normalizer (offset→field, LCG, MOTION…) | match |
| frog-adv-temple playbook (peel-first, corpus-before-permuter, worktree, serial-integrator) | AI decomp method | `notes/holdout-playbook.md` + corpus mining + Workflow worktrees | **we independently arrived at the same patterns** |
| `make compare` oracle | truth | our byte-verify (size + per-fn + reloc-join) | match |

## What we have that they do NOT

- **Instrumented agbcc** (`tools/agbcc-debug/`, PR pret/agbcc#91) — the allocator
  explaining its own register choices. None of these repos have this; it is why
  we can *prove* a holdout unmatchable (beetank) instead of guessing.
- **Corpus pattern index** across our repo + pokeruby (`tools/pattern_index.py`,
  15k functions) — regex-searchable matched codegen.
- **The idiom catalog** with mechanism-level entries (s64 live-range split;
  tail-merge sub-classes: value-branch-independent = crackable, condition-is-value
  = not).

## Genuinely additive — worth building (ranked)

### 1. coddog (cross-version function matching) — HIGH value
`ethteck/coddog`, Rust CLI. FE8J uses it to triage JP↔US as region-same vs
region-different. **For us it automates two things we do by hand:**
- **fork ↔ upstream**: which of upstream's asm functions are byte-identical to
  ours (trivial ports) vs genuinely different — instead of the manual
  `git show upstream/dev:...` grep loop the porting campaign used.
- **cross-game MMZ1/2/4 ↔ MMZ3**: the Zero-series share an engine; coddog would
  surface functions already matched in a sibling game that port near-verbatim.
  This is the single biggest *untapped* throughput lever we have.
Build: `cargo build` in `tools/coddog/`; wire a `us_jp`-style funcmap. Note the
setup bug FE8J hit — the platform-CLI patch needs **two** grep matches
(`from_decompme_name` **and** `from_name`) or `compare2` panics "Invalid
platform: gba".

### 2. Ghidra headless as a second decompiler — HIGH value for structural holdouts
Our m2c drafts fail exactly where FE8J's do: **PC-relative literals surface as
`M2C_ERROR`**, and complex control flow decodes poorly. Ghidra's decompiler
handles both. FE8J drives it via `pyghidra-mcp` (`--wait-for-analysis`, load the
**ELF** not the raw `.gba` so ARM/Thumb + symbols survive). For us this is the
tool for the reconstructions m2c couldn't finish (InitMotionLocation's runtime
counts, IsInHazard's structure). Free, unlike IDA. Build: install Ghidra,
`pyghidra-mcp`, point it at `build/rmz3/…elf` with our symbols.

### 3. objdiff as a per-symbol match% pre-gate — LOW effort, we already have the binary
`objdiff-cli.exe` is vendored. Wire an `objdiff.json` over the holdout units to
get a match% dashboard, so a batch run ranks the whole backlog by closeness in
one pass instead of per-function mdiff. Caveat (FE8J): objdiff only reports
functions with real ELF sizes — it confirms carved code, doesn't enumerate the
backlog, so keep the NON_MATCH scan as the source of truth.

## What to skip

- IDA Pro path (doc 1): paid; Ghidra covers the same need free.
- mizuchi: a the agent→agbcc→objdiff loop — we already have a tighter one (mdiff).
- The obsolete `decomp-permuter-arm` fork: upstream has native ARM32; stay on it.

## Concrete next build order

1. **coddog** cross-game triage (MMZ1/2/4 ↔ MMZ3) — likely finds ready matches.
2. **Ghidra MCP** for the ~6 structural reconstructions m2c couldn't decode.
3. **objdiff.json** gate to re-rank the tie backlog after each idiom discovery.

Everything else in our harness is at or ahead of the reference workflow. The
instrumented compiler remains our differentiator — worth contributing the
findings back (the pret/agbcc PR is the first step).
