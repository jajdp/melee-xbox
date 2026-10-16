# Super Smash Bros. Melee on Xbox — the UWP port

How to take the PC port of *Super Smash Bros. Melee* (GameCube, 2001) —
[`999sian/melee-pc`](https://github.com/999sian/melee-pc), on top of
[doldecomp](https://github.com/doldecomp/melee)'s decompilation — and run it **on an Xbox Series in
Developer Mode**, as a UWP package you build and sign yourself.

*(Español: [README.es.md](README.es.md))*

It is not a theory: the game boots, reads the disc, creates the memory card, **plays with a
controller**, and runs at **59.86 FPS on average** (measured over a four-minute four-CPU match).

## What makes this port unusual: two compilers

The game's code describes the disc's data with `scalar_storage_order("big-endian")`, an extension
**only GCC implements**. Every other UWP port in this catalogue is built with clang and the MSVC
ABI, and clang does not have it.

The way out is using **both at once**, which is what `tools/construir_uwp.py` does: it walks the
desktop build's `compile_commands.json` and sends each command to one or the other.

| Compiler | What it compiles | Objects |
|---|---|---|
| **GCC** (MSYS2 UCRT64) | The game's C, Aurora's matrix maths and the executable's own `.c` files | 1 048 |
| **clang** (llvm-mingw, `--target=x86_64-pc-windows-msvc`, `WINAPI_FAMILY_APP`) | The C++ (Aurora, RmlUi, abseil, imgui, fmt), freetype, sqlite3, xxhash, zstd and the port's own UWP layer | 555 |

It then archives one `.lib` per target — 226 — and links with `ld.lld` in `/appcontainer` mode, at a
**fixed base of `0x10000000`, with no ASLR and no high entropy**, because the game keeps disc
pointers in 32-bit slots and everything it references has to live below 4 GB.

## What this repository is, and is not

**A recipe and the tools that apply it**, applied to your own checkout of `melee-pc`.

There is no **disc, no game data, no executable, no `.msix`, no tiles and none of the UWP
libraries** (Dawn, SDL3, `libuwp`) here — those are other people's binaries.

And there is a split worth understanding, because it is what decides what can be published:

| | |
|---|---|
| **Aurora** (MIT, © 2022 Luke Street) | Its **six** files ship as an applicable patch: `patches/aurora-uwp.patch` |
| **`melee-pc`** (no license) | Its **two** files are not copied here. Both changes are **described** in [`docs/HOW-IT-WORKS.md`](docs/HOW-IT-WORKS.md): three `#if` lines and removing one `ShellExecuteA` |
| **The UWP layer and the tooling** (first-party) | All of it: the WinRT entry point, the MinGW CRT shim, the build translator, the packer and the disc splitter |

## What you need first

| | |
|---|---|
| `melee-pc` | **v0.2.2-beta** is what this was done with, and it has to be **building on your PC first**: its desktop build is the translator's input |
| Your own dump | Of your copy of *Melee* for GameCube |
| MSYS2 UCRT64 with **GCC** | Without this there is no port: it is the only one that understands `scalar_storage_order` |
| llvm-mingw (clang and `ld.lld`) | The C++ and the link |
| Visual Studio 2022 with the **C++ UWP component** | Its `store` environment, and `makeappx`/`signtool` from the Windows SDK |
| The UWP bundles | Dawn, SDL3 and `libuwp` built for UWP |
| Python 3, an Xbox in Developer Mode and a certificate | The scripts, the console and signing |

## How it goes

```powershell
# 1. Aurora (MIT), and melee-pc's two changes by hand (docs/HOW-IT-WORKS.md)
git apply --directory=C:\melee\melee-pc patches\aurora-uwp.patch
python tools\gpu_uwp.py C:\melee\melee-pc
python tools\system_info_uwp.py C:\melee\melee-pc

# 2. translate the desktop build into a UWP one (both compilers)
tools\construir-uwp.bat

# 3. package and sign
python tools\empaquetar_uwp.py --version 1.0.0.0 --certificado <your thumbprint>
```

Step by step, including the console side: **[`docs/INSTALL.md`](docs/INSTALL.md)**.

## What it had to solve

Seven packages in one evening, each fixing what the previous one uncovered. The detail is in
**[`docs/HOW-IT-WORKS.md`](docs/HOW-IT-WORKS.md)**.

| | Symptom | Fix |
|---|---|---|
| 1 | `FATAL: SDL not built with haptic support`, and the console returns to Dev Home | That SDL has no haptics and the game asked for every subsystem at once |
| 2 | The whole disc (1.06 GiB) gives **500** on the Device Portal. In two 900 MiB parts, 500 again; **in five 250 MiB parts, it works** | It goes up split, and the entry point joins it on first boot |
| 3 | "There is no Memory Card in Slot A" | UWP SDL3's `SDL_CreateDirectory` **does not create intermediate folders**, and the card lives in `<user>\USA\Card A` |
| 4 | `_beginthreadex not supported` | SDL3's headers compiled with MinGW pass `_beginthreadex`, and UWP SDL3 rejects it |
| 5 | **B** closed the game | On an Xbox it is also "back", and SDL has to be asked to handle it |
| 6 | **No button responded** (only the Xbox button, which is the system's) | UWP SDL3 ships Windows.Gaming.Input **switched off**, and that is the only route controllers take on a console. One hint, and the log starts saying `Added controller 'Xbox One Game Controller'` |
| 7 | Seven clang errors, a duplicate `WinMain`, `expf` defined twice, zlib twice, and 13 unresolved MinGW symbols | The toll for mixing two compilers: it is all in the guide |

## Credits and license

Port and tooling by **Recompilaciones**. Released under the [MIT](LICENSE), the license of
[Aurora](https://github.com/encounter/aurora) (© 2022 Luke Street), which is the third-party code
this repository patches.

*Super Smash Bros. Melee* is © Nintendo / HAL Laboratory. This project is not affiliated with them,
with Microsoft, or with the authors of the decompilation or the PC port, and distributes nothing
that belongs to them. The detail is in [`NOTICE.md`](NOTICE.md). Rights holders:
**jajdpmail@gmail.com**.
