@echo off
chcp 65001 >nul
title Avci Drone - Yer Kontrol Istasyonu
cd /d "%~dp0"

echo ============================================================
echo   AVCI DRONE - YER KONTROL ISTASYONU
echo ------------------------------------------------------------
echo   Sunucu baslatiliyor, ardindan tarayici acilacak...
echo   Bu pencereyi KAPATMA (sunucu burada calisiyor).
echo   Durdurmak icin: bu pencerede Ctrl + C
echo ============================================================

REM Once sunucuyu baslat (2 saniye sonra tarayiciyi ac)
start "" /min cmd /c "timeout /t 2 /nobreak >nul & start """" http://127.0.0.1:8000"

python server.py

echo.
echo Sunucu durdu. Cikmak icin bir tusa bas...
pause >nul
