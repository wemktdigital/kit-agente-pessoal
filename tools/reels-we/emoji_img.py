"""Troca emoji do HTML por PNG no desenho da Apple (assets/emoji, gerados por gerar_emoji.py).

Emoji dentro de <script>, <style> e atributos ficam como estão.
"""
import re
import shutil
from pathlib import Path

PNG_DIR = Path(__file__).resolve().parent / "assets" / "emoji"

_E = r"[\u2600-\u27BF\u2B00-\u2BFF\u2190-\u21FF\u2300-\u23FF\u203C\u2049\U0001F000-\U0001FAFF]"
EMOJI_RE = re.compile(rf"{_E}[\uFE0F\U0001F3FB-\U0001F3FF]*(?:\u200D{_E}[\uFE0F\U0001F3FB-\U0001F3FF]*)*")
BLOCO_RE = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>|<[^>]*>)", re.S | re.I)
MARCA = "data-emoji-img"
STYLE = f"<style {MARCA}>img.emoji-img{{display:inline-block;width:1em;height:1em;vertical-align:-.06em;object-fit:contain}}</style>"


def nome(e):
    return "-".join(f"{ord(c):x}" for c in e if c != "\ufe0f")


def troca(html, projeto, prefixo="assets/emoji"):
    """Devolve (html, emoji_sem_png). Copia os PNG usados para projeto/prefixo."""
    faltando = set()

    def sub(m):
        e = m.group(0)
        p = PNG_DIR / f"{nome(e)}.png"
        if not p.exists():
            if ord(e[0]) >= 0x1F000 or "\ufe0f" in e:
                faltando.add(e)
            return e
        dest = Path(projeto) / prefixo / p.name
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
        return f'<img class="emoji-img" src="{prefixo}/{p.name}" alt="" />'

    partes = BLOCO_RE.split(html)
    for i in range(0, len(partes), 2):
        partes[i] = EMOJI_RE.sub(sub, partes[i])
    novo = "".join(partes)
    if novo != html and MARCA not in novo:
        if re.search(r"</head>", novo, re.I):
            novo = re.sub(r"</head>", STYLE + "\n</head>", novo, count=1, flags=re.I)
        elif novo.lstrip().startswith("<template>"):
            novo = novo.replace("<template>", "<template>\n" + STYLE, 1)
        else:
            novo = STYLE + novo
    return novo, faltando
