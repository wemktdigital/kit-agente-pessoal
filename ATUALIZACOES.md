# Como atualizar o kit

Sempre que avisarem que o kit mudou (ou se o resultado estiver diferente do Mac principal), atualize a máquina.

## Windows

Abra a pasta `Documentos\kit-agente-pessoal` e dê **dois cliques em `atualizar.cmd`**.

Ou, no PowerShell:

```powershell
cd "$HOME\Documents\kit-agente-pessoal"
powershell -ExecutionPolicy Bypass -File .\atualizar.ps1
```

Ele baixa a versão nova, mostra as novidades e roda o `instalar.ps1` de novo (pula o que já está instalado e instala o que for novo). Opções: `-SoBaixar` (só baixa, sem conferir dependências), `-SemApplio`, `-SemWhisperLarge`.

## macOS

```bash
cd ~/Documents/kit-agente-pessoal && ./atualizar.sh
```

## Depois de atualizar

1. Abra um **chat novo** no Cursor (chat aberto antes continua com as skills antigas).
2. Se a lista de novidades abaixo pedir algo a mais, faça.

## Se der erro

- "Arquivos do kit foram alterados nesta máquina": alguém editou um arquivo dentro do kit. Nada foi apagado. Mande a lista para o agente ou rode `git stash` e atualize de novo.
- Pediu login ou "git pull falhou": rode `gh auth login`, entre com a conta do GitHub da WE e tente de novo.
- Qualquer outro erro: copie a mensagem inteira e mande para o agente.

## Para quem mantém o kit (Mac principal)

Toda melhoria vai **dentro deste repo** (skills, `tools/reels-we`, `we-modelos`), depois `git commit` e `git push`, e uma linha nova em "Novidades" abaixo. Não guarde aprendizado em `~/.cursor/skills/hyperframes*`: o `skills update` apaga.

## Novidades

### 2026-11-13 — dublagem: confirmar quem fala
- Skill `we-reels`: antes de dublar, confirmar se quem fala é o Edson (cabelo e barba grisalhos, `c06-dir`) ou o Waldeir (`c06-esq`). Se já existe dublagem anterior, manter a voz dela.
- Motivo: no 444b1b67 (solo do Edson) a dublagem EN/ES saiu com a voz do Waldeir.

### 2026-11-10 — fontes e emoji iguais ao Mac
- Fontes (Inter, Roboto, Montserrat, Oswald, Playfair) e emoji da Apple embutidos: capa, carrossel e stories saem iguais ao Mac.
- Carrossel e stories exportam com `python exportar.py` (o antigo `exportar.sh` saiu).
- Projetos feitos antes: rode `python exportar.py` de novo na pasta do post, ou `python portatil.py <pasta>` em `~/tools/reels-we` para um reel.
- Nada a instalar além do `atualizar`.

### 2026-11-10 — pipeline dos reels e instalador Windows
- Pipeline `reels-we`, skill `we-reels`, vozes treinadas e `instalar.ps1`.
- Exige rodar o instalador completo uma vez (o `atualizar` já faz isso).
