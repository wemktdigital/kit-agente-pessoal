#!/usr/bin/env python3
"""Versão dublada (en/es) de um reel WE, a partir do projeto PT pronto.

Lê we-corte-NN/scripts/traducao-LL.json (uma frase traduzida por frase de falas.json, chave, capa, cards),
gera a voz (Kokoro + RVC do Waldeir), alinha palavra a palavra (MMS), reajusta o vídeo das câmeras por trechos
e grava we-corte-NN-LL/ com assets/ e scripts/ prontos para o build.py NN-LL.
Abertura estilo documentário: o PT começa sozinho, abaixa quando a dublagem entra e some em poucos segundos.
Uso: ~/tools/Applio/.venv/bin/python dub.py NN en|es
"""
import hashlib, json, os, re, shutil, subprocess, sys, unicodedata
from pathlib import Path
from caminhos import APPLIO, APPLIO_PY, HF, HF_CLI, KOKORO_PY, NPX, TMP
import numpy as np, soundfile as sf, torch, torchaudio

NN, L = sys.argv[1], sys.argv[2]
PT = HF / f"we-corte-{NN}"
P = HF / f"we-corte-{NN}-{L}"
TR = json.load(open(PT / f"scripts/traducao-{L}.json"))
FALAS = json.load(open(PT / "scripts/falas.json"))
SPEC = json.load(open(PT / "scripts/spec.json"))
W = TMP / f"dub-{NN}-{L}"
W.mkdir(parents=True, exist_ok=True)
(P / "assets").mkdir(parents=True, exist_ok=True)
(P / "scripts").mkdir(parents=True, exist_ok=True)
SR = 48000
FPS = 24000 / 1001
RVC = {"wa": ("logs/c06-esq/c06-esq_20e_1740s.pth", "logs/c06-esq/c06-esq.index"),
       "ed": ("logs/c06-dir/c06-dir_20e_1580s.pth", "logs/c06-dir/c06-dir.index")}
ENTRA = TR.get("entra", 1.0)             # dublagem começa aqui; antes só o PT
PT_BAIXO, PT_SOME = TR.get("pt_baixo", 3.0), TR.get("pt_some", 4.0)
fr_pt = FALAS["falas"]
frases = TR["frases"]
assert len(frases) == len(fr_pt), f"{len(frases)} frases traduzidas para {len(fr_pt)} do PT"


def norm(w):
    w = unicodedata.normalize("NFKD", w.lower())
    return re.sub(r"[^a-z]", "", "".join(ch for ch in w if not unicodedata.combining(ch)))


def load(p):
    x, sr = sf.read(str(p), dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    if sr != SR:
        x = torchaudio.functional.resample(torch.from_numpy(x), sr, SR).numpy()
    return x


def apara(x, lim=-42, pad=0.04):
    hop = int(0.01 * SR)
    n = len(x) // hop
    db = 20 * np.log10(np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, 1) + 1e-12) / (np.abs(x).max() + 1e-9))
    on = np.where(db > lim)[0]
    return x[max(0, on[0] * hop - int(pad * SR)):min(len(x), (on[-1] + 1) * hop + int(pad * SR))]


# ---------------------------------------------------------------- blocos (uma frase completa por TTS, prosódia natural)
blocos, atual = [], []
for k, f in enumerate(frases):
    if f.strip():
        atual.append(k)
    if atual and (re.search(r"[.?!]$", f.strip()) or k == len(frases) - 1):
        blocos.append(atual)
        atual = []
quem = lambda b: fr_pt[b[0]].get("quem", SPEC.get("quem", "wa"))
env = dict(os.environ, HYPERFRAMES_PYTHON=KOKORO_PY)
audios = []
for b in blocos:
    txt = " ".join(frases[k] for k in b)
    h = hashlib.md5(f"{TR['voz']}|{TR['pitch']}|{txt}".encode()).hexdigest()[:10]
    base, rvc = W / f"{h}-base.wav", W / f"{h}-rvc.wav"
    if not rvc.exists():
        args = [NPX, "--yes", HF_CLI, "tts", txt, "-v", TR["voz"], "-o", str(base)]
        if L == "es":
            args += ["-l", "es"]
        subprocess.run(args, check=True, capture_output=True, cwd=PT, env=env)
        pth, idx = RVC[quem(b)]
        subprocess.run([APPLIO_PY, "core.py", "infer", "--input-path", str(base), "--output-path", str(rvc),
                        "--pth-path", pth, "--index-path", idx, "--pitch", str(TR["pitch"]), "--index-rate", "0.8", "--protect", "0.4",
                        "--f0-method", "rmvpe", "--export-format", "WAV"], check=True, capture_output=True, cwd=APPLIO)
    audios.append(apara(load(rvc)))
    print(f"bloco {b[0]}-{b[-1]} {len(audios[-1]) / SR:5.2f}s  {txt}")

# ---------------------------------------------------------------- linha do tempo da dublagem (pausas do PT, limitadas)
inicio, t = [], ENTRA
for i, b in enumerate(blocos):
    inicio.append(t)
    t += len(audios[i]) / SR
    if i + 1 < len(blocos):
        gap = fr_pt[blocos[i + 1][0]]["s"] - fr_pt[b[-1]]["e"]
        t += min(max(gap, 0.25), 0.6)
DUB = t + 0.35
dub = np.zeros(int(DUB * SR) + SR, dtype=np.float32)
for i, a in enumerate(audios):
    s = int(inicio[i] * SR)
    dub[s:s + len(a)] += a
dub = dub[:int(DUB * SR)]
sf.write(str(W / "dub-cru.wav"), dub, SR)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(W / "dub-cru.wav"), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), "-ac", "1",
                str(W / "dub-norm.wav")], check=True)
dub = load(W / "dub-norm.wav")[:int(DUB * SR)]

# ---------------------------------------------------------------- alinhamento palavra a palavra (MMS com curinga)
bundle = torchaudio.pipelines.MMS_FA
model = bundle.get_model(with_star=True).eval()
tok, aligner = bundle.get_tokenizer(), bundle.get_aligner()
palavras = []
for i, b in enumerate(blocos):
    ws = [(k, w) for k in b for w in frases[k].split()]
    ok = [j for j, (_, w) in enumerate(ws) if norm(w)]
    a = audios[i]
    x16 = torchaudio.functional.resample(torch.from_numpy(a), SR, 16000)[None]
    with torch.inference_mode():
        em, _ = model(x16)
    seq = [s for j in ok for s in ("*", norm(ws[j][1]))] + ["*"]
    sp = [s for tk, s in zip(seq, aligner(em[0], tok(seq))) if tk != "*"]
    rt = x16.shape[1] / em.shape[1] / 16000
    tw = {j: (inicio[i] + s[0].start * rt, inicio[i] + s[-1].end * rt) for j, s in zip(ok, sp)}
    for j, (k, w) in enumerate(ws):
        a0, a1 = tw.get(j) or tw.get(j - 1) or tw[min(tw)]
        palavras.append(dict(texto=w, inicio=round(a0, 3), fim=round(a1, 3), frase=k))
falas = []
for k, f in enumerate(fr_pt):
    pw = [w for w in palavras if w["frase"] == k]
    if not pw:
        continue
    falas.append({**f, "s": pw[0]["inicio"], "e": pw[-1]["fim"], "texto": frases[k]})
json.dump(palavras, open(P / "scripts/palavras.json", "w"), ensure_ascii=False, indent=1)
json.dump(dict(duracao=round(DUB, 3), falas=falas), open(P / "scripts/falas.json", "w"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- vozes em faixas separadas: dublagem e PT da abertura
pt = load(PT / "assets/voz.wav")
n = int(PT_SOME * SR)
tt = np.arange(n) / SR
g = np.interp(tt, [0, ENTRA - 0.1, ENTRA + 0.3, PT_BAIXO, PT_SOME], [0.75, 0.75, 0.2, 0.2, 0.0])
sf.write(str(P / "assets/voz.wav"), dub / max(1.0, np.abs(dub).max() / 0.97), SR)
sf.write(str(P / "assets/voz-original.wav"), pt[:n] * g, SR)

# ---------------------------------------------------------------- vídeo: igual ao PT na abertura, depois acompanha as frases
mapa_fala = sorted({(f["s"], d["s"]) for f, d in zip([fr_pt[d["frase"]] for d in falas], falas)} |
                   {(f["e"], d["e"]) for f, d in zip([fr_pt[d["frase"]] for d in falas], falas)})
ancoras = [(0.0, 0.0), (PT_SOME, PT_SOME)]
for p_, d_ in sorted((fr_pt[d["frase"]]["s"], d["s"]) for d in falas):
    p0, d0 = ancoras[-1]
    if d_ > PT_SOME + 0.4 and p_ > p0 + 0.3 and 0.6 <= (d_ - d0) / (p_ - p0) <= 1.7:
        ancoras.append((p_, d_))
ancoras.append((FALAS["duracao"], DUB))
print("âncoras do vídeo:", [(round(a, 2), round(b, 2)) for a, b in ancoras])
for cam in sorted(PT.glob("assets/cam-*.mp4")):
    fc, vs = [], []
    for k, ((p0, d0), (p1, d1)) in enumerate(zip(ancoras, ancoras[1:])):
        fc.append(f"[0:v]trim=start={p0:.4f}:end={p1:.4f},setpts=(PTS-STARTPTS)*{(d1 - d0) / (p1 - p0):.5f}[v{k}]")
        vs.append(f"[v{k}]")
    fc.append("".join(vs) + f"concat=n={len(vs)}:v=1:a=0,fps={FPS:.6f}[o]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(cam), "-filter_complex", ";".join(fc), "-map", "[o]", "-an",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(P / "assets" / cam.name)], check=True)


def leva(t, mapa):
    xs, ys = zip(*mapa)
    if t <= xs[0]:
        return ys[0] + t - xs[0]
    if t >= xs[-1]:
        return ys[-1] + t - xs[-1]
    return float(np.interp(t, xs, ys))


def volta(d):
    xs, ys = zip(*ancoras)
    return float(np.interp(d, ys, xs))


# ---------------------------------------------------------------- spec traduzido, tempos na fala dublada
spec = json.loads(json.dumps(SPEC))
spec["idioma"] = L
spec["chave"] = TR.get("chave", [])
CHAVES_T = {"de", "ate", "t", "t_estrelas"}
LISTAS_T = {"trocas", "duplas"}
mt = lambda v: round(max(0.0, leva(v, mapa_fala)), 2)


def anda(o):
    if isinstance(o, dict):
        return {k: (mt(v) if k in CHAVES_T and isinstance(v, (int, float))
                    else [[mt(x) if isinstance(x, (int, float)) else x for x in it] for it in v] if k in LISTAS_T
                    else anda(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [anda(x) for x in o]
    return o


capa = spec.pop("capa", {})
spec = anda(spec)
for c, tr in zip(spec.get("cards", []), TR.get("cards", [])):
    for k, v in tr.items():
        if k in ("itens", "grupos"):
            for it, txt in zip(c.get(k, c.get("passos", [])), v):
                it["txt"] = txt
        else:
            c[k] = v
if spec.get("notif"):
    spec["notif"].update(TR.get("notif", {}))
if capa:
    capa.update(TR.get("capa", {}))
    if "t" in capa:
        alvo = capa["t"]
        capa["t"] = round(next((d for d in np.arange(0, DUB, 0.01) if volta(d) >= alvo), alvo), 2)
    spec["capa"] = capa
for k, v in TR.get("spec", {}).items():
    spec[k] = v
json.dump(spec, open(P / "scripts/spec.json", "w"), ensure_ascii=False, indent=2)
print(f"{L}: dublagem {DUB:.2f}s (PT {FALAS['duracao']:.2f}s), {len(palavras)} palavras -> {P}")
