@echo off
chcp 65001 >nul
title Avci Drone - Arayuz (venv Python 3.12)
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [HATA] .venv bulunamadi. Once kurulum yapilmali.
    echo   py -3.12 -m venv .venv
    pause
    exit /b 1
)

echo ============================================================
echo   AVCI DRONE - YER KONTROL ISTASYONU  (venv Python 3.12)
echo ------------------------------------------------------------
echo   Tarayici: http://127.0.0.1:8000   (2 sn icinde acilir)
echo   Durdurmak icin: Ctrl + C
echo   NOT: Ayni anda TEK arayuz calissin (oyun tek baglanti kabul eder).
echo ============================================================
echo.

start "" /min cmd /c "timeout /t 2 /nobreak >nul & start """" http://127.0.0.1:8000"

".venv\Scripts\python.exe" main.py

echo.
echo Sunucu durdu. Cikmak icin bir tusa bas...
pause >nul
