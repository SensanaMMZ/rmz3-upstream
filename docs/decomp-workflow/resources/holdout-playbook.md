# Holdout playbook — what we can actually do about blocker classes 1–4

Status date: 2026-07-19. Scope: the ~61 NON_MATCH dual-forms plus the
NAKED/INCASM residue. Every entry here already has logic-faithful C and a
byte-matching asm body committed; "solving" a holdout means replacing the asm
with byte-matching C. The ROM verifies either way, so all of this is polish —
but it is the polish that finishes the decomp.

The classes, ordered by expected yield of the attacks below:

---

## Class 1 — Register-allocation ties
*(readKeyInput, blizzackMode0/1/NextMode, CountRodButton, ElfMenuFocusLoop_TabSelect,
CielMinigameEnemy2_Init, Cmd_flag, CopyBgMap, TryContinueLadderDown, FUN_0800a40c,
ResisterNonAffineHitbox, IceBlock_Init, zeroInitKnockBack, isElfUsed_2, FUN_080e964c,
and beetank's r8 as the extreme case)*

One or two extra copies caused by live-range splits, scheduling hoists, or
spill-priority ordering inside agbcc's lreg/greg/reload passes. Pins cascade;
the permuter's randomizer can't find the exact allocation either.

**Attack 1a — corpus fingerprint mining (NEW, proven 2026-07-19).**
For each tie, extract its mismatch fingerprint (e.g. "constant parked in r8",
"copy inserted before strb", "cmp on copies") and search matched corpora for
functions where agbcc EMITS that exact pattern from clean C, then read their
source. This found the r8 recipe in one afternoon (ResetBossBody) after 48h of
permuter search hadn't. Corpora available: our ~2,500 matched fns (indexed),
pokeruby (crawl running), pokefirered/pokeemerald-agbcc (same recipe).
Build-out: a small "codegen pattern index" — for every matched function,
store its .s; grep by regex; map hit → C source. One script, reusable forever.

**Attack 1b — instrumented-agbcc analysis (the expert path, in-house).**
agbcc's SOURCE is available (pret/agbcc = GCC 2.9 with global.c, local-alloc.c,
reload.c). Build a debug copy with logging added to the allocator (why a pseudo
got its reg, spill priority order, reload inheritance decisions) and compile
the near-miss C with it. This does NOT touch the matching toolchain — the
instrumented binary is analysis-only; shipping still uses stock agbcc. This
answers "what source property flips this decision" definitively instead of
guessing. Highest effort, highest certainty; do it once and every Class-1
holdout benefits.

**Attack 1c — community (scratches are ready).**
notes/decompme/ has validated beetank + readKeyInput scratches and the exact
question, including the zero-in-2,500 datapoint. The pret people live in this
compiler. Cost: one post.

**Attack 1d — permuter, but only from engineered basins.**
Random search from plain C is proven useless here (readKeyInput never moved in
3,000 iters). But seeded basins work: copy-pin basin reached 745, the new
asm-barrier basin (which materializes the double-home copies) started below the
old base. Keep permuters running only on engineered seeds, never plain forms.

**Not an attack — the asm-barrier dual-form.**
`asm("" : "=r"(copy) : "0"(orig))` reproduces copy shapes but is not clean C;
fine for proving reachability, not for shipping as a "match".

---

## Class 2 — Retail-suboptimal codegen
*(FUN_0802e338 / zero_ladder_08030ee0 / zero_wall_080303d4 / _zeroTryAttack /
air1 family; InitMotionLocation's addressing; parts of FUN_080e964c)*

Retail's asm is LESS optimized than what agbcc -O2 produces from the faithful
C: duplicated tails that agbcc cross-jumps away, re-computed bases agbcc
strength-reduces, value-propagation retail didn't do. You cannot un-optimize
with cleaner source — so the lever must be the environment, not the source.

**Attack 2a — flag archaeology (cheap, falsifiable, untried).**
Hypothesis: retail built some translation units with different flags. GCC 2.9
has per-pass switches: `-fno-thread-jumps`, `-fno-cse-follow-jumps`,
`-fno-cse-skip-blocks`, `-fno-expensive-optimizations`, and the cross-jump
suppression that would preserve duplicated tails. Experiment per suspect file:
compile the whole TU with each switch; the family function must IMPROVE while
every already-matched function in the same file must STAY matched. If a switch
passes both conditions, that file's true build recipe is found and the whole
family may fall at once. One scripted sweep over ~8 switches × 3 files.

**Attack 2b — de-optimizing source constructs.**
Where 2a fails: constructs that legitimately block the optimization —
assigning through a `volatile` temp kills value-prop; keeping the two arms'
stores textually different (different expression forms with identical values)
can block cross-jumping since GCC2 cross-jump requires IDENTICAL rtl tails.
E.g. `attackMode[1] = ok;` vs `attackMode[1] = 0;` in the other arm already
differs in our C — the missing piece is stopping value-prop from folding
`ok==0`; try reading `ok` back through a struct member or array element
(memory reads aren't value-propagated across in GCC2 without alias info).
Per-function fiddling; moderate odds.

**Attack 2c — accept.** This class is the strongest candidate for permanent
INCASM: the retail devs' compiler genuinely emitted worse code than ours does.
Document (done in the backlog note) and move on.

---

## Class 3 — Structural divergence
*(FlushOAM, IsInHazard's one LICM hoist, InitMotionLocation's base/induction tie)*

The C is decoded and near-matching (IsInHazard literally 78/78 instrs with
only register renumbering left); the last gap is one loop transform agbcc
makes differently.

**Attack 3a — finish IsInHazard with 1a/1b.** Its residual is exactly a
Class-1 tie now (which invariant gets hoisted into which callee-saved reg).
The instrumented allocator (1b) or a corpus exemplar with "3 invariant bases +
idx*stride induction" (1a — grep for `lsls rX, rY, #2..4` + repeated
`adds rZ, base` triples in loops) is the way in. Closest single function to a
new match in the whole backlog.

**Attack 3b — reconstruct FlushOAM from its asm shape, not from logic.**
cur >> exp (65 vs 55) means our MODERN C is structurally wrong (too much
code). Decode the target's loop the way IsInHazard was decoded: identify
whether the copy loop is a do-while with pre-computed end pointer, whether
DISPCNT masking happens in a different order, etc. This worked for IsInHazard
(48→78/78); FlushOAM is the same kind of job, a focused evening.

**Attack 3c — InitMotionLocation: park it.** Counts and loop direction are
decoded and correct; the remaining tie is strength-reduction bases (Class-1
flavored) AND our form is SHORTER than retail (Class-2 flavored). Both
diseases at once → lowest priority in this class.

---

## Class 4 — Permuter-poisoned packed-struct readers
*(onRod and the gOverworld.terrain readers; anything whose context needs
__attribute__((packed)))*

The poison: decomp-permuter's importer strips attributes, so candidates score
against a WRONG struct layout — false matches, useless search.

**Attack 4a — un-poison by making layout attribute-free (structural fix).**
Rewrite the permuter base's context so the packed layout is explicit without
attributes: replace the packed struct with `u8 raw[N]` + accessor macros
(`#define OW_FIELD(base) (*(u16*)((base)+0x1DC))` etc.). pycparser parses it,
agbcc compiles it, the layout is exact by construction, and the permuter's
mutations still apply to the FUNCTION body. One-time transform per poisoned
function; completely removes the false-match problem.

**Attack 4b — auto re-verify wrapper (cheap safety net).**
Wrap the permuter's "found a better score" path: on every new best, re-verify
the candidate through tools/mdiff.sh in the REAL build (real headers, real
packing). Kills false positives even where 4a isn't applied. Small patch to
the longrun scripts' watcher loop.

---

## Recommended order of operations

1. **1a build-out**: the codegen pattern index over ours+pokeruby (+pokefirered
   later). Cheap, reusable, feeds Classes 1 and 3.  [script, ~1 session]
2. **2a flag sweep** on the FUN_0802e338 family files. Cheap, decisive either
   way — either a family of matches or the hypothesis is dead.  [script, hours]
3. **3a/3b**: IsInHazard's last hoist via the index; FlushOAM re-decode.
   [focused manual work, best match-per-effort in the backlog]
4. **1b instrumented agbcc** if the index doesn't crack the ties — the
   definitive tool, unblocks everything in Class 1.  [1–2 sessions]
5. **4a/4b** before any further permuter time on poisoned functions.
6. Scratches posted meanwhile (community answers can short-circuit any of
   the above); permuters keep grinding their engineered basins in the
   background.

What we do NOT do: patch the shipping agbcc (breaks clean-room and every
existing match), hand-edit target asm, or ship asm-barrier forms as matches.
