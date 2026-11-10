#!/usr/bin/env bash
# Atualiza o kit WE no macOS: baixa a versão nova, religa skills/pipeline e atualiza as skills oficiais do HyperFrames.
# Uso: ./atualizar.sh
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"
cd "$KIT"

echo "== Atualizando o kit em $KIT =="
sujo="$(git status --porcelain --untracked-files=no)"
if [[ -n "$sujo" ]]; then
  echo "Arquivos do kit foram alterados nesta máquina:"
  echo "$sujo" | sed 's/^/   /'
  echo "Nada foi atualizado. Faça commit/push (ou git stash) e tente de novo."
  exit 1
fi

antes="$(git rev-parse HEAD)"
git pull --ff-only
depois="$(git rev-parse HEAD)"
if [[ "$antes" == "$depois" ]]; then
  echo "Já estava na versão mais nova."
else
  echo; echo "Novidades:"
  git log --pretty=format:"   %ad  %s" --date=short "$antes..$depois"; echo
fi

echo
"$KIT/instalar.sh"
command -v npx >/dev/null 2>&1 && npx --yes hyperframes skills update
echo
echo "Atualizado. Abra um chat NOVO no Cursor para as skills novas valerem."
