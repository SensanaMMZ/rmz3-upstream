# The matching workflow, in order

Written after the first match produced by the Ghidra harness
(`unused_080e9680` / `unused_080e9698`, ROM verified, upstream PR #49).

Read `notes/backlog-truth.md` alongside this — it holds the per-function
findings. This file is the procedure and the mistakes.
`notes/urls-of-gba-decomps/extracted-practices.md` is the companion knowledge
base: flag levers, C nudge catalog, and tooling surveyed from 17 other GBA
decomps (2026-07-23). Consult it when a function resists step 4.

## 0. Before anything: know which flags the file uses

**Read the per-file overrides at the bottom of `makefile` first.**

```make
$(BUILD_DIR)/src/mmbn4.o:       CFLAGS := -O -mno-thumb-interwork
$(BUILD_DIR)/src/libs/agb_sram.o: CFLAGS := -O -mthumb-interwork
$(BUILD_DIR)/src/libs/m4a.o:    AGBCC  := tools/agbcc/bin/old_agbcc$(EXE)
```

Every ad-hoc probe and both ranking scripts hardcode `-mthumb-interwork -O2`.
For those three files that is simply the wrong compiler invocation, and any
diff taken with it is meaningless. This cost a whole wrong conclusion (below).

## 1. Pick a target

```sh
python3 tools/classify_holdouts.py     # 489 declared holdouts -> withc / pure
```

- **with a C body** → objdiff/permuter territory; the ranking match% is real.
- **pure INCCODE stub** → needs reconstruction first.

Rank by size (`tools/ghidra/rom_symbols.txt` has exact sizes). Small functions
are the cheapest matches — the first two matches were 24 and 46 bytes.

## 2. Get the structure

```sh
python3 tools/ghidra/batch_decompile.py      # -> build/ghidra-drafts/*.c
python3 tools/ghidra/resolve_pool_refs.py    # DAT_08xxxxxx -> real names
```

Cross-check against the m2c draft. Trust a structure when both agree; treat a
disagreement as a signal that one of them mis-decoded control flow.

## 3. Write C, then diff **bytes**

```sh
python3 tools/fnbytes.py ours.o expected/build/rmz3/src/FILE.o FUNC --diff
```

Never judge by `objdump -d`. A function that came from an `INCCODE`'d `.inc` is
stored as raw data in the expected object, so the disassembler renders it as
`.word`s and a disassembly diff says nothing.

## 4. Read the diff as evidence

The byte diff names the source-level property. From the two matches:

| what the bytes showed | what it meant |
|---|---|
| epilogue `pop {r1}; bx r1` instead of `pop {r0}` | `r0` live at exit → the value is **returned**, not discarded |
| an extra `lsls #24; lsrs #24` | a **`u8` return** forcing truncation → the type is a word |
| our size 46 vs their 48 | trailing **alignment padding** counted inside the asm symbol, not a real difference |
| `fff7 feff` vs `fff7 cbff` on a `bl` | **link-equivalent**: compiled code emits a relocation, the `.inc` baked the final offset in as `.byte` data |
| pool word `symbol+0xNNN` (one reloc), other addresses derived by runtime adds | the source anchors a **local pointer at that offset** (`T** ep = &g.member;`) and derives everything else arithmetically from it. `&g.member`/`&arr[N]` pools the addend in place (REL: word holds 0xNNN + R_ARM_ABS32). `ep - K` pools `-0xNNN` instead of folding back to `symbol+0` when the anchor is a local. Proven on FlushOAM (120/120); applies to the `gOverworld+0x1DC` hazard cluster. **Method: write tiny probe TUs to learn which shape produces the pool form before touching the real function.** |

`tools/fnbytes.py` and `build/scratch/cmp_text.py` classify the last one
automatically; check relocations before calling a `bl` difference real.

## 5. Verify at ROM level — the only check that cannot lie

```sh
make -j4 DEVKITARM=/c/devkitPro/devkitARM
sha1sum rmz3.gba      # ff7a801776dc76e6d8c7ef73a6660ae732934a3f
```

Do not commit a match before this passes.

## 6. Ship it upstream

On a match, open a PR against `mmzret/rmz3` so the maintainer can review:

1. `git checkout -b contrib/<name> upstream/dev`
2. apply the change **using their names** (`Coords32`, not `struct Coord`)
3. compile their file and compare against our SHA1-proven
   `expected/build/rmz3/src/*.o` — zero real differences
4. re-compile with `-Werror` (their build uses it) and confirm silence
5. commit, push to the `SensanaMMZ/rmz3-upstream` fork, open the PR with
   `base: dev`

## Build environment traps

Three separate things blocked the verification build, none of them related to
the code:

- **`DEVKITARM`** in the profile points at `/opt/devkitpro/devkitARM`, which
  does not exist here. Pass it explicitly:
  `make DEVKITARM=/c/devkitPro/devkitARM`. Without it `$(TOOL)/arm-none-eabi-as`
  resolves to `/bin/arm-none-eabi-as` and every assemble fails with error 127.
- **Stale `build/**/*.d`** referenced `include/constants/entity/projectile.h`,
  a header that does not exist in this tree. `find build -name '*.d' -delete`.
- **Prebuilt host tools** get rebuilt if their sources look newer, and they do
  not survive `-Werror` on a modern g++. Touch the `.exe`s.

## Corrections to conclusions I got wrong

Recorded because the reasoning errors are more reusable than the facts.

### "src/mmbn4.c is not our compiler's output" — WRONG

I found `push {r7, lr}` / `pop {r7, pc}` in its helpers, confirmed that form
appears only 3 times in the entire ROM (all in mmbn4), and concluded the file
came from a different toolchain — writing off 18 functions.

The evidence was real. The inference was not: I went from *"different from the
rest of the game"* to *"outside our toolchain"* without testing it. In fact the
makefile has always compiled that file with `-O -mno-thumb-interwork`, and
`-mno-thumb-interwork` is exactly what produces `pop {r7, pc}`. Every probe I
ran used the default `-mthumb-interwork -O2`. **The codegen looked foreign
because I compiled it wrong.** agbcc also reproduces `push {r7, lr}` with
`-fno-omit-frame-pointer` (which `-O2` disables), and `old_agbcc.exe` is
already in the tree, already used for `m4a.o`.

Status: **RESOLVED (2026-07-25)** — the module is hand-written assembly.
The `movs r0, r0` / `tst r0, r0` tails are flag-register returns: callers
`beq` immediately after `bl` with no comparison (asm/mmbn4.inc:1681). No
compiler emits flag-returning calls, so no flag sweep can ever match these
18 functions; they stay NAKED permanently, like crt0. The original
"different from the rest of the game" observation was correct — the
error was assuming it had to be a *compiler* difference.

### "The objdiff ranking shows the closest holdouts" — WRONG

`objdiff_rank.sh` compiles at `MODERN=1`, and `MODERN` swaps
`SET_ENTITY_ROUTINE` for a form that schedules differently. Twelve of nineteen
ranked entries **already matched the ROM**. A harness bug that reports 92% reads
as progress; one that reports 40% gets investigated. Trust that match% only for
functions actually declared `NON_MATCH`/`NAKED`.

### Verifications that silently passed while checking nothing

Four in one session. Each looked like a result:

- a byte comparison that piped `objcopy` to `/dev/stdout`, got nothing, and
  printed **BYTE-IDENTICAL** — comparing two empty strings, on functions whose
  sizes differed by 6 bytes;
- a hand-written-asm detector that skipped monolithic `.inc` files and so
  scanned a handful of functions instead of 2,409;
- a build-liveness check whose pattern matched `bash` processes, reporting a
  dead build as alive;
- two build-error greps that fired on the literal `-Werror` in a compile
  command and on a benign line starting with `make`.

The rule that came out of it: **a check that can pass without doing its work is
not a check.** Detectors now print their own coverage (`detect_handwritten_asm.py`
reports segments scanned and warns if too many parse empty), and comparisons are
calibrated in both directions — confirm the tool reports IDENTICAL for a known
match *and* DIFFERS for a known mismatch before believing either.

Addendum to the byte-evidence table: **a declaration's return type is
load-bearing in every CALLER, not just the definition** — retyping a
bool8 helper to bool32 deletes the `lsls #24` truncation at each call
site that tests the result (Mellnet_Update shrank 2 bytes and shifted
the whole ROM). When lifting a stub whose declared type you want to
change, grep its callers first; the sha1 gate is the only reliable
catch. Related: probe TUs never verify declaration-type effects on
callers, and reloc masking never verifies data-index addends — both
are ROM-build-only checks (cattatank, mellnet 2026-07-24).

Second addendum (byte-evidence table growth, 2026-07-24):
- an unexplained register copy WEDGED INSIDE a condition evaluation
  (between `ands` and `cmp`) = the source computes the condition into a
  named temp, assigns an unrelated variable, then tests the temp
  (`t = x & 1; ptr = other; if (t)`) — proven on FUN_080b963c;
- `movs rX,#1; orrs rX,rY` with the 1 landing DIRECTLY in the result
  register = compound two-statement form (`v = 1; v |= y;`); both
  `v = y | 1` and `v = 1 | y` route the constant through a scratch reg
  first — proven on FUN_080b9cf8;
- an asymmetric (u8) truncation between two if/else arms assigning the
  same variable is NOT a contradiction: GCC 2.9 combine is per-basic-
  block, so the arm that only copies a cross-block value keeps its
  truncation while the arm that computes a fresh OR loses it.

## 4b. Cross-reference the decomp corpus BEFORE contorting a harness

Added 2026-07-25. `tools/decomp_crawl.py` mirrors every repo in
`notes/urls-of-gba-decomps/list-of-decomps.md` into `../decomp-corpus/`,
compiles each project's `src/**/*.c` with OUR agbcc, and indexes every
function's instruction stream. That turns "which C shape produces this
instruction?" into a lookup instead of a guess.

```sh
python3 tools/decomp_crawl.py clone [proj ...]   # shallow clone / fetch
python3 tools/decomp_crawl.py index [proj ...]   # compile + index + dated reports
python3 tools/decomp_crawl.py grep 'mov\s+r8'    # corpus-wide instruction search
python3 tools/decomp_crawl.py shim  [proj ...]   # stub build-generated headers
python3 tools/decomp_crawl.py check              # weekly: which upstreams moved
```

`shim` exists because several projects generate headers during their own
build (pokeemerald's `map_groups.h` and friends). We never build them, so cpp
died on the include and the project indexed almost nothing. The shim pass
walks the sources, collects every `fatal error: X: No such file`, writes an
EMPTY stub for each, and repeats until the set stops growing — empty is fine
because the corpus wants representative codegen, not a correct binary. It took
pokeemerald from 37 functions to 15,488. Run `shim` before `index` on any
project whose `files_failed` is high.

Note that goldensun and sma2 index to zero legitimately: at their current
commits they are asm-only decomps with no C sources at all.

Reports land in `notes/decompme/crawl/<proj>_<trait>_report_<YYYY-MM-DD>.md`
(same format as the original `pokeruby_r8_report.md`), one file per trait per
crawl date, so old reports stay as a record and new ones never overwrite them.
Traits indexed: r8/high-reg pinning, `and #0xff` vs `lsl/lsr #24` byte
truncation, `__umodsi3`/`__udivsi3`, `mul`, `rsb`, `bic`, `tst`, `mov ip`.
`../decomp-corpus/manifest.json` records each project's commit + crawl date.

**Ordering rule:** corpus grep comes AFTER the byte diff names the property
(step 4) and BEFORE escalating to decomp.me (step 5). Posting a scratch
without having grepped the corpus for the offending instruction wastes a
community ask on something the corpus can answer — and the scratch write-up
should cite what the corpus did or did not show.

**Cadence:** re-run `check` weekly; re-clone + re-index only the projects it
reports as moved. Note that projects using non-agbcc toolchains still index
usefully (their C compiles under agbcc often enough to be a source-shape
corpus), but `files_failed` in the manifest tells you how much of a project
was unusable.

Third addendum — the u8 post-increment-and-test trichotomy (2026-07-25).
Three spellings of "bump a u8 counter and test bit 0" give three DIFFERENT
encodings under agbcc -O2, so pick by what the target shows:

| source | emitted |
|---|---|
| `if (++p->work[n] & 1)` | `movs r1,#0xff; ands` then `movs r1,#1; ands` |
| `u8 t = ++p->work[n]; if (t & 1)` | `lsls #24; lsrs #24` then `movs r1,#1; ands` |
| `p->work[n]++;` then `if (p->work[n] & 1)` | NO truncation — `movs r1,#1; ands` only |

The third form also leaves the `1` live in r1 for a following
`flags |= DISPLAY`, which is how the target reuses it. Proven on
FUN_080b7e3c (form 1), the elf/laser2 family (form 2) and
FUN_080c6c60/FUN_080c7250 (form 3, matched exactly).

## The duplicated-arm class (2026-07-25) — recognise it and park immediately

A recurring, systematic blocker: the ROM contains two BYTE-IDENTICAL
instruction blocks on the two arms of a branch, where agbcc compiling any
equivalent C emits ONE shared block. Confirmed instances:
  * `_zeroTryAttack` + its four siblings (116B x5) — duplicated
    `attackMode[0]=3; attackMode[1]=0;`
  * `getSunkenLibRoomCoord` — duplicated table lookup across an idx>7 guard
    (noted by an earlier session, independently reconfirmed)
  * partially `FUN_080b7e3c` — the pool constant is emitted twice

agbcc cross-jumps the arms back together no matter how the C is spelled.
Everything tried and FAILED to keep them apart: duplicating the statements
in both arms; making one arm read a known-zero variable instead of a
literal; block-local vs hoisted pointers; member-to-member vs temp stores;
`|=` vs `=` on the shared field.

There is also NO compiler escape hatch: `-fno-crossjumping` does not
exist in gcc 2.9 (agbcc rejects it outright), and the two related flags
that ARE accepted (`-fno-thread-jumps`, `-fno-cse-follow-jumps`) change
the size in the wrong direction and never restore the duplication.

DISPOSITION: when a byte diff shows the target is LARGER than our output
by exactly one duplicated block, stop. Do not spend another cycle on
spellings — record it, and treat the function as a permuter/decomp.me
candidate or leave it as asm. Recognising this class early is worth more
than any individual match.

## 4c. Grep the headers for an accessor macro BEFORE inventing a spelling

Added 2026-07-25 after FUN_08013bdc. When a pool word points at
`global + N` rather than `global + 0`, the source almost certainly went
through an existing accessor macro that bakes N into the address
expression. rmz3 has a lot of these (BGnHOFS/BGnVOFS, BGCNT16,
RESET_BGOFS, SCREEN_BASE_16, SEA, W_TERRAIN_V2, HAZARD, ...). Hand-rolled
pointer anchors get the arithmetic right but usually miss the exact pool
form and cost several failed probes. `grep -n <field> include/*.h` first.

## Signed division by a power of two — recognise the bias

`ldr rX,[..]; cmp rX,#0; bge L; adds rX,#(2^n - 1); L: asrs rX,#n`
is NOT a hand-written round-toward-zero; it is plain `x / (1 << n)` on a
SIGNED value. agbcc adds the (2^n - 1) bias only on the negative path so
the shift truncates toward zero. Write `x / 32`, never `x >> 5` (that
would drop the bias and the compare) and never a hand-rolled ternary.
Confirmed on phunter_080651c0 (`unk_coord.x = d.x / 32`, 88/88 exact).

## Ternary vs if/else for +/-CONST — count the constant materialisations

Both compile to a branch, but they differ in how many times the constant
is built:
  TERNARY `d.x = c ? K : -K;`  -> ONE `movs #K`, then `neg` on one path
                                  (the constant is shared)
  IF/ELSE `if (c) d.x = K; else d.x = -K;` -> TWO `movs #K`, the false
                                  arm following with `rsbs`
So: count the `movs #K` in the target. Two of them means if/else, one
means a ternary. Proven on phunter_080652e8 (two -> if/else, 136/136
exact; the ternary form was 132B with 104 diffs).
This composes with the earlier polarity rule: which constant is
materialised BEFORE the compare tells you the false-branch value.

## Cross-jumping, part 3: when to hoist the call result yourself

Earlier rule said "target has a shared tail -> write the natural
per-branch code and let agbcc merge". That holds for pure stores
(blazin_080403a0, FUN_080c17e8), but NOT when the shared tail tests a
CALL RESULT. Writing
    if (c) { ...; if (Call(a)) Snd(); } else { ...; if (Call(b)) Snd(); }
merges too aggressively and comes out 6 bytes SHORT, while
    if (c) { ...; q = Call(a); } else { ...; q = Call(b); }
    if (q != NULL) Snd();
is exact (phunterShotBuster, 168/168). Rule of thumb: duplicate STORES
may be left to the compiler; a duplicated TEST OF A CALL RESULT should
be hoisted into a variable in the source.

### Branch polarity distinguishes `||` from a fused/ternary condition

Symptom: the whole function is byte-identical except one conditional branch,
where the ROM has `cmp rX, #0 / beq <then>` and we emit `cmp rX, #0 / bne <else>`
(same targets, opposite sense, same size).

agbcc emits **branch-if-FALSE to the else block** for a plain condition or a
`?:` condition, but **branch-if-TRUE to the then block** for the *left* operand
of a short-circuit `||`. So that polarity flip is a reliable signal that the
original condition was written `if (A || B)`, not `if (A ? x : y)`.

Two supporting tells, both seen on `FUN_080964c0`:

- **`cmp` against 0 on every path** means the sub-conditions are separate tests
  (`v == 0`, `v != 0`). Any *fused* boolean compare (`(flag != 0) != v`) folds the
  flag to a constant on one side and produces `cmp rX, #1` on that path — which
  no amount of arm-swapping removes.
- **Two complete call blocks** (each with its own `adds r0,r4,#0 / bl`) means one
  if/else, not nested ifs. Nested ifs give four arms that agbcc tail-merges only
  partially, stranding a `ldr rN, =const` head and forcing an extra literal pool
  mid-function (+6 bytes, and the pool position is the giveaway).

Worked example — ROM shape recovered as:

```c
v = (p->s).d.x < 0;
if ((((p->s).flags & X_FLIP) && v == 0) || (((p->s).flags & X_FLIP) == 0 && v != 0)) {
```

agbcc CSEs the repeated `flags & X_FLIP` and jump-threads the second test away,
so the duplicated-looking source compiles to a single flag test.

### Lifting a function from the MIDDLE of an .inc requires splitting the .inc

If the target is not the first `thumb_func_start` in its `.inc`, you cannot just
delete its block and put the C above the existing `INCASM(...)` — the C function
is emitted where the `INCASM` was, so every asm function that *preceded* the
target inside that `.inc` shifts to a later address. The isolated byte probe
still reports MATCH (it only compares the one function), but the ROM sha1 breaks
and the diff starts at the *first* function of that `.inc`, not at the target.

Correct procedure: split the `.inc` in two at the target — `<name>_a.inc` for the
functions before it, `<name>_b.inc` for those after (both keep the original
header lines) — then emit `INCASM(a); <C function>; INCASM(b);`.

This is exactly why only the in-tree ROM sha1 build is authoritative. Cost when
skipped: one broken build, caught immediately by `make`.

## carve_inc.py: never let a split clobber an existing .inc
Splitting `foo.inc` into `foo_a`/`foo_b` silently overwrote two files that
already existed (`purple_nerple_p1_a_b.inc`, `unk_32_p1_pre_pre_b.inc`) because
earlier splits had already claimed those names. `git status` caught it -- they
showed as ` M` instead of `??`. carve_inc.py now probes for a free suffix.
**After any inc split, read `git status` and confirm every new half is `??`.**

## Verify that a patch actually patched
I "hardened" carve_inc.py with a python `s.replace(old, new)` where `old` was
written in a NON-raw triple-quoted string containing `\n\t\.align` -- Python
turned those into a real newline and tab, so the text never matched, replace()
returned the input unchanged, and my script still printed its success message.
The very next carve silently dropped an orphan `.byte 0x70, 0x47` block.
**A replace/patch step must assert the substring was found, and a success
message must be printed only on the verified path.** For anything non-trivial,
rewrite the file with Write instead of patching it with replace().

## Trailing zero bytes in a ROM slice are alignment padding, not a mismatch
A function measured as "next symbol - start" can include 1-3 bytes of zero
padding emitted by the FOLLOWING object's `.align 2, 0`. FUN_080aada0 and
FUN_08071470 both looked 2 bytes short when they were byte-perfect.
probe_fn.py now trims that, but ONLY when the surplus is <4 bytes, all zero, and
takes the length to a 4-boundary. The seimeran orphan (4 bytes of nonzero
`bx lr`) still fails the size check, which is the whole point.

## fnsize.py: "last pool + 4" is wrong when the pool is mid-function
agbcc dumps a literal pool after any unconditional branch, so a pool can sit in
the MIDDLE of a function with code after it -- every SET_XFLIP spawner does this.
The tool now checks for instructions after the last pool entry and falls back to
the next symbol's address, or refuses to answer rather than guessing.

## Never `rm` an .inc in the same command that inspects it
I ran `grep thumb_func_start <inc> && rm <inc> && ...` -- the grep output only
became visible after the delete had already happened. blizzard_arrow_pre.inc
held THREE functions and I had lifted one, so the link failed on two missing
symbols. Deleting an .inc outright is only correct when it contains exactly ONE
thumb_func_start; otherwise carve it. Confirm the count in a SEPARATE tool call
before the delete.

## Check the file's OWN struct before casting into props[]
flopper.c already defined `struct FlopperObject { OBJECT_HDR; struct Coord c;
u32 unk_08; ... }`. I wrote `*(s32*)&p->props[8]` instead and lost a byte to
signedness. Before reaching for a props[] cast, grep the target .c for an
existing struct covering 0xB4.. -- several files have one.
When switching a function's parameter to that struct type, the file's forward
declarations and its EnemyFunc/ProjectileFunc tables need updating too
(`(EnemyFunc)FUN_x` in the table), or the build fails on conflicting types.

## NEVER `rm -rf build` in this repo
The makefile does not recreate its output directory tree (SUBDIRS is not wired as
an order-only prerequisite), and `find src -type f -name '*.s'` objects are only
built when named explicitly once the tree is gone. Deleting build/ cost a long
recovery: host-tool timestamps had to be refreshed (`touch tools/*/*.exe`), all
715 output dirs recreated, and every asm object built by explicit target before
the link would succeed. To force a rebuild, touch the source or delete the single
.o -- never the tree. Restored sha1 ff7a8017... after the repair.

## Upstream (mmzret/rmz3) contribution conventions
Policy from the upstream dev, 2026-07-25. The fork still uses the OLD nested
style, so anything ported upstream must be converted:

* Entity types are being flattened onto `COLLISION_OBJECT_HDR` (or
  `ENTITY_HDR` + `ENTITY_SPRITE`), so field access is `p->mode[2]`, NOT
  `(p->s).mode[2]`. entity.h upstream is mixed today: `Boss` is flat,
  `struct Enemy` is not yet.
* The dev states the flattening "hasn't affected the compilation results" --
  i.e. the conversion is codegen-neutral and a matched function stays
  byte-exact. Re-probe every converted function anyway; `&p->s` ->
  `(struct Entity*)p` at call sites is where codegen could still move.
* Functions taking `struct Entity*` get a wrapper macro rather than casts at
  each call site:  `void _Func(struct Entity*); #define Func(e) (_Func((struct Entity*)(e)))`
* Prefer `typedef`'d struct names (`Boss`, `Projectile`, `VFX50`, `Coords32`).
* "Motion" is being renamed "SpriteAnimation" -- don't entrench `Motion` in new
  upstream-facing names.

## Upstream PRs: the fork is SensanaMMZ/rmz3-upstream
`SensanaMMZ/rmz3` is a standalone repo, not a GitHub fork, so a cross-repo PR
from it fails with `422 head invalid`. Push contrib branches to
`SensanaMMZ/rmz3-upstream` (a real fork of mmzret/rmz3) and PR against `dev`.
Flattened upstream types: Boss, Projectile, Weapon, FlopperObject, VFX50.
Still nested: Enemy, VFX, Solid. Renames: taskCol -> renderPrio,
struct Motion -> AnimState, props union -> u8 buffer[N].
Verify ports with the per-function byte probe (upstream/dev does not build here).
