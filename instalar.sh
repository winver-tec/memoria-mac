#!/bin/zsh
# Instala o medidor de memória do Mac em ~/.winver/memoria e deixa ligado no boot (LaunchAgent).
# Uso: ./instalar.sh            (padrão: porta 4747)
#      PORTA=5000 ./instalar.sh (outra porta)
# Variáveis para teste: DESTINO=/outra/pasta  SEM_LAUNCHD=1
set -e
ORIGEM=${0:A:h}
DESTINO=${DESTINO:-$HOME/.winver/memoria}
PORTA=${PORTA:-4747}
PLIST=$HOME/Library/LaunchAgents/com.winver.memoria.plist

command -v clang >/dev/null || { echo "Falta o clang. Rode: xcode-select --install"; exit 1; }
[[ -x /usr/bin/python3 ]] || { echo "Falta o python3 do sistema (/usr/bin/python3). Rode: xcode-select --install"; exit 1; }

mkdir -p "$DESTINO"
cp "$ORIGEM"/{servidor.py,index.html,mini.html,logo.svg,temperatura.m,cooler.c,ping_maestro.sh} "$DESTINO"/
chmod +x "$DESTINO/ping_maestro.sh"
echo "• compilando sensores (temperatura e coolers, sem sudo)..."
clang -O2 -fobjc-arc -framework Foundation -framework IOKit -o "$DESTINO/temperatura" "$DESTINO/temperatura.m"
clang -O2 -framework IOKit -framework CoreFoundation -o "$DESTINO/cooler" "$DESTINO/cooler.c"

if [[ -z "$SEM_LAUNCHD" ]]; then
  mkdir -p "$HOME/Library/LaunchAgents"
  sed "s|__DESTINO__|$DESTINO|g; s|__PORTA__|$PORTA|g" "$ORIGEM/com.winver.memoria.plist.modelo" > "$PLIST"
  launchctl bootout "gui/$(id -u)/com.winver.memoria" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  for i in 1 2 3 4 5 6; do curl -fs "http://127.0.0.1:$PORTA/dados" >/dev/null 2>&1 && break; sleep 1; done
  curl -fs "http://127.0.0.1:$PORTA/dados" >/dev/null 2>&1 || { echo "Servidor não respondeu. Veja $DESTINO/servidor.err.log"; exit 1; }
fi
echo "✅ Instalado em $DESTINO"
echo "   Painel:  http://127.0.0.1:$PORTA/"
echo "   Faixa:   http://127.0.0.1:$PORTA/mini   (para o portal do Maestri, 980x289)"
