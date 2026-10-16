# The package tiles

*(Español: [ASSETS.es.md](ASSETS.es.md))*

The manifest names five images, and **this repository ships none of them**: the ones in the real
package were made from the game's own artwork. You supply your own.

| File | Size |
|---|---|
| `StoreLogo.png` | 50 × 50 |
| `Square150x150Logo.png` | 150 × 150 |
| `Square44x44Logo.png` | 44 × 44 |
| `Wide310x150Logo.png` | 310 × 150 |
| `SplashScreen.png` | 620 × 300 |

PNG, 32-bit with alpha. Plain colour images of the right size are enough to get a package
installed; the packer stops if one is missing.

> **Where to type this:** in **PowerShell**, in an **ordinary** window, from this repository's
> folder.

```powershell
$tiles = @{ 'StoreLogo.png' = '50x50'; 'Square150x150Logo.png' = '150x150'
            'Square44x44Logo.png' = '44x44'; 'Wide310x150Logo.png' = '310x150'
            'SplashScreen.png' = '620x300' }
foreach ($t in $tiles.GetEnumerator()) {
  magick -size $t.Value xc:"#1b1b1f" (Join-Path 'package\Assets' $t.Key)
}
```

Keep whatever art you make yours: screenshots, logos and character art from the game belong to
their owners, and a package that carries them is a package you cannot share.
