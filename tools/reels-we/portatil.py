"""Deixa um projeto HyperFrames com render igual no Mac e no Windows:
fontes do kit embutidas (@font-face local) e emoji trocados por PNG da Apple.

Uso: python portatil.py <pasta-do-projeto>   (index.html, compositions/*.html, capa/index.html)
É idempotente: rodar de novo não duplica nada.
"""
import re
import sys
from pathlib import Path

import emoji_img
import fontes

MARCA = "data-fontes-kit"


def _injeta_fontes(html):
    if MARCA in html:
        return html
    bloco = f"<style {MARCA}>\n{fontes.css()}</style>\n"
    if re.search(r"<head[^>]*>", html, re.I):
        return re.sub(r"(<head[^>]*>)", lambda m: m.group(1) + "\n" + bloco, html, count=1, flags=re.I)
    if html.lstrip().startswith("<template>"):
        return html.replace("<template>", "<template>\n" + bloco, 1)
    return bloco + html


def arquivos(projeto):
    projeto = Path(projeto)
    return [p for p in [projeto / "index.html", *sorted((projeto / "compositions").glob("*.html"))] if p.exists()]


def prepara(projeto, lista=None):
    projeto = Path(projeto)
    fontes.copia(projeto)
    faltando = set()
    for arq in lista or arquivos(projeto):
        arq = Path(arq)
        t = arq.read_text(encoding="utf-8")
        novo, f = emoji_img.troca(_injeta_fontes(t), projeto)
        faltando |= f
        if novo != t:
            arq.write_text(novo, encoding="utf-8")
    if faltando:
        print("emoji sem PNG Apple (sai no desenho do sistema):", " ".join(sorted(faltando)), file=sys.stderr)
    return faltando


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    p = Path(sys.argv[1])
    prepara(p)
    if (p / "capa" / "index.html").exists():
        prepara(p / "capa")
