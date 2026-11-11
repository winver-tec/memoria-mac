#!/bin/zsh
# Desliga o medidor e remove os arquivos. Não mexe em mais nada.
DESTINO=${DESTINO:-$HOME/.winver/memoria}
launchctl bootout "gui/$(id -u)/com.winver.memoria" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.winver.memoria.plist"
rm -rf "$DESTINO"
echo "Removido. Se criou o portal e a rotina no Maestri, apague-os por lá."
