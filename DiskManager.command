#!/bin/bash
# Çift tıkla: sunucuyu başlatır ve tarayıcıyı açar. Durdurmak için bu pencereyi kapat.
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null; then
  echo "python3 bulunamadı. https://www.python.org/downloads/ adresinden kur."; read -r -p "Enter'a bas..."; exit 1
fi
exec python3 -m diskmanager "$@"
