# Kit agente pessoal — HyperFrames / WE

Tudo que faz os vídeos e posts da WE saírem no padrão aprovado, para instalar em outra máquina.

## Conteúdo

| Pasta | O quê |
| --- | --- |
| `skills/we-reels` | Fluxo dos reels do podcast + regras aprovadas nos chats |
| `skills/we-posts` | Carrossel + stories WE |
| `tools/reels-we` | Pipeline dos reels: `recorte.py`, `prep.py`, `build.py`, `dub.py`, assets (trilhas, SFX, fecho) e exemplos de `spec.json` |
| `we-modelos/` | Templates HTML aprovados (feed + stories) |
| `instalar.ps1` | Instalação completa no Windows |
| `instalar.sh` | Ligação das skills e do pipeline no macOS |
| `atualizar.cmd` / `atualizar.ps1` / `atualizar.sh` | Atualização (ver [ATUALIZACOES.md](ATUALIZACOES.md)) |

Fora do git, baixado pelo instalador:

- Vozes treinadas (RVC) do Waldeir e do Edson: Release `vozes-v1` deste repo.
- Modelos Whisper (`ggml-small`, `ggml-large-v3`), Applio, Kokoro.
- Repo `wemktdigital/decupagem-videos`.

## Windows

```powershell
git clone https://github.com/wemktdigital/kit-agente-pessoal.git "$HOME\Documents\kit-agente-pessoal"
cd "$HOME\Documents\kit-agente-pessoal"
powershell -ExecutionPolicy Bypass -File .\instalar.ps1
```

O instalador usa o winget para Git, Node, FFmpeg, GitHub CLI e Python 3.11. Depois instala whisper.cpp + modelos, Kokoro, Applio (torch, alguns GB), as vozes, o `decupagem-videos`, os MCPs Envato e Canva e as skills oficiais do HyperFrames. Ele pede login no GitHub (`gh auth login`) para baixar as vozes e o repo privado.

Opções: `-SemApplio` (sem dublagem EN/ES), `-SemWhisperLarge` (pula o modelo de 3 GB).

Depois: reabrir o Cursor, fazer login no Envato e no Canva em Settings > MCP e abrir um chat novo.

## macOS

```bash
git clone https://github.com/wemktdigital/kit-agente-pessoal.git ~/Documents/kit-agente-pessoal
cd ~/Documents/kit-agente-pessoal && ./instalar.sh
npx hyperframes skills update
```

No Mac, Applio, Kokoro e Whisper ainda são instalados à mão (ver `skills/we-reels/SKILL.md`).

## Atualizar

Windows: dois cliques em `atualizar.cmd`. Mac: `./atualizar.sh`. Passo a passo, erros comuns e histórico de mudanças em [ATUALIZACOES.md](ATUALIZACOES.md).
