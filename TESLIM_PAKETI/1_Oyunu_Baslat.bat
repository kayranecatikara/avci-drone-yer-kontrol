@echo off
chcp 65001 >nul
title Drones of War - Oyunu Baslat
cd /d "%~dp0"

REM Oyunu iki olasi yerde ara:
REM   1) repo koku          : <repo>\Drones of War Teknofest\   (README standardi)
REM   2) repo'nun UST klasoru: ..\Drones of War Teknofest\      (alternatif duzen)
set "EXE=%~dp0Drones of War Teknofest\DronesOfWar.exe"
if not exist "%EXE%" set "EXE=%~dp0..\Drones of War Teknofest\DronesOfWar.exe"

if not exist "%EXE%" (
    echo [HATA] DronesOfWar.exe bulunamadi. Su iki yerden birinde olmali:
    echo    1^) %~dp0Drones of War Teknofest\
    echo    2^) %~dp0..\Drones of War Teknofest\
    echo.
    echo Oyun zip'ini README'deki Drive linkinden indirip repo kokune cikart.
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo   DRONES OF WAR - oyun baslatiliyor...
echo   %EXE%
echo ------------------------------------------------------------
echo   Oyun acilinca PLAY moduna gecmeyi unutma.
echo   (Mumkunse Ayarlar'dan PENCERELI / KENARLIKSIZ moda al.)
echo ============================================================

start "" "%EXE%"

timeout /t 3 /nobreak >nul
exit
