# Notice

*(Español: [NOTICE.es.md](NOTICE.es.md))*

## Not affiliated

This is an unofficial, noncommercial fan project. It is **not affiliated with, endorsed by or
connected to Nintendo, HAL Laboratory or Microsoft**, nor to
[doldecomp](https://github.com/doldecomp/melee), nor to the author of
[`melee-pc`](https://github.com/999sian/melee-pc), nor to the author of
[Aurora](https://github.com/encounter/aurora). *Super Smash Bros. Melee*, *Xbox* and all related
names and marks are the property of their respective owners.

Nothing here is for sale, and nothing here is monetized.

## What this repository does not distribute

No disc image. No game data or assets. No built executable. No `.msix`. No save data or memory
cards. No package tiles (`package/Assets/` is empty).

**And none of the UWP libraries**: Dawn, SDL3 and `libuwp` are other people's binaries.

## What it does contain of other people's work

**Patches against Aurora.** `patches/aurora-uwp.patch` (six files) and the two scripts in `tools/`
modify [Aurora](https://github.com/encounter/aurora), which is **MIT**, © 2022 Luke Street. MIT
permits modified versions; this repository is released under [that same license](LICENSE), carrying
Aurora's notice with it.

**Nothing of `melee-pc`.** That project publishes no license, so **no line of it is reproduced
here**: the port's full diff touched two of its files, and those two blocks were split out of the
patch. What they do is *described* in `docs/HOW-IT-WORKS.md` — a `unistd.h` include that has to be
conditional, two `stat` macros MSVC does not define, and a `ShellExecuteA` that has to go in a UWP
build. That is a technical description, not their code.

**The UWP layer in `src/uwp/`** is first-party: the WinRT entry point, a shim for what GCC's objects
ask of MinGW's CRT and the "store" CRT does not have, and an empty updater.

**There are no screenshots here.** A screenshot of this running would be mostly Nintendo's artwork.

## Takedown and contact

If you hold rights in this material and want something here removed or changed, write to
**jajdpmail@gmail.com**, saying what you object to and in what capacity you are writing. Requests
from rights holders are honoured without argument, and you will get a reply confirming it.
