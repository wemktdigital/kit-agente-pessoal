#!/bin/sh
# Exporta um PNG por card em export/.
# Ordem dos clips no index.html: capa escura, cards 2..N, capa clara (sempre o último).
set -e
cd "$(dirname "$0")"

n=$(grep -o 'data-composition-id="main"[^>]*' index.html | grep -o 'data-duration="[0-9]*"' | grep -o '[0-9][0-9]*')
ats=$(seq 0 $((n - 1)) | awk '{ printf "%s%.1f", (NR > 1 ? "," : ""), $1 + 0.5 }')

mkdir -p export
rm -f export/*.png
npx --prefer-offline hyperframes snapshot . --at "$ats" --no-end -o export --json >/dev/null

cd export
last=$((n - 1))
mv frame-00-*.png card-01-escuro.png
mv "$(ls frame-$(printf '%02d' "$last")-*.png)" card-01-claro.png
i=1
while [ "$i" -lt "$last" ]; do
  mv "$(ls frame-$(printf '%02d' "$i")-*.png)" "card-$(printf '%02d' $((i + 1))).png"
  i=$((i + 1))
done
ls
