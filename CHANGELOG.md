# Changelog

All notable changes to this repository. Dates are `YYYY-MM-DD`.

The versions here are **the repository's**, not the package's. The package version is whatever you
pass to the packer, and it has to go up on every package you install.

## [1.0.2] — 2026-10-20

### Changed

- **The comments no longer name the author's own console.** Several of them said measurements were
  taken on "la xbox series cuarto" — a machine name that means nothing to anyone else and should never
  have left the private project. They now say "an Xbox Series X", which is the fact that matters. Only
  comments changed; every number and every date is the same.
- **The README now says which console this was tested on, and which one it was not.** Everything here
  was built and measured on an **Xbox Series X** in Developer Mode; a **Series S has never been tried**,
  so nothing here says anything about one. The wording used to say "Xbox Series", which reads as if it
  covered both, and it does not.

## [1.0.1] — 2026-10-13

### Fixed

- **The two path-substitution tables no longer carry this machine's paths as keys.**
  `SUSTITUIR_INC` and `SUSTITUIR_FUENTE` are compared against what *your* tree's
  `compile_commands.json` says, so with hardcoded keys they would never have matched on another
  machine — and the substitutions they exist for (UWP's headers, and freetype's generic
  `ftsystem.c` instead of the Windows one that opens with `CreateFileA`) would have been skipped
  **silently**, with the build failing later and elsewhere. They are now derived from `MELEE_SRC`.
- The packer's docstring no longer quotes a certificate thumbprint.

## [1.0.0] — 2026-10-13

First publication. The recipe for the UWP port, as it was applied to the build that is played with a
controller on a real Xbox Series X at 59.86 FPS.

### Added

- **`tools/construir_uwp.py`** — the translator, and the reason this port exists at all: it walks
  the desktop build's `compile_commands.json` and sends each command to **GCC or clang** depending
  on what it is. The game's C needs GCC, because `scalar_storage_order("big-endian")` is a GCC-only
  extension; everything else goes to clang with the MSVC ABI. Then one `.lib` per target and a link
  with `ld.lld` at a fixed base, no ASLR, no high entropy.
- **`patches/aurora-uwp.patch`** — the six Aurora files the port changes: `CreateFile2` instead of
  the desktop-only calls, the CPU model without WMI, Dawn's surface from the `CoreWindow`, the older
  UWP Dawn's API, `SDL_Init` without haptics, and `create_directories` for the memory card's path.
- **`tools/gpu_uwp.py`** and **`tools/system_info_uwp.py`** — two of those changes as guarded
  scripts, for trees where the patch does not apply cleanly.
- **`src/uwp/`** — the WinRT entry point (which joins the split disc, redirects output to a file in
  `LocalState`, loads an environment file, asks SDL to handle **B**, and sets the
  Windows.Gaming.Input hint without which no controller is ever seen), a shim for the MinGW CRT
  symbols the "store" CRT lacks, and an empty updater so the executable does not import
  `WINHTTP.dll`.
- **`tools/empaquetar_uwp.py`**, **`tools/partir_disco.py`**, **`tools/censo_compdb.py`** — the
  packer, the splitter (the portal answers 500 to 1.06 GiB, and to 900 MiB parts, but takes 250 MiB
  ones) and a small census of what the compile database contains.
- **Documentation in both languages**, with the seven packages of that first evening and what each
  one fixed.

### Not included, on purpose

- The disc, the game data, the executable, the `.msix`, the saves and the package tiles.
- **`melee-pc`'s two files.** That project has no license, so its blocks were split out of the
  patch and are described instead.
- The UWP libraries (Dawn, SDL3, `libuwp`): other people's binaries.
