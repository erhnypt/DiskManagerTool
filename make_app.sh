#!/bin/bash
# "Disk Manager.app" oluşturur (varsayılan: ~/Applications). Uygulama, projedeki
# DiskManager.command dosyasını Terminal'de açar; sunucu o pencerede çalışır.
# (Sunucuyu uygulamanın arka plan sürecine koymak işe yaramadı: macOS onu kapatıyordu.)
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
<key>CFBundleVersion</key><string>2</string>
</dict></plist>
PLIST
cat > "$APP/Contents/MacOS/launch" <<LAUNCH
#!/bin/bash
exec open -a Terminal "$REPO/DiskManager.command"
LAUNCH
chmod +x "$APP/Contents/MacOS/launch"
echo "Oluşturuldu: $APP"
echo "Açınca Terminal penceresi gelir; sunucu orada çalışır. Durdurmak için pencereyi kapat."
