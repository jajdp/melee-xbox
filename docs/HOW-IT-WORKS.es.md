# Cómo funciona, y por qué cada pieza está ahí

*(English: [HOW-IT-WORKS.md](HOW-IT-WORKS.md))*

## El obstáculo de verdad: el compilador

El código del juego describe los datos del disco con `scalar_storage_order("big-endian")`, una
extensión de GCC que **ningún otro compilador implementa**. Y los ports UWP de este catálogo se
hacen con clang y el ABI de MSVC, porque es lo que entiende el CRT «store» y el enlazador de
AppContainer.

Durante meses eso cerró el camino. La salida no fue elegir: fue **usar los dos compiladores a la
vez**, cada uno con lo que sabe hacer.

| Compilador | Qué compila | Objetos |
|---|---|---|
| **GCC** (MSYS2 UCRT64) | El C del juego, la matemática de Aurora y los `.c` del ejecutable | 1 048 |
| **clang** (llvm-mingw, `--target=x86_64-pc-windows-msvc`, `WINAPI_FAMILY_APP`) | El C++ entero (Aurora, RmlUi, abseil, imgui, fmt), freetype, sqlite3, xxhash, zstd y la capa UWP | 555 |

`tools/construir_uwp.py` recorre el `compile_commands.json` de la build de escritorio y traduce cada
orden a uno de los dos. Después archiva una `.lib` por objetivo —226— y enlaza con `ld.lld -flavor
link` en `/appcontainer`.

**Y el enlazado tiene condiciones raras**, que son del juego y no del port: base fija
`0x10000000`, `/dynamicbase:no`, `/highentropyva:no` y `/force:multiple`. Las tres primeras porque
el juego guarda punteros del disco en ranuras de **32 bits**: todo lo que referencia tiene que vivir
por debajo de 4 GB, y la MEM1 de la GameCube se reserva en una dirección concreta. La cuarta, porque
`expf` y familia están definidos dos veces, en `libgcc` y en el CRT.

## El peaje de mezclar dos compiladores

Lo que salió al enlazar, en el orden en que salió:

| | Qué pasó |
|---|---|
| `WinMain` duplicado | SDL genera el suyo: `-DSDL_MAIN_HANDLED` |
| `expf` y familia dos veces | En `libgcc` y en el CRT: `/force:multiple` |
| zlib dos veces | `nod.lib` es una biblioteca de Rust que ya la lleva dentro: fuera `z.lib` |
| 13 símbolos de MinGW sin resolver | Lo que los objetos de GCC piden al CRT de MinGW y el «store» no tiene: `__mingw_vfprintf` y familia, `sincos`, `gettimeofday`, los mutex y `pthread_once` de winpthreads. Están en `src/uwp/compat_mingw.c`, junto con un sustituto de `GetUserProfileDirectoryW`, que en UWP no existe |
| El ejecutable importaba `WINHTTP.dll` | Del actualizador. En un App Container esa DLL no carga: el actualizador se sustituye por uno vacío |
| Siete errores de clang | Los cinco cambios de Aurora de abajo, más el `ftsystem.c` de Windows (usa `CreateFileA`: se usa el genérico) y la configuración de freetype (sin bzip2) |

## Los seis cambios de Aurora

Van como parche aplicable, porque Aurora es MIT:

| Archivo | Por qué |
|---|---|
| `lib/dolphin/dvd/dvd.cpp` | `CreateFileA` y `CreateFileMappingA` no existen en UWP: `CreateFile2`, `CreateFileMappingFromApp` y `MapViewOfFileFromApp` |
| `lib/system_info.cpp` | Sin WMI en UWP: el modelo de CPU sale de `__cpuid` |
| `lib/dawn/BackendBinding.cpp` | La superficie de Dawn sale de la `CoreWindow`, con la referencia que da `libuwp.dll` |
| `lib/webgpu/gpu.cpp` | La Dawn de UWP es más antigua: sin `DawnNative.h`, solo los conmutadores de instancia, y la caché por `loadDataFunction`/`storeDataFunction` |
| `lib/input.cpp` | `SDL_Init` con `SDL_INIT_HAPTIC` **falla** en ese SDL y el juego moría con FATAL: se inician solo joystick y gamepad |
| `lib/io.cpp` | El `SDL_CreateDirectory` del SDL3 de UWP **no crea las carpetas intermedias**, y la tarjeta de memoria va en `<usuario>\USA\Card A`. Resultado: «There is no Memory Card in Slot A». En UWP se usa `std::filesystem::create_directories` |

## Los dos cambios de `melee-pc`, descritos

Ese proyecto no publica licencia, así que aquí no va su código
([`NOTICE.es.md`](../NOTICE.es.md)). Son pequeños:

- **`src/pc/file_cache.cpp`**: el `#include <unistd.h>` tiene que quedar fuera cuando se compila con
  el ABI de MSVC —ahí solo se usaba `sysconf`—, y hay que definir `S_ISDIR` y `S_ISREG`, que el
  `sys/stat.h` de MSVC no trae, a partir de `_S_IFMT`, `_S_IFDIR` y `_S_IFREG`.
- **`src/pc/updater.cpp`**: la función que abre el navegador usa `ShellExecuteA`, que es de
  escritorio. Se deja fuera con un `#if` en la compilación de UWP, y el actualizador entero se
  sustituye por `src/uwp/updater_uwp.cpp`, que es una API vacía. Sin eso, el ejecutable importa
  `WINHTTP.dll` y no carga en la consola.

## La capa UWP propia

- **`src/uwp/entrada_uwp.cpp`** es la entrada, y hace seis cosas: localiza el `LocalState`, manda la
  salida a un archivo de ahí (en UWP no hay consola), lee un archivo de entorno y lo mete en el CRT
  con `_putenv_s` —en UWP `getenv` no ve el entorno del sistema, pero sí el del CRT—, **une las
  partes del disco**, busca el disco y entra al juego por `SDL_RunApp`. Y pide dos cosas a SDL:
  - `SDL_HINT_WINRT_HANDLE_BACK_BUTTON`, porque en la Xbox la **B** es «atrás» y, si nadie la
    atiende, cierra la aplicación;
  - `SDL_HINT_JOYSTICK_WGI`, sin la cual **no hay mando**: el SDL3 de UWP trae apagado
    Windows.Gaming.Input, que es la única vía por la que llegan los mandos en una consola. El
    usuario probó el port y no respondía ningún botón salvo el del sistema; en el registro no había
    ni una línea `Added controller`. Con la pista, aparece
    `Added controller 'Xbox One Game Controller'`.
- **`src/uwp/compat_mingw.c`**: los 13 símbolos de arriba.
- **`src/uwp/updater_uwp.cpp`**: el actualizador vacío.

## Siete paquetes en una tarde

Así se vio cada cosa, y en este orden:

| | Qué pasó |
|---|---|
| 1 | Arranca: D3D12 sobre la GPU de la consola, 1920×1080, y siembra 11 905 tuberías de su caché. Y muere con `FATAL … SDL not built with haptic support` |
| 2 | Ya no muere. Falta el disco, y el portal responde **500** con 1,06 GiB |
| 3 | En dos partes de 900 MiB, **500 otra vez**; en cinco de 250 MiB, bien. Ahora: «There is no Memory Card in Slot A», y el hilo de entrada falla con `_beginthreadex not supported` |
| 4 | Tarjeta creada y el hilo de 1 000 Hz en marcha. El `_beginthreadex` era que las cabeceras de SDL3 compiladas con MinGW lo pasan, y el SDL3 de UWP lo rechaza: se compila el C con `-DSDL_BeginThreadFunction=NULL` |
| 5 | «Create Game Data? Yes / No», con la **B** ya atendida |
| 6 | **El mando no respondía.** La pista de Windows.Gaming.Input |
| 7 | Los mosaicos |

Y después: el usuario creó la partida y jugó. Sin mando, una partida de cuatro CPU de cuatro minutos
dio **59,86 FPS de media**, y los únicos cuadros lentos coinciden con las capturas que se le estaban
sacando.

## Lo que falta

- **La suspensión del modo desarrollador**: al volver de Home el juego empieza de nuevo.
- El aviso `aurora::card: Failed to close file at idx: 0` sale dos veces antes de crear la partida.
  En PC sale igual y es inocuo.
