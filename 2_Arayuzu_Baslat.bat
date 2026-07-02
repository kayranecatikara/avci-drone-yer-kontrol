@echo off
chcp 65001 >nul
title Avci Drone - Yer Kontrol Istasyonu
cd /d "%~dp0"

if not exist "main.py" (
    echo [HATA] main.py bulunamadi: "%CD%"
    echo Bu .bat dosyasi repo kokunde ^(avci-drone-yer-kontrol\^) durmali.
    echo.
    pause
    exit /b 1
)

REM Python komutunu sec (once "python", yoksa "py" launcher)
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
    where py >nul 2>nul && set "PY=py"
)
if not defined PY (
    echo [HATA] Python bulunamadi. Python 3.10-3.12 kurup PATH'e ekle.
    echo   https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo   AVCI DRONE - YER KONTROL ISTASYONU
echo ------------------------------------------------------------
echo   Sunucu baslatiliyor; tarayici otomatik acilacak.
echo   Bu pencereyi KAPATMA (sunucu burada calisiyor).
echo   Durdurmak icin: Ctrl + C
echo   NOT: Ayni anda TEK arayuz calissin; yeniden baslatmadan
echo        once eski pencereyi kapat (oyun tek baglanti kabul eder).
echo ============================================================
echo.

REM Tarayiciyi 2 sn sonra ac (sunucu ayaga kalksin), sonra sunucuyu baslat
start "" /min cmd /c "timeout /t 2 /nobreak >nul & start """" http://127.0.0.1:8000"

%PY% main.py

echo.
echo Sunucu durdu. Cikmak icin bir tusa bas...
pause >nul
