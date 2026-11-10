"""Caminhos e executáveis do pipeline, iguais no macOS e no Windows.

Sobrescreva com variáveis de ambiente quando a máquina usar outro lugar:
  WE_DOCS    pasta que contém hyperframes/ e decupagem-videos/ (padrão: ~/Documents)
  WE_TOOLS   pasta que contém Applio/ e kokoro/ (padrão: ~/tools)
  WHISPER_DIR  modelos ggml do whisper.cpp (padrão: ~/models/whisper)
"""
import os
import sys
import tempfile
from pathlib import Path

WIN = os.name == "nt"
if WIN and not sys.flags.utf8_mode:
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, "-X", "utf8", *sys.orig_argv[1:]]))
HOME = Path.home()
DOCS = Path(os.environ.get("WE_DOCS", HOME / "Documents"))
TOOLS = Path(os.environ.get("WE_TOOLS", HOME / "tools"))
HF = DOCS / "hyperframes"
DECUP = DOCS / "decupagem-videos"
REELS = Path(__file__).resolve().parent
ASSETS = REELS / "assets"
APPLIO = TOOLS / "Applio"
WHISPER_DIR = Path(os.environ.get("WHISPER_DIR", HOME / "models/whisper"))
TMP = Path(tempfile.gettempdir())
HF_CLI = "hyperframes@0.8.185"
NPX = "npx.cmd" if WIN else "npx"


def venv_python(root):
    for rel in (".venv/bin/python", ".venv/Scripts/python.exe", "env/python.exe", "env/bin/python"):
        p = root / rel
        if p.exists():
            return str(p)
    return sys.executable


APPLIO_PY = venv_python(APPLIO)
KOKORO_PY = venv_python(TOOLS / "kokoro")
