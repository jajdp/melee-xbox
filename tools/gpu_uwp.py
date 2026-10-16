from pathlib import Path

# La raiz del arbol de melee-pc, por argumento:
#     python tools/gpu_uwp.py <ruta del arbol de melee-pc>
import sys as _sys
_libres = [a for a in _sys.argv[1:] if not a.startswith('-')]
if not _libres:
    raise SystemExit('uso: gpu_uwp.py <ruta del arbol de melee-pc>')
_raiz = Path(_libres[0]).resolve()
if not (_raiz / 'extern' / 'aurora').is_dir():
    raise SystemExit('no es la raiz de melee-pc (falta extern/aurora): %s' % _raiz)
# Porta a BackendBinding.cpp y gpu.cpp del Aurora de melee-pc el cambio UWP de SternXD (uwp-dusk),
# adaptado a la Dawn UWP de uwp-dep (anterior a la v20260807 que pide melee-pc). Idempotente.
import os


def editar(ruta, cambios):
    t = open(ruta, encoding="utf-8", newline="").read()
    if "melee-uwp" in t:
        print("ya aplicado:", ruta)
        return
    for a, b in cambios:
        n = t.count(a)
        assert n == 1, (ruta, n, a[:70])
        t = t.replace(a, b)
    tmp = ruta + ".tmp"
    open(tmp, "w", encoding="utf-8", newline="").write(t)
    os.replace(tmp, ruta)
    print("aplicado:", ruta)


editar(str(_raiz / 'extern/aurora/lib/dawn/BackendBinding.cpp'), [
    ("namespace aurora::webgpu {\nnamespace utils {\n",
     "#if defined(AURORA_WINDOWS_STORE)\n"
     "// melee-uwp: libuwp.dll (uwp-dep de SternXD) da la CoreWindow de la app.\n"
     "extern \"C\" __declspec(dllimport) void* uwp_GetWindowReference();\n"
     "#endif\n\n"
     "namespace aurora::webgpu {\nnamespace utils {\n"),
    ("std::shared_ptr<wgpu::ChainedStruct> SetupWindowAndGetSurfaceDescriptor(SDL_Window* window) {\n"
     "#if defined(SDL_PLATFORM_MACOS) || defined(SDL_PLATFORM_IOS) || defined(SDL_PLATFORM_TVOS)\n",
     "std::shared_ptr<wgpu::ChainedStruct> SetupWindowAndGetSurfaceDescriptor(SDL_Window* window) {\n"
     "#if defined(AURORA_WINDOWS_STORE)\n"
     "  // En un AppContainer no hay HWND: Dawn presenta sobre la CoreWindow.\n"
     "  (void)window;\n"
     "  auto desc = std::make_shared<wgpu::SurfaceDescriptorFromWindowsCoreWindow>();\n"
     "  desc->coreWindow = uwp_GetWindowReference();\n"
     "  return std::move(desc);\n"
     "#elif defined(SDL_PLATFORM_MACOS) || defined(SDL_PLATFORM_IOS) || defined(SDL_PLATFORM_TVOS)\n"),
])

editar(str(_raiz / 'extern/aurora/lib/webgpu/gpu.cpp'), [
    ("#ifdef WEBGPU_DAWN\n#include \"../dawn/TracyPlatform.hpp\"\n#include <dawn/native/DawnNative.h>\n#endif\n",
     "#if defined(WEBGPU_DAWN) && !defined(AURORA_WINDOWS_STORE) // melee-uwp: la Dawn UWP no expone dawn::native\n"
     "#include \"../dawn/TracyPlatform.hpp\"\n#include <dawn/native/DawnNative.h>\n#endif\n"),
    ("#if defined(WEBGPU_DAWN) && !defined(__MINGW32__)\n    constexpr std::array instanceToggles{",
     "#if defined(WEBGPU_DAWN) && !defined(__MINGW32__) && !defined(AURORA_WINDOWS_STORE)\n"
     "    constexpr std::array instanceToggles{"),
    ("#elif defined(WEBGPU_DAWN)\n    // dawn::native::DawnInstanceDescriptor is unusable from MinGW",
     "#elif defined(WEBGPU_DAWN) && defined(AURORA_WINDOWS_STORE)\n"
     "    // melee-uwp: sin dawn::native, solo los toggles de instancia (se pierde el registro de Dawn).\n"
     "    constexpr std::array instanceToggles{\n"
     "        \"allow_unsafe_apis\",\n"
     "    };\n"
     "    wgpu::DawnTogglesDescriptor instanceTogglesDescriptor{};\n"
     "    instanceTogglesDescriptor.enabledToggleCount = instanceToggles.size();\n"
     "    instanceTogglesDescriptor.enabledToggles = instanceToggles.data();\n"
     "    instanceDescriptor.nextInChain = &instanceTogglesDescriptor;\n"
     "#elif defined(WEBGPU_DAWN)\n    // dawn::native::DawnInstanceDescriptor is unusable from MinGW"),
    ("    wgpu::DawnCacheDeviceDescriptor cacheDescriptor({.nextInChain = nullptr});\n"
     "    cacheDescriptor.SetDawnLoadCacheDataCallback(",
     "#if defined(AURORA_WINDOWS_STORE)\n"
     "    // melee-uwp: la Dawn UWP usa todavía las funciones con userdata, no los callback info.\n"
     "    wgpu::DawnCacheDeviceDescriptor cacheDescriptor{};\n"
     "    cacheDescriptor.loadDataFunction = [](const void* key, size_t keySize, void* value, size_t valueSize,\n"
     "                                          void*) -> size_t {\n"
     "      return load_from_cache(key, keySize, value, valueSize, nullptr);\n"
     "    };\n"
     "    cacheDescriptor.storeDataFunction = [](const void* key, size_t keySize, const void* value, size_t valueSize,\n"
     "                                           void*) { store_to_cache(key, keySize, value, valueSize, nullptr); };\n"
     "#else\n"
     "    wgpu::DawnCacheDeviceDescriptor cacheDescriptor({.nextInChain = nullptr});\n"
     "    cacheDescriptor.SetDawnLoadCacheDataCallback("),
    ("          store_to_cache(key.data(), key.size(), value.data(), value.size(), nullptr);\n        });\n",
     "          store_to_cache(key.data(), key.size(), value.data(), value.size(), nullptr);\n        });\n#endif\n"),
])
