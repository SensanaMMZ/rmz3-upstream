---
name: rmz-decomp-port
description: Port byte-matched functions from a private RMZ decomp fork to an upstream repo (mmzret-style), with the full fixer chain, local gates, CI byte-verification, and PR hygiene. Use for any Mega Man Zero / agbcc GBA decomp porting, upstream PR work, stub decompilation, or de-duplication across PRs.
---

# RMZ decomp upstream porting

Battle-tested workflow for moving byte-matched C between two decomps of the
same ROM (a fork and an upstream that diverged), decompiling trivial stubs,
and keeping dozens of PRs conflict-free. Built on rmz3 (agbcc / GCC 2.9 Thumb);
applies to any sibling repo (rmz1/2/4) with path adjustments.

All referenced scripts are in `scripts/` next to this file. They assume:
worktree of the upstream repo, `upstream/dev` fetched, fork available as
`main` ref or a sibling repo, devkitARM + the fork's agbcc on disk.

## The one rule that outranks everything

**Only `make compare` against the ROM's sha1 proves a match.** Compiling
proves nothing about bytes; assembling nothing about size; linking nothing
about the ROM. Every claim of "verified" must name the stage that ran, and a
CI verdict only counts when the run's harness-commit PARENT equals the exact
local tip being claimed.

## Porting one cluster (functions sharing one upstream .inc)

`port_cluster.sh <asm/path/file.inc> <fn>...` does all of this; pieces below.

1. Branch fresh from `upstream/dev` (`port/<dir>-<base>` — dir in the name;
   basenames collide across asm/). Never rebase old port branches.
2. Carve: `port_to_upstream.py` splits the .inc at `thumb_func_start`
   boundaries and interleaves INCASM/C. It validates EVERY precondition
   (piece paths free, INCASM marker present in the .c) before writing a
   single byte — a half-applied carve once shipped in a commit.
   C bodies are located by `git grep` in the fork, never by assuming the
   mirrored path (upstream renames unk_NN.c to descriptive names).
3. Fixer chain (each pass is a script; order matters):
   `rename_fork_types → fix_struct_keyword → to_flat → flatten_converted →
   fix_return_type(lifted fns only) → fix_specific → fix_common →
   fix_struct_fields → fix_buffer_offsets → fix_nested_access →
   fix_field_offsets → fix_macro_names → apply_map_renames(lifted bodies
   ONLY — its table contains the AllocEntityFirst/Last SWAP and will flip
   correct calls on mixed files) → align_protos → fix_includes →
   fix_init_macro → fix_calls → fix_arg_casts(+_n)`.
4. Gates, all must pass, else auto-revert:
   - `cc_check.sh` — compile AND assemble with the real flags
     (`-mthumb-interwork -Wimplicit -Wparentheses -Werror -O2 -fshort-enums
     -fhex-asm`); assembling catches duplicate symbols.
   - `verify_calls.py` — decode every BL, resolve the TARGET ADDRESS against
     both linker maps. Catches spelled-right-wrong-function (the First/Last
     swap class). Run after ANY rename pass.
   - `check_carve.py` / `check_incasm.py` — no function lost, no orphaned or
     missing .inc.
   - `size_check.py` — positive deltas only (negative = map-boundary noise).
     A function that matches in the fork can assemble LONGER in a new file.
5. Commit (project author identity, casual message), provenance scrub
   (`check_shared_branch.sh` run from INSIDE the repo — it prints a fake OK
   elsewhere), push the ci/ harness branch (`ci_verify.sh`), wait for the
   run whose head parent == your tip, and only then push the PR branch.

## Before building ANY work list

Subtract what open PRs already claim. "Still asm on dev" does NOT mean
unclaimed — an unmerged PR leaves its functions as asm. Skipping this once
produced 205 duplicate submissions, and a second time a 189-stub PR that was
99% redundant. `undecl_recount.py <prfork/branch>...` computes:
asm-on-dev, claimed-by-PRs, and UNCLAIMED. `recompute_overlaps.py` finds
functions claimed by >1 PR (holdouts) — recompute from live PR heads, never
quote a stored count after any structural change.

## Trivial stubs

`find_stubs.py` finds bodies that are exactly `bx lr` (empty) or
`movs r0,#1; bx lr` (return TRUE) — the only shapes with one possible C form.
`port_stubs.py` generates the body; the signature is READ (from the file's
declaration, or the file's prevailing convention when only asm references
it), never invented. `return TRUE` stubs declared `void` get retyped bool8
and their routine-table entries get the neighbours' cast.

## Structure conversion (nested → flat, maintainer policy)

The maintainer's policy: standardize on `COLLISION_OBJECT_HDR` (or
`ENTITY_HDR + ENTITY_SPRITE`) splices — no `(p->s).x` on flat types; wrapper
macros (`_Func` + `#define Func`) over per-call casts; prefer typedefs;
"Motion" is becoming "SpriteAnimation". `run_conversion.sh <branch> <worktree>
<result-file>` converts a whole branch: dev headers wholesale +
`preserve_header_additions.py` (a plain revert deletes real contributions),
then the chain over EVERY file the branch touches (header changes break files
that never named the macro), with `CONV_NO_FIELD_RENAMES=1` (fork-body renames
like props→buffer fire wrongly on upstream-idiom code). Writes results
atomically and takes an mkdir LOCK on the worktree. `audit_policy.py` counts
violations; `pr_audit.py` audits every open PR for duplicates + current-tip CI.

## Traps that each cost hours (all encoded in the scripts, listed so you
recognize the symptoms)

- Resolve a variable's type PER FUNCTION, never file-wide — file-wide hits a
  prototype at the top. Symptom: "the fix did nothing", error unchanged.
- Restrictions must fail CLOSED: an empty span list means rewrite nothing.
- Never patch these scripts through a bash heredoc: `\b` becomes a literal
  backspace and the regex silently matches nothing. `repair_escapes.py`
  sweeps for control characters; run it after any scripted edit.
- Read result files only when written ATOMICALLY (tmp + mv). Reading a file
  a background job is still writing produced three wrong counts in one day.
- One worktree = one writer. Background jobs outlive TaskStop on Windows
  (`ps -ef | grep <runner>` and kill; verify zero). The conversion runner's
  mkdir lock enforces this.
- Layout comments lie (`// 0xC8` on a field that starts at 0xCA): compute
  offsets from declared types; comments are only a cross-check.
- Upstream declares some types as ANONYMOUS typedefs — `struct Omega1` is a
  DIFFERENT, incomplete type from `Omega1`. Reads like a missing include.
- INIT_*_ROUTINE macros already store renderPrio/tileNum/palID (and for
  OBJECT_ENTITY: flags2 |= WHITE_PAINTABLE, invincibleID=uniqueID). Fork
  bodies spell these out; lifted verbatim they double-store and read as
  "doesn't fit". The ROM's codegen IS the macro expansion.
- An "impossible" negative (every subset overflows) can mean per-FILE damage
  from your own tooling (NAKED stripped from asm-bodied neighbours), not
  per-function impossibility. Find the mechanism before declaring defeat:
  `insn_diff.py` (normalized ROM-vs-built instruction diff) and nm-offset
  drift comparison locate growth precisely.
- decomp.me scratches must compile SERVER-side before sharing a link; verify
  ctx+src through the assembler too, and the source name must equal the diff
  label. agbcc does NOT preprocess (// comments error, #define no-ops into
  implicit calls) — the faithful local gate is cpp -> agbcc -> as, and the
  post must be re-verified with POST /api/scratch/<slug>/compile.
- HOMONYMS: a fork C function and a dev asm function sharing a name can be
  DIFFERENT functions (a static copy in another TU vs the global — e.g.
  BlizzardArrow_Update: 144-byte static in buster.c, 872-byte global still
  asm in BOTH repos). Never queue by name alone: exclude any name that still
  appears as `thumb_func_start` in the FORK's asm (portable_next.py does).
  The ROM span between .inc labels is the arbiter of which function you have.
- `NAKED` is not the only asm-body attribute: upstream also has `WIP`
  (same `__attribute__((naked))`). Every guard that skips
  NAKED/INCCODE/NON_MATCH must include WIP, or a pass strips it from a
  neighbour and the compiler adds a prologue (+2 on a function you never
  touched).
- Run the offset-mapper passes (fix_buffer_offsets/fix_field_offsets)
  BEFORE to_flat: the fork distinguishes entity work ((p->s).work, 0x10)
  from a kind-struct's own work (p->work, 0xB4); flattening first collapses
  both to `p->work` and the mapper rewrites entity stores to buffer[] at
  0xB4 (+8 bytes per store pair).

## Verification chain summary

local gates → ci_verify.sh (harness branch on the PR fork) → GitHub Actions
container build → `make compare` vs sha1 → exact-sha parent check → push PR
branch → PR against upstream `dev` (head `owner:branch`). On failure,
`ci_reason.sh` pulls the log's error lines; `rom_diff.sh` downloads the
built ROM artifact and locates differing bytes exactly.
