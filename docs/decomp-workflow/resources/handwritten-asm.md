# Holdouts that are hand-written assembly (4)

A compiler always emits the prologue first. A function that does
real work *before* its `push` was written by hand, so there is no C
source to recover and no amount of permuting will reach it.

Regenerate with `python3 tools/detect_handwritten_asm.py`.

## r7 frame-pointer prologue (3)

- **FUN_08001328** — `asm/mmbn4.inc`
  - push {r7, lr}
- **SioLink_GetLocalPlayerId** — `src/mmbn4.c`
  - push {r7, lr}
- **SioLink_SetTransmitParams** — `src/mmbn4.c`
  - push {r7, lr}

## work before the prologue (1)

- **FUN_080ee328** — `asm/wip/FUN_080ee328.inc`
  - 1 instruction(s) precede `push {r4, r5, r6, r7}`: lsrs r1, r1, #1

