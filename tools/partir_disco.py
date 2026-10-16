# Parte un archivo en trozos para subirlo por el Device Portal de la Xbox, que respondió 500 al subir
# el disco de Melee entero (1,06 GiB) y en partes de 900 MiB; en partes de 250 MiB, no (2026-10-01).
# La entrada UWP de Melee (uwp/entrada_uwp.cpp) los une al arrancar.
# Uso: py -3.13 partir_disco.py <archivo> [MiB por parte, 250 por defecto]
import hashlib
import os
import sys

ruta = sys.argv[1]
tam = (int(sys.argv[2]) if len(sys.argv) > 2 else 250) * 1024 * 1024
h = hashlib.sha1()
i = 0
with open(ruta, "rb") as f:
    while True:
        datos = f.read(tam)
        if not datos:
            break
        i += 1
        h.update(datos)
        destino = f"{ruta}.parte{i}"
        tmp = destino + ".tmp"
        with open(tmp, "wb") as o:
            o.write(datos)
        os.replace(tmp, destino)
        print(f"{destino}: {len(datos)} bytes")
print(f"{i} partes; SHA-1 del total {h.hexdigest()}")
