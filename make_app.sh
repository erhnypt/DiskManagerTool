#!/bin/bash
# Terminal penceresi açmayan bir "Disk Manager.app" oluşturur (varsayılan: ~/Applications).
# Uygulama bu klasörü işaret eder; klasörü taşırsan scripti yeniden çalıştır.
set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-$HOME/Applications}"
APP="$DEST/Disk Manager.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Disk Manager</string>
<key>CFBundleIdentifier</key><string>local.diskmanager.launcher</string>
<key>CFBundleExecutable</key><string>launch</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleVersion</key><string>1</string>
</dict></plist>
PLIST
# supervise: keeps the server alive. If it dies (crash, kill) it is restarted and
# the exit code is logged, so we can see why it stopped.
cat > "$APP/Contents/MacOS/supervise" <<SUPERVISE
#!/bin/bash
PORT=\${DISKMANAGER_PORT:-8765}
LOG="\$HOME/Library/Logs/DiskManager.log"
mkdir -p "\$HOME/Library/Logs"
cd "$REPO" || exit 1
while true; do
  echo "\$(date '+%F %T') sunucu başlıyor (port \$PORT)" >> "\$LOG"
  python3 -X faulthandler -u -m diskmanager --no-browser --port "\$PORT" >> "\$LOG" 2>&1
  rc=\$?
  echo "\$(date '+%F %T') sunucu kapandı, çıkış kodu \$rc (137=zorla öldürüldü, 139=çöktü)" >> "\$LOG"
  sleep 2
done
SUPERVISE
cat > "$APP/Contents/MacOS/launch" <<LAUNCH
#!/bin/bash
REPO="$REPO"
PORT=\${DISKMANAGER_PORT:-8765}
URL="http://127.0.0.1:\$PORT/"
OPEN=\$(command -v open || command -v xdg-open)
SUP="$APP/Contents/MacOS/supervise"
up() { curl -s -o /dev/null "\${URL}api/status"; }
# Server running outdated code (e.g. after git pull)? Kill it; the supervisor restarts it.
if up; then
  NEW=\$(cd "\$REPO" && python3 -c "from diskmanager.server import code_version; print(code_version())" 2>/dev/null)
  RUN=\$(curl -s "\${URL}api/version.txt")
  if [ -n "\$NEW" ] && [ "\$NEW" != "\$RUN" ]; then
    pkill -f "diskmanager --no-browser --port \$PORT"; sleep 1
  fi
fi
pgrep -f "\$SUP" >/dev/null || { nohup "\$SUP" >/dev/null 2>&1 & }
for _ in \$(seq 1 75); do up && break; sleep 0.2; done
"\$OPEN" "\$URL"
LAUNCH
chmod +x "$APP/Contents/MacOS/supervise"
chmod +x "$APP/Contents/MacOS/launch"
echo "Oluşturuldu: $APP"
echo "Durdurmak için: ./stop.sh   |   Günlük: ~/Library/Logs/DiskManager.log"
