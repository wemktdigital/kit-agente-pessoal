---
name: we-reels
description: Edita os reels verticais do podcast da WE Marketing Médico (Waldeir e Edson) no HyperFrames com o pipeline reels-we já aprovado - recorte da fala sem comer palavras, projeto gerado por spec.json (legendas, cards, notificação, capa, fecho, SFX, trilha), render e versões dubladas EN/ES nas vozes treinadas. Use quando pedirem "corte NN", "reel do podcast", "editar o próximo corte", "versão en/es", "áudio truncado/palavra cortada" ou ajustes num we-corte-NN.
---

# Reels do podcast WE (pipeline reels-we)

Os reels **não** são montados à mão. Eles saem dos scripts de `tools/reels-we` deste kit, ligados em `~/tools/reels-we`. Montar do zero com a skill genérica do HyperFrames dá um resultado bem abaixo do aprovado. Leia a skill `hyperframes` só para o contrato e para o `check`.

## Onde fica cada coisa

| O quê | Caminho |
| --- | --- |
| Scripts | `~/tools/reels-we/` (`caminhos.py` resolve tudo; `WE_DOCS` e `WE_TOOLS` sobrescrevem) |
| Decupagem (entrada) | `~/Documents/decupagem-videos/cortes/NN/` (repo `wemktdigital/decupagem-videos`, skill `decupagem-videos`) |
| Projeto do corte | `~/Documents/hyperframes/we-corte-NN/` (EN/ES: `we-corte-NN-en`, `-es`) |
| Finais | `~/Documents/hyperframes/we-reels-finais/corte-NN-pt.mp4` (`-en`, `-es`) |
| Exemplos de spec e tradução | `~/tools/reels-we/exemplos/` |

Python de cada script:

| Script | macOS | Windows |
| --- | --- | --- |
| `recorte.py`, `prep.py`, `dub.py`, `rostos.py`, `refaz_cortes.py` (precisam de torch) | `~/tools/Applio/.venv/bin/python` | `%USERPROFILE%\tools\Applio\env\python.exe` |
| `build.py`, `remapeia.py` (só biblioteca padrão) | `python3` | `python` |

Rode sempre de dentro de `~/tools/reels-we`. Se `WE_DOCS` estiver definido (Windows com Documentos no OneDrive), troque `~/Documents` por ele em todos os caminhos.

## Fluxo de um corte

1. **Decupagem.** O corte precisa existir em `decupagem-videos/cortes/NN/` (`cortes-4k.json`, `entrega/`). Se não existir, use a skill `decupagem-videos` primeiro.
2. **Recorte da fala.** `recorte.py NN` refaz o corte direto da fonte 4K, com cada borda no silêncio real entre as palavras. Sem a fonte 4K ele usa `entrega/trecho-completo.mp4`. `--so-analise` só mostra as emendas. Para ajustar uma borda à mão, use `cortes/NN/bordas.json`.
3. **Preparo.** `ENTREGA=~/Documents/hyperframes/we-corte-NN/fonte prep.py NN` gera `assets/cam-wa.mp4`, `assets/cam-ed.mp4`, `assets/voz.wav`, `scripts/palavras.json` e `scripts/falas.json`.
4. **Spec.** Escreva `scripts/spec.json` (modelo, palavras-chave, cards, notificação, capa, trilha). Parta de `exemplos/spec-corte-18.json`. Se o spec já existia antes do recorte, `remapeia.py NN` leva os tempos para a linha nova.
5. **Build.** `build.py NN` gera `index.html`, `compositions/` (legendas, cards, notif, fecho), a capa e os SFX. `--sem-capa` mantém a capa que já existe.
6. **Conferir.** `npx hyperframes check --json` e `snapshot` dos momentos com card. Transcreva o `voz.wav` com whisper (`ggml-large-v3`) e confira se nenhuma palavra saiu cortada. Depois abra o preview e passe o link.
7. **Render** quando o usuário aprovar: `we-reels-finais/corte-NN-pt.mp4`.
8. **EN/ES.** Escreva `scripts/traducao-en.json` e `traducao-es.json` (modelo em `exemplos/`), rode `dub.py NN en` e `dub.py NN es`, depois `build.py NN-en` e `build.py NN-es`, `check` e render.
9. **Posts.** Carrossel e stories PT/EN/ES com a skill `we-posts`, usando os prints do próprio vídeo. Depois, as legendas de postagem.

`refaz_cortes.py NN [NN…]` repete os passos 2, 3, 5 e a transcrição de conferência para vários cortes.

### spec.json em uma olhada

- `modelo`: `A` (câmera cheia, legenda de uma linha, cards de vidro), `B` (tela dividida, legenda caixa alta com pílula ciano) ou `C` (câmera cheia, cards estilo janela macOS, legenda em duas linhas, notificação do Google). Alterne entre os três ao longo dos cortes.
- `quem` (`wa` ou `ed`), `trocas` (trechos de cada câmera), `chave` (palavras em destaque na legenda), `corrige` (correção de palavra da transcrição), `sem_vicios`, `duplas`, `trilha` (`arq`, `volume`), `idioma`.
- `cards`: `versus`, `perfil`, `review`, `frase`, `lista`, `fluxo`, `estrelas`, `nps`, `contador`, `barra`, `busca`, `alerta`. Cada um com `de`/`ate` e os tempos `t*` presos à palavra falada.
- `notif`, `capa` (`linhas`, `cam`, `t`, `icone`, `icone_selo`).

## Regras aprovadas (não repetir os erros)

**Áudio e cortes**
- Nunca cortar palavra. Toda emenda fica numa pausa real. Confira cada emenda com o whisper antes de entregar.
- Hesitação (né, hum, é…) sai. Conector (e, aí, então) só sai se houver silêncio para cortar. Se tirar um vício for comer palavra vizinha, ele fica no áudio e sai **só da legenda**.
- Para achar fala cortada, compare com o bruto ou o `trecho-completo.mp4`. **Não** jogue o bruto inteiro no projeto e não refaça cenas ou legendas para isso.
- Palavrão: corte um pedacinho do áudio. Nada de "piii".
- Áudio da voz em mono.
- Depois de mudar o áudio, renderize de novo. Um MP4 antigo com áudio novo já causou entrega com palavras cortadas.

**Legenda e visual**
- Cores da WE flat. Nada de b-roll genérico de apoio; prefira fundo liso da marca.
- Card entra **só quando a palavra é dita**.
- Print real no lugar de emoji ou ilustração: tela do Google Maps, página de avaliação, livro, sistema. Ícone de marca real (WhatsApp, Google Meu Negócio) no lugar de 💬 ou ⭐.
- "Google" com G maiúsculo. Corrija a transcrição com `corrige`.
- Rosto centralizado no plano fechado. Tela dividida preenche a largura inteira, sem faixa na lateral.
- Não trocar a voz de quem fala (o Waldeir é `wa`, o Edson é `ed`).
- Menos é mais: quando o usuário pedir só legendas num trecho, tire as animações dali e não as traga de volta.

**Capa**
- Só a chamada. Sem o texto do topo com `//`, sem avatar e sem "WE Marketing Médico / Marketing para médicos".
- Molde aprovado: frame do apresentador sorrindo, ícone real (Google Maps etc.) e emoji ❌ atrás dele; ou tela dividida com Edson e Waldeir sorrindo e o texto no centro vertical.
- A capa ocupa os primeiros quadros do vídeo.

**Trilha, SFX e fecho**
- Trilha lo-fi beat moderna e suave (Envato), baixa sob a voz. Trocar quando pedirem, sem mexer no resto.
- Clique no botão "seguir" do fecho.

**EN/ES**
- O PT começa sozinho e abaixa quando a dublagem entra (`entra`, `pt_baixo`, `pt_some`). PT e dublagem ficam em faixas de áudio separadas.
- Vozes: `wa` = Waldeir (c06-esq), `ed` = Edson (c06-dir), via RVC no Applio.
- Confirme quem fala antes de dublar. O Edson é o de cabelo grisalho cacheado e barba grisalha; o outro é o Waldeir. Vídeo solo vindo do CapCut (`we-<hash>`) pode ser de qualquer um dos dois: o nome da pasta não diz, e "WE" não quer dizer Waldeir.
- Se o projeto já tem dublagem ou script anterior (`dublar.py`, `roteiro.json`, cache `*-rvc.wav`), mantenha a voz que ele usa (ex.: `c06-dir` = Edson). Só troque com confirmação do usuário.

**Edição manual do usuário**
- O usuário ajusta direto no HyperFrames (texto, volume, camadas desativadas). Antes de mexer, rode `npx hyperframes history --since mine` e preserve esses ajustes.
- **Não rode `build.py` de novo num projeto que o usuário já editou à mão**: ele sobrescreve `index.html` e `compositions/`. Faça a mudança pedida direto nos arquivos ou faça backup antes e reaplique os ajustes.

**Entrega e limpeza**
- Entregue o link do preview e o caminho dos MP4 finais.
- Legenda de postagem por idioma, com a legenda literal do vídeo embaixo quando pedirem.
- Vídeo publicado: o usuário costuma pedir para apagar brutos, decupagem e projeto. Apague só o que ele confirmar.

## Windows

- Instalação: `instalar.ps1` na raiz do kit.
- PowerShell, passo 3: `$env:ENTREGA="$HOME\Documents\hyperframes\we-corte-NN\fonte"; & "$HOME\tools\Applio\env\python.exe" prep.py NN`.
- `caminhos.py` reexecuta o Python em UTF-8 sozinho. Se ler JSON com acento der erro, confira `PYTHONUTF8=1`.
- Fontes e emoji: o `build.py` embute as fontes do kit (Inter, Roboto, Montserrat, Oswald, Playfair) e troca emoji por PNG da Apple (`portatil.py`), então capa, legendas e cards saem iguais ao Mac. Só use essas fontes e emoji que tenham PNG em `assets/emoji/` (o build avisa os que faltam).
- Mexeu à mão no HTML (capa, cards) ou num projeto antigo? Rode `python portatil.py <pasta-do-projeto>` antes do snapshot/render. Ele é idempotente e também trata `capa/`.
- `npx` vira `npx.cmd` e o temporário é `%TEMP%`; os scripts já tratam isso.

## Atualizar o kit

`KIT_ROOT` = pasta do kit, dois níveis acima do destino do link `~/tools/reels-we` (Mac: `readlink ~/tools/reels-we`; Windows: `(Get-Item "$HOME\tools\reels-we").Target`), normalmente `~/Documents/kit-agente-pessoal`.

Se pedirem para atualizar o kit, ou se faltar algo que esta skill cita (ex.: `exportar.py`, `portatil.py`), atualize: Windows `powershell -ExecutionPolicy Bypass -File "$KIT_ROOT\atualizar.ps1"`, Mac `"$KIT_ROOT/atualizar.sh"`. Depois peça para abrir um chat novo. Passo a passo e novidades em `KIT_ROOT/ATUALIZACOES.md`. Ao melhorar o kit, registre a mudança na seção "Novidades" desse arquivo.
