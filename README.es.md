# Super Smash Bros. Melee en la Xbox — el port UWP

Cómo coger el port de PC de *Super Smash Bros. Melee* (GameCube, 2001) —
[`999sian/melee-pc`](https://github.com/999sian/melee-pc), sobre la decompilación de
[doldecomp](https://github.com/doldecomp/melee)— y hacerlo correr **en una Xbox Series en modo
desarrollador**, como un paquete UWP que compilas y firmas tú.

*(English: [README.md](README.md))*

No es una teoría: el juego arranca, lee el disco, crea la tarjeta de memoria, **se juega con mando**
y va a **59,86 FPS de media** (medidos en una partida de cuatro CPU de cuatro minutos).

## Lo que hace raro a este port: dos compiladores

El código del juego describe los datos del disco con `scalar_storage_order("big-endian")`, una
extensión que **solo implementa GCC**. Los demás ports UWP de este catálogo se hacen con clang y el
ABI de MSVC, y clang no la tiene.

La salida es usar **los dos a la vez**, y es lo que hace `tools/construir_uwp.py`: recorre el
`compile_commands.json` de la build de escritorio y manda cada orden a uno o a otro.

| Compilador | Qué compila | Objetos |
|---|---|---|
| **GCC** (MSYS2 UCRT64) | El C del juego, la matemática de Aurora y los `.c` del propio ejecutable | 1 048 |
| **clang** (llvm-mingw, `--target=x86_64-pc-windows-msvc`, `WINAPI_FAMILY_APP`) | El C++ (Aurora, RmlUi, abseil, imgui, fmt), freetype, sqlite3, xxhash, zstd y la capa UWP propia | 555 |

Después archiva una `.lib` por objetivo —226— y enlaza con `ld.lld` en modo `/appcontainer`, con
**base fija `0x10000000`, sin ASLR y sin entropía alta**, porque el juego guarda punteros del disco
en ranuras de 32 bits y todo lo que referencia tiene que vivir por debajo de 4 GB.

## Qué es este repositorio, y qué no

**Una receta y las herramientas que la aplican**, aplicadas a tu propia copia de `melee-pc`.

Aquí no hay **disco, ni datos del juego, ni ejecutable, ni `.msix`, ni mosaicos, ni las bibliotecas
de UWP** (Dawn, SDL3, `libuwp`), que son binarios de otros.

Y hay un reparto que conviene entender, porque es lo que decide qué se puede publicar:

| | |
|---|---|
| **Aurora** (MIT, © 2022 Luke Street) | Sus **seis** archivos van como parche aplicable: `patches/aurora-uwp.patch` |
| **`melee-pc`** (sin licencia) | Sus **dos** archivos no se copian aquí. Los dos cambios están **descritos** en [`docs/HOW-IT-WORKS.es.md`](docs/HOW-IT-WORKS.es.md): son tres líneas de `#if` y quitar un `ShellExecuteA` |
| **La capa UWP y las herramientas** (nuestras) | Todo: la entrada WinRT, el relleno del CRT de MinGW, el traductor de la compilación, el empaquetador y el partidor del disco |

## Qué hace falta antes

| | |
|---|---|
| `melee-pc` | **v0.2.2-beta** es con la que se hizo esto, y **compilando en tu PC primero**: su build de escritorio es la entrada del traductor |
| Tu propio volcado | De tu copia de *Melee* de GameCube |
| MSYS2 UCRT64 con **GCC** | Sin esto no hay port: es el único que entiende `scalar_storage_order` |
| llvm-mingw (clang y `ld.lld`) | El C++ y el enlazado |
| Visual Studio 2022 con el componente de **UWP para C++** | Su entorno `store`, y el `makeappx`/`signtool` del Windows SDK |
| Los bundles de UWP | Dawn, SDL3 y `libuwp` compilados para UWP |
| Python 3, una Xbox en modo desarrollador y un certificado | Los scripts, la consola y la firma |

## Cómo va

```powershell
# 1. Aurora (MIT), y los dos cambios de melee-pc a mano (docs/HOW-IT-WORKS.es.md)
git apply --directory=C:\melee\melee-pc patches\aurora-uwp.patch
python tools\gpu_uwp.py C:\melee\melee-pc
python tools\system_info_uwp.py C:\melee\melee-pc

# 2. traducir la compilación de escritorio a UWP (los dos compiladores)
tools\construir-uwp.bat

# 3. empaquetar y firmar
python tools\empaquetar_uwp.py --version 1.0.0.0 --certificado <tu huella>
```

Paso a paso, con el lado de la consola: **[`docs/INSTALL.es.md`](docs/INSTALL.es.md)**.

## Qué hubo que resolver

Siete paquetes en una tarde, cada uno arreglando lo que el anterior destapó. El detalle está en
**[`docs/HOW-IT-WORKS.es.md`](docs/HOW-IT-WORKS.es.md)**.

| | Síntoma | Arreglo |
|---|---|---|
| 1 | `FATAL: SDL not built with haptic support`, y la consola vuelve a Dev Home | Ese SDL no trae háptica y el juego pedía todos los subsistemas de golpe |
| 2 | El disco entero (1,06 GiB) da **500** en el Device Portal. En dos partes de 900 MiB, otra vez 500; **en cinco de 250 MiB, sí** | Se parte, y la entrada lo une en el primer arranque |
| 3 | «There is no Memory Card in Slot A» | El `SDL_CreateDirectory` del SDL3 de UWP **no crea las carpetas intermedias**, y la tarjeta va en `<usuario>\USA\Card A` |
| 4 | `_beginthreadex not supported` | Las cabeceras de SDL3 compiladas con MinGW pasan `_beginthreadex`, y el SDL3 de UWP lo rechaza |
| 5 | La **B** cerraba el juego | En la Xbox es también «atrás», y hay que pedir a SDL que la atienda |
| 6 | **Ningún botón respondía** (solo el botón Xbox, que es del sistema) | El SDL3 de UWP trae **apagado** Windows.Gaming.Input, que es la única vía de los mandos en la consola. Una pista, y el registro pasa a decir `Added controller 'Xbox One Game Controller'` |
| 7 | Siete errores de clang, `WinMain` duplicado, `expf` definido dos veces, zlib dos veces y 13 símbolos de MinGW sin resolver | El peaje de mezclar dos compiladores: está todo en la guía |

## Créditos y licencia

Port y herramientas de **Recompilaciones**. Publicado bajo la [MIT](LICENSE), la licencia de
[Aurora](https://github.com/encounter/aurora) (© 2022 Luke Street), que es el código de terceros que
este repositorio parchea.

*Super Smash Bros. Melee* es © Nintendo / HAL Laboratory. Este proyecto no está afiliado a ellos, ni
a Microsoft, ni a los autores de la decompilación o del port de PC, y no distribuye nada que les
pertenezca. El detalle está en [`NOTICE.es.md`](NOTICE.es.md). Quien tenga derechos puede escribir a
**jajdpmail@gmail.com**.
