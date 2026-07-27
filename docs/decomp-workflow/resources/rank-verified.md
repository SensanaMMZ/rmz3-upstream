# objdiff ranking, re-verified against the real build (MODERN=0)

`objdiff_rank.sh` compiles at MODERN=1, which swaps shared macros
(`SET_ENTITY_ROUTINE`), so its match% is only meaningful for functions
that are actually declared `NON_MATCH`/`NAKED`. Everything else in the
ranking is an artifact of the harness, not open work.

| rank% | function | file | declared holdout | verdict |
|---|---|---|---|---|
| 97.12 | CopyX_Update | src/boss/copy_x.c | no | already matches -- ranking artifact |
| 95.34 | Blazin_Update | src/boss/blazin.c | no | already matches -- ranking artifact |
| 92.57 | tryKillGlacierle | src/boss/glacierle.c | no | already matches -- ranking artifact |
| 92.57 | tryKillDeathtanz | src/boss/deathtanz.c | no | already matches -- ranking artifact |
| 92.57 | tryKillChildre | src/boss/childre.c | no | already matches -- ranking artifact |
| 91.60 | CreateBlazin | src/boss/blazin.c | no | already matches -- ranking artifact |
| 90.79 | blizzackMode0 | src/boss/blizzack.c | yes | **open** -- rank% is the real signal |
| 89.89 | loadMugshot | src/bg0/text_window.c | no | already matches -- ranking artifact |
| 89.88 | blizzackMode1 | src/boss/blizzack.c | yes | **open** -- rank% is the real signal |
| 88.00 | blizzackNextMode | src/boss/blizzack.c | yes | **open** -- rank% is the real signal |
| 87.90 | CreateCopyX | src/boss/copy_x.c | no | already matches -- ranking artifact |
| 87.90 | CreateBlizzack | src/boss/blizzack.c | no | already matches -- ranking artifact |
| 85.41 | DrawStatus | src/bg0/hud.c | no | already matches -- ranking artifact |
| 82.73 | Deathtanz_Init | src/boss/deathtanz.c | no | already matches -- ranking artifact |
| 81.46 | Childre_Init | src/boss/childre.c | no | already matches -- ranking artifact |
| 79.09 | PrintAllStrings | src/bg0/text.c | yes | **open** -- rank% is the real signal |
| 78.67 | FUN_08050090 | src/boss/anubis.c | yes | **open** -- rank% is the real signal |
| 76.17 | ResetCharTiles | src/bg0/text.c | yes | **open** -- rank% is the real signal |
| 68.48 | childre_08040428 | src/boss/childre.c | yes | **open** -- rank% is the real signal |
