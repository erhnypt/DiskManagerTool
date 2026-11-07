#!/bin/bash
# Arka planda çalışan Disk Manager sunucusunu ve onu ayakta tutan gözetmeni durdurur.
pkill -f "Disk Manager.app/Contents/MacOS/supervise"
pkill -f "python3 .*-m diskmanager"
echo "Durduruldu."
