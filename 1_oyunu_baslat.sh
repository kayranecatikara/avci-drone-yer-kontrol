#!/usr/bin/env bash
# ============================================================
#  DRONES OF WAR - oyunu GE-Proton (umu-launcher) ile baslatir
# ------------------------------------------------------------
#  NEDEN wine DEGIL Proton: wine-10.0'in mfplat/GStreamer video
#  yolu intro/menu mp4'unu oynatirken cokuyordu
#  (UE EXCEPTION_ACCESS_VIOLATION, crash hash BDD3858F..., ~56-59s'te).
#  GE-Proton duzgun Media Foundation icerir -> mp4 crash'i giderir.
#
#  Oyun acilinca PLAY moduna gec. Mumkunse Ayarlar'dan
#  PENCERELI / KENARLIKSIZ moda al (ekran yakalama icin saglikli).
# ============================================================
set -e
cd "$(dirname "$0")"

EXE="Drones of War Teknofest/DronesOfWar.exe"

# --- Proton / umu yollari ---
UMU_RUN="$HOME/.local/share/umu/umu/umu-run"
PROTON="$HOME/.local/share/Steam/compatibilitytools.d/GE-Proton11-1"
# umu zipapp Python 3.10+ ister; sistemde python3.10 (deadsnakes) kurulu.
PY="$(command -v python3.10 || command -v python3)"

if [ ! -f "$EXE" ]; then
    echo "HATA: Oyun bulunamadi: $EXE"
    exit 1
fi
if [ ! -f "$UMU_RUN" ]; then
    echo "HATA: umu-launcher bulunamadi: $UMU_RUN"
    echo "  (Proton kurulumu eksik.)"
    exit 1
fi
if [ ! -d "$PROTON" ]; then
    echo "HATA: GE-Proton bulunamadi: $PROTON"
    exit 1
fi

# XDG_DATA_HOME'u sabitle: VSCode snap altinda bu degisken snap-sandbox
# yoluna kayar -> umu runtime'i baska yere iner. Kanonik yola pinle.
export XDG_DATA_HOME="$HOME/.local/share"
export WINEPREFIX="$HOME/Games/dronesofwar/pfx"
export GAMEID="umu-dronesofwar"
export PROTONPATH="$PROTON"
export STORE="none"

echo "============================================================"
echo "  DRONES OF WAR - GE-Proton ile baslatiliyor..."
echo "  Oyun acilinca PLAY moduna gecmeyi unutma."
echo "============================================================"

"$PY" "$UMU_RUN" "$EXE" &
