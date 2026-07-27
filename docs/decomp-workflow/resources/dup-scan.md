# Duplicate scan over the ROM (5834 functions, 1030018 bytes)

Regenerate with `python3 tools/dup_scan.py`. A holdout in a
cluster with a matched function is a candidate free match:
reuse the matched body, then map callees/globals from the
holdout's own relocations (`tools/fnbytes.py` verifies).

## Byte-identical (2 clusters) — identical including call offsets and pool words

(1 trivial clusters under 8 bytes omitted: 2 unmatched nop-class functions)

- **FREE via C twin** (52 B): holdouts `FUN_080e964c`*; C `FUN_0803a5c8`
- **solve-one-get-3** (108 B): holdouts `FUN_080e58bc`*; asm `FUN_080e2510`, `FUN_080e2b78`

## Identical modulo call targets (3 clusters) — bl offset bits masked; everything else identical

- **solve-one-get-5** (116 B): holdouts `_zeroTryAttack`*, `FUN_0802e338`*, `air1`*, `zero_wall_080303d4`*, `zero_ladder_08030ee0`*
- **solve-one-get-2** (216 B): asm `SeaOtterElf_Init`, `BirdElf_Init`
- **FREE via C twin** (232 B): holdouts `Ghost28_Init`; C `VFX59_Init`, `Ghost66_Init`

## Identical modulo calls and pool literals (5 clusters) — bl bits and address-like pool words masked

- **solve-one-get-2** (36 B): asm `FUN_08000994`, `FUN_08000c64`
- **solve-one-get-3** (108 B): holdouts `FUN_080e58bc`*; asm `FUN_080e2510`, `FUN_080e2b78`
- **solve-one-get-2** (216 B): asm `SeaOtterElf_Init`, `BirdElf_Init`
- **FREE via C twin** (232 B): holdouts `Ghost28_Init`; C `VFX59_Init`, `Ghost66_Init`
- **solve-one-get-2** (308 B): asm `FUN_080b7e3c`, `FUN_080bd288`

`*` = holdout already has a C body (withc list).

4 holdout names were AMBIGUOUS (static name reused across files or renamed in the map) and were excluded from the scan — check these by address by hand:
- LayerDraw_3 (2 decls, 1 map entries)
- handle_rod_input (2 decls, 1 map entries)
- handle_shield_input (3 decls, 1 map entries)
- onCollision (2 decls, 1 map entries)
