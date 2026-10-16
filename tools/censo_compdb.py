# Cuenta las unidades de compilación de melee-pc por objetivo y extensión, a partir del
# compile_commands.json de la configuración de escritorio con MinGW.
import collections
import json
import os
import sys

if len(sys.argv) < 2:
    raise SystemExit("uso: censo_compdb.py <compile_commands.json>")
ruta = sys.argv[1]
cc = json.load(open(ruta, encoding="utf-8"))
print("unidades:", len(cc))
por = collections.Counter()
lang = collections.Counter()
for e in cc:
    f = e["file"].replace("\\", "/")
    o = e.get("output", "").replace("\\", "/")
    tgt = "?"
    if "CMakeFiles/" in o:
        tgt = o.split("CMakeFiles/")[1].split(".dir")[0]
    por[tgt] += 1
    lang[(tgt, os.path.splitext(f)[1])] += 1
for t, n in por.most_common(80):
    print(f"{n:5d}  {t}")
print()
for (t, ext), n in sorted(lang.items()):
    print(f"{n:5d}  {t:45s} {ext}")
