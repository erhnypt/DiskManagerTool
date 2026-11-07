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
cat > "$APP/Contents/MacOS/launch" <<LAUNCH
#!/bin/bash
REPO="$REPO"
PORT=\${DISKMANAGER_PORT:-8765}
URL="http://127.0.0.1:\$PORT/"
OPEN=\$(command -v open || command -v xdg-open)
# Restart the background server if it runs outdated code (e.g. after git pull).
if curl -s -o /dev/null "\${URL}api/status"; then
  NEW=\$(cd "\$REPO" && python3 -c "from diskmanager.server import code_version; print(code_version())" 2>/dev/null)
  RUN=\$(curl -s "\${URL}api/version" | sed -n 's/.*"version": "\\([0-9a-f]*\\)".*/\\1/p')
  if [ -n "\$NEW" ] && [ "\$NEW" != "\$RUN" ]; then
    pkill -f "diskmanager --no-browser --port \$PORT"; sleep 1
  fi
fi
if ! curl -s -o /dev/null "\${URL}api/status"; then
  mkdir -p "\$HOME/Library/Logs"
  cd "\$REPO" || exit 1
  nohup python3 -m diskmanager --no-browser --port "\$PORT" >> "\$HOME/Library/Logs/DiskManager.log" 2>&1 &
  for _ in \$(seq 1 50); do curl -s -o /dev/null "\${URL}api/status" && break; sleep 0.2; done
fi
"\$OPEN" "\$URL"
LAUNCH
chmod +x "$APP/Contents/MacOS/launch"
echo "Oluşturuldu: $APP"
echo "Durdurmak için: pkill -f 'python3 -m diskmanager'"
