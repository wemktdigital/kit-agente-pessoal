#!/usr/bin/env python3
"""Refaz o áudio/vídeo dos reels a partir da fonte 4K sem picotar palavras e reconstrói os projetos.

Mesmo fluxo do refaz-cortes.sh, mas roda no macOS e no Windows.
Uso: <python do Applio> refaz_cortes.py NN [NN ...]   (log em <temp>/refaz/NN.log)
"""
import os
import subprocess
import sys

from caminhos import APPLIO_PY, HF, REELS, TMP, WHISPER_DIR

LOGS = TMP / "refaz"
LOGS.mkdir(parents=True, exist_ok=True)


def roda(log, args, env=None, filtro=None):
    r = subprocess.run(args, cwd=REELS, env=env, capture_output=True, text=True)
    saida = r.stdout + r.stderr
    log.write(saida)
    for linha in saida.splitlines():
        if filtro is None or any(f in linha for f in filtro):
            if "warn" not in linha.lower():
                print("  ", linha)
    if r.returncode:
        raise RuntimeError(f"{args[1] if len(args) > 1 else args[0]} saiu com {r.returncode}")


for n in sys.argv[1:]:
    with open(LOGS / f"{n}.log", "w") as log:
        print("=====", n)
        try:
            roda(log, [APPLIO_PY, "recorte.py", n], filtro=("duracao", "termina", "nenhuma", "fora", "voltam"))
            env = dict(os.environ, ENTREGA=str(HF / f"we-corte-{n}/fonte"))
            roda(log, [APPLIO_PY, "prep.py", n], env=env, filtro=("duracao", "não bate"))
            roda(log, [sys.executable, "remapeia.py", n], filtro=())
            roda(log, [sys.executable, "build.py", n, "--sem-capa"], filtro=None)
            roda(log, ["whisper-cli", "-m", str(WHISPER_DIR / "ggml-large-v3.bin"), "-l", "pt",
                       "-f", str(HF / f"we-corte-{n}/assets/voz.wav"), "-nt"], filtro=None)
            print("OK", n)
        except Exception as e:
            print("FALHOU", n, "-", e)
print("REFAZ_DONE")
