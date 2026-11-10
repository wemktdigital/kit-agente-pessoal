#!/usr/bin/env python3
"""Prepara um corte da decupagem para virar reel no HyperFrames.

Gera em ~/Documents/hyperframes/we-corte-NN/:
  assets/cam-wa.mp4, assets/cam-ed.mp4 (1080x1920), assets/voz.wav
  scripts/palavras.json (palavra a palavra, alinhada ao srt) e scripts/falas.json (quem fala em cada frase)
Uso: ~/tools/Applio/.venv/bin/python prep.py NN
"""
import json, os, re, subprocess, sys, unicodedata
from pathlib import Path
from caminhos import DECUP, HF
import numpy as np, soundfile as sf, torch, torchaudio

NN = sys.argv[1]
E = Path(os.environ.get("ENTREGA", DECUP / f"cortes/{NN}/entrega"))
P = HF / f"we-corte-{NN}"
V = E / "video-decupado.mp4"
(P / "assets").mkdir(parents=True, exist_ok=True)
(P / "scripts").mkdir(exist_ok=True)

CROPS = {"wa": "crop=1216:2160:272:0", "ed": "crop=1216:2160:2488:0"}
for who, crop in CROPS.items():
    out = P / f"assets/cam-{who}.mp4"
    if not out.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(V), "-vf", f"{crop},scale=1080:1920:flags=lanczos",
                        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(out)], check=True)
voz = P / "assets/voz.wav"
if not voz.exists():
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(V), "-vn", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-ar", "48000", "-ac", "1", str(voz)], check=True)
DUR = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(voz)],
                           capture_output=True, text=True).stdout)


def ts(s):
    h, m, r = s.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(r)


cues = []
for blk in re.split(r"\n\s*\n", (E / "legenda-video-cortado.srt").read_text().strip()):
    ln = blk.strip().splitlines()
    a, b = [ts(x.strip()) for x in ln[1].split("-->")]
    cues.append(dict(s=a, e=b, text=" ".join(ln[2:]).strip()))


def norm(w):
    w = unicodedata.normalize("NFKD", w.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", w)


x, sr = sf.read(str(voz), dtype="float32")
x16 = torchaudio.functional.resample(torch.from_numpy(x), sr, 16000)
bundle = torchaudio.pipelines.MMS_FA
model = bundle.get_model(with_star=False).eval()
tok, aligner = bundle.get_tokenizer(), bundle.get_aligner()

palavras = []
for ci, c in enumerate(cues):
    a = max(0.0, c["s"] - 0.12)
    b = min(DUR, c["e"] + 0.12)
    seg = x16[int(a * 16000):int(b * 16000)][None]
    ws = c["text"].split()
    keys = [norm(w) for w in ws]
    keep = [i for i, k in enumerate(keys) if k]
    rows = [dict(texto=w, inicio=None, fim=None, frase=ci) for w in ws]
    try:
        with torch.inference_mode():
            em, _ = model(seg)
        spans = aligner(em[0], tok([keys[i] for i in keep]))
        ratio = seg.shape[1] / em.shape[1] / 16000
        for i, sp in zip(keep, spans):
            rows[i]["inicio"] = round(a + sp[0].start * ratio, 3)
            rows[i]["fim"] = round(a + sp[-1].end * ratio, 3)
    except Exception as ex:
        print("falha alinhando frase", ci, ex)
    n = len(rows)
    for i, r in enumerate(rows):
        if r["inicio"] is None:
            r["inicio"] = round(c["s"] + (c["e"] - c["s"]) * i / n, 3)
            r["fim"] = round(c["s"] + (c["e"] - c["s"]) * (i + 1) / n, 3)
    palavras += rows

# Quem fala: movimento da boca de cada um (diferença entre quadros na região da boca, 4K).
BOCA = {"wa": (800, 760, 260, 220), "ed": (3020, 720, 260, 220)}
energia = {}
for who, (bx, by, bw, bh) in (BOCA.items() if V.exists() else []):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(V), "-vf", f"fps=12,crop={bw}:{bh}:{bx}:{by},scale=64:54,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 54, 64).astype(np.float32)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    energia[who] = np.concatenate([[d[0]], d])
base = {w: np.median(e) + 1e-6 for w, e in energia.items()}
if not energia:
    energia = {w: np.ones(1000000) for w in BOCA}
    base = {w: 1.0 for w in BOCA}
falas = []
for ci, c in enumerate(cues):
    i0, i1 = int(c["s"] * 12), max(int(c["s"] * 12) + 1, int(c["e"] * 12))
    sc = {w: float(np.mean(e[i0:i1]) / base[w]) for w, e in energia.items()}
    falas.append(dict(frase=ci, s=c["s"], e=c["e"], quem=max(sc, key=sc.get), wa=round(sc["wa"], 2), ed=round(sc["ed"], 2), texto=c["text"]))

mms = E / "palavras-mms.json"
if mms.exists():
    ref = json.load(open(mms))
    if [w["texto"] for w in ref] == [w["texto"] for w in palavras]:
        for w, r in zip(palavras, ref):
            w["inicio"], w["fim"] = r["inicio"], r["fim"]
    else:
        print("palavras-mms.json não bate com o srt; mantive o alinhamento por frase")
json.dump(palavras, open(P / "scripts/palavras.json", "w"), ensure_ascii=False, indent=1)
json.dump(dict(duracao=round(DUR, 3), falas=falas), open(P / "scripts/falas.json", "w"), ensure_ascii=False, indent=1)
print("duracao", round(DUR, 3))
for f in falas:
    print(f'{f["frase"]:2d} {f["s"]:6.2f}-{f["e"]:6.2f} {f["quem"]} (wa {f["wa"]:.2f} ed {f["ed"]:.2f}) {f["texto"]}')
print()
print(" ".join(f'{w["texto"]}@{w["inicio"]:.2f}' for w in palavras))
