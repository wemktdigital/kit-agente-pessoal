#!/bin/sh
# Exporta um PNG por story em export/ (story-01.png, story-02.png...).
set -e
cd "$(dirname "$0")"

n=$(grep -o 'data-composition-id="main"[^>]*' index.html | grep -o 'data-duration="[0-9]*"' | grep -o '[0-9][0-9]*')
ats=$(seq 0 $((n - 1)) | awk '{ printf "%s%.1f", (NR > 1 ? "," : ""), $1 + 0.5 }')

mkdir -p export
rm -f export/*.png
npx --prefer-offline hyperframes snapshot . --at "$ats" --no-end -o export --json >/dev/null

cd export
i=0
while [ "$i" -lt "$n" ]; do
  mv "$(ls frame-$(printf '%02d' "$i")-*.png)" "story-$(printf '%02d' $((i + 1))).png"
  i=$((i + 1))
done
ls
