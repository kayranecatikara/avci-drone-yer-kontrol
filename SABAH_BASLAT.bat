@echo off
chcp 65001 >nul
title AVCI - Sabah Devam
cd /d "%~dp0"

echo ============================================================
echo   SABAH DEVAM  --  gece kampanyasini kaldigi yerden surdur
echo ------------------------------------------------------------
echo   ONCE SEN: oyunda "PRESS FOR START" ekranini gec ve
echo             gorev basladiginda 'E' ile drone'u dogur.
echo             (Oyunun baslik ekrani sentetik tus kabul etmiyor;
echo              gece bunu deneyip basaramadim -- GECE_2026-08-17.md)
echo.
echo   Hazir oldugunda bu pencereye don ve bir tusa bas.
echo ============================================================
pause >nul

echo.
echo [1/3] Oyun baglantisi kontrol ediliyor (port 12345)...
powershell -NoProfile -Command "$ok=$false; try{ $c=New-Object System.Net.Sockets.TcpClient; $c.Connect('127.0.0.1',12345); $ok=$true; $c.Close() }catch{}; if($ok){ Write-Host '      OK - oyun gorevde' -ForegroundColor Green } else { Write-Host '      HAYIR - once oyunda goreve gir ve E ile drone dogur' -ForegroundColor Red; exit 1 }"
if errorlevel 1 (
  echo.
  echo   Oyun hazir degil. Goreve girip 'E' bastiktan sonra tekrar calistir.
  pause
  exit /b 1
)

echo [2/3] Eski surecler temizleniyor...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' -or $_.CommandLine -like '*kampanya*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 3 /nobreak >nul

echo [3/3] Kampanya baslatiliyor (K recetesi, 6 ayar x 11 dk, surekli dongu)...
echo.
echo   Sonuclar : veri\gece\kampanya_sonuc.csv
echo   Gunluk   : veri\gece\kampanya.log
echo   Ozet     : python arac\kampanya_ozet.py --iz
echo.
echo   Durdurmak icin: Ctrl+C
echo ============================================================
echo.

set AVCI_POSE=0
set AVCI_IZ_HZ=50
set AVCI_GIL_HIZLI=1
set AVCI_GPS_LOG_S=20
set AVCI_GPS_LOG_MAX=3000

python -u arac\kampanya.py --recete arac\recete_gece.json --dk 11 --tur 99

pause
