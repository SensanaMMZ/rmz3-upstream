# objdiff holdout ranking (closest first)

> **⚠ Read `notes/backlog-truth.md` before using this table.**
>
> These numbers come from `tools/objdiff_rank.sh`, which compiles at
> `MODERN=1`. `MODERN` swaps `SET_ENTITY_ROUTINE` for a form that schedules
> differently, so **functions that already match the shipped ROM appear here as
> 85-97% near-misses**. Verified already matching: CopyX_Update, Blazin_Update,
> tryKill{Childre,Deathtanz,Glacierle}, CreateBlazin, CreateCopyX,
> CreateBlizzack, loadMugshot, DrawStatus, and more.
>
> The match% is only meaningful for functions actually declared
> `NON_MATCH`/`NAKED`. Run `tools/verify_rank.sh` for the labelled version
> (`notes/rank-verified.md`).


| match% | function | file |
|---|---|---|
| 97.12% | CopyX_Update | src/boss/copy_x.c |
| 95.34% | Blazin_Update | src/boss/blazin.c |
| 92.57% | tryKillGlacierle | src/boss/glacierle.c |
| 92.57% | tryKillDeathtanz | src/boss/deathtanz.c |
| 92.57% | tryKillChildre | src/boss/childre.c |
| 91.60% | CreateBlazin | src/boss/blazin.c |
| 90.79% | blizzackMode0 | src/boss/blizzack.c |
| 89.89% | loadMugshot | src/bg0/text_window.c |
| 89.88% | blizzackMode1 | src/boss/blizzack.c |
| 88.00% | blizzackNextMode | src/boss/blizzack.c |
| 87.90% | CreateCopyX | src/boss/copy_x.c |
| 87.90% | CreateBlizzack | src/boss/blizzack.c |
| 85.41% | DrawStatus | src/bg0/hud.c |
| 82.73% | Deathtanz_Init | src/boss/deathtanz.c |
| 81.46% | Childre_Init | src/boss/childre.c |
| 79.09% | PrintAllStrings | src/bg0/text.c |
| 78.67% | FUN_08050090 | src/boss/anubis.c |
| 76.17% | ResetCharTiles | src/bg0/text.c |
| 68.48% | childre_08040428 | src/boss/childre.c |
