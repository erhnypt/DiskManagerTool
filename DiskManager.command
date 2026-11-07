#!/bin/bash
# Çift tıkla: sunucuyu bu Terminal penceresinde başlatır ve tarayıcıyı açar.
# Durdurmak için pencereyi kapat. (Terminal'in Tam Disk Erişimi izni bu sürece de geçer.)
cd "$(dirname "$0")" || exit 1
PORT="${DISKMANAGER_PORT:-8765}"
URL="http://127.0.0.1:$PORT/"
if ! command -v python3 >/dev/null; then
  echo "python3 bulunamadı. https://www.python.org/downloads/ adresinden kur."; read -r -p "Enter'a bas..."; exit 1
fi
# Zaten bir sunucu çalışıyorsa: aynı sürümse yalnızca tarayıcıyı aç, eskiyse kapat.
if curl -s -m 2 -o /dev/null "${URL}api/status"; then
  NEW=$(python3 -c "from diskmanager.server import code_version; print(code_version())" 2>/dev/null)
  RUN=$(curl -s -m 2 "${URL}api/version.txt")
  if [ -n "$NEW" ] && [ "$NEW" = "$RUN" ]; then
    echo "Sunucu zaten çalışıyor, tarayıcı açılıyor: $URL"
    (command -v open >/dev/null && open "$URL") || xdg-open "$URL"
    exit 0
  fi
  echo "Eski sunucu kapatılıyor..."
  pkill -f "python3 .*-m diskmanager"; sleep 1
fi
exec python3 -X faulthandler -u -m diskmanager --port "$PORT" "$@"
