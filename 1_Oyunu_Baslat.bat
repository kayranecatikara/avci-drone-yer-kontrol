@echo off
chcp 65001 >nul
title Drones of War - Oyunu Baslat
cd /d "%~dp0"

echo ============================================================
echo   DRONES OF WAR - oyun baslatiliyor...
echo ------------------------------------------------------------
echo   Oyun acilinca PLAY moduna gecmeyi unutma.
echo   (Mumkunse Ayarlar'dan PENCERELI / KENARLIKSIZ moda al;
echo    ekran goruntusu yakalama icin daha saglikli olur.)
echo ============================================================

start "" "Drones of War Teknofest\DronesOfWar.exe"

timeout /t 3 /nobreak >nul
exit
