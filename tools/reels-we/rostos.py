#!/usr/bin/env python3
"""Folha de rostos: para cada frase do srt, 3 quadros com os dois rostos lado a lado (esq = wa, dir = ed).
Uso: ~/tools/Applio/.venv/bin/python rostos.py NN  -> /tmp/rostos-NN.jpg
"""
import io, json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from caminhos import DECUP, HF, TMP

NN = sys.argv[1]
V = DECUP / f"cortes/{NN}/entrega/video-decupado.mp4"
F = json.load(open(HF / f"we-corte-{NN}/scripts/falas.json"))["falas"]
W, H = 200, 186
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 26)


def frame(t):
    png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(V), "-frames:v", "1", "-vf",
                          f"split[x][y];[x]crop=560:520:600:520,scale={W}:{H}[l];[y]crop=560:520:2840:470,scale={W}:{H}[r];[l][r]hstack",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGB")


rows = []
for f in F:
    d = f["e"] - f["s"]
    ims = [frame(f["s"] + d * k) for k in (0.2, 0.5, 0.8)]
    row = Image.new("RGB", (3 * 2 * W + 8, H), "black")
    for k, im in enumerate(ims):
        row.paste(im, (k * (2 * W + 4), 0))
    ImageDraw.Draw(row).text((6, 4), str(f["frase"]), fill="yellow", font=font, stroke_width=3, stroke_fill="black")
    rows.append(row)
sheet = Image.new("RGB", (rows[0].width, len(rows) * (H + 4)), "black")
for i, r in enumerate(rows):
    sheet.paste(r, (0, i * (H + 4)))
sheet.save(TMP / f"rostos-{NN}.jpg", quality=80)
print(TMP / f"rostos-{NN}.jpg")
