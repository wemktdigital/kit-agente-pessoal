#!/usr/bin/env bash
# Liga este kit (HyperFrames / WE) no Cursor nesta máquina.
# Uso: ./instalar.sh          # links (git pull atualiza)
#      ./instalar.sh --copy   # cópia
set -euo pipefail

KIT="$(cd "$(dirname "$0")" && pwd)"
MODO="link"
[[ "${1:-}" == "--copy" ]] && MODO="copy"

SKILLS_DIR="$HOME/.cursor/skills"
BACKUP_DIR="$HOME/.cursor/skills-backup"
SKILLS=(we-posts we-reels)

echo "== Kit HyperFrames: $KIT ($MODO) =="
mkdir -p "$SKILLS_DIR"

for s in "${SKILLS[@]}"; do
  src="$KIT/skills/$s"
  dst="$SKILLS_DIR/$s"
  [[ -d "$src" ]] || { echo "FALTA $src"; exit 1; }

  if [[ -L "$dst" && "$(readlink "$dst")" == "$src" ]]; then
    echo "ok   $dst (já linkado)"
    continue
  fi
  if [[ -e "$dst" || -L "$dst" ]]; then
    mkdir -p "$BACKUP_DIR"
    bk="$BACKUP_DIR/$s-$(date +%Y%m%d-%H%M%S)"
    mv "$dst" "$bk"
    echo "     backup → $bk"
  fi
  if [[ "$MODO" == link ]]; then
    ln -s "$src" "$dst"
  else
    cp -R "$src" "$dst"
  fi
  echo "ok   $dst"
done

reels_src="$KIT/tools/reels-we"
reels_dst="$HOME/tools/reels-we"
mkdir -p "$HOME/tools"
if [[ -L "$reels_dst" && "$(readlink "$reels_dst")" == "$reels_src" ]]; then
  echo "ok   $reels_dst (já linkado)"
else
  if [[ -e "$reels_dst" || -L "$reels_dst" ]]; then
    bk="$reels_dst-backup-$(date +%Y%m%d-%H%M%S)"
    mv "$reels_dst" "$bk"
    echo "     backup → $bk"
  fi
  ln -s "$reels_src" "$reels_dst"
  echo "ok   $reels_dst → kit"
fi

HF="$HOME/Documents/hyperframes"
if [[ -d "$HF" && ! -e "$HF/we-modelos" ]]; then
  ln -s "$KIT/we-modelos" "$HF/we-modelos"
  echo "ok   $HF/we-modelos → kit"
elif [[ -e "$HF/we-modelos" ]]; then
  echo "ok   $HF/we-modelos (já existe)"
fi

echo
echo "== Skill oficial HyperFrames =="
if command -v npx >/dev/null 2>&1; then
  echo "Rode: npx hyperframes skills update"
else
  echo "Instale Node 22+ e depois: npx hyperframes skills update"
fi

echo
echo "Pronto. Abra um chat novo no Cursor."
echo "Modelos WE: $KIT/we-modelos"
