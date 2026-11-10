"""Fontes dentro do kit (assets/fonts), para o render não depender do Google Fonts na hora.

Com @font-face próprio na página, o HyperFrames não baixa a família; o resultado
fica igual em qualquer máquina, com ou sem internet.

  python fontes.py baixar             # (re)baixa os .woff2 e gera assets/fonts/fontes.css
"""
import re
import shutil
import sys
import urllib.request
from pathlib import Path

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
CSS = FONT_DIR / "fontes.css"
FAMILIAS = {
    "Inter": "ital,wght@0,100..900;1,100..900",
    "Roboto": "ital,wght@0,100..900;1,100..900",
    "Montserrat": "ital,wght@0,100..900;1,100..900",
    "Oswald": "wght@200..700",
    "Playfair Display": "ital,wght@0,400..900;1,400..900",
}
SUBSETS = {"latin", "latin-ext"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def baixar():
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    blocos = []
    for fam, eixo in FAMILIAS.items():
        url = f"https://fonts.googleapis.com/css2?family={fam.replace(' ', '+')}:{eixo}&display=block"
        css = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA})).read().decode()
        for subset, bloco in re.findall(r"/\* ([\w-]+) \*/\s*(@font-face\s*\{[^}]*\})", css):
            if subset not in SUBSETS:
                continue
            src = re.search(r"url\((https://[^)]+\.woff2)\)", bloco).group(1)
            estilo = re.search(r"font-style:\s*(\w+)", bloco).group(1)
            arq = f"{fam.lower().replace(' ', '-')}-{estilo}-{subset}.woff2"
            if not (FONT_DIR / arq).exists():
                urllib.request.urlretrieve(src, FONT_DIR / arq)
            blocos.append(bloco.replace(src, f"FONTDIR/{arq}"))
    CSS.write_text("\n".join(blocos) + "\n", encoding="utf-8")
    print(len(blocos), "@font-face em", CSS)


def css(prefixo="assets/fonts"):
    return CSS.read_text(encoding="utf-8").replace("FONTDIR", prefixo)


def copia(projeto, prefixo="assets/fonts"):
    dest = Path(projeto) / prefixo
    dest.mkdir(parents=True, exist_ok=True)
    for f in FONT_DIR.glob("*.woff2"):
        if not (dest / f.name).exists():
            shutil.copy2(f, dest / f.name)


if __name__ == "__main__":
    if sys.argv[1:] == ["baixar"]:
        baixar()
    else:
        raise SystemExit(__doc__)
