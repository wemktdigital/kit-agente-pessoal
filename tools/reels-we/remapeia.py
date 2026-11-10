#!/usr/bin/env python3
"""Leva os tempos do scripts/spec.json da linha do tempo antiga para a nova depois do recorte.py.

Âncoras: palavras de scripts/palavras-antes-recorte.json casadas com scripts/palavras.json (difflib).
Cada tempo vai junto da palavra antiga mais próxima. Lê spec-antes-recorte.json, grava spec.json.
Uso: python3 remapeia.py NN
"""
import difflib, json, re, sys, unicodedata
from pathlib import Path
from caminhos import HF

NN = sys.argv[1]
P = HF / f"we-corte-{NN}/scripts"
velho = json.load(open(P / "palavras-antes-recorte.json"))
novo = json.load(open(P / "palavras.json"))
spec = json.load(open(P / "spec-antes-recorte.json"))
CHAVES_T = {"de", "ate", "t", "t_estrelas", "t_res"}


def norm(w):
    w = unicodedata.normalize("NFKD", w.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(ch for ch in w if not unicodedata.combining(ch)))


sm = difflib.SequenceMatcher(None, [norm(w["texto"]) for w in velho], [norm(w["texto"]) for w in novo], autojunk=False)
pares = [(velho[a + k], novo[b + k]) for a, b, n in sm.get_matching_blocks() for k in range(n)]
dur = max(w["fim"] for w in novo)


def leva(t):
    v, n = min(pares, key=lambda p: min(abs(t - p[0]["inicio"]), abs(t - p[0]["fim"])))
    base = (v["inicio"], n["inicio"]) if abs(t - v["inicio"]) <= abs(t - v["fim"]) else (v["fim"], n["fim"])
    return round(min(max(0.0, base[1] + t - base[0]), dur + 0.3), 2)


LISTAS_T = {"trocas", "duplas"}


def anda(o):
    if isinstance(o, dict):
        return {k: ([[leva(x) if isinstance(x, (int, float)) else x for x in item] for item in v] if k in LISTAS_T else
                    leva(v) if k in CHAVES_T and isinstance(v, (int, float)) else anda(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [anda(x) for x in o]
    return o


capa = spec.pop("capa", None)
out = anda(spec)
for (a0, a1), d in zip(spec.get("duplas", []), out.get("duplas", [])):
    d[1] = round(min(dur, max(d[1], d[0] + min(a1 - a0, 1.5))), 2)
if capa:
    capa["t"] = leva(capa["t"]) if "t" in capa else capa.get("t")
    out["capa"] = capa
json.dump(out, open(P / "spec.json", "w"), ensure_ascii=False, indent=2)
print(f"{len(pares)}/{len(velho)} palavras casadas")
fv = P / "falas-antes-recorte.json"
if fv.exists():
    quem_velho = {f["frase"]: f["quem"] for f in json.load(open(fv))["falas"]}
    idx = {id(n): v for v, n in pares}
    falas = json.load(open(P / "falas.json"))
    trocas = []
    for f in falas["falas"]:
        votos = [quem_velho.get(idx[id(w)].get("frase")) for w in novo if w.get("frase") == f["frase"] and id(w) in idx]
        votos = [v for v in votos if v]
        if votos:
            q = max(set(votos), key=votos.count)
            if q != f["quem"]:
                trocas.append(f["frase"])
            f["quem"] = q
    json.dump(falas, open(P / "falas.json", "w"), ensure_ascii=False, indent=1)
    print("quem fala:", " ".join(f'{f["frase"]}:{f["quem"]}' for f in falas["falas"]))
for a, b in zip(spec.get("cards", []), out.get("cards", [])):
    print(f'{a["tipo"]:9s} {a["de"]:6.2f}-{a["ate"]:6.2f} -> {b["de"]:6.2f}-{b["ate"]:6.2f}')
