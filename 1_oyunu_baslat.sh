#!/usr/bin/env bash
# ============================================================
#  DRONES OF WAR - oyunu Wine ile baslatir (Ubuntu/Linux)
# ------------------------------------------------------------
#  Windows .bat karsiligi. Oyun bir Windows .exe oldugu icin
#  Wine uzerinden calisir. Oyun acilinca PLAY moduna gec.
#  Mumkunse Ayarlar'dan PENCERELI / KENARLIKSIZ moda al
#  (ekran goruntusu yakalama icin daha saglikli olur).
#  (Fatih / gps-log-server branch'inden alindi.)
# ============================================================
set -e
cd "$(dirname "$0")"

EXE="Drones of War Teknofest/DronesOfWar.exe"

if ! command -v wine >/dev/null 2>&1; then
    echo "HATA: 'wine' kurulu degil. Kur:  sudo apt install wine64"
    exit 1
fi

if [ ! -f "$EXE" ]; then
    echo "HATA: Oyun bulunamadi: $EXE"
    exit 1
fi

echo "============================================================"
echo "  DRONES OF WAR - Wine ile baslatiliyor..."
echo "  Oyun acilinca PLAY moduna gecmeyi unutma."
echo "============================================================"

wine "$EXE" &