#!/usr/bin/env python3
"""Refaz o corte de um reel direto da fonte 4K, sem picotar o fim/início das palavras.

Lê cortes/NN/cortes-4k.json, leva cada borda para o silêncio real entre as palavras (energia do áudio),
alinha ao quadro do vídeo e gera em ~/Documents/hyperframes/we-corte-NN/:
  assets/cam-wa.mp4, assets/cam-ed.mp4, assets/voz.wav, fonte/legenda-video-cortado.srt, fonte/recorte.json
Remapeia os tempos do scripts/spec.json para a nova linha do tempo (guarda spec-antes-recorte.json).
O áudio é cortado no ponto mais baixo entre as palavras (sem prender ao quadro do vídeo) e emendado com crossfade curto.
Sem a fonte original, usa entrega/trecho-completo.mp4 (começa em intervalo.inicio da fonte); FONTE e FONTE_INI forçam outra.
Hesitações (né, hum...) saem mesmo sem silêncio para cortar; conectores (e, aí, então...) só saem se houver silêncio
ou se tirá-los não piorar a emenda. --manter-vicios volta ao comportamento antigo.
Uso: ~/tools/Applio/.venv/bin/python recorte.py NN [--so-analise] [--manter-vicios]
"""
import difflib, json, os, re, subprocess, sys, unicodedata
from pathlib import Path
from caminhos import DECUP, HF, TMP
import numpy as np, soundfile as sf, torch, torchaudio

NN = sys.argv[1]
C = DECUP / f"cortes/{NN}"
P = HF / f"we-corte-{NN}"
J = json.load(open(C / "cortes-4k.json"))
SRC = os.environ.get("FONTE") or J["video"]
INI = float(os.environ.get("FONTE_INI", 0))
if not Path(SRC).exists():
    SRC, INI = str(C / "entrega/trecho-completo.mp4"), J["intervalo"]["inicio"]
MANTER_VICIOS = "--manter-vicios" in sys.argv
CLIPS = J["clips_to_keep"]
FPS = 24000 / 1001
SR = 48000
HOP = 0.01
XF = 0.02

a0 = max(INI, CLIPS[0]["start_time"] - 2.5)
a1 = CLIPS[-1]["end_time"] + 2.5
tmp = TMP / f"recorte-{NN}.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a0 - INI:.3f}", "-t", f"{a1 - a0:.3f}", "-i", SRC, "-vn", "-ac", "1", "-ar", str(SR), str(tmp)], check=True)
x, _ = sf.read(str(tmp), dtype="float32")
win = int(0.02 * SR)
hop = int(HOP * SR)
n = (len(x) - win) // hop
rms = np.array([np.sqrt(np.mean(x[i * hop:i * hop + win] ** 2)) for i in range(n)])
db = 20 * np.log10(rms + 1e-7)
piso, fala = np.percentile(db, 10), np.percentile(db, 90)
LIM = piso + 0.3 * (fala - piso)


def idx(t):
    return int(round((t - a0) / HOP))


def tempo(i):
    return a0 + i * HOP + 0.01


def norm(w):
    w = unicodedata.normalize("NFKD", w.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(ch for ch in w if not unicodedata.combining(ch)))


# alinhamento forçado da fonte com a transcrição completa (inclui as palavras que saíram)
TR = json.load(open(DECUP / f"temp/lote/{NN}/transcricao.json"))
OFF = CLIPS[0]["start_time"] - json.load(open(C / "cortes.json"))["clips_to_keep"][0]["start_time"]
fw = [w["word"].strip() for w in TR["words"] if w["end"] + OFF >= a0 + 0.05 and w["start"] + OFF <= a1 - 0.3 and norm(w["word"])]
bundle = torchaudio.pipelines.MMS_FA
model = bundle.get_model(with_star=True).eval()
tok, aligner = bundle.get_tokenizer(), bundle.get_aligner()
x16 = torchaudio.functional.resample(torch.from_numpy(x), SR, 16000)[None]
NUM = {"0": "zero", "1": "um", "2": "dois", "3": "tres", "4": "quatro", "5": "cinco", "6": "seis", "7": "sete", "8": "oito", "9": "nove"}


def falavel(w):
    k = norm(w)
    return "".join(NUM.get(ch, ch) for ch in k) if re.search(r"\d", k) else k


with torch.inference_mode():
    em, _ = model(x16)
seq_f = [t for w in fw for t in ("*", falavel(w))] + ["*"]
sp = [s_ for t, s_ in zip(seq_f, aligner(em[0], tok(seq_f))) if t != "*"]
rt = x16.shape[1] / em.shape[1] / 16000
fs = [(a0 + s[0].start * rt, a0 + s[-1].end * rt) for s in sp]


# palavras que a decupagem quis manter: cada trecho vai da sua primeira à sua última palavra,
# procuradas na transcrição perto das bordas do trecho (o texto do meio pode divergir da transcrição)
def ponta(ws, alvo_t, de_onde, lado):
    for desloc, w in enumerate(ws[:3]):
        cand = [i for i in range(de_onde, len(fw)) if norm(fw[i]) == w and abs(fs[i][0 if lado == 0 else 1] - alvo_t) < 2.0]
        if cand:
            i = min(cand, key=lambda i: abs(fs[i][0 if lado == 0 else 1] - alvo_t))
            return i - desloc if lado == 0 else i + desloc
    meio = [i for i in range(de_onde, len(fw)) if (fs[i][0] + fs[i][1]) / 2 >= alvo_t - 0.05] if lado == 0 else \
           [i for i in range(de_onde, len(fw)) if (fs[i][0] + fs[i][1]) / 2 <= alvo_t + 0.05]
    return (meio[0] if lado == 0 else meio[-1]) if meio else None


VICIOS = {"ne", "ai", "cara", "ali", "tipo", "assim", "ah", "eh", "hum", "ta", "sabe", "entao", "e"}
mant, ult, sem_vicio = [], -1, set()
for k, c in enumerate(CLIPS):
    ws = [norm(w) for w in c["text"].split() if norm(w)]
    if not ws:
        continue
    i0 = ponta(ws, c["start_time"], ult + 1, 0)
    i1 = ponta(ws[::-1], c["end_time"], ult + 1, 1)
    if i0 is None or i1 is None or i1 < i0:
        raise SystemExit(f"trecho {k} sem bordas: {c['text'][:60]}")
    i0 = max(i0, ult + 1)
    if abs((i1 - i0 + 1) - len(ws)) > max(2, 0.3 * len(ws)):
        print(f"aviso trecho {k}: decupagem {len(ws)} palavras, fonte {i1 - i0 + 1}: «{' '.join(fw[i0:i1 + 1])[:90]}»")
    mant += range(i0, i1 + 1)
    # vício no meio do trecho que a decupagem tirou do texto
    sem_vicio |= {i for i in range(i0 + 1, i1) if norm(fw[i]) in VICIOS and norm(fw[i]) not in ws}
    ult = i1
mset = set(mant)
HESITA = {"ne", "hum", "hm", "ah", "eh", "ahn", "uhm"}
if MANTER_VICIOS:
    # vício colado entre duas palavras mantidas volta (cortar picotaria a vizinha)
    for i in range(1, len(fw) - 1):
        meio = (fs[i][0] + fs[i][1]) / 2
        na_decupagem = any(c["start_time"] <= meio <= c["end_time"] for c in CLIPS)
        if i not in mset and i - 1 in mset and i + 1 in mset and na_decupagem and fs[i][0] - fs[i - 1][1] < 0.08 and fs[i + 1][0] - fs[i][1] < 0.08:
            mset.add(i)
else:
    mset -= {i for i in mset if norm(fw[i]) in HESITA} | sem_vicio
corte_velho = [c["end_time"] for c in CLIPS[:-1]]
if "--palavras" in sys.argv:
    print(" ".join(f"{fw[i]}@{fs[i][0]:.2f}-{fs[i][1]:.2f}" for i in range(len(fw))))


def vale(t0, t1, dentro=None, lado=1):
    """Instante, entre t0 e t1, onde o áudio está mais baixo; evita entrar na palavra (dentro)."""
    if t1 <= t0:
        return (t0 + t1) / 2
    pena = lambda t: 1.6 if dentro is not None and (t - dentro) * lado > 0 else 1.0
    return float(min(np.arange(t0, t1 + 1e-9, 0.002), key=lambda t: energia(t) * pena(t)))


def energia(t, meia=0.012):
    c = int((t - a0) * SR)
    w = x[max(0, c - int(meia * SR)):c + int(meia * SR)]
    return float(np.sqrt(np.mean(w ** 2)))


def db(t):
    return 20 * np.log10(energia(t) + 1e-7)


BORDAS = ([c["start_time"] for c in CLIPS], [c["end_time"] for c in CLIPS])


def ancora(t, lado, lo, hi):
    """Borda da decupagem perto de t, se cair em silêncio. O alinhamento forçado arrasta palavras através de pausas longas.
    lo/hi: a borda não pode atravessar a palavra vizinha (senão o trecho engole palavras que saíram)."""
    perto = [b for b in BORDAS[lado] if abs(b - t) < 0.8 and lo <= b <= hi]
    if not perto:
        return None
    b = min(perto, key=lambda b: abs(b - t))
    v = vale(b - 0.1, b + 0.1)
    return v if db(v) <= LIM else None


def montar(mset):
    mant = sorted(mset)
    runs = [[mant[0]]]
    for i in mant[1:]:
        p_ = runs[-1][-1]
        pausa_cortada = any(fs[p_][1] - 0.05 <= t <= fs[i][0] + 0.05 for t in corte_velho) and fs[i][0] - fs[p_][1] > 0.4
        if i == p_ + 1 and not pausa_cortada:
            runs[-1].append(i)
        else:
            runs.append([i])
    out = []
    for r in runs:
        i, j = r[0], r[-1]
        ant_fim = fs[i - 1][1] if i > 0 else fs[i][0] - 0.4
        prox_ini = fs[j + 1][0] if j + 1 < len(fw) else fs[j][1] + 0.4
        s = vale(max(ant_fim - 0.03, fs[i][0] - 0.18), fs[i][0] + 0.03, fs[i][0], 1)
        e = vale(max(fs[j][1] - 0.06, fs[j][0] + 0.1), min(prox_ini + 0.03, fs[j][1] + 0.25), fs[j][1], -1)
        # a borda da decupagem só amplia o trecho: encurtar já picotou fim de palavra
        s = min(s, ancora(s, 0, ant_fim - 0.03, fs[i][0] + 0.03) or s)
        e = max(e, ancora(e, 1, fs[j][1] - 0.03, prox_ini + 0.03) or e)
        ant = out[-1]["e"] if out else a0
        s, e = round(max(s, ant), 4), round(e, 4)
        out.append(dict(s=s, e=e, ids=r, txt=" ".join(fw[t] for t in r),
                        vizinhas=(fw[i - 1] if i else "", fw[j + 1] if j + 1 < len(fw) else ""),
                        db=(round(db(s), 1), round(db(e), 1))))
    return out


def vao_db(a, b):
    """dB do ponto mais baixo entre as palavras a e b (vizinhas, em qualquer ordem)."""
    lo, hi = (fs[a][1], fs[b][0]) if a < b else (fs[b][1], fs[a][0])
    return db(vale(lo - 0.03, hi + 0.03))


def corte_db(a, b):
    """dB do corte entre a palavra a (que voltaria) e a b; sem corte (b mantida) = -99."""
    if b in mset or not 0 <= b < len(fw):
        return -99.0
    return vao_db(a, b)


def pode_voltar(k):
    """Conector (e, aí, ali, então...) volta quando não há silêncio para tirá-lo; hesitação (né, hum) só com --manter-vicios."""
    return k not in mset and norm(fw[k]) in VICIOS and fs[k][1] - fs[k][0] < 0.35 and (MANTER_VICIOS or norm(fw[k]) not in HESITA)


for _ in range(5):
    novos = montar(mset)
    volta, sai = set(), set()
    for c in novos:
        i, j = c["ids"][0], c["ids"][-1]
        # sem --manter-vicios, só volta se a nova emenda ficar mais limpa que a atual
        if c is not novos[-1] and c["db"][1] > LIM and j + 1 < len(fw) and pode_voltar(j + 1) and (MANTER_VICIOS or corte_db(j + 1, j + 2) < c["db"][1]):
            volta.add(j + 1)
        if c is not novos[0] and c["db"][0] > LIM and i > 0 and pode_voltar(i - 1) and (MANTER_VICIOS or corte_db(i - 1, i - 2) < c["db"][0]):
            volta.add(i - 1)
        # vício na borda do trecho, colado na palavra que saiu: sai também se a emenda do outro lado for bem mais limpa
        if not MANTER_VICIOS and len(c["ids"]) > 1:
            if c is not novos[0] and c["db"][0] > LIM and norm(fw[i]) in VICIOS and vao_db(i, i + 1) <= c["db"][0] - 5:
                sai.add(i)
            if c is not novos[-1] and c["db"][1] > LIM and norm(fw[j]) in VICIOS and vao_db(j - 1, j) <= c["db"][1] - 5:
                sai.add(j)
    if not volta and not sai:
        break
    if volta:
        print("voltam (sem silêncio para cortar):", " ".join(fw[i] for i in sorted(volta)))
    if sai:
        print("saem (vício colado na borda):", " ".join(fw[i] for i in sorted(sai)))
    mset = (mset | volta) - sai
mant = sorted(mset)
novos = montar(mset)

# ajuste manual por corte, em segundos da fonte, quando o alinhamento estica a palavra até a vizinha:
# cortes/NN/bordas.json = {"mover": [[borda_atual, nova], ...], "tirar": [[de, ate], ...]}
AJ = json.load(open(C / "bordas.json")) if (C / "bordas.json").exists() else {}
for perto, nova in AJ.get("mover", []):
    for c in novos:
        for k in ("s", "e"):
            if abs(c[k] - perto) < 0.15:
                c[k] = nova
for a, b in AJ.get("tirar", []):
    for k, c in enumerate(novos):
        if c["s"] < a < b < c["e"]:
            meio = lambda i: (fs[i][0] + fs[i][1]) / 2
            ids0 = [i for i in c["ids"] if meio(i) < (a + b) / 2]
            ids1 = [i for i in c["ids"] if meio(i) >= (a + b) / 2]
            novos[k:k + 1] = [dict(c, e=a, ids=ids0, txt=" ".join(fw[i] for i in ids0)),
                              dict(c, s=b, ids=ids1, txt=" ".join(fw[i] for i in ids1))]
            break
for c in novos:
    c["db"] = (round(db(c["s"]), 1), round(db(c["e"]), 1))
if AJ:
    print("bordas.json aplicado:", AJ)

print(f"limiar {LIM:.1f} dB (piso {piso:.1f}, fala {fala:.1f})")
print("fora:", " ".join(fw[i] for i in range(mant[0], mant[-1]) if i not in mset))
for k, c in enumerate(novos):
    print(f'{k:2d} {c["s"]:.3f}-{c["e"]:.3f} ({c["db"][0]:.0f}/{c["db"][1]:.0f} dB)  [{c["vizinhas"][0]}] {c["txt"]} [{c["vizinhas"][1]}]')
if "--so-analise" in sys.argv:
    sys.exit()

# ---------------------------------------------------------------- mídia
(P / "fonte").mkdir(parents=True, exist_ok=True)
for nome in ("palavras.json", "spec.json", "falas.json"):
    velho, guarda = P / f"scripts/{nome}", P / f"scripts/{nome[:-5]}-antes-recorte.json"
    if velho.exists() and not guarda.exists():
        guarda.write_text(velho.read_text())
(P / "assets").mkdir(parents=True, exist_ok=True)
# vídeo em quadros inteiros; o erro de arredondamento é distribuído para o total seguir o áudio (dessincronia < 1 quadro)
fbase = max(0, int(np.floor((novos[0]["s"] - INI - 0.5) * FPS)))
vseek = (fbase - 0.5) / FPS if fbase else 0.0
vdur = novos[-1]["e"] - INI - vseek + 0.5
DUR = sum(c["e"] - c["s"] for c in novos)
fc, acc, f_ant = [], 0.0, 0
for k, c in enumerate(novos):
    acc += c["e"] - c["s"]
    f_tot = round(acc * FPS)
    f0 = round((c["s"] - INI) * FPS) - fbase
    fc.append(f"[0:v]trim=start_frame={f0}:end_frame={f0 + f_tot - f_ant},setpts=PTS-STARTPTS[v{k}]")
    f_ant = f_tot
    s = c["s"] - INI - vseek - (XF / 2 if k else 0)
    e = c["e"] - INI - vseek + (XF / 2 if k < len(novos) - 1 else 0)
    fc.append(f"[0:a]atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:channel_layouts=mono[a{k}]")
fc.append("".join(f"[v{k}]" for k in range(len(novos))) + f"concat=n={len(novos)}:v=1:a=0[v]")
emenda = "a0"
for k in range(1, len(novos)):
    fc.append(f"[{emenda}][a{k}]acrossfade=d={XF}:c1=qsin:c2=qsin[x{k}]")
    emenda = f"x{k}"
fc.append(f"[{emenda}]afade=t=in:d=0.005,afade=t=out:st={DUR - 0.015:.4f}:d=0.015[a]")
fc.append("[v]split=2[vw][ve]")
fc.append("[vw]crop=1216:2160:272:0,scale=1080:1920:flags=lanczos[ow]")
fc.append("[ve]crop=1216:2160:2488:0,scale=1080:1920:flags=lanczos[oe]")
fc.append("[a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[oa]")
enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", f"{FPS:.6f}", "-movflags", "+faststart"]
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{vseek:.4f}", "-t", f"{vdur:.3f}", "-i", SRC, "-filter_complex", ";".join(fc),
                "-map", "[ow]", "-an", *enc, str(P / "assets/cam-wa.mp4"),
                "-map", "[oe]", "-an", *enc, str(P / "assets/cam-ed.mp4"),
                "-map", "[oa]", "-ac", "1", "-ar", "48000", str(P / "assets/voz.wav")], check=True)

# ---------------------------------------------------------------- alinhamento global e legenda
palavras, ci, n_cue = [], 0, 0
for k, c in enumerate(novos):
    for m, i in enumerate(c["ids"]):
        if palavras and (m == 0 or n_cue >= 8 or palavras[-1][1][-1] in ".?!" or (palavras[-1][1][-1] == "," and n_cue >= 4)):
            ci += 1
            n_cue = 0
        palavras.append((ci, fw[i]))
        n_cue += 1
cues = [" ".join(w for c_, w in palavras if c_ == k) for k in range(ci + 1)]
y, _ = sf.read(str(P / "assets/voz.wav"), dtype="float32")
y16 = torchaudio.functional.resample(torch.from_numpy(y), SR, 16000)[None]
keep = [i for i, (_, w) in enumerate(palavras) if norm(w)]
with torch.inference_mode():
    em, _ = model(y16)
seq = [t for i in keep for t in ("*", falavel(palavras[i][1]))] + ["*"]
spans = [sp for t, sp in zip(seq, aligner(em[0], tok(seq))) if t != "*"]
ratio = y16.shape[1] / em.shape[1] / 16000
tw = {i: (sp[0].start * ratio, sp[-1].end * ratio) for i, sp in zip(keep, spans)}


def fmt(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


blocos = []
for ci, t in enumerate(cues):
    ids = [i for i in keep if palavras[i][0] == ci]
    s, e = tw[ids[0]][0], tw[ids[-1]][1]
    blocos.append(f"{ci + 1}\n{fmt(max(0, s - 0.02))} --> {fmt(min(DUR, e + 0.06))}\n{t}\n")
(P / "fonte/legenda-video-cortado.srt").write_text("\n".join(blocos))
json.dump([dict(texto=palavras[i][1], inicio=round(tw[i][0], 3), fim=round(tw[i][1], 3)) for i in keep],
          open(P / "fonte/palavras-mms.json", "w"), ensure_ascii=False, indent=1)

# conferência: a última palavra de cada trecho termina antes do corte?
offs, acc = [], 0.0
for c in novos:
    offs.append((acc, acc + c["e"] - c["s"]))
    acc += c["e"] - c["s"]
avisos = []
for i in keep:
    s, e = tw[i]
    for k, (o0, o1) in enumerate(offs):
        if o0 <= s < o1 and e > o1 - 0.025:
            avisos.append(f"«{palavras[i][1]}» termina {e - o1:+.3f}s do corte {k}")
print("duracao", round(DUR, 3))
print("\n".join(avisos) if avisos else "nenhuma palavra encostando no corte")
json.dump(dict(fonte=SRC, fonte_ini=INI, fps=FPS, trechos=[{k: v for k, v in c.items()} for c in novos]), open(P / "fonte/recorte.json", "w"), ensure_ascii=False, indent=1)
