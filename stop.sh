#!/bin/bash
# Çalışan Disk Manager sunucusunu (ve eski sürümlerden kalan gözetmeni) durdurur.
pkill -f "Disk Manager.app/Contents/MacOS/supervise"
pkill -f "python3 .*-m diskmanager"
echo "Durduruldu."
