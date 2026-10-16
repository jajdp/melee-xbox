# Aviso

*(English: [NOTICE.md](NOTICE.md))*

## Sin afiliación

Esto es un proyecto de aficionado, no oficial y sin ánimo de lucro. **No está afiliado a Nintendo,
HAL Laboratory ni Microsoft**, ni cuenta con su respaldo, ni lo está con
[doldecomp](https://github.com/doldecomp/melee), ni con el autor de
[`melee-pc`](https://github.com/999sian/melee-pc), ni con el de
[Aurora](https://github.com/encounter/aurora). *Super Smash Bros. Melee*, *Xbox* y todos los nombres
y marcas relacionados son de sus respectivos propietarios.

Aquí no se vende nada, y nada de esto está monetizado.

## Qué no distribuye este repositorio

Ni imagen del disco. Ni datos ni recursos del juego. Ni ejecutable compilado. Ni `.msix`. Ni
partidas ni tarjetas de memoria. Ni mosaicos del paquete (`package/Assets/` está vacía).

**Ni ninguna de las bibliotecas de UWP**: Dawn, SDL3 y `libuwp` son binarios de otros.

## Qué contiene de trabajo de otros

**Parches contra Aurora.** `patches/aurora-uwp.patch` (seis archivos) y los dos scripts de `tools/`
modifican [Aurora](https://github.com/encounter/aurora), que es **MIT**, © 2022 Luke Street. La MIT
permite versiones modificadas; este repositorio se publica bajo [esa misma licencia](LICENSE),
llevando con él el aviso de Aurora.

**Nada de `melee-pc`.** Ese proyecto no publica licencia, así que **aquí no se reproduce ni una
línea suya**: el diff completo del port tocaba dos de sus archivos, y esos dos bloques se sacaron
del parche. Lo que hacen está *descrito* en `docs/HOW-IT-WORKS.es.md` —un `unistd.h` que tiene que
ser condicional, dos macros de `stat` que MSVC no define y un `ShellExecuteA` que en UWP hay que
quitar—. Eso es una descripción técnica, no su código.

**La capa UWP de `src/uwp/`** es propia: la entrada WinRT, un relleno de lo que los objetos de GCC
piden al CRT de MinGW y el CRT «store» no tiene, y un actualizador vacío.

**Aquí no hay capturas de pantalla.** Una captura de esto funcionando sería casi toda arte de
Nintendo.

## Retirada y contacto

Si tienes derechos sobre este material y quieres que algo de aquí se quite o se cambie, escribe a
**jajdpmail@gmail.com** diciendo a qué te opones y en calidad de qué escribes. Las peticiones de
quien tiene los derechos se atienden sin discutir, y recibirás una respuesta confirmándolo.
