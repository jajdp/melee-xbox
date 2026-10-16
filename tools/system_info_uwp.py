from pathlib import Path

# La raiz del arbol de melee-pc, por argumento:
#     python tools/system_info_uwp.py <ruta del arbol de melee-pc>
import sys as _sys
_libres = [a for a in _sys.argv[1:] if not a.startswith('-')]
if not _libres:
    raise SystemExit('uso: system_info_uwp.py <ruta del arbol de melee-pc>')
_raiz = Path(_libres[0]).resolve()
if not (_raiz / 'extern' / 'aurora').is_dir():
    raise SystemExit('no es la raiz de melee-pc (falta extern/aurora): %s' % _raiz)
# Porta a system_info.cpp del Aurora de melee-pc el cambio UWP de SternXD (uwp-dusk): sin WMI en un
# AppContainer; el modelo de la CPU sale de cpuid. Idempotente.
import os

P = str(_raiz / 'extern/aurora/lib/system_info.cpp')
t = open(P, encoding="utf-8", newline="").read()
if "melee-uwp" in t:
    print("ya aplicado")
    raise SystemExit(0)

a = "#include <combaseapi.h>\n#include <wbemidl.h>\n#include <comutil.h>\n"
b = ("#include <combaseapi.h>\n"
     "#ifndef AURORA_WINDOWS_STORE\n"
     "#include <wbemidl.h>\n"
     "#include <comutil.h>\n"
     "#else\n"
     "#include <intrin.h> // melee-uwp: WMI no existe en UWP; el modelo de CPU sale de cpuid\n"
     "#endif\n")
assert t.count(a) == 1
t = t.replace(a, b)

a = "std::string GetCpuModel() {\n  // Good fucking lord Microsoft"
b = ("#ifdef AURORA_WINDOWS_STORE\n"
     "std::string GetCpuModel() {\n"
     "  int regs[4] = {};\n"
     "  __cpuid(regs, static_cast<int>(0x80000000u));\n"
     "  if (static_cast<unsigned>(regs[0]) < 0x80000004u) {\n"
     "    return Unknown;\n"
     "  }\n"
     "  char buf[49] = {};\n"
     "  for (unsigned leaf = 0x80000002u, off = 0; leaf <= 0x80000004u; ++leaf, off += 16) {\n"
     "    __cpuidex(regs, static_cast<int>(leaf), 0);\n"
     "    std::memcpy(buf + off, regs, 16);\n"
     "  }\n"
     "  std::string s{buf};\n"
     "  while (!s.empty() && s.front() == ' ') s.erase(s.begin());\n"
     "  while (!s.empty() && s.back() == ' ') s.pop_back();\n"
     "  return s.empty() ? Unknown : s;\n"
     "}\n"
     "#else\n"
     "std::string GetCpuModel() {\n  // Good fucking lord Microsoft")
assert t.count(a) == 1
t = t.replace(a, b)

a = "  return result;\n}\n\nuint64_t GetMemoryAmount() {\n  MEMORYSTATUSEX status;"
b = "  return result;\n}\n#endif // AURORA_WINDOWS_STORE\n\nuint64_t GetMemoryAmount() {\n  MEMORYSTATUSEX status;"
assert t.count(a) == 1
t = t.replace(a, b)

tmp = P + ".tmp"
open(tmp, "w", encoding="utf-8", newline="").write(t)
os.replace(tmp, P)
print("aplicado")
