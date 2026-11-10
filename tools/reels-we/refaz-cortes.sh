#!/bin/zsh
# Refaz o áudio/vídeo dos reels a partir da fonte 4K sem picotar palavras e reconstrói os projetos.
# Uso: refaz-cortes.sh NN [NN ...]   (log em /tmp/refaz/NN.log)
PY=~/tools/Applio/.venv/bin/python
cd ~/tools/reels-we
mkdir -p /tmp/refaz
for n in "$@"; do
  L=/tmp/refaz/$n.log
  {
    echo "===== $n"
    $PY recorte.py $n 2>&1 | grep -v -i warn | grep -E "duracao|termina|nenhuma|fora|voltam" &&
    ENTREGA=$HOME/Documents/hyperframes/we-corte-$n/fonte $PY prep.py $n 2>&1 | grep -E "^duracao|não bate" &&
    python3 remapeia.py $n &&
    python3 build.py $n --sem-capa 2>&1 | tail -1 &&
    whisper-cli -m ~/models/whisper/ggml-large-v3.bin -l pt -f ~/Documents/hyperframes/we-corte-$n/assets/voz.wav -nt 2>/dev/null | tr -s ' \n' ' ' &&
    echo && echo "OK $n" || echo "FALHOU $n"
  } > $L 2>&1
  tail -1 $L
done
echo REFAZ_DONE
