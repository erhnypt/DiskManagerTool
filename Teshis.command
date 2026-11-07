#!/bin/bash
# Çift tıkla: sorunu bulmak için gereken bilgileri toplar ve panoya kopyalar (Cmd+V ile yapıştır).
cd "$(dirname "$0")" || exit 1
PORT="${DISKMANAGER_PORT:-8765}"
{
  echo "== Tarih: $(date)"
  echo "== macOS: $(sw_vers -productVersion 2>/dev/null || uname -a)   python3: $(python3 --version 2>&1)"
  echo "== Kod sürümü (git): $(git log --oneline -1 2>&1)"
  echo "== Çalışan süreçler:"
  ps -axo pid,etime,rss,command | grep -E "diskmanager|supervise" | grep -v grep | cut -c1-160
  echo "== Sunucu yanıtı:"
  curl -s -m 3 "http://127.0.0.1:$PORT/api/status" || echo "(yanıt yok — sunucu çalışmıyor)"
  echo
  echo "== Günlük (son 40 satır):"
  tail -40 "$HOME/Library/Logs/DiskManager.log" 2>&1 | cut -c1-200
  echo "== Boş disk:"; df -h / 2>&1 | tail -1
} > /tmp/diskmanager_teshis.txt 2>&1
cat /tmp/diskmanager_teshis.txt
if command -v pbcopy >/dev/null; then pbcopy < /tmp/diskmanager_teshis.txt; echo; echo ">>> Panoya kopyalandı. Cmd+V ile bana yapıştır."; fi
read -r -p "Kapatmak için Enter'a bas..."
