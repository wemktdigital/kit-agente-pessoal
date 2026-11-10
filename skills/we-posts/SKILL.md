---
name: we-posts
description: Cria carrossel de feed (1080×1350) e sequência de stories (1080×1920) da WE Marketing Médico no visual padrão já aprovado, a partir de um corte, roteiro ou tema. Use quando pedirem "carrossel do corte X", "stories do corte X", "post no modelo WE", "mesmo visual do carrossel/stories" ou legenda para esses posts.
---

# Posts WE (carrossel + stories)

`KIT_ROOT` = pasta raiz deste kit (irmã de `skills/`). Modelos aprovados em `KIT_ROOT/we-modelos/`.

Se a skill estiver linkada em `~/.cursor/skills/we-posts`, resolva assim:

```bash
readlink ~/.cursor/skills/we-posts   # …/kit-agente-pessoal/skills/we-posts
# modelos = …/kit-agente-pessoal/we-modelos
```

No Windows: `(Get-Item "$HOME\.cursor\skills\we-posts").Target`.

- `carrossel/`: 8 cards + capa clara alternativa (conteúdo de exemplo: corte 13, NPS e avaliações no Google).
- `stories/`: 6 stories orgânicos (mesmo tema de exemplo).
- Cada pasta tem `index.html`, `exportar.py` e `referencia.jpg` (prancha com o visual esperado). Olhe `referencia.jpg` antes de começar.

Leia também a skill `hyperframes` só se precisar mexer em algo além de texto e layout.

## Fluxo

1. Pegue o conteúdo: transcrição do corte (ex.: `we-corte-NN/scripts/falas.json`), roteiro ou tema dado pelo usuário.
2. Copie o modelo para uma pasta nova, sem tocar no modelo (nunca rode o export dentro de `we-modelos/`):
   - Mac: `cp -R "$KIT_ROOT/we-modelos/carrossel" we-corte-NN-carrossel`
   - Windows: `Copy-Item -Recurse "$KIT_ROOT\we-modelos\carrossel" we-corte-NN-carrossel`
   (ou `stories` → `we-corte-NN-stories`). Atualize `id` e `name` em `meta.json`.
3. Troque só os textos e, se preciso, a ilustração dos cards. Mantenha classes, cores, fontes e posições.
4. Se mudar a quantidade de cards: ajuste `data-start` de cada `.clip` (1s cada, sequencial) e `data-duration` do `#root`. No carrossel, a capa clara (`#c1b`) é sempre o último clip.
5. Rode `npx --prefer-offline hyperframes check --json` na pasta e corrija `text_occluded`/overflow.
6. Exporte com `python3 exportar.py` (Windows: `python exportar.py`). Nunca exporte de outro jeito (print, render, snapshot à mão): o script embute as fontes do kit e troca os emoji por PNG da Apple, e é isso que deixa igual no Mac e no Windows. Se ele terminar com "ATENÇÃO: alguma fonte não carregou", resolva antes de entregar. Saída em `export/`:
   - carrossel: `card-01-escuro.png`, `card-01-claro.png`, `card-02.png`...
   - stories: `story-01.png`...
7. Abra `export/contact-sheet.jpg` e confira: texto cortado, palavra órfã, elementos sobrepostos, balão saindo da borda.
8. Se pedirem, escreva a legenda (gancho, passo a passo curto, ganhos, CTA, "salva esse post", hashtags com #marketingmedico).

Posts já publicados não devem ser alterados. Sempre trabalhe numa pasta nova.

## Carrossel (feed 1080×1350): regras do visual

Base no guia de marca https://we.marketing/guia-de-marca/ e no hero do site.

- Fonte Inter. Títulos: peso 600, `letter-spacing: -0.045em`, `line-height: 0.97`, 88–120px.
- Título em duas linhas: `.l1` ciano `#29CEDF`; `.l2` `#181818` no claro ou branco no escuro.
- Cores: ciano `#29CEDF`, ciano escuro `#006875`, preto `#000`, bordas `#E5E5E5` (claro) / `#292929` (escuro), texto `#444` (claro) / `#C6C6C6` (escuro).
- Verde `#2FDEA4` só no botão principal do CTA, com texto preto.
- Quadriculado (`.grade` + `.brilho`) só na capa. Células de 120px, bem sutil. Os outros cards são lisos.
- Alternar fundos `dark` e `light` entre os cards para dar ritmo.
- Cabeçalho em todo card (`.tw`): avatar `assets/avatar-ig.png` com anel degradê de stories do Instagram, "WE Marketing Médico", selo azul verificado `#0095F6`, `@wemarketingmedico`. Nunca usar a logo da empresa no lugar do avatar.
- Chip (`.selo`) no estilo `dk-chip` do site: fundo `rgba(41,206,223,.09)`, borda 2px, raio 16px, texto `#006875` (claro) / `#29CEDF` (escuro).

Peças disponíveis no `index.html` (reaproveite as classes):

- `.capa`: chip + título de 3 linhas + ilustração + balão "Arrasta pro lado". Existe em versão escura (`#c1`) e clara (`#c1b`).
- `.maps` / `.zap`: card do Google Maps e conversa de WhatsApp, usados como ilustração da capa.
- `.apoio`: parágrafo de apoio com `<b>` para destacar.
- `.lista`: card preto com itens de seta ciano (no máximo 3 itens curtos, sem quebrar em palavra órfã).
- `.call`: balão com seta circular ciano.
- `.nps`: card da pergunta NPS com escala 0–10 e legenda.
- `.faixa`: card de etapa com título grande, pílulas `.num` e emoji `.emoji` grande inclinado.
- `#c7 .itens`: lista de benefícios com ícone de linha ciano, título e descrição.
- `.azul` (`#2664EB`): card de CTA do Invisible CRM, com logo `assets/invisible-branco.png`, `.l1` em `#A8F0F7`, checklist, botão verde e URL `we.marketing/crm`.

Último card: CTA. Se o tema tiver relação com automação, WhatsApp, NPS, follow-up ou secretária, use o card do Invisible CRM (conteúdo de https://we.marketing/crm/, CTA "Agende uma demonstração").

Nome fictício de médico nos exemplos: "Dr. João Silva".

## Stories (1080×1920): regras do visual

Estilo orgânico, com cara de story feito no app. Sem foto ou ilustração de pessoa.

- Cores sólidas alternando: ciano `#34BFD3` (`.ciano`) e azul-marinho `#01071A` (`.preto`). Nada de degradê.
- Fontes: Roboto (interface do Instagram), Oswald (texto corrido), Playfair Display (frases de efeito).
- Peças: caixinha de pergunta (`.qbox`), mensagem com escala NPS (`.msg`), enquete (`.poll`), reação em bolha com emoji (`.react`), tag "Continua 👉" (`.tag`), pílula "SEGURE COM O DEDO PARA LER" (`.pill-top`), destaques `.hl` (marca-texto), `.esc` (fundo branco) e `.mk` (sublinhado à mão).
- Sequência típica: pergunta da caixinha respondida → explicação → passo a passo → ganhos → enquete → caixinha aberta para dúvidas.
- Use só recursos nativos do Instagram Stories: figurinhas (caixinha respondida/aberta, enquete de 2 a 4 opções, slider de emoji, quiz com resposta revelada, "Adicione o seu", menção, reação de emoji) e os estilos de texto do app (Clássico com fundo arredondado por linha, Forte em Oswald caixa alta, Editor em Playfair itálico). Nada de mockup de outros apps (notificações, Notas, chat), que foi reprovado.
- Não repita o mesmo molde em toda sequência: cada story usa uma figurinha e um tom de escrita diferentes dos vizinhos. Exemplo aprovado de variação: `we-99cabbaa-stories/`.
- Emojis com a classe `.emo` (Apple Color Emoji).

## Fontes e emoji (igual em qualquer máquina)

- Só use as fontes que vêm no kit: Inter, Roboto, Montserrat, Oswald e Playfair Display (qualquer peso). Outra família depende do Google na hora e do que está instalado na máquina.
- Emoji: use os que têm PNG em `KIT_ROOT/tools/reels-we/assets/emoji/` (nome = código do emoji, ex. `1f60d.png` = 😍). O export avisa os que não têm PNG; troque por um que tenha ou gere no Mac com `python gerar_emoji.py <emoji>` (precisa de Pillow) e suba no kit.
- Não apague o bloco `<style data-fontes-kit>` nem as `<img class="emoji-img">` que o export coloca no `index.html`.
