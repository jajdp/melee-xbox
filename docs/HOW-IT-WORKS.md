# How it works, and why each piece is there

*(Español: [HOW-IT-WORKS.es.md](HOW-IT-WORKS.es.md))*

## The real obstacle: the compiler

The game's code describes the disc's data with `scalar_storage_order("big-endian")`, a GCC extension
**no other compiler implements**. And the UWP ports in this catalogue are built with clang and the
MSVC ABI, because that is what the "store" CRT and the App Container linker understand.

For months that closed the road. The way out was not choosing: it was **using both compilers at
once**, each on what it can do.

| Compiler | What it compiles | Objects |
|---|---|---|
| **GCC** (MSYS2 UCRT64) | The game's C, Aurora's matrix maths and the executable's `.c` files | 1 048 |
| **clang** (llvm-mingw, `--target=x86_64-pc-windows-msvc`, `WINAPI_FAMILY_APP`) | All the C++ (Aurora, RmlUi, abseil, imgui, fmt), freetype, sqlite3, xxhash, zstd and the UWP layer | 555 |

`tools/construir_uwp.py` walks the desktop build's `compile_commands.json` and translates each
command to one of the two. It then archives one `.lib` per target — 226 — and links with
`ld.lld -flavor link` in `/appcontainer` mode.

**And the link has odd conditions**, which belong to the game and not to the port: a fixed base of
`0x10000000`, `/dynamicbase:no`, `/highentropyva:no` and `/force:multiple`. The first three because
the game keeps disc pointers in **32-bit** slots: everything it references has to live below 4 GB,
and the GameCube's MEM1 is reserved at a specific address. The fourth because `expf` and friends are
defined twice, in `libgcc` and in the CRT.

## The toll for mixing two compilers

What came up at link time, in the order it came up:

| | What happened |
|---|---|
| Duplicate `WinMain` | SDL generates its own: `-DSDL_MAIN_HANDLED` |
| `expf` and friends twice | In `libgcc` and in the CRT: `/force:multiple` |
| zlib twice | `nod.lib` is a Rust library that already carries it: drop `z.lib` |
| 13 unresolved MinGW symbols | What GCC's objects ask of MinGW's CRT and the "store" one does not have: `__mingw_vfprintf` and friends, `sincos`, `gettimeofday`, winpthreads' mutexes and `pthread_once`. They are in `src/uwp/compat_mingw.c`, along with a stand-in for `GetUserProfileDirectoryW`, which does not exist in UWP |
| The executable imported `WINHTTP.dll` | From the updater. In an App Container that DLL will not load: the updater is replaced by an empty one |
| Seven clang errors | The five Aurora changes below, plus Windows' `ftsystem.c` (it uses `CreateFileA`: the generic one is used instead) and freetype's configuration (no bzip2) |

## The six Aurora changes

They ship as an applicable patch, because Aurora is MIT:

| File | Why |
|---|---|
| `lib/dolphin/dvd/dvd.cpp` | `CreateFileA` and `CreateFileMappingA` do not exist in UWP: `CreateFile2`, `CreateFileMappingFromApp` and `MapViewOfFileFromApp` |
| `lib/system_info.cpp` | No WMI in UWP: the CPU model comes from `__cpuid` |
| `lib/dawn/BackendBinding.cpp` | Dawn's surface comes from the `CoreWindow`, through the reference `libuwp.dll` provides |
| `lib/webgpu/gpu.cpp` | UWP's Dawn is older: no `DawnNative.h`, only the instance toggles, and caching through `loadDataFunction`/`storeDataFunction` |
| `lib/input.cpp` | `SDL_Init` with `SDL_INIT_HAPTIC` **fails** on that SDL and the game died with FATAL: only joystick and gamepad are started |
| `lib/io.cpp` | UWP SDL3's `SDL_CreateDirectory` **does not create intermediate folders**, and the memory card lives in `<user>\USA\Card A`. Result: "There is no Memory Card in Slot A". In UWP, `std::filesystem::create_directories` |

## `melee-pc`'s two changes, described

That project publishes no license, so its code is not here
([`NOTICE.md`](../NOTICE.md)). They are small:

- **`src/pc/file_cache.cpp`**: the `#include <unistd.h>` has to be excluded when building with the
  MSVC ABI — only `sysconf` was used from it — and `S_ISDIR` and `S_ISREG` have to be defined, which
  MSVC's `sys/stat.h` does not provide, from `_S_IFMT`, `_S_IFDIR` and `_S_IFREG`.
- **`src/pc/updater.cpp`**: the function that opens a browser uses `ShellExecuteA`, which is
  desktop-only. It is excluded with an `#if` in the UWP build, and the whole updater is replaced by
  `src/uwp/updater_uwp.cpp`, an empty API. Without that, the executable imports `WINHTTP.dll` and
  will not load on the console.

## The port's own UWP layer

- **`src/uwp/entrada_uwp.cpp`** is the entry point, and it does six things: finds `LocalState`,
  redirects output to a file there (there is no console in UWP), reads an environment file and pushes
  it into the CRT with `_putenv_s` — in UWP `getenv` does not see the system environment, but it does
  see the CRT's — **joins the split disc**, finds the disc, and enters the game through
  `SDL_RunApp`. And it asks SDL for two things:
  - `SDL_HINT_WINRT_HANDLE_BACK_BUTTON`, because on an Xbox **B** is also "back" and, if nobody
    handles it, it closes the app;
  - `SDL_HINT_JOYSTICK_WGI`, without which **there is no controller**: UWP SDL3 ships
    Windows.Gaming.Input switched off, and that is the only route controllers take on a console. The
    user tried the port and no button responded except the system's; the log had no `Added
    controller` line at all. With the hint, `Added controller 'Xbox One Game Controller'` shows up.
- **`src/uwp/compat_mingw.c`**: the 13 symbols above.
- **`src/uwp/updater_uwp.cpp`**: the empty updater.

## Seven packages in one evening

This is how each thing showed up, and in this order:

| | What happened |
|---|---|
| 1 | It boots: D3D12 on the console's GPU, 1920×1080, and it seeds 11 905 pipelines from its cache. Then dies with `FATAL … SDL not built with haptic support` |
| 2 | No longer dies. The disc is missing, and the portal answers **500** to 1.06 GiB |
| 3 | In two 900 MiB parts, **500 again**; in five 250 MiB ones, fine. Now: "There is no Memory Card in Slot A", and the input thread fails with `_beginthreadex not supported` |
| 4 | Card created and the 1 000 Hz thread running. The `_beginthreadex` was SDL3's headers compiled with MinGW passing it, and UWP SDL3 rejecting it: the C is compiled with `-DSDL_BeginThreadFunction=NULL` |
| 5 | "Create Game Data? Yes / No", with **B** now handled |
| 6 | **The controller did not respond.** The Windows.Gaming.Input hint |
| 7 | The tiles |

And afterwards: the user created the save and played. With no controller, a four-minute four-CPU
match averaged **59.86 FPS**, and the only slow frames coincide with the screenshots being taken.

## What is missing

- **Developer Mode suspension**: coming back from Home, the game starts over.
- The warning `aurora::card: Failed to close file at idx: 0` shows up twice before the save is
  created. It does the same on the PC and is harmless.
