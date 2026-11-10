#!/usr/bin/env python3
"""Monta o projeto HyperFrames de um corte a partir de scripts/spec.json.

Modelos:
  A  câmera em tela cheia com zoom seco, legenda de uma linha (palavra-chave ciano maior), cards de vidro claros.
  B  tela dividida (painel azul-marinho em cima, quem fala embaixo), legenda em caixa alta com pílula ciano na palavra ativa.
  C  câmera em tela cheia com zoom seco, cards estilo janela macOS, legenda minúscula em duas linhas, notificação do Google.
Uso: python3 build.py NN
"""
import html, json, re, shutil, subprocess, sys
from pathlib import Path
from caminhos import ASSETS, HF, HF_CLI, NPX, TMP

NN = sys.argv[1]
P = HF / f"we-corte-{NN}"
S = json.load(open(P / "scripts/spec.json"))
PAL = json.load(open(P / "scripts/palavras.json"))
FAL = json.load(open(P / "scripts/falas.json"))
for _i, _w in enumerate(PAL):
    _w["texto"] = S.get("corrige", {}).get(_w["texto"], _w["texto"])
    if _i and _w["inicio"] < PAL[_i - 1]["inicio"] + 0.05:
        _w["inicio"] = round(PAL[_i - 1]["inicio"] + 0.08, 2)
        _w["fim"] = max(_w["fim"], round(_w["inicio"] + 0.12, 2))
M = S["modelo"]
DUR = round(S.get("duracao", FAL["duracao"]), 2)
FECHO = 0 if M == "B" else 4.0
TOTAL = round(DUR + FECHO, 2)
CARDS = S.get("cards", [])
for _c in CARDS:
    if _c.get("tipo") in ("lista", "fluxo"):
        _ts = [i["t"] for i in _c.get("itens", _c.get("passos", [])) if "t" in i]
        if _ts and min(_ts) - _c["de"] > 1.0:
            _c["de"] = round(min(_ts) - 0.9, 2)
_ord = sorted(CARDS, key=lambda c: c["de"])
for _a, _b in zip(_ord, _ord[1:]):
    if _a["ate"] > _b["de"] - 0.1:
        _a["ate"] = round(_b["de"] - 0.1, 2)
if S["modelo"] == "B":
    _ord = sorted(CARDS, key=lambda c: c["de"])
    for _a, _b in zip(_ord, _ord[1:]):
        if 0 < _b["de"] - _a["ate"] < 0.45:
            _a["ate"] = _b["de"]
r2 = lambda x: f"{round(x, 2):g}"

for sub in ("sfx", "bgm", "fecho"):
    (P / "assets" / sub).mkdir(parents=True, exist_ok=True)
for f in ("whoosh.wav", "whoosh-cine.mp3", "click.mp3", "pop.mp3", "sparkle.mp3"):
    shutil.copy(ASSETS / "sfx" / f, P / "assets/sfx" / f)
TRILHA = S.get("trilha", {})
if not isinstance(TRILHA, dict):
    TRILHA = {} if TRILHA else {"off": True}
TRILHA_ARQ = TRILHA.get("arq", "lofi.mp3")
if not TRILHA.get("off"):
    shutil.copy(ASSETS / f"bgm/{TRILHA_ARQ}", P / f"assets/bgm/{TRILHA_ARQ}")
IDIOMA = S.get("idioma", "pt")
LOCALE = {"pt": "pt-BR", "en": "en-US", "es": "es-ES"}[IDIOMA]
AGORA = {"pt": "agora", "en": "now", "es": "ahora"}[IDIOMA]
if FECHO:
    ig = ASSETS / f"fecho/ig-follow-{IDIOMA}.webm"
    if not ig.exists():
        print(f"aviso: sem {ig.name}, card do Instagram fica em PT")
        ig = ASSETS / "fecho/ig-follow.webm"
    shutil.copy(ig, P / "assets/fecho/ig-follow.webm")
(P / "compositions").mkdir(exist_ok=True)
for name, txt in {
    "hyperframes.json": json.dumps({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                                    "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
                                    "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
                                    "media": {"autoProxy": True}, "authoringSkill": "hyperframes"}, indent=2),
    "meta.json": json.dumps({"id": P.name, "name": P.name, "createdAt": "2026-10-29T12:00:00.000Z"}, indent=2),
}.items():
    if not (P / name).exists():
        (P / name).write_text(txt)

# ---------------------------------------------------------------- planos (quem aparece)
QUEM = S.get("quem", "wa")
TROCAS = S.get("trocas", [])  # [[t0, t1, cam], ...]


def cam_at(t):
    for a, b, c in TROCAS:
        if a <= t < b:
            return c
    return QUEM


def outro(c):
    return "ed" if c == "wa" else "wa"


cuts = sorted({0.0, DUR, *[x for a, b, _ in TROCAS for x in (a, b)]})
planos = []
for a, b in zip(cuts, cuts[1:]):
    if b - a > 0.01:
        c = cam_at((a + b) / 2)
        if planos and planos[-1][0] == c:
            planos[-1][2] = b
        else:
            planos.append([c, a, b])

# Pontos de corte seco (zoom alterna): inícios de frase do srt, peças de no mínimo 1,3 s.
starts = sorted({round(f["s"], 2) for f in FAL["falas"]} | {round(c["de"], 2) for c in CARDS})
zoom_pts = []
for t in starts:
    if 0.5 < t < DUR - 0.8 and (not zoom_pts or t - zoom_pts[-1] >= 1.3):
        zoom_pts.append(t)

# ---------------------------------------------------------------- legendas
CHAVE = {re.sub(r"[^\wÀ-ÿ]", "", k).upper() for k in S.get("chave", [])}
NOMES = {"GOOGLE": "Google", "INSTAGRAM": "Instagram", "WHATSAPP": "WhatsApp", "CHATGPT": "ChatGPT", "IA": "IA", "IAS": "IAs", "NPS": "NPS", "WE": "WE", "QR": "QR"}
if IDIOMA != "pt":
    NOMES.pop("WE")
limpa = lambda p: re.sub(r"[^\wÀ-ÿ]", "", p).upper()
OCULTA = [tuple(x) for x in S.get("sem_legenda", [])]
VICIOS_LEG = {"NÉ", "CARA", "AÍ", "ALI", "INCLUSIVE", "TIPO", "ASSIM", "ENTÃO", "AH", "EH", "HUM", "TÁ", "SABE"} if S.get("sem_vicios") else set()


def janela_card(a, b):
    return any(a < c["ate"] and b > c["de"] for c in CARDS)


def blocos_de(max_w, max_c):
    out, cur = [], []
    for w in PAL:
        if any(x <= w["inicio"] < y for x, y in OCULTA) or limpa(w["texto"]) in VICIOS_LEG:
            continue
        if cur:
            prev = cur[-1]
            chars = sum(len(x["texto"]) for x in cur) + len(w["texto"])
            if (len(cur) >= max_w or chars > max_c or prev["texto"][-1] in ",.?!:;"
                    or w["inicio"] - prev["fim"] > 0.35
                    or (limpa(prev["texto"]) in CHAVE and limpa(w["texto"]) not in CHAVE and len(cur) >= 2)):
                out.append(cur)
                cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def fim_bloco(bl, i):
    b = bl[i]
    fim = b[-1]["fim"] + 0.25
    if i + 1 < len(bl):
        prox = bl[i + 1][0]["inicio"] - 0.06
        fim = prox if prox - b[-1]["fim"] < 0.6 else min(fim, prox)
    return min(fim, DUR)


def caixa(t, kw):
    t = t.replace("'", "’")
    k = limpa(t)
    if k in NOMES:
        return re.sub(r"[\wÀ-ÿ]+", NOMES[k], t, count=1)
    return t.lower()


def split_ativo(t):
    return any(a <= t < b for a, b, kind in cenas_b() if kind != "full")


def legendas_html():
    caps = []
    if M == "C":
        bl = blocos_de(3, 18)
        for i, b in enumerate(bl):
            ini, fim = round(b[0]["inicio"] - 0.06, 2), round(fim_bloco(bl, i), 2)
            pos = "alto" if janela_card(ini, fim) else "baixo"
            linhas = []
            for w in b:
                kw = limpa(w["texto"]) in CHAVE
                if linhas and linhas[-1][0] == kw:
                    linhas[-1][1].append(w)
                else:
                    linhas.append((kw, [w]))
            h = []
            for kw, ws in linhas:
                chars = sum(len(w["texto"]) for w in ws) + len(ws) - 1
                fs = min(124, int(980 / (0.56 * chars))) if kw else min(70, int(960 / (0.55 * chars)))
                spans = " ".join(f'<span class="w" data-s="{w["inicio"]:.2f}">{html.escape(caixa(w["texto"], kw))}</span>' for w in ws)
                h.append(f'<div class="ln {"big" if kw else "sm"}" style="font-size:{fs}px">{spans}</div>')
            caps.append(f'    <div id="c{i+1}" class="clip cap {pos}" data-start="{ini}" data-duration="{round(fim-ini,2)}" data-track-index="{i%4+1}"><div class="cap-in">{"".join(h)}</div></div>')
    elif M == "A":
        bl = blocos_de(4, 22)
        for i, b in enumerate(bl):
            ini, fim = round(b[0]["inicio"] - 0.06, 2), round(fim_bloco(bl, i), 2)
            spans = []
            for w in b:
                kw = limpa(w["texto"]) in CHAVE
                spans.append(f'<span class="{"em" if kw else "w"}">{html.escape(caixa(w["texto"], kw))}</span>')
            caps.append(f'    <div id="c{i+1}" class="clip cap" data-start="{ini}" data-duration="{round(fim-ini,2)}" data-track-index="{i%4+1}"><div class="cap-in">{"".join(spans)}</div></div>')
    else:
        bl = blocos_de(3, 20)
        for i, b in enumerate(bl):
            ini, fim = round(max(0, b[0]["inicio"] - 0.04), 2), round(fim_bloco(bl, i), 2)
            pos = "seam" if split_ativo(b[0]["inicio"] + 0.02) else "low"
            text = " ".join(w["texto"] for w in b).upper()
            size = max(52, int(min(80, 930 / (len(text) * 0.74 + 0.6 * len(b)))))
            spans = []
            for k, w in enumerate(b):
                cls = "w kw" if limpa(w["texto"]) in CHAVE else "w"
                t = html.escape(w["texto"].replace("'", "’").upper())
                spans.append(f'<span class="{cls}" data-s="{w["inicio"]:.2f}" data-e="{w["fim"]:.2f}"><span class="w-bg"></span><span class="w-t">{t}</span></span>')
            caps.append(f'    <div id="c{i+1}" class="clip cap {pos}" data-start="{ini}" data-duration="{round(fim-ini,2)}" data-track-index="{i%4+1}"><div class="cap-in" style="font-size:{size}px">{"".join(spans)}</div></div>')
    return LEG_TPL[M].replace("<!--BLOCOS-->", "\n".join(caps))


LEG_TPL = {
    "C": """<template>
  <style>
    #root { position: absolute; inset: 0; }
    .cap { position: absolute; left: 0; width: 1080px; z-index: 10; text-align: center; overflow: visible; }
    .cap.baixo { top: 1090px; }
    .cap.alto { top: 935px; }
    .cap-in { display: flex; flex-direction: column; align-items: center; gap: 2px; }
    .ln { white-space: nowrap; font-family: Inter, sans-serif; font-weight: 800; letter-spacing: -0.035em; line-height: 1.04; }
    .ln.sm { color: #ffffff; }
    .ln.big { color: #34BFD3; }
    .w { display: inline-block; text-shadow: 0 3px 12px rgba(1, 7, 26, 0.45); }
  </style>
  <div id="root" data-composition-id="legendas" data-width="1080" data-height="1920">
<!--BLOCOS-->
  </div>
  <script>
    const tl = gsap.timeline({ paused: true });
    document.querySelectorAll("#root .cap").forEach((cap) => {
      const a = parseFloat(cap.dataset.start);
      const b = a + parseFloat(cap.dataset.duration);
      const inner = cap.querySelector(".cap-in");
      cap.querySelectorAll(".w").forEach((w) => {
        const s = parseFloat(w.dataset.s);
        gsap.set(w, { opacity: 0 });
        tl.fromTo(w, { opacity: 0, y: 16, filter: "blur(10px)" }, { opacity: 1, y: 0, filter: "blur(0px)", duration: 0.22, ease: "power2.out", immediateRender: false }, Math.max(a, s - 0.03));
      });
      tl.to(inner, { opacity: 0, duration: 0.08, ease: "power2.in" }, b - 0.08);
    });
    window.__timelines["legendas"] = tl;
  </script>
</template>
""",
    "A": """<template>
  <style>
    #root { position: absolute; inset: 0; }
    /* Uma linha, sem caixa: texto branco e a palavra-chave em ciano, maior. */
    .cap { position: absolute; left: 0; width: 1080px; top: 900px; z-index: 10; text-align: center; overflow: visible; }
    .cap-in { display: inline-flex; justify-content: center; align-items: baseline; gap: 14px; white-space: nowrap; }
    .w, .em { font-family: Inter, sans-serif; color: #ffffff; font-weight: 700; font-size: 50px; letter-spacing: -0.03em; line-height: 1;
      text-shadow: 0 4px 18px rgba(1, 7, 26, 0.6), 0 1px 3px rgba(1, 7, 26, 0.5); }
    .em { font-weight: 800; font-size: 72px; color: #34BFD3; }
  </style>
  <div id="root" data-composition-id="legendas" data-width="1080" data-height="1920">
<!--BLOCOS-->
  </div>
  <script>
    const tl = gsap.timeline({ paused: true });
    document.querySelectorAll("#root .cap").forEach((cap) => {
      const a = parseFloat(cap.dataset.start);
      const b = a + parseFloat(cap.dataset.duration);
      const inner = cap.querySelector(".cap-in");
      gsap.set(inner, { opacity: 0 });
      tl.fromTo(inner, { opacity: 0, filter: "blur(8px)" }, { opacity: 1, filter: "blur(0px)", duration: 0.16, ease: "power4.out", immediateRender: false }, a);
      tl.to(inner, { opacity: 0, filter: "blur(6px)", duration: 0.12, ease: "power2.in" }, b - 0.12);
    });
    window.__timelines["legendas"] = tl;
  </script>
</template>
""",
    "B": """<template>
  <style>
    #root { position: absolute; inset: 0; }
    /* Caixa alta; a palavra falada ganha a pílula ciano. Na tela dividida a legenda fica na emenda. */
    .cap { position: absolute; left: 0; width: 1080px; z-index: 10; text-align: center; overflow: visible; }
    .cap.low { top: 1240px; }
    .cap.seam { top: 902px; }
    .cap-in { display: inline-flex; flex-wrap: nowrap; justify-content: center; align-items: center; gap: 6px; white-space: nowrap; opacity: 0; }
    .w { position: relative; display: inline-block; padding: 8px 14px 10px; line-height: 1; transform-origin: 50% 60%; }
    .w-bg { position: absolute; inset: 0; border-radius: 14px; background: #29cedf; box-shadow: 0 10px 28px rgba(41, 206, 223, 0.35); opacity: 0; transform-origin: 0% 50%; }
    .w-t { position: relative; font-family: Inter, sans-serif; font-weight: 900; letter-spacing: 0.005em; color: #ffffff;
      -webkit-text-stroke: 9px #081012; paint-order: stroke fill; text-shadow: 0 6px 18px rgba(0, 0, 0, 0.45); }
    .kw .w-t { color: #29cedf; }
  </style>
  <div id="root" data-composition-id="legendas" data-width="1080" data-height="1920">
<!--BLOCOS-->
  </div>
  <script>
    const tl = gsap.timeline({ paused: true });
    document.querySelectorAll("#root .cap").forEach((cap) => {
      const a = parseFloat(cap.dataset.start);
      const b = a + parseFloat(cap.dataset.duration);
      const inner = cap.querySelector(".cap-in");
      gsap.set(inner, { opacity: 0 });
      tl.fromTo(inner, { opacity: 0, y: 18, scale: 0.92 }, { opacity: 1, y: 0, scale: 1, duration: 0.16, ease: "back.out(2)", immediateRender: false }, a);
      cap.querySelectorAll(".w").forEach((w) => {
        const s = parseFloat(w.dataset.s);
        const e = Math.min(parseFloat(w.dataset.e), b - 0.02);
        const bg = w.querySelector(".w-bg");
        const t = w.querySelector(".w-t");
        const base = w.classList.contains("kw") ? "#29cedf" : "#ffffff";
        gsap.set(w, { opacity: 0, scale: 0.7 });
        gsap.set(bg, { opacity: 0, scaleX: 0 });
        tl.to(w, { opacity: 1, scale: 1, duration: 0.18, ease: "back.out(2.6)" }, Math.max(a, s - 0.02));
        tl.to(bg, { opacity: 1, scaleX: 1, duration: 0.14, ease: "power2.out" }, s);
        tl.set(t, { color: "#06262b", webkitTextStroke: "0px #081012", textShadow: "none" }, s);
        tl.to(bg, { opacity: 0, duration: 0.1, ease: "power2.in" }, e);
        tl.set(t, { color: base, webkitTextStroke: "9px #081012", textShadow: "0 6px 18px rgba(0, 0, 0, 0.45)" }, e);
        tl.set(bg, { scaleX: 0 }, e + 0.1);
      });
      tl.to(inner, { opacity: 0, duration: 0.1, ease: "power2.in" }, b - 0.1);
    });
    window.__timelines["legendas"] = tl;
  </script>
</template>
""",
}

# ---------------------------------------------------------------- cenas do modelo B
_cenas = None


def cenas_b():
    """(ini, fim, tipo): 'painel' (card em cima), 'dupla' (os dois), 'full' (quem fala em tela cheia)."""
    global _cenas
    if _cenas is not None:
        return _cenas
    if M != "B":
        _cenas = []
        return _cenas
    marks = [(c["de"], c["ate"], "painel") for c in CARDS]
    g = S.get("gancho", {})
    if g:
        marks.append((0.0, g.get("ate", 2.0), "dupla"))
    for a, b in S.get("duplas", []):
        marks.append((a, b, "dupla"))
    marks.sort()
    out, t = [], 0.0
    for a, b, k in marks:
        a = max(a, t)
        if out and a - t < 0.45:
            out[-1] = (out[-1][0], a, out[-1][2])
        elif a > t + 0.01:
            out.append((t, a, "full"))
        if b > a:
            out.append((a, b, k))
            t = b
    if out and DUR - t < 0.45:
        out[-1] = (out[-1][0], DUR, out[-1][2])
    elif t < DUR - 0.01:
        out.append((t, DUR, "full"))
    _cenas = [(round(a, 2), round(b, 2), k) for a, b, k in out]
    return _cenas


# ---------------------------------------------------------------- cards
STAR = 'M11 1l2.8 5.8 6.4.9-4.6 4.5 1.1 6.3L11 15.5l-5.7 3 1.1-6.3L1.8 7.7l6.4-.9z'
PIN = ('<svg viewBox="0 0 48 64" class="pin"><path d="M24 0C10.7 0 0 10.6 0 23.8 0 41.6 24 64 24 64s24-22.4 24-40.2C48 10.6 37.3 0 24 0z" fill="#EA4335"/>'
       '<path d="M24 0C10.7 0 0 10.6 0 23.8c0 6 2.7 12.8 6.6 19.1L24 23.8z" fill="#4285F4" opacity=".9"/>'
       '<path d="M6.6 42.9C12.4 52.4 24 64 24 64l9-15.5L24 23.8z" fill="#34A853" opacity=".9"/>'
       '<path d="M48 23.8C48 10.6 37.3 0 24 0v23.8l17.4 19.1C45.3 36.6 48 29.8 48 23.8z" fill="#FBBC04" opacity=".9"/>'
       '<circle cx="24" cy="23" r="8.5" fill="#fff"/></svg>')
SFX = []  # (arquivo, t, volume)


def estrelas_svg(cid, w, h, n_on=5, fill_id=None):
    off = f'<svg width="{w}" height="{h}" viewBox="0 0 120 22"><g fill="var(--star-off)"><path id="{cid}-s" d="{STAR}"/>' + "".join(
        f'<use href="#{cid}-s" x="{24*k}"/>' for k in range(1, 5)) + "</g></svg>"
    on = f'<svg id="{fill_id or cid + "-on"}" width="{w}" height="{h}" viewBox="0 0 120 22"><g fill="#FBBC04">' + "".join(
        f'<use href="#{cid}-s" x="{24*k}"/>' for k in range(n_on)) + "</g></svg>"
    return off + on


def body_card(c, cid, js):
    t = c["tipo"]
    if t == "perfil":
        ts = c.get("t", c["de"] + 0.6)
        js.append(f'gsap.set("#{cid}-on", {{ clipPath: "inset(0 100% 0 0)" }});')
        js.append(f'tl.fromTo("#{cid}-on", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 0.9, ease: "power2.out", immediateRender: false }}, {r2(ts)});')
        SFX.append(("pop.mp3", ts, 0.24))
        return (f'<div class="pf">{PIN}<div class="pf-tx"><div class="nm">{c.get("nome","Dr. João Silva")}</div><div class="sb">{c.get("sub","Médico · Perfil no Google")}</div></div></div>'
                f'<div class="rt"><span class="nota">{c.get("nota","5,0")}</span><div class="stars" style="width:300px;height:55px">{estrelas_svg(cid, 300, 55)}</div>'
                f'<span class="rl">{c.get("rotulo","")}</span></div>')
    if t == "lista":
        rows = []
        for k, it in enumerate(c["itens"]):
            ok = it.get("ok")
            ic, cls = ("✓", "ok") if ok is True else ("✕", "bad") if ok is False else (str(k + 1), "dot")
            ic = it.get("ic", ic)
            rows.append(f'<div class="li" id="{cid}-i{k}"><span class="ic {cls}">{ic}</span><span class="tx">{it["txt"]}</span></div>')
            ti = it.get("t", c["de"] + 0.3 + 0.5 * k)
            js.append(f'gsap.set("#{cid}-i{k}", {{ opacity: 0 }});')
            js.append(f'tl.fromTo("#{cid}-i{k}", {{ opacity: 0, x: -24 }}, {{ opacity: 1, x: 0, duration: 0.3, ease: "power3.out", immediateRender: false }}, {r2(ti)});')
            js.append(f'tl.fromTo("#{cid}-i{k} .ic", {{ scale: 0.4 }}, {{ scale: 1, duration: 0.34, ease: "back.out(2.4)", immediateRender: false }}, {r2(ti + 0.06)});')
            SFX.append(("click.mp3" if ok is not False else "pop.mp3", ti, 0.28 if ok is not False else 0.22))
        return f'<div class="ls">{"".join(rows)}</div>'
    if t == "frase":
        td = c.get("t", c["de"] + 0.5)
        txt = re.sub(r"\*(.+?)\*", r'<b class="mk"><i class="mk-bg"></i><span>\1</span></b>', c["texto"])
        js.append(f'gsap.set("#{cid} .mk-bg", {{ scaleX: 0 }});')
        js.append(f'tl.to("#{cid} .mk-bg", {{ scaleX: 1, duration: 0.35, ease: "power3.out", stagger: 0.12 }}, {r2(td)});')
        js.append(f'tl.set("#{cid} .mk span", {{ color: "var(--mk-fg)" }}, {r2(td + 0.12)});')
        SFX.append(("pop.mp3", td, 0.2))
        return f'<div class="fr">{txt}</div>'
    if t == "barra":
        tb, de, ate = c.get("t", c["de"] + 0.5), c.get("de_pct", 20), c.get("ate_pct", 92)
        tr = c.get("t_res", tb + 0.9)
        js.append(f'gsap.set("#{cid}-f", {{ scaleX: {de/100} }}); gsap.set("#{cid}-r", {{ opacity: 0 }});')
        js.append(f'tl.to("#{cid}-f", {{ scaleX: {ate/100}, duration: 0.9, ease: "power2.out" }}, {r2(tb)});')
        if c.get("resultado"):
            js.append(f'tl.fromTo("#{cid}-r", {{ opacity: 0, scale: 0.6 }}, {{ opacity: 1, scale: 1, duration: 0.32, ease: "back.out(2.2)", immediateRender: false }}, {r2(tr)});')
            SFX.append(("pop.mp3", tr, 0.24))
        return (f'<div class="br-l">{c.get("rotulo","")}</div><div class="br-t"><div class="br-f" id="{cid}-f"></div></div>'
                f'<div class="br-s"><span>{c.get("esq","BAIXA")}</span><span class="hi">{c.get("dir","ALTA")}</span></div>'
                f'<div class="br-r" id="{cid}-r">{c.get("resultado","")}</div>')
    if t == "fluxo":
        parts = []
        for k, p in enumerate(c["passos"]):
            if k:
                parts.append(f'<div class="ar" id="{cid}-a{k}">→</div>')
            parts.append(f'<div class="st" id="{cid}-p{k}"><span class="n">{k+1}</span><span class="tx">{p["txt"]}</span></div>')
            tp = p.get("t", c["de"] + 0.3 + 0.6 * k)
            sel = f'["#{cid}-p{k}"' + (f', "#{cid}-a{k}"]' if k else "]")
            js.append(f'gsap.set({sel}, {{ opacity: 0 }});')
            js.append(f'tl.fromTo({sel}, {{ opacity: 0, y: 20, scale: 0.9 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.3, ease: "back.out(1.8)", immediateRender: false }}, {r2(tp)});')
            SFX.append(("click.mp3", tp, 0.28))
        return f'<div class="fx">{"".join(parts)}</div>'
    if t == "estrelas":
        t0, passo = c.get("t", c["de"] + 0.4), c.get("passo", 0.18)
        stars = "".join(f'<svg class="bs" id="{cid}-b{k}" viewBox="0 0 22 22"><path d="{STAR}" fill="#FBBC04"/></svg>' for k in range(5))
        for k in range(5):
            js.append(f'gsap.set("#{cid}-b{k}", {{ opacity: 0.18, scale: 0.7 }});')
            js.append(f'tl.to("#{cid}-b{k}", {{ opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.6)" }}, {r2(t0 + passo*k)});')
            SFX.append(("pop.mp3", t0 + passo * k, 0.16))
        return f'<div class="bst">{stars}</div>' + (f'<div class="bst-t">{c["texto"]}</div>' if c.get("texto") else "")
    if t == "review":
        t0, dur_t = c.get("t", c["de"] + 0.5), c.get("dur_texto", 1.4)
        words = c["texto"].split()
        sp = " ".join(f'<span class="rw">{w}</span>' for w in words)
        js.append(f'gsap.set("#{cid} .rw", {{ opacity: 0.12 }});')
        js.append(f'tl.to("#{cid} .rw", {{ opacity: 1, duration: 0.12, stagger: {r2(dur_t/max(1,len(words)))} }}, {r2(t0)});')
        n = c.get("estrelas", 5)
        if c.get("t_estrelas"):
            js.append(f'gsap.set("#{cid}-on", {{ clipPath: "inset(0 100% 0 0)" }});')
            js.append(f'tl.fromTo("#{cid}-on", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 0.6, ease: "power2.out", immediateRender: false }}, {r2(c["t_estrelas"])});')
            SFX.append(("pop.mp3", c["t_estrelas"], 0.2))
        return (f'<div class="rv-h"><div class="av" style="background:{c.get("cor","#7B61FF")}">{c.get("autor","M")[0]}</div><div><div class="nm">{c.get("autor","Maria S.")}</div>'
                f'<div class="stars" style="width:200px;height:37px">{estrelas_svg(cid, 200, 37, n)}</div></div><span class="rv-q">{c.get("quando", AGORA)}</span></div>'
                f'<div class="rv-t">{sp}</div>')
    if t == "contador":
        t0, d = c.get("t", c["de"] + 0.4), c.get("dur", 1.2)
        js.append(f'const {cid.replace("-","_")}_o = {{ v: {c.get("de_n",0)} }};')
        js.append(f'tl.to({cid.replace("-","_")}_o, {{ v: {c["ate_n"]}, duration: {d}, ease: "power2.out", onUpdate: () => {{ document.getElementById("{cid}-n").textContent = Math.round({cid.replace("-","_")}_o.v).toLocaleString("{LOCALE}"); }} }}, {r2(t0)});')
        SFX.append(("sparkle.mp3", t0 + d - 0.2, 0.2))
        return f'<div class="ct"><span class="ct-p">{c.get("prefixo","")}</span><span class="ct-n" id="{cid}-n">{c.get("de_n",0)}</span><span class="ct-s">{c.get("sufixo","")}</span></div><div class="ct-l">{c.get("rotulo","")}</div>'
    if t == "versus":
        cols = []
        for k, side in enumerate(("esq", "dir")):
            s = c[side]
            ok = s.get("ok")
            ic, cls = ("✓", "ok") if ok is True else ("✕", "bad") if ok is False else ("•", "dot")
            cols.append(f'<div class="vs-c {cls}" id="{cid}-{side}"><span class="ic {cls}">{ic}</span><div class="vs-t">{s["titulo"]}</div><div class="vs-x">{s.get("txt","")}</div></div>')
            tv = s.get("t", c["de"] + 0.3 + 0.8 * k)
            js.append(f'gsap.set("#{cid}-{side}", {{ opacity: 0 }});')
            js.append(f'tl.fromTo("#{cid}-{side}", {{ opacity: 0, y: 26, scale: 0.92 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.32, ease: "back.out(1.8)", immediateRender: false }}, {r2(tv)});')
            SFX.append(("click.mp3", tv, 0.28))
        return f'<div class="vs">{cols[0]}<div class="vs-x0">{c.get("meio","vs")}</div>{cols[1]}</div>'
    if t == "busca":
        t0 = c.get("t", c["de"] + 0.3)
        q = c["query"]
        chars = "".join(f'<span class="qc">{html.escape(ch) if ch != " " else "&nbsp;"}</span>' for ch in q)
        js.append(f'gsap.set("#{cid} .qc", {{ opacity: 0 }});')
        js.append(f'tl.to("#{cid} .qc", {{ opacity: 1, duration: 0.01, stagger: {r2(min(0.05, 0.9/len(q)))} }}, {r2(t0)});')
        rows = []
        for k, rr in enumerate(c.get("resultados", [])):
            hi = " hi" if k == c.get("destaque", 0) else ""
            rows.append(f'<div class="bs-r{hi}" id="{cid}-r{k}"><span class="n">{k+1}</span><span class="tx">{rr}</span>' + (f'<span class="mini">{estrelas_svg(cid+"m"+str(k), 120, 22)}</span>' if hi else "") + '</div>')
            tr = c.get("t_res", t0 + 1.0) + 0.15 * k
            js.append(f'gsap.set("#{cid}-r{k}", {{ opacity: 0 }});')
            js.append(f'tl.fromTo("#{cid}-r{k}", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.26, ease: "power3.out", immediateRender: false }}, {r2(tr)});')
        if rows:
            SFX.append(("click.mp3", c.get("t_res", t0 + 1.0), 0.26))
        return (f'<div class="bs-bar"><span class="g">G</span><span class="q">{chars}</span></div>' + (f'<div class="bs-list">{"".join(rows)}</div>' if rows else ""))
    if t == "nps":
        t0 = c.get("t", c["de"] + 0.4)
        cores = {"ok": ("#0BDEA4", "#01071A"), "meio": ("#FEBC2E", "#01071A"), "bad": ("#FF5A5F", "#ffffff")}
        boxes = "".join(f'<span class="nb" id="{cid}-n{n}">{n}</span>' for n in range(11))
        js.append(f'gsap.set("#{cid} .nb", {{ opacity: 0 }}); gsap.set("#{cid} .np-x", {{ opacity: 0 }});')
        js.append(f'tl.fromTo("#{cid} .nb", {{ opacity: 0, y: 18 }}, {{ opacity: 1, y: 0, duration: 0.22, ease: "back.out(2)", stagger: 0.045, immediateRender: false }}, {r2(t0)});')
        labels = []
        prev = None
        for k, g in enumerate(c.get("grupos", [])):
            bg, fg = cores[g.get("cor", "ok")]
            sel = "[" + ", ".join(f'"#{cid}-n{n}"' for n in range(g["de_n"], g["ate_n"] + 1)) + "]"
            js.append(f'tl.to({sel}, {{ backgroundColor: "{bg}", borderColor: "{bg}", color: "{fg}", duration: 0.2, ease: "power2.out" }}, {r2(g["t"])});')
            js.append(f'tl.fromTo({sel}, {{ scale: 1.18 }}, {{ scale: 1, duration: 0.35, ease: "back.out(2.2)", immediateRender: false }}, {r2(g["t"])});')
            labels.append(f'<span class="np-x" id="{cid}-l{k}">{g.get("txt","")}</span>')
            if prev is not None:
                js.append(f'tl.to("#{cid}-l{prev}", {{ opacity: 0, duration: 0.15 }}, {r2(g["t"] - 0.05)});')
            js.append(f'tl.fromTo("#{cid}-l{k}", {{ opacity: 0, y: 12 }}, {{ opacity: 1, y: 0, duration: 0.25, ease: "power3.out", immediateRender: false }}, {r2(g["t"] + 0.05)});')
            prev = k
            SFX.append(("pop.mp3", g["t"], 0.22))
        q = f'<div class="np-q">{c["pergunta"]}</div>' if c.get("pergunta") else ""
        return f'{q}<div class="np">{boxes}</div><div class="np-l">{"".join(labels)}</div>'
    if t == "alerta":
        t0 = c.get("t", c["de"] + 0.3)
        js.append(f'tl.fromTo("#{cid} .al-i", {{ scale: 0.3, rotation: -20 }}, {{ scale: 1, rotation: 0, duration: 0.45, ease: "back.out(2.4)", immediateRender: false }}, {r2(t0)});')
        js.append(f'tl.to("#{cid} .al-i", {{ x: 8, duration: 0.05, yoyo: true, repeat: 5, ease: "none" }}, {r2(t0 + 0.45)});')
        SFX.append(("pop.mp3", t0, 0.24))
        return f'<div class="al"><span class="al-i emoji">{c.get("icone","⚠️")}</span><div><div class="al-t">{c["chamada"]}</div><div class="al-x">{c.get("texto","")}</div></div></div>'
    raise SystemExit(f"tipo de card desconhecido: {t}")


CARD_CSS_COMMON = """
    @font-face { font-family: "Apple Color Emoji"; src: local("Apple Color Emoji"); }
    .emoji { font-family: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif; }
    .pf { display: flex; align-items: center; gap: 24px; }
    .pin { width: calc(var(--k) * 74px); height: calc(var(--k) * 98px); flex: none; }
    .nm { font-size: calc(var(--k) * 44px); font-weight: 800; letter-spacing: -0.02em; color: var(--fg); }
    .sb { margin-top: 4px; font-size: calc(var(--k) * 28px); font-weight: 600; color: var(--muted); }
    .rt { display: flex; align-items: center; gap: 20px; margin-top: 24px; padding: 18px 24px; border-radius: 22px; background: var(--soft); }
    .nota { font-size: calc(var(--k) * 40px); font-weight: 800; color: var(--fg); }
    .stars { position: relative; flex: none; }
    .stars svg { position: absolute; left: 0; top: 0; }
    .rl { font-size: calc(var(--k) * 28px); font-weight: 700; color: var(--muted); }
    .ls { display: flex; flex-direction: column; gap: calc(var(--k) * 18px); }
    .li { display: flex; align-items: center; gap: 22px; }
    .ic { flex: none; width: calc(var(--k) * 58px); height: calc(var(--k) * 58px); border-radius: 50%; display: flex; align-items: center; justify-content: center;
      font-size: calc(var(--k) * 32px); font-weight: 900; color: #fff; }
    .ic.ok { background: #0BDEA4; color: #01071A; } .ic.bad { background: #FF5A5F; } .ic.dot { background: #34BFD3; color: #01071A; }
    .tx { font-size: calc(var(--k) * 40px); font-weight: 700; letter-spacing: -0.02em; color: var(--fg); line-height: 1.15; }
    .fr { font-size: calc(var(--k) * 56px); font-weight: 800; letter-spacing: -0.035em; line-height: 1.14; color: var(--fg); text-align: center; }
    .mk { position: relative; display: inline-block; font-weight: 900; }
    .mk-bg { position: absolute; left: -8px; right: -8px; top: 8%; bottom: 4%; border-radius: 12px; background: #34BFD3; transform-origin: 0% 50%; }
    .mk span { position: relative; }
    .br-l { font-size: calc(var(--k) * 28px); font-weight: 800; letter-spacing: 0.1em; color: var(--muted); text-transform: uppercase; }
    .br-t { position: relative; margin-top: 18px; height: calc(var(--k) * 54px); border-radius: 999px; background: var(--soft); overflow: hidden; }
    .br-f { position: absolute; inset: 0; border-radius: 999px; background: linear-gradient(90deg, #1a8f9c, #34BFD3); transform-origin: 0% 50%; }
    .br-s { display: flex; justify-content: space-between; margin-top: 12px; font-size: calc(var(--k) * 24px); font-weight: 800; letter-spacing: 0.1em; color: var(--muted); }
    .br-s .hi { color: #34BFD3; }
    .br-r { margin-top: 14px; text-align: center; font-size: calc(var(--k) * 64px); font-weight: 900; letter-spacing: -0.03em; color: #34BFD3; text-transform: uppercase; }
    .fx { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 14px; }
    .st { display: flex; align-items: center; gap: 14px; padding: 16px 22px; border-radius: 22px; background: var(--soft); border: 2px solid var(--line); }
    .st .n { width: calc(var(--k) * 46px); height: calc(var(--k) * 46px); border-radius: 50%; background: #34BFD3; color: #01071A; display: flex; align-items: center;
      justify-content: center; font-size: calc(var(--k) * 26px); font-weight: 900; }
    .st .tx { font-size: calc(var(--k) * 34px); }
    .ar { font-size: calc(var(--k) * 44px); font-weight: 900; color: #34BFD3; }
    .bst { display: flex; justify-content: center; gap: 18px; }
    .bs { width: calc(var(--k) * 128px); height: calc(var(--k) * 128px); }
    .bst-t { margin-top: 18px; text-align: center; font-size: calc(var(--k) * 44px); font-weight: 800; letter-spacing: -0.02em; color: var(--fg); }
    .rv-h { display: flex; align-items: center; gap: 20px; }
    .av { width: calc(var(--k) * 80px); height: calc(var(--k) * 80px); border-radius: 50%; color: #fff; display: flex; align-items: center; justify-content: center;
      font-size: calc(var(--k) * 40px); font-weight: 800; flex: none; }
    .rv-h .nm { font-size: calc(var(--k) * 36px); }
    .rv-h .stars { margin-top: 6px; }
    .rv-q { margin-left: auto; align-self: flex-start; font-size: calc(var(--k) * 24px); font-weight: 600; color: var(--muted); }
    .rv-t { margin-top: 20px; font-size: calc(var(--k) * 38px); font-weight: 600; line-height: 1.3; color: var(--fg); }
    .ct { display: flex; align-items: baseline; justify-content: center; gap: 10px; color: #34BFD3; font-weight: 900; letter-spacing: -0.04em; }
    .ct-n { font-size: calc(var(--k) * 150px); line-height: 1; font-variant-numeric: tabular-nums; }
    .ct-p, .ct-s { font-size: calc(var(--k) * 70px); }
    .ct-l { margin-top: 6px; text-align: center; font-size: calc(var(--k) * 36px); font-weight: 700; color: var(--fg); }
    .vs { display: flex; align-items: stretch; gap: 16px; }
    .vs-c { flex: 1; padding: 22px 20px; border-radius: 26px; background: var(--soft); border: 3px solid var(--line); display: flex; flex-direction: column; align-items: center; gap: 10px; text-align: center; }
    .vs-c.ok { border-color: #0BDEA4; } .vs-c.bad { border-color: #FF5A5F; }
    .vs-t { font-size: calc(var(--k) * 40px); font-weight: 900; letter-spacing: -0.02em; color: var(--fg); line-height: 1.05; }
    .vs-x { font-size: calc(var(--k) * 28px); font-weight: 600; color: var(--muted); line-height: 1.2; }
    .vs-x0 { align-self: center; font-size: calc(var(--k) * 30px); font-weight: 900; color: var(--muted); text-transform: uppercase; }
    .bs-bar { display: flex; align-items: center; gap: 18px; padding: 18px 26px; border-radius: 999px; background: var(--soft); border: 2px solid var(--line); }
    .bs-bar .g { font-family: Montserrat, sans-serif; font-weight: 800; font-size: calc(var(--k) * 44px); color: #4285F4; }
    .bs-bar .q { display: flex; font-size: calc(var(--k) * 36px); font-weight: 600; color: var(--fg); white-space: nowrap; }
    .bs-list { margin-top: 18px; display: flex; flex-direction: column; gap: 10px; }
    .bs-r { display: flex; align-items: center; gap: 16px; padding: 12px 18px; border-radius: 18px; }
    .bs-r .n { width: 40px; font-size: calc(var(--k) * 30px); font-weight: 800; color: var(--muted); }
    .bs-r .tx { font-size: calc(var(--k) * 34px); }
    .bs-r.hi { background: rgba(52, 191, 211, 0.16); border: 2px solid #34BFD3; }
    .bs-r.hi .n { color: #34BFD3; }
    .mini { position: relative; margin-left: auto; width: 120px; height: 22px; }
    .mini svg { position: absolute; left: 0; top: 0; }
    .np-q { margin-bottom: 20px; font-size: calc(var(--k) * 36px); font-weight: 700; letter-spacing: -0.02em; line-height: 1.2; color: var(--fg); text-align: center; }
    .np { display: flex; gap: 8px; }
    .nb { flex: 1; height: calc(var(--k) * 72px); border-radius: 14px; background: var(--soft); border: 2px solid var(--line); display: flex; align-items: center;
      justify-content: center; font-size: calc(var(--k) * 32px); font-weight: 800; color: var(--fg); }
    .np-l { position: relative; margin-top: 18px; height: calc(var(--k) * 52px); }
    .np-x { position: absolute; left: 0; right: 0; top: 0; text-align: center; font-size: calc(var(--k) * 36px); font-weight: 800; letter-spacing: -0.02em; color: var(--fg); }
    .al { display: flex; align-items: center; gap: 26px; }
    .al-i { font-size: calc(var(--k) * 96px); line-height: 1; flex: none; }
    .al-t { font-size: calc(var(--k) * 44px); font-weight: 900; letter-spacing: -0.02em; color: var(--fg); line-height: 1.08; }
    .al-x { margin-top: 6px; font-size: calc(var(--k) * 30px); font-weight: 600; color: var(--muted); line-height: 1.2; }
"""

SHELL_CSS = {
    "C": """
    #root { position: absolute; inset: 0; --k: 1; --fg: #01071A; --muted: #6B7280; --soft: #F6F7F9; --line: #E3E6EA; --star-off: #D5D8DC; --mk-fg: #01071A; font-family: Inter, sans-serif; }
    .card { position: absolute; left: 90px; top: 1170px; width: 900px; background: #ffffff; border: 2px solid #E3E6EA; border-radius: 34px; overflow: hidden; transform-origin: 50% 0%;
      box-shadow: 0 24px 60px rgba(1, 7, 26, 0.28); }
    .bar { height: 68px; display: flex; align-items: center; gap: 12px; padding: 0 28px; background: #F6F7F9; border-bottom: 2px solid #ECEEF1; }
    .dot { width: 18px; height: 18px; border-radius: 50%; }
    .ttl { margin-left: 16px; font-size: 27px; font-weight: 700; color: #5B6270; }
    .body { padding: 30px 36px 36px; }
""",
    "A": """
    #root { position: absolute; inset: 0; --k: 1; --fg: #102026; --muted: #5c6b70; --soft: rgba(16, 32, 38, 0.06); --line: rgba(16, 32, 38, 0.1); --star-off: #D5DEE1; --mk-fg: #01071A; font-family: Inter, sans-serif; }
    .card { position: absolute; left: 70px; top: 1090px; width: 940px; border-radius: 30px; overflow: hidden; transform-origin: 50% 0%;
      background: rgba(244, 247, 248, 0.94); -webkit-backdrop-filter: blur(18px); backdrop-filter: blur(18px);
      box-shadow: 0 22px 50px rgba(0, 0, 0, 0.35); }
    .kick { padding: 24px 32px 0; font-size: 24px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #5c6b70; text-align: center; }
    .body { padding: 18px 32px 30px; }
""",
    "B": """
    #root { position: absolute; inset: 0; --k: 1.45; --fg: #ffffff; --muted: rgba(255, 255, 255, 0.62); --soft: rgba(255, 255, 255, 0.08); --line: rgba(255, 255, 255, 0.16); --star-off: rgba(255, 255, 255, 0.18); --mk-fg: #01071A; font-family: Inter, sans-serif; }
    .card { position: absolute; left: 0; top: 0; width: 1080px; height: 960px; overflow: hidden; background: radial-gradient(ellipse 80% 70% at 50% 40%, #12343a 0%, #0b1416 70%); }
    .grid { position: absolute; inset: 0; background-image: linear-gradient(rgba(41, 206, 223, 0.06) 2px, transparent 2px), linear-gradient(90deg, rgba(41, 206, 223, 0.06) 2px, transparent 2px);
      background-size: 90px 90px; }
    .kick { position: absolute; left: 0; top: 210px; width: 1080px; text-align: center; }
    .kick span { display: inline-block; padding: 14px 30px; border-radius: 999px; background: rgba(255, 255, 255, 0.1); border: 2px solid rgba(255, 255, 255, 0.18);
      font-size: 38px; font-weight: 800; letter-spacing: 0.04em; color: #fff; text-transform: uppercase; }
    .body { position: absolute; left: 60px; top: 300px; width: 960px; height: 600px; display: flex; flex-direction: column; justify-content: center; }
""",
}


def cards_html():
    js, divs = [], []
    for i, c in enumerate(CARDS):
        cid = f"k{i+1}"
        de, ate = c["de"], c["ate"]
        body = body_card(c, cid, js)
        titulo = c.get("titulo", "")
        if M == "C":
            shell = (f'<div class="bar"><div class="dot" style="background:#FF5F57"></div><div class="dot" style="background:#FEBC2E"></div>'
                     f'<div class="dot" style="background:#28C840"></div><div class="ttl">{titulo}</div></div><div class="body">{body}</div>')
        elif M == "A":
            shell = (f'<div class="kick">{titulo}</div>' if titulo else "") + f'<div class="body">{body}</div>'
        else:
            shell = '<div class="grid"></div>' + (f'<div class="kick"><span>{titulo}</span></div>' if titulo else "") + f'<div class="body">{body}</div>'
        divs.append(f'    <div id="{cid}" class="clip card" data-start="{r2(de)}" data-duration="{r2(ate-de)}" data-track-index="{i%3+1}">{shell}</div>')
        if M == "B":
            js.insert(0, f'tl.fromTo("#{cid}", {{ xPercent: -100 }}, {{ xPercent: 0, duration: 0.32, ease: "power3.out", immediateRender: false }}, {r2(de)});')
            js.insert(1, f'tl.fromTo("#{cid} .kick span", {{ opacity: 0, y: 20 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "power3.out", immediateRender: false }}, {r2(de+0.18)});')
            js.insert(2, f'tl.to("#{cid} .body", {{ opacity: 0, duration: 0.12, ease: "power2.in" }}, {r2(ate-0.12)});')
            SFX.append(("whoosh.wav", de - 0.05, 0.35))
        else:
            js.insert(0, f'gsap.set("#{cid}", {{ opacity: 0 }});')
            js.insert(1, f'tl.fromTo("#{cid}", {{ opacity: 0, y: 40, scale: 0.92 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.38, ease: "back.out(1.6)", immediateRender: false }}, {r2(de+0.02)});')
            js.insert(2, f'tl.to("#{cid}", {{ opacity: 0, y: 24, scale: 0.96, duration: 0.18, ease: "power2.in" }}, {r2(ate-0.18)});')
            SFX.append(("whoosh.wav", de, 0.16))
    return f"""<template>
  <style>{SHELL_CSS[M]}{CARD_CSS_COMMON}  </style>
  <div id="root" data-composition-id="cards" data-width="1080" data-height="1920">
{chr(10).join(divs)}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join("    " + j for j in js).lstrip()}
    tl.to({{}}, {{ duration: {r2(DUR)} }}, 0);
    window.__timelines["cards"] = tl;
  </script>
</template>
"""


def notif_html(n):
    at = n["de"]
    ts = n.get("t_estrelas", at + 0.5)
    SFX.append(("pop.mp3", at + 0.05, 0.26))
    top = 196 if M == "B" else 120
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; --star-off: #d5d8dc; }}
    #nt-ban {{ position: absolute; left: 60px; top: {top}px; width: 960px; border-radius: 46px; padding: 30px 34px;
      background: rgba(246, 247, 249, 0.96); box-shadow: 0 26px 60px rgba(0, 0, 0, 0.42); display: flex; gap: 26px; align-items: flex-start; }}
    #nt-ic {{ width: 96px; height: 96px; flex: 0 0 96px; border-radius: 24px; background: #ffffff; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
      display: flex; align-items: center; justify-content: center; font-family: Montserrat, sans-serif; font-weight: 800; font-size: 62px; color: #4285F4; }}
    #nt-body {{ flex: 1; font-family: Inter, sans-serif; }}
    #nt-app {{ display: flex; justify-content: space-between; font-size: 28px; font-weight: 600; letter-spacing: 0.04em; color: #6e6e73; }}
    #nt-tit {{ margin-top: 6px; font-size: 42px; font-weight: 800; color: #1d1d1f; }}
    #nt-txt {{ margin-top: 4px; font-size: 34px; font-weight: 500; color: #3a3a3c; }}
    #nt-stars {{ position: relative; margin-top: 14px; width: 280px; height: 52px; }}
    #nt-stars svg {{ position: absolute; left: 0; top: 0; }}
  </style>
  <div id="root" data-composition-id="notif" data-width="1080" data-height="1920">
    <div id="nt-ban">
      <div id="nt-ic">G</div>
      <div id="nt-body">
        <div id="nt-app"><span>{n.get("app","GOOGLE")}</span><span>{n.get("quando", AGORA)}</span></div>
        <div id="nt-tit">{n["titulo"]}</div>
        <div id="nt-txt">{n.get("texto","")}</div>
        <div id="nt-stars">{estrelas_svg("nt", 280, 52)}</div>
      </div>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.set("#nt-ban", {{ opacity: 0, y: -260 }}, 0);
    gsap.set("#nt-on", {{ clipPath: "inset(0 100% 0 0)" }});
    tl.to("#nt-ban", {{ opacity: 1, duration: 0.12, ease: "power1.out" }}, {r2(at)});
    tl.to("#nt-ban", {{ y: 0, duration: 0.55, ease: "back.out(1.5)" }}, {r2(at)});
    tl.fromTo("#nt-on", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: 0.8, ease: "power2.out", immediateRender: false }}, {r2(ts)});
    tl.to("#nt-ban", {{ y: -300, opacity: 0, duration: 0.35, ease: "power2.in" }}, {r2(n["ate"] - 0.35)});
    tl.to({{}}, {{ duration: {r2(DUR)} }}, 0);
    window.__timelines["notif"] = tl;
  </script>
</template>
"""


def gancho_html(g):
    """Modelo B: pergunta em caixa escura no topo durante a abertura (tela dividida com os dois)."""
    ate = g.get("ate", 2.0)
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; }}
    .titulo {{ position: absolute; left: 0; top: 150px; width: 1080px; text-align: center; }}
    #titulo-in {{ display: inline-block; padding: 18px 34px 22px; border-radius: 26px; background: rgba(8, 14, 16, 0.86); box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
      font-family: Inter, sans-serif; font-weight: 800; font-size: 60px; line-height: 1.08; letter-spacing: -0.02em; color: #fff; }}
    #titulo-in b {{ color: #29cedf; font-weight: 900; }}
  </style>
  <div id="root" data-composition-id="gancho" data-width="1080" data-height="1920">
    <div class="titulo"><div id="titulo-in">{g["texto"]}</div></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#titulo-in", {{ scale: 1.06 }}, {{ scale: 1, duration: 0.5, ease: "power3.out", immediateRender: true }}, 0);
    tl.to("#titulo-in", {{ opacity: 0, duration: 0.14, ease: "power2.in" }}, {r2(ate - 0.14)});
    tl.to({{}}, {{ duration: {r2(ate)} }}, 0);
    window.__timelines["gancho"] = tl;
  </script>
</template>
"""


FECHO_HTML = """<template>
  <style>
    #root { position: absolute; inset: 0; }
    #fc-bg { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; }
    #fc-ig { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; }
  </style>
  <div id="root" data-composition-id="fecho" data-width="1080" data-height="1920">
    <img id="fc-bg" src="assets/fecho/fundo.jpg" alt="" />
    <video id="fc-ig" class="clip" src="assets/fecho/ig-follow.webm" muted playsinline data-start="0" data-duration="4" data-media-start="0" data-track-index="0"></video>
  </div>
  <script>
    const tl = gsap.timeline({ paused: true });
    tl.fromTo("#fc-bg", { opacity: 0, scale: 1.08 }, { opacity: 1, scale: 1, duration: 0.35, ease: "power2.out" }, 0);
    tl.to({}, { duration: 4 }, 0);
    window.__timelines["fecho"] = tl;
  </script>
</template>
"""

# ---------------------------------------------------------------- index.html
def index_html():
    body, js, css = [], [], []
    ZS = 1.15 if M == "C" else 1.13
    if M in ("A", "C"):
        for i, (c, a, b) in enumerate(planos):
            sid = f"sh{i+1}"
            body.append(f'      <div id="{sid}" class="shot"><video id="v{i+1}" class="clip" src="assets/cam-{c}.mp4" muted playsinline data-start="{r2(a)}" data-duration="{r2(b-a)}" data-media-start="{r2(a)}" data-track-index="0"></video></div>')
            pts = [a] + [t for t in zoom_pts if a < t < b] + [b]
            for k, (x, y) in enumerate(zip(pts, pts[1:])):
                s0 = 1.0 if k % 2 == 0 else ZS
                js.append(f'["#{sid}", {r2(x)}, {s0}, {r2(y)}, {round(s0 + 0.03, 2)}],')
    else:
        # Tela cheia: quem fala (zoom seco). Tela dividida: painel/ouvinte em cima, quem fala embaixo.
        n = 0
        for a, b, kind in cenas_b():
            for c, pa, pb in planos:
                x, y = max(a, pa), min(b, pb)
                if y - x < 0.01:
                    continue
                n += 1
                if kind == "full":
                    sid = f"fs{n}"
                    body.append(f'      <div id="{sid}" class="shot"><video id="fv{n}" class="clip" src="assets/cam-{c}.mp4" muted playsinline data-start="{r2(x)}" data-duration="{r2(y-x)}" data-media-start="{r2(x)}" data-track-index="0"></video></div>')
                    pts = [x] + [t for t in zoom_pts if x < t < y] + [y]
                    for k, (u, v) in enumerate(zip(pts, pts[1:])):
                        s0 = 1.0 if k % 2 == 0 else ZS
                        js.append(f'["#{sid}", {r2(u)}, {s0}, {r2(v)}, {round(s0 + 0.03, 2)}],')
                else:
                    body.append(f'      <div id="hb{n}" class="half bot"><video id="hbv{n}" class="clip cam-{c}" src="assets/cam-{c}.mp4" muted playsinline data-start="{r2(x)}" data-duration="{r2(y-x)}" data-media-start="{r2(x)}" data-track-index="3"></video></div>')
                    if kind == "dupla":
                        body.append(f'      <div id="ht{n}" class="half top"><video id="htv{n}" class="clip cam-{outro(c)}" src="assets/cam-{outro(c)}.mp4" muted playsinline data-start="{r2(x)}" data-duration="{r2(y-x)}" data-media-start="{r2(x)}" data-track-index="5"></video></div>')
                    body.append(f'      <div id="seam{n}" class="seam clip" data-start="{r2(x)}" data-duration="{r2(y-x)}" data-track-index="6"></div>')
    comps = [("cards", 0, DUR, 5, "graphics")] if CARDS else []
    if S.get("notif"):
        comps.append(("notif", 0, DUR, 8, "graphics"))
    if M == "B" and S.get("gancho"):
        comps.append(("gancho", 0, S["gancho"].get("ate", 2.0), 9, "graphics"))
    comps.append(("legendas", 0, DUR, 12, "captions"))
    if FECHO:
        comps.append(("fecho", DUR, FECHO, 20, "graphics"))
    for name, a, d, z, kind in comps:
        body.append(f'      <div id="{name}" data-composition-id="{name}" data-composition-src="compositions/{name}.html" data-start="{r2(a)}" data-duration="{r2(d)}" data-track-index="{z}" data-track-kind="{kind}" data-width="1080" data-height="1920"></div>')
        css.append(f"#{name} {{ position: absolute; inset: 0; z-index: {z}; }}")
    body.append(f'      <img id="capa" class="clip" src="assets/capa.jpg" alt="" data-start="0" data-duration="0.1" data-track-index="30" />')
    body.append(f'      <audio id="voz" class="clip" src="assets/voz.wav" data-start="0" data-duration="{r2(DUR)}" data-media-start="0" data-volume="1" data-track-index="40"></audio>')
    if (P / "assets/voz-original.wav").exists():
        d_or = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(P / "assets/voz-original.wav")],
                                    capture_output=True, text=True).stdout)
        body.append(f'      <audio id="voz-original" class="clip" src="assets/voz-original.wav" data-start="0" data-duration="{r2(d_or)}" data-media-start="0" data-volume="1" data-track-index="39"></audio>')
    if not TRILHA.get("off"):
        t_arq = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(ASSETS / f"bgm/{TRILHA_ARQ}")],
                                     capture_output=True, text=True).stdout)
        m0 = TRILHA.get("inicio", max(0.0, t_arq - TRILHA.get("final", 0) - TOTAL) if TRILHA.get("final") is not None else 0.0)
        body.append(f'      <audio id="trilha" class="clip" src="assets/bgm/{TRILHA_ARQ}" data-start="0" data-duration="{r2(TOTAL)}" data-media-start="{r2(m0)}" data-volume="{TRILHA.get("volume", 0.1)}" data-fade-in="0.6" data-fade-out="{TRILHA.get("fade", 2.2)}" data-track-index="41"></audio>')
    if FECHO:
        SFX.append(("whoosh-cine.mp3", DUR - 0.17, 0.26))
        SFX.append(("click.mp3", DUR + 3.30, 0.5))
    used = []
    for k, (f, t, v) in enumerate(sorted(SFX, key=lambda x: x[1])):
        t = max(0.0, t)
        if any(abs(t - u) < 0.12 for u in used):
            continue
        used.append(t)
        d = {"whoosh.wav": 0.5, "whoosh-cine.mp3": 1.2, "click.mp3": 0.36, "pop.mp3": 0.4, "sparkle.mp3": 1.0}[f]
        body.append(f'      <audio id="sfx{k+1}" class="clip" src="assets/sfx/{f}" data-start="{r2(t)}" data-duration="{d}" data-volume="{v}" data-track-index="{42 + k % 3}"></audio>')
    zoom_js = "\n        ".join(js)
    return f"""<!doctype html>
<html lang="{LOCALE}" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Apple Color Emoji"; src: local("Apple Color Emoji"); }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #01071A; }}
      .shot {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; overflow: hidden; transform-origin: 50% 30%; z-index: 1; }}
      .shot video {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; }}
      .half {{ position: absolute; left: 0; width: 1080px; height: 960px; overflow: hidden; z-index: 3; }}
      .half.top {{ top: 0; }}
      .half.bot {{ top: 960px; }}
      .half video {{ position: absolute; left: -54px; top: -270px; width: 1188px; height: 2112px; object-fit: cover; }}
      .half video.cam-ed {{ top: -150px; }}
      .seam {{ position: absolute; left: 0; top: 956px; width: 1080px; height: 8px; z-index: 7; background: #29cedf; box-shadow: 0 0 24px rgba(41, 206, 223, 0.7); }}
      #capa {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; z-index: 30; }}
      {chr(10).join("      " + c for c in css).lstrip()}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{r2(TOTAL)}" data-width="1080" data-height="1920">
{chr(10).join(body)}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      // Corte seco a cada frase: alterna plano aberto (1,0) e fechado, com deriva lenta.
      [
        {zoom_js}
      ].forEach(([sel, t0, s0, t1, s1]) => {{
        tl.set(sel, {{ scale: s0 }}, t0);
        tl.to(sel, {{ scale: s1, duration: t1 - t0, ease: "none" }}, t0);
      }});
      tl.to({{}}, {{ duration: {r2(TOTAL)} }}, 0);
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


# ---------------------------------------------------------------- capa
def capa():
    c = S["capa"]
    d = P / "capa"
    (d / "assets").mkdir(parents=True, exist_ok=True)
    cam = c.get("cam", QUEM)
    t = c.get("t", 1.0)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(P / f"assets/cam-{cam}.mp4"), "-frames:v", "1", "-q:v", "2",
                    str(d / "assets/foto.jpg")], check=True)
    shutil.copy(ASSETS / "avatar.png", d / "assets/avatar.png")
    ic = c.get("icone")
    if ic:
        marca = d / "assets/pessoa.txt"
        if not (d / "assets/pessoa.png").exists() or not marca.exists() or marca.read_text() != f"{cam} {t}":
            subprocess.run([NPX, "--yes", HF_CLI, "remove-background", str(d / "assets/foto.jpg"), "-o", str(d / "assets/pessoa.png")],
                           check=True, capture_output=True)
            marca.write_text(f"{cam} {t}")
        if (ASSETS / f"{ic}.svg").exists():
            shutil.copy(ASSETS / f"{ic}.svg", d / f"assets/{ic}.svg")
    ls = (c["linhas"] + ["", "", ""])[:3]
    x, y, tam = c.get("icone_pos", [700, 470, 270])
    selo = c.get("icone_selo", "")
    icone = ""
    if ic:
        img = f'<img src="assets/{ic}.svg" alt="" />' if (ASSETS / f"{ic}.svg").exists() else f'<span class="emoji">{ic}</span>'
        icone = f"""<div id="icone" style="left:{x}px;top:{y}px;width:{tam}px;height:{tam}px">{img}</div>
      {f'<div id="selo-ic" class="emoji" style="left:{x + tam * 0.62}px;top:{y + tam * 0.58}px;font-size:{tam * 0.42}px">{selo}</div>' if selo else ""}
      <img id="pessoa" src="assets/pessoa.png" alt="" />"""
    topo_html = f'<div id="topo"><span>{c["topo"]}</span><span>//</span><span>@wemarketingmedico</span></div>' if c.get("topo") else ""
    selo_html = ('<div id="selo"><div id="av"><img src="assets/avatar.png" alt="" /></div>'
                 '<div><div id="nome">WE Marketing Médico</div><div id="sub">Marketing para médicos</div></div></div>') if c.get("selo") else ""
    (d / "index.html").write_text(f"""<!doctype html>
<html lang="{LOCALE}" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Apple Color Emoji"; src: local("Apple Color Emoji"); }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #01071A; }}
      #root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #01071A; font-family: Inter, sans-serif; }}
      #foto, #pessoa {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; transform: scale(1.06); transform-origin: 50% 30%; }}
      #sombra {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; background: linear-gradient(180deg, rgba(1,7,26,0.30) 0%, rgba(1,7,26,0) 20%, rgba(1,7,26,0) 48%, rgba(1,7,26,0.55) 100%); }}
      #topo {{ position: absolute; left: 0; top: 250px; width: 1080px; display: flex; justify-content: center; gap: 70px;
        font-size: 34px; font-weight: 600; letter-spacing: -0.01em; color: #ffffff; text-shadow: 0 2px 12px rgba(1,7,26,0.55); }}
      #icone {{ position: absolute; border-radius: 50%; background: #ffffff; display: flex; align-items: center; justify-content: center;
        box-shadow: 0 18px 50px rgba(1,7,26,0.35); transform: rotate(8deg); }}
      #icone img {{ height: 62%; }}
      #icone .emoji {{ position: static; font-size: 150px; }}
      .emoji {{ position: absolute; font-family: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif; line-height: 1; }}
      #selo-ic {{ transform: rotate(-8deg); filter: drop-shadow(0 8px 18px rgba(1,7,26,0.35)); }}
      #titulo {{ position: absolute; left: 0; top: {c.get("titulo_y", 1030)}px; width: 1080px; display: flex; flex-direction: column; align-items: center; }}
      .pill {{ display: inline-block; border-radius: 18px; font-weight: 800; letter-spacing: -0.045em; line-height: 1; white-space: nowrap; }}
      #p1 {{ padding: 16px 30px 24px; background: rgba(28,28,30,0.9); color: #ffffff; font-size: {c.get("tamanho", 112)}px; }}
      #p2 {{ margin-top: -4px; padding: 12px 34px 22px; background: #34BFD3; color: #14161A; font-size: {round(c.get("tamanho", 112) * 0.9)}px; }}
      #p3 {{ margin-top: 30px; font-size: 56px; font-weight: 500; letter-spacing: -0.02em; color: #ffffff; text-shadow: 0 2px 14px rgba(1,7,26,0.6); }}
      #selo {{ position: absolute; left: 0; top: 1540px; width: 1080px; display: flex; justify-content: center; align-items: center; gap: 22px; }}
      #av {{ width: 116px; height: 116px; border-radius: 50%; border: 5px solid #34BFD3; overflow: hidden; background: #34BFD3; }}
      #av img {{ width: 100%; height: 100%; object-fit: cover; }}
      #nome {{ font-size: 44px; font-weight: 800; letter-spacing: -0.03em; color: #ffffff; text-shadow: 0 2px 12px rgba(1,7,26,0.5); }}
      #sub {{ margin-top: 2px; font-size: 34px; font-weight: 400; color: rgba(255,255,255,0.85); text-shadow: 0 2px 12px rgba(1,7,26,0.5); }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="1" data-width="1080" data-height="1920">
      <img id="foto" class="clip" src="assets/foto.jpg" alt="" data-start="0" data-duration="1" data-track-index="0" />
      {topo_html}
      {icone}
      <div id="sombra"></div>
      <div id="titulo">
        {f'<div id="p1" class="pill">{ls[0]}</div>' if ls[0] else ""}
        {f'<div id="p2" class="pill">{ls[1]}</div>' if ls[1] else ""}
        {f'<div id="p3">{ls[2]}</div>' if ls[2] else ""}
      </div>
      {selo_html}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
""")
    snap = TMP / f"capa-{NN}"
    shutil.rmtree(snap, ignore_errors=True)
    out = subprocess.run([NPX, "--yes", HF_CLI, "snapshot", str(d), "--at", "0.5", "--no-end", "--describe", "false", "-o", str(snap)],
                         capture_output=True, text=True)
    pngs = [f for f in list(snap.rglob("*.png")) + list(snap.rglob("*.jpg")) if "contact" not in f.name]
    if not pngs:
        print(out.stdout[-1500:], out.stderr[-1500:])
        raise SystemExit("capa: snapshot não gerou imagem")
    src = max(pngs, key=lambda p: p.stat().st_mtime)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-q:v", "2", str(P / "assets/capa.jpg")], check=True)
    print("capa:", src)


# ---------------------------------------------------------------- escreve tudo
if "--sem-capa" not in sys.argv or not (P / "assets/capa.jpg").exists():
    capa()
if FECHO:
    ultimo = planos[-1][0]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.1", "-i", str(P / f"assets/cam-{ultimo}.mp4"), "-frames:v", "1",
                    "-vf", "gblur=sigma=40", "-q:v", "2", str(P / "assets/fecho/fundo.jpg")], check=True)
    (P / "compositions/fecho.html").write_text(FECHO_HTML)
if CARDS:
    (P / "compositions/cards.html").write_text(cards_html())
if S.get("notif"):
    (P / "compositions/notif.html").write_text(notif_html(S["notif"]))
if M == "B" and S.get("gancho"):
    (P / "compositions/gancho.html").write_text(gancho_html(S["gancho"]))
(P / "compositions/legendas.html").write_text(legendas_html())
(P / "index.html").write_text(index_html())
print("ok", P, "modelo", M, "duracao", TOTAL, "planos", planos, "cenas", cenas_b())
