# Building the port and getting it onto the console

*(Español: [INSTALL.es.md](INSTALL.es.md))*

## 0. Before you start: where the commands go

Everything here goes in **PowerShell**, the ordinary Windows terminal: press the **Windows** key,
type `powershell` and press **Enter** on *Windows PowerShell*. To move to a folder use `cd` with the
path, in quotes if it has spaces; or open the folder in File Explorer, click the address bar, type
`powershell` over whatever is there and press **Enter**.

**No administrator is needed** anywhere. And in one step it **breaks** things: the certificate in §5
is created in the store of whoever runs the command, so elevated it would land in the
administrator's store and signing would not find it. The only thing that asks for administrator is
the Visual Studio installer.

**PowerShell 7 is not needed**: the one Windows ships is enough.

---

## 1. What you need first

| | What for |
|---|---|
| **MSYS2 UCRT64 with GCC** | **Essential.** The game's C uses `scalar_storage_order("big-endian")`, an extension only GCC implements |
| **llvm-mingw** (clang and `ld.lld`) | The C++ and the link, with the MSVC ABI |
| **Visual Studio 2022** with the **C++ UWP component** | Its `store` environment, and `makeappx`/`signtool` from the Windows SDK |
| **The UWP bundles** | Dawn, SDL3 and `libuwp` built for UWP |
| **Python 3** | The scripts |
| **Your dump** of *Melee* for GameCube | The game |
| **An Xbox in Developer Mode** and a certificate | Installing, and signing |

### The environment variables

The scripts carry no machine's paths inside them:

```powershell
$env:MELEE_SRC      = "C:\melee\melee-pc"        # the PC port's tree, already patched
$env:MELEE_TRABAJO  = "C:\melee\trabajo"         # where objects and .libs go
$env:MELEE_TOOLKIT  = "C:\melee\llvm-mingw\bin"  # clang and ld.lld
$env:MELEE_MSYS     = "C:\msys64\ucrt64"          # GCC and ninja
$env:MELEE_CERT     = "<your certificate's thumbprint>"
```

If one is missing, the script stops saying which and what it is for. The Windows SDK and Visual
Studio **are found**: no version is pinned.

---

## 2. `melee-pc`, and its desktop build

```powershell
git clone https://github.com/999sian/melee-pc.git C:\melee\melee-pc
```

This recipe was made against **v0.2.2-beta**.

⚠ **Build it and test it on your PC first**, with its own instructions and MSYS2. Two reasons: if it
does not run there it will not run on the console, and above all **the recipe comes out of that
build** — the translator reads its `compile_commands.json`, so it has to exist and be current.

---

## 3. The patches

**Aurora** (MIT), six files:

```powershell
git apply --directory=C:\melee\melee-pc patches\aurora-uwp.patch
```

If the patch does not apply cleanly — because your `melee-pc` is a different version — two of those
changes also come as guarded scripts, which tell you what does not match instead of leaving the file
half done:

```powershell
python tools\gpu_uwp.py C:\melee\melee-pc
python tools\system_info_uwp.py C:\melee\melee-pc
```

**`melee-pc`'s two files**, by hand. They are not a patch here because that project publishes no
license; they are three small things, explained precisely in
[`HOW-IT-WORKS.md`](HOW-IT-WORKS.md):

- in `src/pc/file_cache.cpp`, the `#include <unistd.h>` has to become conditional (clang with the
  MSVC ABI does not ship it, and only `sysconf` was used from it), and `S_ISDIR` and `S_ISREG` have
  to be defined, because MSVC's `sys/stat.h` does not have them;
- in `src/pc/updater.cpp`, the `ShellExecuteA` that opens a browser does not exist in UWP: it is
  left out with an `#if`, and the whole updater is replaced by `src/uwp/updater_uwp.cpp` (otherwise
  the executable ends up importing `WINHTTP.dll`, which will not load in an App Container).

All of the delta sits behind `AURORA_WINDOWS_STORE` or `MELEE_UWP`, so the same tree **still builds
for the PC**.

---

## 4. Building for the console

```powershell
tools\construir-uwp.bat
```

That `.bat` enters Visual Studio's **store** environment and calls `tools\construir_uwp.py`, which
is where the work is: it walks the desktop build's `compile_commands.json` and sends **each command
to GCC or to clang** depending on what it is (see the README), archives one `.lib` per target, and
links with `ld.lld`.

⚠ The link uses a **fixed base of `0x10000000`, no ASLR and no high entropy**. That is not caution:
the game keeps disc pointers in 32-bit slots, so everything it references has to live below 4 GB.

---

## 5. A certificate, and your identity in the manifest

```powershell
$c = New-SelfSignedCertificate -Type Custom -Subject "CN=YourName" `
       -KeyUsage DigitalSignature -FriendlyName "UWP signing" `
       -CertStoreLocation "Cert:\CurrentUser\My" `
       -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
$c.Thumbprint
```

And in `package\Package.appxmanifest`, the `CHANGE-ME`s: `Identity Name`, `Publisher` (**identical**
to your certificate's subject), `PublisherDisplayName` and `PhoneProductId`.

---

## 6. Tiles, packaging and signing

`package\Assets\` ships **empty on purpose**: [`ASSETS.md`](ASSETS.md) lists the names and sizes.

```powershell
python tools\empaquetar_uwp.py --version 1.0.0.0 --certificado=<your thumbprint>
```

⚠ **Bump the version for every new package**: the console will not replace a package whose version
matches the installed one, nor change its tiles.

---

## 7. Installing it on the console

### Before touching anything: how the console has to be

- **In Developer Mode**, with Dev Home installed.
- **On, and with your profile signed in.** ⚠ With no user signed in the console **will not launch
  apps**: the package installs, shows up in the list, and launching it does nothing.
- **On the same network as your PC**, with its address at hand (Dev Home shows it). The Device
  Portal listens on port **11443** over HTTPS and asks for the username and
  password you set in Dev Home.

Open `https://<ip>:11443`. ⚠ The browser will warn that the site's certificate is not trusted: it is
the console's own. Go in anyway — in Edge and Chrome, **Advanced** → **Continue to … (unsafe)**; in
Firefox, **Advanced** → **Accept the Risk and Continue**.

In **My games & apps → Add**: your `.msix`, and under **Dependency** the Windows SDK's
`Microsoft.VCLibs.x64.14.00.appx` the first time. **Certificate** is not needed.

---

## 8. The disc, split

The disc does **not** go inside the package: it is uploaded into the app's `LocalState`, which the
first launch creates.

And it has to be split. This was measured, not assumed:

| How it was uploaded | What the portal answered |
|---|---|
| Whole, 1.06 GiB | **500** |
| In two 900 MiB parts | **500** again |
| **In five 250 MiB parts** | **Fine** |

The exact reason for the 500 at 900 MiB was never established; at 250 MiB it works.

```powershell
python tools\partir_disco.py "C:\path\to\your\disc.rvz" C:\melee\parts 250
```

Upload the parts to `LocalState` with the portal's **File explorer**: the entry point joins them on
first boot and leaves the whole disc. The parts stay there (1.06 GiB) and can be deleted afterwards
through the portal without affecting the game.

The game's log ends up in `melee-salida.txt`, inside `LocalState`. On a console it is all you have.

---

## 9. Removing it from the console

⚠ **Your saves and your disc go with it**, since they live in the package's `LocalState`. Download
them first with the **File explorer** if you want to keep them. To update without losing them, do
not uninstall: install a package with a **higher version** on top.

---

## If something goes wrong

| Symptom | Cause |
|---|---|
| The package installs and launching does nothing | Is a **profile signed in**? And read `melee-salida.txt` in `LocalState` |
| `FATAL: SDL not built with haptic support` | The `input.cpp` change from the Aurora patch is missing |
| The portal answers 500 uploading the disc | It has to be split into 250 MiB parts (§8) |
| "There is no Memory Card in Slot A" | The `io.cpp` change is missing: that SDL's `SDL_CreateDirectory` does not create intermediate folders |
| `_beginthreadex not supported` | The C has to be compiled with `-DSDL_BeginThreadFunction=NULL` ([`HOW-IT-WORKS.md`](HOW-IT-WORKS.md)) |
| No button responds, only the Xbox button | The Windows.Gaming.Input hint is missing, which the entry point sets. The log says it: without it there is no `Added controller` line at all |
| **B** closes the game | `SDL_HINT_WINRT_HANDLE_BACK_BUTTON` is missing |
| The executable imports `WINHTTP.dll` and will not load | The updater has not been replaced with the empty one (§3) |
