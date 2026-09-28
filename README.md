# Steam Heart's English translation – crash fix

An IPS patch for **Steam Heart's [T-En by Psyklax v0.99]** (PC-98) that fixes
the game crashing during dialogue, usually shortly after a stage starts.

The translation itself is Psyklax's work
([romhacking.net: Steam Heart's translation](https://www.romhacking.net/translations/3509/));
this patch only fixes a compatibility bug in it. The original Japanese release does not need it.

## Download

[`SteamHearts_T-En_v0.99_crashfix.ips`](SteamHearts_T-En_v0.99_crashfix.ips)
(475 bytes). Apply it with any IPS tool (Floating IPS, Lunar IPS, …).

| | Size | CRC32 | SHA1 |
|---|---|---|---|
| Input: `Steam Heart's [T-En by Psyklax v0.99].hdi` | 10,479,616 | `BFFD2ADA` | `9E99AE620A0CB6A337BC8C1F3478E69D4AE2AFB4` |
| Output (patched) | 10,479,616 | `8A741BCA` | `B926F2CDBFD6A7583024AF9EA99547408A800238` |

The HDI uses 256-byte sectors (SASI 10 MB geometry).

## What was wrong

To print English text, the translation replaced the game's two-byte character
fetch in `ST1.EXE`–`ST7.EXE`:

```
mov ah,[si] / sub al,al / mov cl,[si+1] / sub ch,ch / add ax,cx
```

with a far call to a small helper appended to each stage (ASCII → half-width
character code). All 27 of those calls use a hard-coded absolute segment,
`25E3h`, with no relocation entry. That address was only correct for the DOS
memory layout on the translator's own machine (program loaded at segment
`13C6h`). On any other setup – another DOS version, other drivers, HIMEM, an
emulator or an FPGA core – the calls jump into the middle of unrelated game
code, the stack is unbalanced and the game crashes.

## What the patch does

Each call keeps its target offset but gets a segment relative to the program
(`121Dh`) plus a relocation entry, so DOS points it at the helper wherever the
game is loaded. No text, graphics or game logic changes; on the translator's
original layout the behaviour is identical.

`make_fix.py` is the script that produced the patch, for reference:
`python make_fix.py <translation.hdi> <out_dir> <dir with the HDI's ST1-ST7.EXE>`.

Found while testing the [Zet98 486 PC-98 MiSTer core](https://github.com/Elrinth/Zet98_486_MiSTer).
