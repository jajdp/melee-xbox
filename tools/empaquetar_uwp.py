# -*- coding: utf-8 -*-
"""Arma y firma el .msix del port UWP de Melee (Decompilaciones).

Uso:  py -3.13 empaquetar_uwp.py <versión, p. ej. 0.1.0.0>

Contenido: melee.exe, las DLL UWP (SDL3 de uwp-dep-sdl; Dawn, DXC, libpng, zlib y libuwp de
uwp-dep), resources\\ de melee-pc, initial_pipeline_cache.db (la semilla de shaders que también
reparte la build de Windows), el manifiesto y los mosaicos. Los mosaicos salen del arte del
usuario en dependencias-usuario\\Display Images\\ (xbox-sq1/sq2, xbox-ss1/ss2) por medio de
herramientas\\identidad-visual.py --aplicar-a, que además pone el nombre del Excel; los neutros
generados aquí solo quedan donde no haya arte (el mosaico ancho, que la Xbox no dibuja).
El disco NO va dentro: se sube a LocalState por el Device Portal.
Firma con TU certificado del almacén del usuario: la huella se da en --certificado= o en
la variable MELEE_CERT (docs/INSTALL.es.md §5).
"""
import gzip
import shutil
import subprocess
import sys
from pathlib import Path


def _entorno(nombre, que):
    """La ruta de la variable de entorno `nombre`, o un error que dice cual falta."""
    import os
    v = os.environ.get(nombre)
    if not v:
        raise SystemExit('falta la variable de entorno %s (%s). docs/INSTALL.es.md §2.'
                         % (nombre, que))
    if not Path(v).exists():
        raise SystemExit('%s apunta a algo que no existe: %s' % (nombre, v))
    return Path(v)

from PIL import Image, ImageDraw, ImageFont

# El Windows SDK, buscado y no fijado a una version.
def _sdk():
    kits = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")
    if kits.is_dir():
        for d in sorted(kits.iterdir(), reverse=True):
            if (d / "x64" / "makeappx.exe").is_file():
                return d / "x64"
    raise SystemExit("no encuentro makeappx.exe en el Windows SDK bajo %s" % kits)


SDK = _sdk()

# La huella SHA-1 de TU certificado de firma (40 digitos hexadecimales), por --certificado o en la
# variable MELEE_CERT. Aqui no hay ninguna: un certificado es de quien lo crea.
#   Get-ChildItem Cert:\CurrentUser\My | Format-List Subject, Thumbprint
import os as _os
import re as _re
HUELLA = (next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--certificado=')),
               None) or _os.environ.get('MELEE_CERT', '')).strip().replace(' ', '').replace(':', '')
if not _re.fullmatch(r'[0-9A-Fa-f]{40}', HUELLA or ''):
    raise SystemExit('falta la huella de tu certificado: --certificado=<40 hex> o la variable '
                     'MELEE_CERT. docs/INSTALL.es.md §5.')

MKW = _entorno('MELEE_TOOLKIT', 'el llvm-mingw con clang y ld.lld')
# Los dos bundles de UWP: por omision, junto al toolkit; con MELEE_UWP_DEP y MELEE_UWP_SDL, donde digas.
UWPDEP_BIN = Path(_os.environ.get('MELEE_UWP_DEP') or (MKW / r"xbox\uwp-dep\x64\bin"))
UWPSDL_BIN = Path(_os.environ.get('MELEE_UWP_SDL') or (MKW / r"xbox\uwp-dep-sdl\x64\bin"))
SRC = _entorno('MELEE_SRC', 'el arbol de melee-pc')
EXE = SRC / "build-uwp" / "melee.exe"
TRABAJO = _entorno('MELEE_TRABAJO', 'una carpeta de trabajo para los objetos')
SALIDA = TRABAJO / "salida"
DLLS = ["webgpu_dawn.dll", "dxcompiler.dll", "dxil.dll", "libpng16.dll", "z.dll", "libuwp.dll"]
# La identidad visual (los mosaicos) la pones tu: docs/ASSETS.es.md.
IDENTIDAD = Path(__file__).resolve().parent.parent / "package"
JUEGO = "Super Smash Bros Melee"   # su fila en identidad-visual.xlsx (columna «juego»)
MOSAICOS = {"StoreLogo.png": (50, 50), "Square44x44Logo.png": (44, 44),
            "Square150x150Logo.png": (150, 150), "Wide310x150Logo.png": (310, 150),
            "SplashScreen.png": (620, 300)}


def mosaico(ruta, tam):
    w, h = tam
    img = Image.new("RGBA", (w, h), (32, 20, 60, 255))
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype(str(SRC / "resources" / "font-bold.ttf"), max(10, h // 5))
    except OSError:
        f = ImageFont.load_default()
    texto = "MELEE" if w < 150 else "SUPER SMASH BROS.\nMELEE"
    caja = d.multiline_textbbox((0, 0), texto, font=f, align="center")
    d.multiline_text(((w - (caja[2] - caja[0])) / 2, (h - (caja[3] - caja[1])) / 2 - caja[1]), texto,
                     font=f, fill=(240, 200, 60, 255), align="center")
    img.save(ruta)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ver = sys.argv[1]
    raiz = SALIDA / "contenido"
    if raiz.exists():
        shutil.rmtree(raiz)  # carpeta de trabajo propia y regenerable, en F:
    (raiz / "Assets").mkdir(parents=True)
    shutil.copy2(EXE, raiz / "melee.exe")
    shutil.copy2(UWPSDL_BIN / "SDL3.dll", raiz / "SDL3.dll")
    for d in DLLS:
        shutil.copy2(UWPDEP_BIN / d, raiz / d)
    shutil.copytree(SRC / "resources", raiz / "resources")
    with gzip.open(SRC / "tools" / "initial_pipeline_cache.db.gz", "rb") as g, \
            open(raiz / "initial_pipeline_cache.db", "wb") as o:
        shutil.copyfileobj(g, o)
    for nombre, tam in MOSAICOS.items():
        mosaico(raiz / "Assets" / nombre, tam)
    manifiesto = (TRABAJO / "paquete" / "Package.appxmanifest").read_text(encoding="utf-8")
    (raiz / "AppxManifest.xml").write_text(manifiesto.replace("@VERSION@", ver), encoding="utf-8")
    # Identidad visual del proyecto sobre la copia de trabajo: nombre del Excel y mosaicos con el
    # arte de Display Images (con sus variantes scale-200). El árbol del proyecto no se toca.
    r = subprocess.run([sys.executable, "-X", "utf8", str(IDENTIDAD), "--aplicar-a", JUEGO,
                        str(raiz / "AppxManifest.xml")], capture_output=True, text=True, errors="replace")
    print(r.stdout.rstrip())
    if r.returncode != 0:
        print("identidad-visual.py falló:", r.stderr[-1500:])
        return 1
    total = sum(p.stat().st_size for p in raiz.rglob("*") if p.is_file())
    print(f"contenido: {sum(1 for p in raiz.rglob('*') if p.is_file())} archivos, {total / 1048576:.1f} MB")
    msix = SALIDA / f"Decompilaciones-SuperSmashBrosMelee_{ver}_x64.msix"
    r = subprocess.run([str(SDK / "makeappx.exe"), "pack", "/o", "/d", str(raiz), "/p", str(msix)],
                       capture_output=True, text=True, errors="replace")
    print("makeappx:", "OK" if r.returncode == 0 else r.stdout[-1500:] + r.stderr[-800:])
    if r.returncode != 0:
        return 1
    r = subprocess.run([str(SDK / "signtool.exe"), "sign", "/fd", "SHA256", "/sha1", HUELLA, "/s", "My", str(msix)],
                       capture_output=True, text=True, errors="replace")
    print("signtool:", "OK" if r.returncode == 0 else r.stdout[-800:] + r.stderr[-800:])
    print(msix, f"{msix.stat().st_size / 1048576:.1f} MB")
    return 0 if r.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
