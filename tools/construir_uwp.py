# -*- coding: utf-8 -*-
"""Construye melee-pc (Super Smash Bros. Melee) para UWP / Xbox Series.

Reparto de compiladores, el mismo que usa el autor fuera de Windows x86-64:
  * GCC (MinGW UCRT64 de C:\\msys64-dkr) para el C: el código del juego describe los datos del
    disco con scalar_storage_order("big-endian"), que solo implementa GCC. MinGW ya emite COFF
    con el ABI de llamadas de Microsoft, así que lld lo enlaza junto a lo de clang.
  * clang de llvm-mingw con ABI de MSVC (--target=x86_64-pc-windows-msvc) y WINAPI_FAMILY_APP
    para el C++ (Aurora, RmlUi, abseil, imgui, fmt...) y para las dependencias en C.
  * ld.lld en modo link: /APPCONTAINER, base fija 0x10000000 y sin ASLR (los punteros del disco
    son ranuras de 32 bits; probado en la xbox series cuarto el 2026-10-01).

Las órdenes salen del compile_commands.json de la build de escritorio con MSYS2 —la que vive dentro
del árbol de melee-pc—, que es la lista exacta de unidades de cada objetivo.

Uso (desde construir-uwp.bat, que carga el entorno «store» de Visual Studio):
    py -3.13 construir_uwp.py [--solo gcc|clang|extras] [--objetivos a,b] [--enlazar] [--j N]
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
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

# --- herramientas ------------------------------------------------------------------------------
MKW = _entorno('MELEE_TOOLKIT', 'el llvm-mingw con clang y ld.lld')
TOOLKIT = MKW / r"pc\WiiCompiled\Install\Toolkit\llvm-mingw\bin"
CLANG = TOOLKIT / "clang.exe"
CLANGXX = TOOLKIT / "clang++.exe"
LLD = TOOLKIT / "ld.lld.exe"
LLVM_LIB = TOOLKIT / "llvm-lib.exe"
RESOURCE_DIR = TOOLKIT.parent / "lib" / "clang" / "22"
DEPS_MKW = MKW / r"pc\WiiCompiled\Install\BuildWorkspace\Dependencies"

MSYS = _entorno('MELEE_MSYS', 'el MSYS2 UCRT64 con GCC y ninja')
GCC = MSYS / "bin" / "gcc.exe"
LIBGCC = MSYS / r"lib\gcc\x86_64-w64-mingw32\16.2.0\libgcc.a"

UWPDEP = MKW / r"xbox\uwp-dep\x64"          # Dawn, nod, libpng, zlib, libuwp (SternXD)
UWPSDL = MKW / r"xbox\uwp-dep-sdl\x64"      # SDL3 3.4.8 de verdad para UWP (commit ae39aa0)

SRC = _entorno('MELEE_SRC', 'el arbol de melee-pc')
BMW = SRC / "build-mingw"
OUT = SRC / "build-uwp"
OBJ = OUT / "obj"
LIBS = OUT / "lib"
TRABAJO = _entorno('MELEE_TRABAJO', 'una carpeta de trabajo para los objetos')
UWP_SRC = TRABAJO / "uwp"                   # fuentes propias del port (entrada, compatibilidad)
TARGET = "x86_64-pc-windows-msvc"

# --- qué entra en melee.exe (sacado de LINK_LIBRARIES de build.ninja) -------------------------
EXE = "melee"
OBJETIVOS = [
    "melee_game", "aurora_gd", "aurora_gx", "aurora_vi", "aurora_pad", "aurora_si",
    "aurora_mtx", "aurora_os", "aurora_dvd", "aurora_card", "aurora_thp", "aurora_core", "fmt",
    "TracyClient", "imgui", "imgui_backends", "rmlui_backends", "rmlui_debugger", "rmlui_core",
    "freetype",
]
# aurora_main (lib/main.cpp) NO: la entrada UWP la pone uwp/entrada_uwp.cpp.
# De abseil, todos los objetivos absl_* que aparezcan (van a un .lib: solo entra lo que se use).
GCC_OBJETIVOS = {"melee_game", "aurora_mtx"}   # y además los .c del propio ejecutable

# --- traducción común -----------------------------------------------------------------------------
# Las claves son las rutas tal como las escribe el compile_commands.json de TU arbol, asi que se
# derivan de MELEE_SRC: con una ruta fija no casarian en otra maquina y la sustitucion se quedaria
# sin hacer, en silencio.
_DEPS = (SRC / "build-mingw" / "_deps").as_posix()
SUSTITUIR_INC = {
    "%s/sdl3_prebuilt-src/include" % _DEPS: str(UWPSDL / "include"),
    "%s/dawn_prebuilt-src/include" % _DEPS: str(UWPDEP / "include"),
    "%s/nod_prebuilt-src/include" % _DEPS: str(UWPDEP / "include"),
}
DEFS_COMUNES = ["-DMELEE_UWP=1", "-DAURORA_WINDOWS_STORE=1",
                # main.c deja su main() como aurora_main y la entrada la pone uwp/entrada_uwp.cpp
                "-DSDL_MAIN_HANDLED"]
QUITAR_DEFS = {"-DXXH_EXPORT"}   # xxhash va compilado dentro, no como DLL

# clang: banderas de GCC que no significan nada con ABI de MSVC
FUERA_CLANG = {"-fdiagnostics-color=always", "-mno-ms-bitfields", "-fno-keep-inline-dllexport",
               "-Winvalid-pch", "-pedantic", "-fpermissive", "-fno-lto",
               "-Wall", "-Wextra", "-Werror", "-w"}
FUERA_CLANG_PREFIJO = ("-Werror=", "-Wno-", "-W")
DEFS_UWP_CLANG = [
    "-DWINAPI_FAMILY=WINAPI_FAMILY_APP", "-D_WIN32_WINNT=0x0A00", "-DWINVER=0x0A00",
    "-D_CRT_SECURE_NO_WARNINGS", "-D_CRT_NONSTDC_NO_WARNINGS", "-DNOMINMAX",
]
INC_EXTRA_CLANG = [
    "-I", str(DEPS_MKW / "zstd" / "lib"),
    "-I", str(DEPS_MKW / "xxhash"),
    "-I", str(DEPS_MKW / "sqlite3"),
    "-I", str(UWPDEP / "include"),
]
INC_EXTRA_GCC = [
    "-I", str(UWP_SRC / "include"),
]
# GCC compila sin WINAPI_FAMILY, así que las cabeceras de SDL3 eligen _beginthreadex para
# SDL_CreateThread, y el SDL3 de UWP lo rechaza («not supported on this platform»).
DEFS_GCC_UWP = ["-DSDL_BeginThreadFunction=NULL", "-DSDL_EndThreadFunction=NULL"]


def normaliza(p):
    return str(p).replace("\\", "/")


def objetivo_de(salida):
    s = normaliza(salida)
    if "CMakeFiles/" not in s:
        return "?"
    return s.split("CMakeFiles/")[1].split(".dir")[0]


def carga_compdb():
    cc = json.loads((BMW / "compile_commands.json").read_text(encoding="utf-8", errors="replace"))
    porobj = defaultdict(list)
    for e in cc:
        t = objetivo_de(e.get("output", ""))
        porobj[t].append(e)
    return porobj


COPIAS_PCH = {}


def copia_pch(ruta):
    """La cabecera del PCH de CMake, copiada donde no tenga su .gch al lado (clang se lo comería)."""
    if ruta in COPIAS_PCH:
        return COPIAS_PCH[ruta]
    destino = OUT / "pch" / (objetivo_de(ruta) + "_" + Path(ruta).name)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ruta, destino)
    COPIAS_PCH[ruta] = str(destino)
    return COPIAS_PCH[ruta]


def tokens(cmd):
    return shlex.split(cmd, posix=False)


def limpia_def(t):
    # En compile_commands.json las comillas de un define van escapadas para el shell de ninja;
    # aquí el argumento va directo al proceso.
    return t.replace(chr(92) + '"', '"')


def traduce_gcc(e, salida):
    toks = tokens(e["command"])
    argv = [str(GCC)]
    i = 1
    while i < len(toks):
        t = toks[i]
        if t in ("-o",):
            i += 2
            continue
        if t == "-c":
            i += 2  # -c <fuente>
            continue
        if t in QUITAR_DEFS or t == "-fdiagnostics-color=always":
            i += 1
            continue
        if t.startswith("-I"):
            r = t[2:].strip('"')
            argv.append("-I" + SUSTITUIR_INC.get(normaliza(r), r))
            i += 1
            continue
        if t == "-isystem":
            r = toks[i + 1].strip('"')
            argv += ["-isystem", SUSTITUIR_INC.get(normaliza(r), r)]
            i += 2
            continue
        if t.startswith("-D"):
            argv.append(limpia_def(t))
            i += 1
            continue
        argv.append(t)
        i += 1
    argv += DEFS_COMUNES + DEFS_GCC_UWP + INC_EXTRA_GCC
    argv += ["-fdiagnostics-color=never", "-c", e["file"], "-o", str(salida)]
    return argv


SUSTITUIR_FUENTE = {
    # freetype: el ftsystem de Windows abre con CreateFileA (escritorio); el genérico usa stdio.
    # Las dos rutas salen de MELEE_SRC, por lo mismo que SUSTITUIR_INC.
    "%s/freetype-src/builds/windows/ftsystem.c" % _DEPS:
        "%s/freetype-src/src/base/ftsystem.c" % _DEPS,
}


def traduce_clang(e, salida):
    toks = tokens(e["command"])
    fuente = SUSTITUIR_FUENTE.get(normaliza(e["file"]), e["file"])
    es_cxx = Path(fuente).suffix.lower() in (".cpp", ".cc", ".cxx")
    argv = [str(CLANGXX if es_cxx else CLANG), f"--target={TARGET}", "-fms-runtime-lib=dll",
            "-fms-compatibility-version=19.44", "-gcodeview", "-g1", "-w",
            "-I", str(UWP_SRC / "include")]   # cabeceras sustitutas del port: las primeras
    i = 1
    while i < len(toks):
        t = toks[i]
        if t == "-o":
            i += 2
            continue
        if t == "-c":
            i += 2
            continue
        if t in ("-x",):
            i += 2
            continue
        if t == "-include":
            r = toks[i + 1].strip('"')
            if "cmake_pch" in r:
                argv += ["-include", copia_pch(r)]
            else:
                argv += ["-include", r]
            i += 2
            continue
        if t in QUITAR_DEFS or t in FUERA_CLANG or t.startswith(FUERA_CLANG_PREFIJO):
            i += 1
            continue
        if t.startswith("-I"):
            r = t[2:].strip('"')
            argv.append("-I" + SUSTITUIR_INC.get(normaliza(r), r))
            i += 1
            continue
        if t == "-isystem":
            r = toks[i + 1].strip('"')
            argv += ["-isystem", SUSTITUIR_INC.get(normaliza(r), r)]
            i += 2
            continue
        if t.startswith("-D"):
            argv.append(limpia_def(t))
            i += 1
            continue
        argv.append(t)
        i += 1
    argv += DEFS_COMUNES + DEFS_UWP_CLANG + INC_EXTRA_CLANG
    # Las cabeceras de clang DELANTE de las de MSVC (lección de Diddy Kong Racing: el emmintrin.h
    # de Visual Studio solo declara las intrínsecas SSE2).
    argv += ["-isystem", str(RESOURCE_DIR / "include")]
    for d in os.environ.get("INCLUDE", "").split(";"):
        if d.strip():
            argv += ["-isystem", d.strip()]
    argv += ["-c", fuente, "-o", str(salida)]
    return argv


# --- fuentes que no están en compile_commands.json ---------------------------------------------
def extras():
    """(objetivo, fuente, banderas, compilador) de las dependencias que en escritorio eran DLL de
    MSYS2 y de las fuentes propias del port."""
    base_c = ["-O2", "-DNDEBUG", "-std=gnu11"]
    base_cxx = ["-O2", "-DNDEBUG", "-std=gnu++20"]
    lista = []
    sq = DEPS_MKW / "sqlite3" / "sqlite3.c"
    lista.append(("sqlite3", str(sq), base_c + ["-DSQLITE_OS_WINRT=1", "-DSQLITE_THREADSAFE=1",
                                                  "-DSQLITE_OMIT_LOAD_EXTENSION=1"], "clang"))
    lista.append(("xxhash", str(DEPS_MKW / "xxhash" / "xxhash.c"), base_c, "clang"))
    zstd = DEPS_MKW / "zstd" / "lib"
    for sub in ("common", "compress", "decompress"):
        for f in sorted((zstd / sub).glob("*.c")):
            lista.append(("zstd", str(f), base_c + ["-DZSTD_DISABLE_ASM=1", "-DZSTD_MULTITHREAD=0"],
                          "clang"))
    for f in sorted((UWP_SRC).glob("*.cpp")):
        lista.append(("uwp", str(f), base_cxx + ["-DSDL_MAIN_HANDLED",
                                                  "-I" + str(SRC / "extern" / "aurora" / "include"),
                                                  "-I" + str(SRC / "src")],
                      "clang"))
    for f in sorted((UWP_SRC).glob("*.c")):
        lista.append(("uwp", str(f), base_c, "clang"))
    return lista


def traduce_extra(objetivo, fuente, banderas, salida):
    e = {"file": fuente, "command": "cc " + " ".join(banderas)}
    return traduce_clang(e, salida)


# --- compilación ----------------------------------------------------------------------------------
def nombre_obj(objetivo, fuente):
    f = normaliza(fuente)
    for raiz in (normaliza(BMW) + "/", normaliza(SRC) + "/", normaliza(DEPS_MKW) + "/",
                 normaliza(UWP_SRC) + "/"):
        if f.startswith(raiz):
            f = f[len(raiz):]
            break
    return OBJ / objetivo / (f.replace("/", "_").replace(":", "") + ".obj")


def env_gcc():
    env = dict(os.environ)
    env["PATH"] = str(MSYS / "bin") + ";" + env.get("PATH", "")
    return env


def main():
    if not os.environ.get("INCLUDE"):
        print("ERROR: falta el entorno «store» de Visual Studio: lanza construir-uwp.bat.")
        return 2
    args = sys.argv[1:]
    solo = None
    if "--solo" in args:
        solo = args[args.index("--solo") + 1]
    filtro = None
    if "--objetivos" in args:
        filtro = set(args[args.index("--objetivos") + 1].split(","))
    jobs = 16
    if "--j" in args:
        jobs = int(args[args.index("--j") + 1])

    porobj = carga_compdb()
    absl = sorted(t for t in porobj if t.startswith("absl_"))
    trabajos = []   # (objetivo, fuente, argv, salida, compilador)

    def añade(objetivo, e, compilador):
        salida = nombre_obj(objetivo, e["file"])
        argv = traduce_gcc(e, salida) if compilador == "gcc" else traduce_clang(e, salida)
        trabajos.append((objetivo, e["file"], argv, salida, compilador))

    for t in OBJETIVOS + absl + [EXE]:
        if filtro and t not in filtro:
            continue
        for e in porobj.get(t, []):
            f = e["file"]
            if f.endswith(".rc") or f.endswith("cmake_pch.hxx.cxx") or f.endswith("cmake_pch.h.c"):
                continue
            if normaliza(f).endswith("extern/aurora/lib/main.cpp"):
                continue
            if normaliza(f).endswith("src/pc/updater.cpp"):   # WinHTTP: lo sustituye uwp/updater_uwp.cpp
                continue
            usa_gcc = t in GCC_OBJETIVOS or (t == EXE and f.lower().endswith(".c"))
            comp = "gcc" if usa_gcc else "clang"
            if solo in ("gcc", "clang") and comp != solo:
                continue
            if solo == "extras":
                continue
            añade(t, e, comp)
    if solo in (None, "extras") and not filtro:
        for objetivo, fuente, banderas, comp in extras():
            salida = nombre_obj(objetivo, fuente)
            trabajos.append((objetivo, fuente, traduce_extra(objetivo, fuente, banderas, salida),
                             salida, comp))

    print("=== construcción UWP de melee-pc ===")
    print(f"  unidades: {len(trabajos)}  (gcc {sum(1 for x in trabajos if x[4]=='gcc')}, "
          f"clang {sum(1 for x in trabajos if x[4]=='clang')})")
    t0 = time.time()
    resultados = []

    def compila(tr):
        objetivo, fuente, argv, salida, comp = tr
        salida.parent.mkdir(parents=True, exist_ok=True)
        if salida.exists() and salida.stat().st_mtime > Path(fuente).stat().st_mtime and \
                "--forzar" not in args:
            return (objetivo, fuente, 0, "", salida, comp, True)
        r = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                           env=env_gcc() if comp == "gcc" else None, cwd=str(BMW))
        return (objetivo, fuente, r.returncode, r.stderr, salida, comp, False)

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for i, res in enumerate(ex.map(compila, trabajos), 1):
            resultados.append(res)
            if i % 100 == 0:
                fallos = sum(1 for x in resultados if x[2] != 0)
                print(f"  {i:5}/{len(trabajos)}   fallan {fallos}   ({time.time()-t0:.0f} s)")

    ok = [r for r in resultados if r[2] == 0]
    mal = [r for r in resultados if r[2] != 0]
    print(f"=== compilación: {len(ok)} bien ({sum(1 for r in ok if r[6])} ya estaban), "
          f"{len(mal)} mal  ({time.time()-t0:.0f} s) ===")
    errores = TRABAJO / "registros" / "errores-uwp.txt"
    if mal:
        texto = []
        for r in mal:
            texto.append(f"##### [{r[5]}] {r[0]} :: {r[1]}\n{r[3]}")
        errores.write_text("\n".join(texto), encoding="utf-8")
        porobjetivo = Counter(r[0] for r in mal)
        print("  fallan por objetivo:", dict(porobjetivo.most_common(30)))
        todos = "\n".join(r[3] for r in mal)
        msgs = [re.sub(r"'[^']*'", "'X'", m) for m in re.findall(r"error: (.+)", todos)]
        print("  errores más repetidos:")
        for m, n in Counter(msgs).most_common(25):
            print(f"    {n:4}  {m[:130]}")
        faltan = sorted(set(re.findall(r"'([^']+)' file not found", todos)) |
                        set(re.findall(r"fatal error: ([^:]+): No such file", todos)))
        if faltan:
            print("  cabeceras que faltan:", faltan[:30])
        print(f"  detalle en {errores}")

    # .lib por objetivo (para que el enlazador saque solo lo que se use)
    porlib = defaultdict(list)
    for r in ok:
        porlib[r[0]].append(str(r[4]))
    (OUT / "objetos.json").write_text(json.dumps(porlib, indent=1), encoding="utf-8")
    if "--enlazar" in args:
        return enlaza(porlib)
    return 0 if not mal else 1


def archiva(objetivo, objs):
    LIBS.mkdir(parents=True, exist_ok=True)
    lib = LIBS / f"{objetivo}.lib"
    rsp = LIBS / f"{objetivo}.rsp"
    rsp.write_text("\n".join(f'"{o}"' for o in objs), encoding="utf-8")
    r = subprocess.run([str(LLVM_LIB), "/nologo", f"/out:{lib}", f"@{rsp}"],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print(f"  llvm-lib {objetivo}: {r.stdout}{r.stderr}")
    return lib


def enlaza(porlib):
    print("=== enlace con ld.lld (AppContainer, base fija 0x10000000) ===")
    exe = OUT / "melee.exe"
    objs_exe = porlib.get(EXE, []) + porlib.get("uwp", [])
    libs = [archiva(t, o) for t, o in porlib.items() if t not in (EXE, "uwp")]
    argv = [str(LLD), "-flavor", "link", "/nologo", "/machine:x64", "/subsystem:windows,10.0",
            "/appcontainer", "/base:0x10000000", "/dynamicbase:no", "/highentropyva:no",
            "/nxcompat", "/manifest:no", "/opt:ref", "/debug", f"/pdb:{exe.with_suffix('.pdb')}",
            "/nodefaultlib:libcmt", "/nodefaultlib:libcpmt",
            # el juego trae sus propias expf, acosf... (las de la decomp): ganan las suyas, como en escritorio
            "/force:multiple",
            f"/out:{exe}"]
    for d in os.environ.get("LIB", "").split(";"):
        if d.strip():
            argv.append(f"/libpath:{d.strip()}")
    argv += [f"/libpath:{UWPDEP / 'lib'}", f"/libpath:{UWPSDL / 'lib'}"]
    rsp = OUT / "melee.rsp"
    rsp.write_text("\n".join(f'"{o}"' for o in objs_exe + [str(l) for l in libs]), encoding="utf-8")
    argv.append(f"@{rsp}")
    argv += [str(LIBGCC),
             str(UWPSDL / "lib" / "SDL3.lib"), "webgpu_dawn.lib", "nod.lib", "libpng16.lib",
             "libuwp.lib",          # zlib: ya va dentro de nod.lib (staticlib de Rust)
             "WindowsApp.lib", "bcrypt.lib", "ws2_32.lib", "iphlpapi.lib", "dxgi.lib",
             "runtimeobject.lib", "ntdll.lib",
             "msvcrt.lib", "msvcprt.lib", "vcruntime.lib", "ucrt.lib",
             "legacy_stdio_definitions.lib"]
    r = subprocess.run(argv, capture_output=True, text=True, errors="replace")
    salida = (r.stdout or "") + (r.stderr or "")
    (TRABAJO / "registros" / "enlace-uwp.txt").write_text(salida, encoding="utf-8")
    if r.returncode == 0:
        print(f"  ENLAZA: {exe} ({exe.stat().st_size / 1048576:.1f} MB)")
        return 0
    faltan = sorted(set(re.findall(r"undefined symbol: (.+)", salida)))
    print(f"  no enlaza: {len(faltan)} símbolos sin resolver")
    for s in faltan[:80]:
        print(f"    {s}")
    otros = [l for l in salida.splitlines() if "error" in l.lower() and "undefined symbol" not in l]
    for l in otros[:20]:
        print(f"    {l[:160]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
