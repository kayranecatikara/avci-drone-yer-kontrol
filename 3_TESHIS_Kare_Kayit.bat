@echo off
chcp 65001 >nul
title Avci Drone - TESHIS (dedektor kare kayit)
cd /d "%~dp0"

if not exist "main.py" (
    echo [HATA] main.py bulunamadi: "%CD%"  -- bu .bat repo kokunde durmali.
    pause
    exit /b 1
)

REM TESHIS ANAHTARI: dedektorun gordugu kareleri kaydet (yakin hedefte).
set AVCI_KARE_KAYIT=1

set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY ( where py >nul 2>nul && set "PY=py" )
if not defined PY (
    echo [HATA] Python bulunamadi. Python 3.10-3.12 kurup PATH'e ekle.
    pause
    exit /b 1
)

echo ============================================================
echo   TESHIS MODU - KARE KAYIT ACIK
echo ------------------------------------------------------------
echo   Normal ucus gibi baslat: Gorev Baslat, Talon YAKINDAN gecsin.
echo   Hedef 25 m'den yakinken dedektorun gordugu kareler buraya:
echo       veri\kacan_kareler\
echo   Dosya adi: KACAN/TESPIT + mesafe + conf + COZUNURLUK (WxH)
echo   Ucustan sonra bu klasoru Claude'a ver -- model mi kor,
echo   canli kare mi bozuk KESIN anlasilir.
echo   Durdurmak icin: Ctrl + C
echo ============================================================
echo.

start "" /min cmd /c "timeout /t 2 /nobreak >nul & start """" http://127.0.0.1:8000"

%PY% main.py

echo.
echo Sunucu durdu. Cikmak icin bir tusa bas...
pause >nul
