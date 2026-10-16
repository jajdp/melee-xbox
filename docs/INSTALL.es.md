# Construir el port y meterlo en la consola

*(English: [INSTALL.md](INSTALL.md))*

## 0. Antes de empezar: dónde se escriben las órdenes

Todo lo de esta guía va en **PowerShell**, la terminal normal de Windows: pulsa la tecla
**Windows**, escribe `powershell` y pulsa **Enter** sobre *Windows PowerShell*. Para ir a una
carpeta, `cd` con la ruta entre comillas si tiene espacios; o abre la carpeta en el Explorador, haz
clic en la barra de direcciones, escribe `powershell` encima y pulsa **Enter**.

**No hace falta administrador** en ningún paso. Y en uno concreto, usarlo lo **estropea**: el
certificado del §5 se crea en el almacén del usuario que ejecuta la orden, así que elevado acabaría
en el del administrador y la firma no lo encontraría. Lo único que pide administrador es el
instalador de Visual Studio.

**PowerShell 7 no hace falta**: con la que trae Windows basta.

---

## 1. Lo que hace falta antes

| | Para qué |
|---|---|
| **MSYS2 UCRT64 con GCC** | **Imprescindible.** El C del juego usa `scalar_storage_order("big-endian")`, una extensión que solo GCC implementa |
| **llvm-mingw** (clang y `ld.lld`) | El C++ y el enlazado, con el ABI de MSVC |
| **Visual Studio 2022** con el componente de **UWP para C++** | Su entorno `store`, y el `makeappx`/`signtool` del Windows SDK |
| **Los bundles de UWP** | Dawn, SDL3 y `libuwp` compilados para UWP |
| **Python 3** | Los scripts |
| **Tu volcado** de *Melee* de GameCube | El juego |
| **Una Xbox en modo desarrollador** y un certificado | Instalar y firmar |

### Las variables de entorno

Los scripts no llevan ninguna ruta de ninguna máquina dentro:

```powershell
$env:MELEE_SRC      = "C:\melee\melee-pc"        # el arbol del port de PC, ya parcheado
$env:MELEE_TRABAJO  = "C:\melee\trabajo"         # donde van los objetos y las .lib
$env:MELEE_TOOLKIT  = "C:\melee\llvm-mingw\bin"  # clang y ld.lld
$env:MELEE_MSYS     = "C:\msys64\ucrt64"          # GCC y ninja
```

Si falta una, el script se detiene diciendo cuál y para qué sirve. El Windows SDK y Visual Studio
**se buscan**: no hay ninguna versión fijada.

---

## 2. `melee-pc`, y su build de escritorio

```powershell
git clone https://github.com/999sian/melee-pc.git C:\melee\melee-pc
```

Esta receta se hizo contra la **v0.2.2-beta**.

⚠ **Compílalo y pruébalo en tu PC primero**, con sus propias instrucciones y con MSYS2. Dos
razones: si no corre ahí no va a correr en la consola, y sobre todo que **de esa build sale la
receta**: el traductor lee su `compile_commands.json`, así que tiene que existir y estar al día.

---

## 3. Los parches

**Aurora** (MIT), seis archivos:

```powershell
git apply --directory=C:\melee\melee-pc patches\aurora-uwp.patch
```

Si el parche no entra limpio —porque tu `melee-pc` no es la misma versión—, dos de esos cambios van
también como scripts con anclas, que te dicen qué no cuadra en vez de dejar el archivo a medias:

```powershell
python tools\gpu_uwp.py C:\melee\melee-pc
python tools\system_info_uwp.py C:\melee\melee-pc
```

**Los dos archivos de `melee-pc`**, a mano. Aquí no van como parche porque ese proyecto no publica
licencia; son tres cosas pequeñas, y están explicadas con precisión en
[`HOW-IT-WORKS.es.md`](HOW-IT-WORKS.es.md):

- en `src/pc/file_cache.cpp`, el `#include <unistd.h>` tiene que ser condicional (clang con ABI de
  MSVC no lo trae, y ahí solo se usaba `sysconf`), y hay que definir `S_ISDIR` y `S_ISREG`, que el
  `sys/stat.h` de MSVC no tiene;
- en `src/pc/updater.cpp`, el `ShellExecuteA` que abre el navegador no existe en UWP: se deja fuera
  con un `#if`, y el actualizador lo sustituye `src/uwp/updater_uwp.cpp` (si no, el ejecutable
  acaba importando `WINHTTP.dll`, que en un App Container no carga).

Todo el delta queda detrás de `AURORA_WINDOWS_STORE` o `MELEE_UWP`, así que el mismo árbol **sigue
compilando para PC**.

---

## 4. Compilar para la consola

```powershell
tools\construir-uwp.bat
```

Ese `.bat` entra al entorno **store** de Visual Studio y llama a `tools\construir_uwp.py`, que es
donde está el trabajo: recorre el `compile_commands.json` de la build de escritorio y manda **cada
orden a GCC o a clang** según lo que sea (§«Lo que hace raro a este port», en el README), archiva
una `.lib` por objetivo y enlaza con `ld.lld`.

⚠ El enlazado va con **base fija `0x10000000`, sin ASLR y sin entropía alta**. No es una
precaución: el juego guarda punteros del disco en ranuras de 32 bits, así que todo lo que referencia
tiene que vivir por debajo de 4 GB.

---

## 5. Un certificado, y tu identidad en el manifiesto

```powershell
$c = New-SelfSignedCertificate -Type Custom -Subject "CN=TuNombre" `
       -KeyUsage DigitalSignature -FriendlyName "Firma UWP" `
       -CertStoreLocation "Cert:\CurrentUser\My" `
       -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
$c.Thumbprint
```

Y en `package\Package.appxmanifest`, los `CHANGE-ME`: `Identity Name`, `Publisher` (**idéntico** al
sujeto de tu certificado), `PublisherDisplayName` y el `PhoneProductId`.

---

## 6. Los mosaicos, empaquetar y firmar

`package\Assets\` viene **vacía a propósito**: [`ASSETS.es.md`](ASSETS.es.md) dice los nombres y
medidas.

```powershell
python tools\empaquetar_uwp.py --version 1.0.0.0 --certificado <tu huella>
```

⚠ **La versión sube en cada paquete nuevo**: la consola no reemplaza un paquete por otro de la misma
versión, ni cambia sus mosaicos.

---

## 7. Instalarlo en la consola

### Antes de tocar nada: cómo tiene que estar la consola

- **En modo desarrollador**, con Dev Home instalado.
- **Encendida y con tu perfil iniciado.** ⚠ Sin un usuario conectado, la consola **no abre
  aplicaciones**: el paquete se instala, aparece en la lista y al lanzarlo no pasa nada.
- **En la misma red que tu PC**, y con su dirección a mano (la dice Dev Home). El Device Portal
  escucha en el puerto **11443** por HTTPS y pide el usuario y la contraseña
  que definiste en Dev Home.

Abre `https://<ip>:11443`. ⚠ El navegador avisará de que el certificado del sitio no es de
confianza: es el de la propia consola. Entra igual — en Edge y Chrome, **Avanzado** → **Continuar
a … (no seguro)**; en Firefox, **Avanzado** → **Aceptar el riesgo y continuar**.

En **My games & apps → Add**: tu `.msix`, y en **Dependency** el `Microsoft.VCLibs.x64.14.00.appx`
del Windows SDK la primera vez. **Certificate** no hace falta.

---

## 8. El disco, partido

El disco **no va dentro del paquete**: se sube al `LocalState` de la aplicación, que crea el primer
arranque.

Y hay que partirlo. Esto se midió, no se supuso:

| Cómo se subió | Qué contestó el portal |
|---|---|
| Entero, 1,06 GiB | **500** |
| En dos partes de 900 MiB | **500** otra vez |
| **En cinco partes de 250 MiB** | **Bien** |

El motivo exacto del 500 con 900 MiB no se averiguó; con 250 MiB va.

```powershell
python tools\partir_disco.py "C:\ruta\a\tu\disco.rvz" C:\melee\partes 250
```

Sube las partes a `LocalState` con el **File explorer** del portal: la entrada las une en el primer
arranque y deja el disco entero. Las partes se quedan ahí (1,06 GiB) y se pueden borrar después
desde el portal sin afectar al juego.

El registro del juego queda en `melee-salida.txt`, dentro del `LocalState`. En una consola es lo
único que tienes.

---

## 9. Quitarlo de la consola

⚠ **Se van tus partidas y tu disco**, que viven en el `LocalState` del paquete. Bájalos antes con el
**File explorer** si quieres conservarlos. Para actualizar sin perderlos, no desinstales: instala
encima un paquete con una **versión mayor**.

---

## Si algo no sale bien

| Síntoma | Causa |
|---|---|
| El paquete instala y al abrirlo no pasa nada | ¿Hay un **perfil iniciado**? Y mira `melee-salida.txt` en el `LocalState` |
| `FATAL: SDL not built with haptic support` | Falta el cambio de `input.cpp` del parche de Aurora |
| El portal responde 500 al subir el disco | Hay que partirlo en trozos de 250 MiB (§8) |
| «There is no Memory Card in Slot A» | Falta el cambio de `io.cpp`: el `SDL_CreateDirectory` de ese SDL no crea las carpetas intermedias |
| `_beginthreadex not supported` | Falta compilar el C con `-DSDL_BeginThreadFunction=NULL` ([`HOW-IT-WORKS.es.md`](HOW-IT-WORKS.es.md)) |
| Ningún botón responde, solo el botón Xbox | Falta la pista de Windows.Gaming.Input, que pone la entrada. El registro lo dice: sin ella no hay ninguna línea `Added controller` |
| La **B** cierra el juego | Falta `SDL_HINT_WINRT_HANDLE_BACK_BUTTON` |
| El ejecutable importa `WINHTTP.dll` y no carga | Falta sustituir el actualizador por el vacío (§3) |
