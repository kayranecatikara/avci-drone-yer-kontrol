#!/bin/bash
# GECE NOBETCISI: kampanya surecini ayakta tutar.
# Kampanya kendi icinde sunucuyu yonetiyor; bu nobetci YALNIZ kampanyayi izler.
# ⚠ Sunucuyu DOGRUDAN baslatma -- kampanyayla catisir (bu gece bir kez oldu:
#   iki main.py ayni anda kostu, oyun tek baglanti kabul ediyor).
cd "C:/Users/Zeylo/Desktop/avci-drone-yer-kontrol-kayran" || exit 1
while true; do
  n=$(powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -like '*kampanya*' } | Measure-Object).Count" 2>/dev/null | tr -d '\r')
  if [ "${n:-0}" -eq 0 ]; then
    echo "[NOBETCI] $(date +%H:%M:%S) kampanya YOK -> yeniden baslatiliyor"
    PYTHONIOENCODING=utf-8 python -u arac/kampanya.py --recete arac/recete_gece.json --dk 11 --tur 99 >> veri/gece/kampanya_stdout.log 2>&1 &
    sleep 60
  fi
  sleep 45
done
