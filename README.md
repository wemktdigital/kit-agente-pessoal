# Kit agente pessoal — HyperFrames / WE

Aprendizados e modelos **seus** para posts WE no HyperFrames. Serve pra clonar em outra máquina.

A skill oficial HyperFrames (HeyGen) fica fora daqui. Na máquina nova:

```bash
npx hyperframes skills update
```

## Conteúdo

| Pasta | O quê |
| --- | --- |
| `skills/we-posts` | Fluxo carrossel + stories WE |
| `we-modelos/` | Templates HTML aprovados (feed + stories) |

## Máquina nova

```bash
git clone <url-do-repo> ~/Documents/kit-agente-pessoal
cd ~/Documents/kit-agente-pessoal
chmod +x instalar.sh && ./instalar.sh
npx hyperframes skills update
```

Abra um **chat novo** no Cursor depois do install.

## Atualizar

Nesta máquina: edite `skills/we-posts` ou `we-modelos` → `git commit` → `git push`.  
Na outra: `git pull` (com `./instalar.sh` em modo link, não reinstala).

## Fora deste kit

Pipeline CapCut, Canva e skills HeyGen oficiais. CapCut continua no repo `wemktdigital/agentes-video-capcut` se precisar um dia.
