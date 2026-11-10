"""Exporta um PNG por card/story em export/ (Mac e Windows): python exportar.py

Antes do snapshot embute as fontes do kit e troca os emoji por PNG da Apple
(tools/reels-we/portatil.py), para sair igual em qualquer máquina.
Carrossel (tem #c1b): card-01-escuro, card-02..N, card-01-claro (último clip).
Stories: story-01..N.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8", errors="replace")


def acha_reels_we():
    for p in [os.environ.get("WE_TOOLS") and Path(os.environ["WE_TOOLS"]) / "reels-we",
              Path.home() / "tools" / "reels-we",
              AQUI.parent.parent / "tools" / "reels-we"]:
        if p and (p / "portatil.py").exists():
            return p
    raise SystemExit("não achei tools/reels-we do kit (rode o instalador do kit-agente-pessoal)")


sys.path.insert(0, str(acha_reels_we()))
import portatil  # noqa: E402

html = (AQUI / "index.html").read_text(encoding="utf-8")
n = int(re.search(r'data-composition-id="main"[^>]*?data-duration="(\d+)"', html).group(1))
carrossel = 'id="c1b"' in html

portatil.prepara(AQUI)

exp = AQUI / "export"
exp.mkdir(exist_ok=True)
for f in exp.glob("*.png"):
    f.unlink()
npx = "npx.cmd" if os.name == "nt" else "npx"
ats = ",".join(f"{i + 0.5:.1f}" for i in range(n))
r = subprocess.run([npx, "--yes", "hyperframes", "snapshot", ".", "--at", ats, "--no-end", "-o", "export", "--json"],
                   cwd=AQUI, capture_output=True, text=True, encoding="utf-8", errors="replace")
if r.returncode:
    print(r.stdout[-2000:], r.stderr[-2000:])
    raise SystemExit("snapshot falhou")

for i in range(n):
    src = next(exp.glob(f"frame-{i:02d}-*.png"))
    if carrossel:
        dest = "card-01-escuro.png" if i == 0 else "card-01-claro.png" if i == n - 1 else f"card-{i + 1:02d}.png"
    else:
        dest = f"story-{i + 1:02d}.png"
    src.replace(exp / dest)

avisos = [l for l in r.stderr.splitlines() if "[WARN]" in l and "font" in l.lower() and "Emoji" not in l]
print("\n".join(sorted(p.name for p in exp.iterdir())))
if avisos:
    print("\nATENÇÃO: alguma fonte não carregou e o visual pode ter mudado:\n" + "\n".join(avisos), file=sys.stderr)
    raise SystemExit(2)
