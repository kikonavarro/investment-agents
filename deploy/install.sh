#!/bin/bash
# Instala/actualiza el procesador autónomo de la bandeja (launchd) + el helper.
# Reproducible: deploy/ es la fuente de verdad; esto copia a las ubicaciones del sistema.
# Uso:  bash deploy/install.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
AGENTS="$HOME/Library/LaunchAgents"
BIN="$HOME/bin"
GUI="gui/$(id -u)"

mkdir -p "$AGENTS" "$BIN"

echo "Copiando plists y helper..."
cp "$HERE/com.investment.inbox.plist"          "$AGENTS/"
cp "$HERE/com.investment.inbox-watchdog.plist" "$AGENTS/"
cp "$HERE/bandeja"                              "$BIN/bandeja"
chmod +x "$BIN/bandeja"
chmod +x "$HERE/../tools/process_inbox.sh"

echo "Validando plists..."
plutil -lint "$AGENTS/com.investment.inbox.plist" "$AGENTS/com.investment.inbox-watchdog.plist"

echo "(Re)cargando en launchd..."
for L in com.investment.inbox com.investment.inbox-watchdog; do
    launchctl bootout "$GUI/$L" 2>/dev/null || true
    launchctl bootstrap "$GUI" "$AGENTS/$L.plist"
done

echo "Listo. Estado:"
"$BIN/bandeja" status
