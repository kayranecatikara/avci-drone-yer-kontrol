#!/usr/bin/env bash
# ============================================================
#  DRONES OF WAR - simulasyon oyununu Wine ile baslatir (Linux)
# ------------------------------------------------------------
#  Oyun bir Windows .exe oldugu icin Wine uzerinden calisir.
#  Oyun acilinca PLAY moduna gec, sonra AYRI bir terminalde:
#      python3 -m control.main
#
#  PENCERE MODU: kamera hatti (perception/camera.py) EKRANI yakalar
#  (mss). Oyun penceresi GORUNUR/ONDE kalmali; KENARLIKSIZ PENCERE
#  modu en saglikli sonucu verir.
#
#  NEDEN LAUNCHER DEGIL SHIPPING EXE:
#  Kok dizindeki "DronesOfWar.exe" bir launcher; once
#  Engine/Extras/Redist/en-us/UEPrereqSetup_x64.exe (32-bit kurucu)
#  calistirmaya calisiyor. wine32:i386 kurulu degilse
#  "failed to load syswow64\ntdll.dll (c0000135)" verip oyunu hic
#  baslatmadan kapaniyor. Asil oyun binary'si
#  DronesOfWar/Binaries/Win64/DronesOfWar-Win64-Shipping.exe
#  dogrudan calisiyor -> varsayilan olarak onu baslatiyoruz.
#  Launcher'i denemek istersen: scripts/start_game.sh --launcher
# ============================================================
set -e
cd "$(dirname "$0")/.."          # depo koku

OYUN_DIZIN="Drones of War Teknofest"
SHIPPING="$OYUN_DIZIN/DronesOfWar/Binaries/Win64/DronesOfWar-Win64-Shipping.exe"
LAUNCHER="$OYUN_DIZIN/DronesOfWar.exe"

# Pencere modu / cozunurluk (istersen ortam degiskeniyle ez):
#   PENCERE_ARGS="-fullscreen" scripts/start_game.sh
PENCERE_ARGS="${PENCERE_ARGS:--windowed -ResX=1280 -ResY=720}"

# wine'in d3d hata spam'i (dakikada yuz binlerce satir) hem terminali
# hem oyunu bogar; ayrintili log icin: WINEDEBUG=+d3d
export WINEDEBUG="${WINEDEBUG:--all}"

if ! command -v wine >/dev/null 2>&1; then
    echo "HATA: 'wine' kurulu degil. Kur:  sudo apt install wine64"
    exit 1
fi

if [ "$1" = "--launcher" ]; then
    EXE="$LAUNCHER"
    ARGS=""
    echo "UYARI: launcher modu -- wine32:i386 yoksa oyun acilmadan kapanir."
    echo "       Kur:  sudo dpkg --add-architecture i386 && sudo apt update && sudo apt install wine32:i386"
else
    EXE="$SHIPPING"
    ARGS="$PENCERE_ARGS"
fi

if [ ! -f "$EXE" ]; then
    echo "HATA: Oyun bulunamadi: $EXE"
    echo "      Yarisma paketini repo kokune '$OYUN_DIZIN' klasoru olacak sekilde cikart (README)."
    exit 1
fi

echo "============================================================"
echo "  DRONES OF WAR - Wine ile baslatiliyor..."
echo "  Calistirilan: $EXE $ARGS"
echo "  Oyun acilinca PLAY moduna gecmeyi unutma."
echo "  Ardindan:  python3 -m control.main"
echo "============================================================"

cd "$(dirname "$EXE")"
wine "./$(basename "$EXE")" $ARGS &
