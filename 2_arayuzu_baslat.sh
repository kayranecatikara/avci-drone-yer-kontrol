#!/usr/bin/env bash
# ============================================================
#  AVCI DRONE - YER KONTROL ISTASYONU (Ubuntu/Linux)
# ------------------------------------------------------------
#  Windows .bat karsiligi. Python sunucusunu baslatir ve
#  tarayiciyi acar. Bu pencereyi KAPATMA (sunucu burada calisir).
#  Durdurmak icin: Ctrl + C
# ============================================================
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
URL="http://127.0.0.1:8000"

echo "============================================================"
echo "  AVCI DRONE - YER KONTROL ISTASYONU"
echo "  Sunucu baslatiliyor, ardindan tarayici acilacak..."
echo "  Durdurmak icin: Ctrl + C"
echo "============================================================"

# Sunucu ayaga kalksin, sonra tarayiciyi ac (arka planda)
( sleep 2; xdg-open "$URL" >/dev/null 2>&1 || echo "Tarayici otomatik acilmadi: $URL" ) &

exec "$PY" server.py
