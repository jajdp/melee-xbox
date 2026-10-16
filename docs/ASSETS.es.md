# Los mosaicos del paquete

*(English: [ASSETS.md](ASSETS.md))*

El manifiesto nombra cinco imágenes, y **este repositorio no trae ninguna**: las del paquete real se
hicieron con el propio material artístico del juego. Las pones tú.

| Archivo | Medida |
|---|---|
| `StoreLogo.png` | 50 × 50 |
| `Square150x150Logo.png` | 150 × 150 |
| `Square44x44Logo.png` | 44 × 44 |
| `Wide310x150Logo.png` | 310 × 150 |
| `SplashScreen.png` | 620 × 300 |

PNG de 32 bits con alfa. Imágenes lisas con el tamaño correcto bastan para instalar un paquete; el
empaquetador se detiene si falta alguna.

> **Dónde se escribe esto:** en **PowerShell**, en una ventana **normal**, desde la carpeta de este
> repositorio.

```powershell
$tiles = @{ 'StoreLogo.png' = '50x50'; 'Square150x150Logo.png' = '150x150'
            'Square44x44Logo.png' = '44x44'; 'Wide310x150Logo.png' = '310x150'
            'SplashScreen.png' = '620x300' }
foreach ($t in $tiles.GetEnumerator()) {
  magick -size $t.Value xc:"#1b1b1f" (Join-Path 'package\Assets' $t.Key)
}
```

Que el arte que hagas sea tuyo: las capturas, los logotipos y los dibujos de los personajes del
juego son de sus dueños, y un paquete que los lleve es un paquete que no puedes compartir.
